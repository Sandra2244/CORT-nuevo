"""Abrir aplicaciones y sitios con allowlist: nunca se ejecuta texto libre del usuario."""

from __future__ import annotations

import os
import shlex
import subprocess

from ..text import normalizar

SITIOS = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "whatsapp": "https://web.whatsapp.com",
    "netflix": "https://www.netflix.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "spotify": "https://open.spotify.com",
}


def _lanzar(cmd: str) -> None:
    cmd = os.path.expandvars(os.path.expanduser(cmd))
    subprocess.Popen(
        shlex.split(cmd),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def abrir(ctx, nombre: str) -> str:
    pedido = normalizar(nombre)
    if not pedido:
        return "¿Qué querés que abra? Decime el nombre de la aplicación."

    apps = ctx.cfg.apps
    for clave, cmd in apps.items():
        clave_n = normalizar(clave)
        if pedido == clave_n or pedido.startswith(clave_n) or clave_n.startswith(pedido):
            try:
                _lanzar(cmd)
                ctx.log(f"app · {clave}")
                return f"Abrí {clave}."
            except Exception as exc:  # noqa: BLE001
                return f"No pude abrir {clave}: {type(exc).__name__}. Revisá que esté instalada."

    for sitio, url in SITIOS.items():
        if pedido == sitio or pedido.startswith(sitio):
            try:
                _lanzar(f"xdg-open {url}")
                ctx.log(f"web · {sitio}")
                return f"Abrí {sitio} en el navegador."
            except Exception as exc:  # noqa: BLE001
                return f"No pude abrir el navegador: {type(exc).__name__}."

    disponibles = ", ".join(sorted(apps)) + ", " + ", ".join(sorted(SITIOS))
    return f"No tengo «{nombre}» en la lista permitida. Puedo abrir: {disponibles}."
