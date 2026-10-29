"""Hora y fecha del sistema. Nunca se inventan."""

from __future__ import annotations

from datetime import datetime

from ..text import fecha_larga, hora_larga


def hora(ctx=None) -> str:
    ahora = datetime.now()
    return f"Son las {hora_larga(ahora)} ({ahora.strftime('%H:%M:%S')})."


def fecha(ctx=None) -> str:
    ahora = datetime.now()
    return f"Hoy es {fecha_larga(ahora)}."
