"""Búsquedas web abriendo el navegador. No bloquea ni inventa resultados."""

from __future__ import annotations

import subprocess
import webbrowser
from urllib.parse import quote_plus

from ..text import recortar


def _abrir(url: str) -> bool:
    try:
        if webbrowser.open(url):
            return True
    except Exception:  # noqa: BLE001
        pass
    try:
        subprocess.Popen(
            ["xdg-open", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def buscar(ctx, consulta: str, motor: str = "google") -> str:
    consulta = recortar((consulta or "").strip(), 200)
    if not consulta:
        return "¿Qué querés que busque?"
    motor = (motor or "google").lower()
    if motor == "youtube":
        url = f"https://www.youtube.com/results?search_query={quote_plus(consulta)}"
        nombre = "YouTube"
    else:
        url = f"https://www.google.com/search?q={quote_plus(consulta)}"
        nombre = "Google"
    if not _abrir(url):
        return f"No pude abrir el navegador para buscar «{consulta}». La URL era: {url}"
    ctx.log(f"buscar · {nombre} · {recortar(consulta, 40)}")
    return f"Busqué «{consulta}» en {nombre}."
