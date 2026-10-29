"""Conocimiento local: lee knowledge/*.md y *.txt sin embeddings."""

from __future__ import annotations

import time
from pathlib import Path

from ..text import normalizar, recortar

_CACHE: dict[str, tuple[float, list[dict]]] = {}
_EXT = {".md", ".txt", ".rst"}
_IGNORAR = {"readme.md"}


def _parrafos(archivo: Path) -> list[dict]:
    try:
        texto = archivo.read_text(encoding="utf-8", errors="ignore")[:200_000]
    except Exception:  # noqa: BLE001
        return []
    bloques = [b.strip() for b in texto.split("\n\n") if b.strip()]
    return [{"archivo": archivo.name, "texto": b} for b in bloques if len(b) > 40]


def _indice(ctx) -> list[dict]:
    carpeta = Path(ctx.cfg.conocimiento_dir)
    clave = str(carpeta)
    ahora = time.time()
    if clave in _CACHE and ahora - _CACHE[clave][0] < 30:
        return _CACHE[clave][1]
    datos: list[dict] = []
    if carpeta.is_dir():
        for archivo in sorted(carpeta.iterdir()):
            if archivo.suffix.lower() in _EXT and archivo.name.lower() not in _IGNORAR:
                datos.extend(_parrafos(archivo))
    _CACHE[clave] = (ahora, datos)
    return datos


def _puntuar(tema: str, parrafo: str) -> float:
    palabras = [p for p in normalizar(tema).split() if len(p) > 2]
    if not palabras:
        return 0.0
    texto = normalizar(parrafo)
    return sum(1 for p in palabras if p in texto) / len(palabras)


def buscar(ctx, tema: str, limite: int = 3) -> str:
    tema = (tema or "").strip()
    if not tema:
        return "¿Sobre qué querés que consulte en tus apuntes?"
    indice = _indice(ctx)
    if not indice:
        return (
            "No hay apuntes en la carpeta knowledge/. Poné archivos .md o .txt ahí y los leo."
        )
    puntuados = sorted(
        ((_puntuar(tema, p["texto"]), p) for p in indice), key=lambda x: x[0], reverse=True
    )
    mejores = [(s, p) for s, p in puntuados if s > 0][:limite]
    if not mejores:
        return f"No encontré «{tema}» en mis apuntes."
    partes = [f"[{p['archivo']}] {recortar(p['texto'], 420)}" for _, p in mejores]
    ctx.log(f"conocimiento · {tema} · {len(mejores)} fragmento(s)")
    return "Encontré esto en tus apuntes:\n" + "\n\n".join(partes)


def contexto(ctx, tema: str, limite: int = 2) -> str:
    indice = _indice(ctx)
    if not indice or not tema:
        return ""
    puntuados = sorted(
        ((_puntuar(tema, p["texto"]), p) for p in indice), key=lambda x: x[0], reverse=True
    )
    mejores = [p for s, p in puntuados if s >= 0.34][:limite]
    if not mejores:
        return ""
    return "\n\n".join(f"[{p['archivo']}] {recortar(p['texto'], 500)}" for p in mejores)
