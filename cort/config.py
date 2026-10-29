"""Configuración de CORT: TOML con valores por defecto sensatos."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent

DEFAULTS: dict[str, Any] = {
    "nombre": {"wake": ["cort", "sofi"], "usuario": ""},
    "cerebro": {
        "url": "http://127.0.0.1:11434",
        "modelo": "qwen3:0.6b",
        "respaldo": "qwen2.5:0.5b",
        "modelo_profundo": "qwen3.5:2b",
        "temperatura": 0.6,
        "num_ctx": 4096,
        "num_predict": 256,
        "timeout_s": 240,
        "mantener": "5m",
        "historial_mensajes": 8,
        "historial_caracteres": 2400,
    },
    "voz": {
        "tts": True,
        "motor": "espeak-ng",
        "voz": "es-mx+f3",
        "velocidad": 165,
        "tono": 52,
        "stt": True,
        "modelo_vosk": "",
        "silencio_s": 1.0,
    },
    "hud": {
        "host": "127.0.0.1",
        "puerto": 8765,
        "abrir": "auto",  # auto | webview | navegador | ninguno
        "fps": 30,
        "particulas": "auto",  # auto | alto | medio | bajo
    },
    "sistema": {"avisos": True, "cpu_max": 85, "ram_max": 90},
    "clima": {"cache_min": 10, "ciudad": ""},
    "arnes": {"auto": False, "max_pasos": 3},
    "apps": {
        "calculadora": "galculator",
        "archivos": "thunar $HOME",
        "navegador": "xdg-open https://www.google.com",
        "editor": "featherpad",
        "terminal": "x-terminal-emulator",
        "vscodium": "codium",
        "geany": "geany",
        "vlc": "vlc",
        "musica": "cvlc --intf dummy --play-and-exit $HOME/Música",
    },
    "rutas": {
        "datos": "~/.local/share/cort",
        "conocimiento": "knowledge",
        "playlists": "~/Música",
    },
}


def _fusionar(base: dict, extra: dict) -> dict:
    salida = dict(base)
    for clave, valor in extra.items():
        if isinstance(valor, dict) and isinstance(salida.get(clave), dict):
            salida[clave] = _fusionar(salida[clave], valor)
        else:
            salida[clave] = valor
    return salida


class Config:
    """Acceso por ruta con puntos: cfg.get('hud.puerto', 8765)."""

    def __init__(self, raw: dict | None = None, raiz: Path | None = None):
        self.raiz = Path(raiz or RAIZ)
        self._d = _fusionar(DEFAULTS, raw or {})
        datos = os.environ.get("CORT_HOME", self.get("rutas.datos"))
        self.datos_dir = Path(os.path.expandvars(os.path.expanduser(datos)))
        self.datos_dir.mkdir(parents=True, exist_ok=True)
        conoc = Path(os.path.expanduser(str(self.get("rutas.conocimiento"))))
        self.conocimiento_dir = conoc if conoc.is_absolute() else self.raiz / conoc
        listas = Path(os.path.expanduser(str(self.get("rutas.playlists"))))
        self.playlists_dir = listas
        self.db_path = self.datos_dir / "cort.db"

    # --- acceso ---------------------------------------------------------
    def get(self, ruta: str, default: Any = None) -> Any:
        actual: Any = self._d
        for parte in ruta.split("."):
            if not isinstance(actual, dict) or parte not in actual:
                return default
            actual = actual[parte]
        return actual

    def set(self, ruta: str, valor: Any) -> None:
        partes = ruta.split(".")
        actual = self._d
        for parte in partes[:-1]:
            actual = actual.setdefault(parte, {})
        actual[partes[-1]] = valor

    @property
    def wake(self) -> list[str]:
        valor = self.get("nombre.wake", ["cort"])
        if isinstance(valor, str):
            return [valor]
        return [str(v).lower() for v in valor]

    @property
    def apps(self) -> dict[str, str]:
        return dict(self.get("apps", {}))

    # --- carga ----------------------------------------------------------
    @classmethod
    def cargar(cls, ruta: Path | None = None) -> "Config":
        raiz = RAIZ
        candidatas = []
        if ruta:
            candidatas.append(Path(ruta))
        env = os.environ.get("CORT_CONFIG")
        if env:
            candidatas.append(Path(env))
        candidatas.append(raiz / "config" / "cort.toml")
        for c in candidatas:
            if c.is_file():
                with c.open("rb") as fh:
                    return cls(tomllib.load(fh), raiz=raiz)
        return cls(raiz=raiz)

    def describir(self) -> str:
        return (
            f"datos={self.datos_dir} · db={self.db_path}\n"
            f"conocimiento={self.conocimiento_dir} · playlists={self.playlists_dir}\n"
            f"modelo={self.get('cerebro.modelo')} · hud={self.get('hud.host')}:"
            f"{self.get('hud.puerto')}"
        )
