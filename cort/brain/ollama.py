"""Cliente mínimo de Ollama para CORT."""

from __future__ import annotations

import json
import re
import threading
from typing import Callable

import requests

from ..text import recortar

_RE_MODELO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}$")

# Tamaños aproximados de descarga; el tamaño real lo confirma /api/pull.
RECOMENDADOS = [
    {"nombre": "qwen2.5:0.5b", "gb": 0.4, "ram_gb": 1.0, "nota": "el más liviano; español aceptable"},
    {"nombre": "qwen3:0.6b", "gb": 0.5, "ram_gb": 1.2, "nota": "razona algo mejor; arranque rápido"},
    {"nombre": "gemma3:1b", "gb": 0.8, "ram_gb": 1.6, "nota": "buen español para su tamaño"},
    {"nombre": "llama3.2:1b", "gb": 1.3, "ram_gb": 2.0, "nota": "más contexto, más lento en 2 núcleos"},
]


class _Progreso:
    """Suma el avance de todas las capas que Ollama va anunciando."""

    def __init__(self) -> None:
        self.capas: dict[str, tuple[int, int]] = {}
        self.estado = ""
        self.terminado = False

    def absorber(self, dato: dict) -> dict:
        estado = str(dato.get("status") or "").strip()
        if estado:
            self.estado = estado
        if estado in ("success", "verifying sha256 digest", "writing manifest"):
            self.terminado = estado == "success"
        try:
            total = int(dato.get("total") or 0)
            completado = int(dato.get("completed") or 0)
        except (TypeError, ValueError):
            total, completado = 0, 0
        if total > 0:
            clave = str(dato.get("digest") or estado or "capa")
            self.capas[clave] = (max(0, min(completado, total)), total)
        suma_total = sum(t for _, t in self.capas.values())
        suma_completado = sum(c for c, _ in self.capas.values())
        if self.terminado:
            porcentaje = 100.0
        elif suma_total > 0:
            porcentaje = round(suma_completado * 100 / suma_total, 1)
        else:
            porcentaje = None
        return {
            "estado": self.estado,
            "completado": suma_completado,
            "total": suma_total,
            "porcentaje": porcentaje,
            "capas": len(self.capas),
            "terminado": self.terminado,
        }


class Ollama:
    def __init__(self, cfg):
        self.url = str(cfg.get("cerebro.url", "http://127.0.0.1:11434")).rstrip("/")
        self.modelo = str(cfg.get("cerebro.modelo", "qwen3:0.6b"))
        self.respaldo = str(cfg.get("cerebro.respaldo", "qwen2.5:0.5b"))
        self.profundo = str(cfg.get("cerebro.modelo_profundo", "qwen3.5:2b"))
        self.temperatura = float(cfg.get("cerebro.temperatura", 0.6))
        self.num_ctx = int(cfg.get("cerebro.num_ctx", 2048))
        self.num_predict = int(cfg.get("cerebro.num_predict", 220))
        self.timeout = float(cfg.get("cerebro.timeout_s", 60))
        self.mantener = str(cfg.get("cerebro.mantener", "5m"))
        self.ultimo_error = ""
        self.cancelado = False
        self._turno = threading.Event()
        self._lock = threading.RLock()
        self._pull_lock = threading.Lock()
        self._pull_resp = None
        self._cancelar = threading.Event()

    # --- cancelación del turno -----------------------------------------
    def cancelar_turno(self) -> None:
        """Pide al stream de /api/chat que corte en la próxima línea."""
        self._turno.set()

    def limpiar_cancelacion(self) -> None:
        self._turno.clear()
        self.cancelado = False

    # --- estado ---------------------------------------------------------
    def disponible(self) -> bool:
        try:
            r = requests.get(f"{self.url}/api/tags", timeout=5)
            ok = r.status_code == 200
            self.ultimo_error = "" if ok else f"HTTP {r.status_code}"
            return ok
        except Exception as exc:  # noqa: BLE001
            self.ultimo_error = type(exc).__name__
            return False

    def modelos(self) -> list[str]:
        try:
            r = requests.get(f"{self.url}/api/tags", timeout=5)
            if r.status_code != 200:
                return []
            return [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
        except Exception:  # noqa: BLE001
            return []

    def modelos_info(self) -> list[dict]:
        """Modelos instalados con tamaño y familia; lista vacía si Ollama no responde."""
        try:
            r = requests.get(f"{self.url}/api/tags", timeout=5)
            if r.status_code != 200:
                self.ultimo_error = f"HTTP {r.status_code}"
                return []
            datos = r.json()
            self.ultimo_error = ""
        except Exception as exc:  # noqa: BLE001
            self.ultimo_error = type(exc).__name__
            return []
        salida: list[dict] = []
        for m in datos.get("models", []):
            nombre = str(m.get("name") or "").strip()
            if not nombre:
                continue
            detalles = m.get("details") or {}
            try:
                gigas = round(float(m.get("size") or 0) / (1024 ** 3), 2)
            except (TypeError, ValueError):
                gigas = 0.0
            salida.append(
                {
                    "nombre": nombre,
                    "tamano_gb": gigas,
                    "modificado": str(m.get("modified_at") or ""),
                    "familia": str(detalles.get("family") or ""),
                    "parametros": str(detalles.get("parameter_size") or ""),
                    "cuantizacion": str(detalles.get("quantization_level") or ""),
                }
            )
        return salida

    @staticmethod
    def nombre_valido(nombre: str) -> bool:
        return bool(_RE_MODELO.fullmatch((nombre or "").strip()))

    def cancelar_descarga(self) -> bool:
        """Corta el /api/pull en curso. Ollama abandona la descarga al cerrar la conexión."""
        self._cancelar.set()
        with self._pull_lock:
            r = self._pull_resp
        if r is None:
            return False
        try:
            r.close()
        except Exception:  # noqa: BLE001
            pass
        return True

    def descargar(self, nombre: str, al_progreso: Callable[[dict], None] | None = None) -> dict:
        """Descarga un modelo con /api/pull y reporta el avance línea a línea.

        Agrupa el progreso por capa (Ollama manda una línea por blob) y permite
        cancelar cerrando la respuesta. No hay shell de por medio: el nombre se
        valida y viaja en el JSON de Ollama.
        """
        nombre = (nombre or "").strip()
        if not self.nombre_valido(nombre):
            return {"ok": False, "error": "Nombre de modelo inválido; probá con qwen3:0.6b."}
        self._cancelar.clear()
        try:
            r = requests.post(
                f"{self.url}/api/pull",
                json={"model": nombre, "stream": True},
                stream=True,
                timeout=(5, 120),
            )
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        with self._pull_lock:
            self._pull_resp = r
        if r.status_code != 200:
            detalle = recortar(getattr(r, "text", ""), 300)
            self._limpiar_pull()
            try:
                r.close()
            except Exception:  # noqa: BLE001
                pass
            return {"ok": False, "error": f"HTTP {r.status_code}: {detalle}".strip()}
        acumulado = _Progreso()
        try:
            for linea in r.iter_lines(decode_unicode=True):
                if self._cancelar.is_set():
                    return {"ok": False, "cancelado": True, "error": "Descarga cancelada."}
                if not linea:
                    continue
                if isinstance(linea, bytes):
                    linea = linea.decode("utf-8", "replace")
                try:
                    dato = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                if dato.get("error"):
                    return {"ok": False, "error": str(dato["error"])}
                avance = acumulado.absorber(dato)
                if al_progreso:
                    al_progreso(avance)
            if self._cancelar.is_set():
                return {"ok": False, "cancelado": True, "error": "Descarga cancelada."}
            return {"ok": True, "modelo": nombre, "estado": acumulado.estado or "completado"}
        except Exception as exc:  # noqa: BLE001
            if self._cancelar.is_set():
                return {"ok": False, "cancelado": True, "error": "Descarga cancelada."}
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        finally:
            self._limpiar_pull()
            try:
                r.close()
            except Exception:  # noqa: BLE001
                pass

    def _limpiar_pull(self) -> None:
        with self._pull_lock:
            self._pull_resp = None
        self._cancelar.clear()

    def elegir_modelo(self) -> str:
        """Prefiere el configurado; si no está, el respaldo o el más pequeño disponible."""
        with self._lock:
            disponibles = self.modelos()
            if not disponibles:
                return ""
            for candidato in (self.modelo, self.respaldo, self.profundo):
                if candidato in disponibles:
                    self.modelo = candidato
                    return candidato
            # coincidencia por familia (por si el tag exacto cambia)
            for candidato in (self.modelo, self.respaldo):
                familia = candidato.split(":")[0]
                for nombre in disponibles:
                    if nombre.startswith(familia):
                        self.modelo = nombre
                        return nombre
            for nombre in disponibles:
                if any(t in nombre for t in ("135m", "0.5b", "0.6b", "1b", "1.5b", "2b", "3b")):
                    self.modelo = nombre
                    return nombre
            self.modelo = disponibles[0]
            return self.modelo

    # --- conversación ---------------------------------------------------
    def conversar(
        self,
        mensajes: list[dict],
        al_token: Callable[[str], None] | None = None,
        modelo: str | None = None,
        num_predict: int | None = None,
    ) -> str:
        modelo = modelo or self.modelo
        if not modelo:
            modelo = self.elegir_modelo()
        if not modelo:
            self.ultimo_error = "sin modelo"
            return ""
        cuerpo = {
            "model": modelo,
            "messages": mensajes,
            "stream": True,
            "keep_alive": self.mantener,
            "options": {
                "temperature": self.temperatura,
                "num_ctx": self.num_ctx,
                "num_predict": int(num_predict or self.num_predict),
            },
        }
        try:
            r = requests.post(
                f"{self.url}/api/chat",
                json=cuerpo,
                stream=True,
                timeout=(5, self.timeout),
            )
        except Exception as exc:  # noqa: BLE001
            self.ultimo_error = f"{type(exc).__name__}: {exc}"
            return ""
        if r.status_code != 200:
            detalle = recortar(r.text, 300)
            self.ultimo_error = f"HTTP {r.status_code}: {detalle}"
            if r.status_code == 404:
                # el modelo configurado no está: elegir otro y reintentar una vez
                nuevo = self.elegir_modelo()
                if nuevo and nuevo != modelo:
                    return self.conversar(
                        mensajes, al_token=al_token, modelo=nuevo, num_predict=num_predict
                    )
            return ""
        partes: list[str] = []
        try:
            for linea in r.iter_lines(decode_unicode=True):
                if self._turno.is_set():
                    self.cancelado = True
                    break
                if not linea:
                    continue
                try:
                    dato = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                texto = (dato.get("message") or {}).get("content") or ""
                if texto:
                    partes.append(texto)
                    if al_token:
                        al_token(texto)
                if dato.get("error"):
                    self.ultimo_error = str(dato["error"])
        finally:
            cerrar = getattr(r, "close", None)
            if callable(cerrar):
                try:
                    cerrar()
                except Exception:  # noqa: BLE001
                    pass
        if self._turno.is_set():
            self.cancelado = True
        respuesta = "".join(partes).strip()
        if not respuesta and not self.cancelado:
            self.ultimo_error = self.ultimo_error or "respuesta vacía"
        return respuesta
