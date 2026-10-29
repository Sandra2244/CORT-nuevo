"""Utilidades de texto: normalización, extracción de horas y similitud."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta

_RE_NO_ALFA = re.compile(r"[^a-z0-9ñ :]+")
_RE_ESPACIOS = re.compile(r"\s+")

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
DIAS = [
    "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo",
]


def sin_tildes(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def normalizar(texto: str) -> str:
    texto = sin_tildes(str(texto or "").lower())
    texto = _RE_NO_ALFA.sub(" ", texto)
    return _RE_ESPACIOS.sub(" ", texto).strip()


def tokens(texto: str) -> list[str]:
    return [t for t in normalizar(texto).split() if len(t) > 2]


def contiene(normalizado: str, *frases: str) -> bool:
    """Coincidencia por palabra/frase completa: «ram» no debe activarse en «programa»."""
    for frase in frases:
        if re.search(r"(?<!\w)" + re.escape(frase) + r"(?!\w)", normalizado):
            return True
    return False


def despues_de(normalizado: str, *marcas: str) -> str:
    """Devuelve lo que hay tras la primera marca encontrada (texto normalizado)."""
    for marca in marcas:
        pos = normalizado.find(marca)
        if pos >= 0:
            return normalizado[pos + len(marca):].strip(" ,.;:¡!¿?")
    return ""


def antes_de(normalizado: str, marca: str) -> str:
    pos = normalizado.find(marca)
    return normalizado[:pos].strip(" ,.;:¡!¿?") if pos >= 0 else normalizado


def fecha_larga(momento: datetime | None = None) -> str:
    m = momento or datetime.now()
    return f"{DIAS[m.weekday()]} {m.day} de {MESES[m.month - 1]} de {m.year}"


def hora_larga(momento: datetime | None = None) -> str:
    m = momento or datetime.now()
    h12 = m.hour % 12 or 12
    if m.hour < 6:
        sufijo = "de la madrugada"
    elif m.hour < 12:
        sufijo = "de la mañana"
    elif m.hour < 19:
        sufijo = "de la tarde"
    else:
        sufijo = "de la noche"
    return f"{h12}:{m.minute:02d} {sufijo}"


def hora_desde_texto(normalizado: str, ahora: datetime | None = None) -> tuple[int, int] | None:
    """Extrae una hora de frases como '6:30', '6 y media', 'a las 6 pm', '18:30'."""
    ahora = ahora or datetime.now()
    m = re.search(r"\b(\d{1,2})[:.](\d{2})\b", normalizado)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\b(\d{1,2})\s+y\s+(media|cuarto)\b", normalizado)
    if m:
        return int(m.group(1)), 30 if m.group(2) == "media" else 15
    m = re.search(r"\b(\d{1,2})\s*(am|pm|a m|p m)\b", normalizado)
    if m:
        hora = int(m.group(1))
        sufijo = m.group(2).replace(" ", ".")
        if sufijo == "pm" and hora < 12:
            hora += 12
        if sufijo == "am" and hora == 12:
            hora = 0
        return hora, 0
    m = re.search(r"\ba\s+las?\s+(\d{1,2})\b", normalizado)
    if m:
        return int(m.group(1)), 0
    m = re.search(r"\b(\d{1,2})\s+de\s+la\s+(manana|tarde|noche|madrugada)\b", normalizado)
    if m:
        hora = int(m.group(1))
        parte = m.group(2)
        if parte in ("tarde", "noche") and hora < 12:
            hora += 12
        if parte == "madrugada" and hora == 12:
            hora = 0
        return hora, 0
    return None


def proxima_ocurrencia(hora: int, minuto: int, ahora: datetime | None = None) -> datetime:
    ahora = ahora or datetime.now()
    objetivo = ahora.replace(hour=hora % 24, minute=minuto % 60, second=0, microsecond=0)
    if objetivo <= ahora + timedelta(seconds=30):
        objetivo += timedelta(days=1)
    return objetivo


def similitud(a: str, b: str) -> float:
    ta, tb = set(tokens(a)), set(tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def recortar(texto: str, limite: int = 280) -> str:
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"
