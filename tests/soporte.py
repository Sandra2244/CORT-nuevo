"""Ayudas comunes para las pruebas: configuración aislada y dobles de prueba."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

from cort.brain.memory import Memoria
from cort.bus import Bus
from cort.config import Config
from cort.tools.base import Contexto

RAIZ = Path(__file__).resolve().parent.parent


def config_de_prueba(base: Path, **extra) -> Config:
    """Config con rutas dentro de `base` y sin voz, sin depender del entorno real."""
    raw: dict = {
        "rutas": {
            "datos": str(base / "datos"),
            "conocimiento": str(base / "knowledge"),
            "playlists": str(base / "musica"),
        },
        "voz": {"tts": False, "stt": False},
        "hud": {"puerto": 0},
    }
    for seccion, valores in extra.items():
        if isinstance(valores, dict):
            raw.setdefault(seccion, {})
            raw[seccion].update(valores)
        else:
            raw[seccion] = valores
    # CORT_HOME tiene prioridad sobre rutas.datos; en pruebas debe mandar `base`.
    with mock.patch.dict(os.environ):
        os.environ.pop("CORT_HOME", None)
        return Config(raw, raiz=RAIZ)


def contexto_de_prueba(base: Path, **extra) -> Contexto:
    cfg = config_de_prueba(base, **extra)
    memoria = Memoria(cfg.db_path)
    # En pruebas no hace falta durabilidad; sin esto cada commit espera al disco.
    memoria._db.execute("PRAGMA synchronous=OFF")
    memoria._db.execute("PRAGMA journal_mode=MEMORY")
    bus = Bus()
    return Contexto(cfg, memoria, bus)


class RespuestaFalsa:
    """Imita lo justo de requests.Response."""

    def __init__(self, datos: dict, codigo: int = 200):
        self._datos = datos
        self.status_code = codigo
        self.text = str(datos)

    def json(self) -> dict:
        return self._datos
