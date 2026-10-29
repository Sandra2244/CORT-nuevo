"""Estado compartido entre el núcleo, el HUD y la voz."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field


@dataclass
class Mensaje:
    rol: str
    texto: str
    ts: float = field(default_factory=time.time)
    herramienta: str = ""
    ms: int = 0

    def como_dict(self) -> dict:
        d = asdict(self)
        d["ts"] = round(self.ts, 3)
        return d


class Bus:
    def __init__(self, max_mensajes: int = 40, max_log: int = 60):
        self._lock = threading.RLock()
        self._estado = "idle"
        self._mensajes: deque[Mensaje] = deque(maxlen=max_mensajes)
        self._log: deque[str] = deque(maxlen=max_log)
        self._metricas: dict = {}
        self._flags = {
            "silencio": False,
            "voz_activa": False,
            "ollama_ok": False,
            "modelo": "",
            "ultima_herramienta": "",
        }
        self._eventos: deque[dict] = deque(maxlen=30)
        self._evento_id = 0
        self._version = 0

    # --- escritura ------------------------------------------------------
    def estado(self, valor: str) -> None:
        with self._lock:
            self._estado = valor

    def log(self, linea: str) -> None:
        with self._lock:
            self._log.append(f"{time.strftime('%H:%M:%S')}  {linea}")
            self._version += 1

    def mensaje(self, rol: str, texto: str, herramienta: str = "", ms: int = 0) -> Mensaje:
        m = Mensaje(rol=rol, texto=texto, herramienta=herramienta, ms=ms)
        with self._lock:
            self._mensajes.append(m)
            self._version += 1
        return m

    def metricas(self, datos: dict) -> None:
        with self._lock:
            self._metricas = dict(datos)

    def flag(self, clave: str, valor) -> None:
        with self._lock:
            self._flags[clave] = valor
            self._version += 1

    def evento(self, tipo: str, etiqueta: str = "", detalle: dict | None = None) -> dict:
        """Marca una acción para que el HUD la anime (ejecución, alarma, descarga).

        `detalle` viaja al panel de actividad: herramienta, argumentos recortados,
        duración y resultado. Debe ser pequeño y sin datos sensibles.
        """
        with self._lock:
            self._evento_id += 1
            dato = {
                "id": self._evento_id,
                "tipo": str(tipo or "evento"),
                "etiqueta": str(etiqueta or ""),
                "ts": round(time.time(), 3),
                "detalle": dict(detalle or {}),
            }
            self._eventos.append(dato)
            self._version += 1
            return dict(dato)

    # --- lectura --------------------------------------------------------
    def instantanea(self) -> dict:
        with self._lock:
            return {
                "estado": self._estado,
                "mensajes": [m.como_dict() for m in self._mensajes],
                "log": list(self._log),
                "metricas": dict(self._metricas),
                "flags": dict(self._flags),
                "evento": dict(self._eventos[-1]) if self._eventos else {},
                "eventos": [dict(e) for e in self._eventos],
                "version": self._version,
            }

    def estado_actual(self) -> str:
        with self._lock:
            return self._estado

    def historial(self, limite: int = 8) -> list[dict]:
        with self._lock:
            return [{"role": m.rol, "content": m.texto} for m in list(self._mensajes)[-limite:]]
