"""Punto de entrada de CORT."""

from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

from . import __version__
from .app import Cort
from .config import Config


def _bucle_voz(app: Cort, parar: threading.Event) -> None:
    claves = app.cfg.wake
    while not parar.is_set():
        try:
            clave, resto = app.stt.escuchar_palabra(claves)
        except Exception:  # noqa: BLE001
            time.sleep(1)
            continue
        if not clave:
            continue
        app.bus.log(f"voz · activación «{clave}»")
        if resto:
            app.responder(resto)
        else:
            texto = app.stt.escuchar()
            if texto:
                app.responder(texto)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cort", description="CORT, asistente personal local")
    parser.add_argument("--hud", action="store_true", help="abre el HUD y el servidor local")
    parser.add_argument("--once", metavar="TEXTO", help="responde una sola frase y sale")
    parser.add_argument("--doctor", action="store_true", help="diagnóstico del entorno")
    parser.add_argument("--voz", action="store_true", help="activa la escucha por palabra clave")
    parser.add_argument("--sin-voz", action="store_true", help="no habla en voz alta")
    parser.add_argument("--no-abrir", action="store_true", help="no abre ventana; solo imprime la URL")
    parser.add_argument("--puerto", type=int, help="puerto del HUD (por defecto 8765)")
    parser.add_argument("--config", type=Path, help="ruta alternativa de cort.toml")
    parser.add_argument("--version", action="store_true", help="muestra la versión")
    args = parser.parse_args(argv)

    cfg = Config.cargar(args.config)
    if args.puerto:
        cfg.set("hud.puerto", args.puerto)
    if args.no_abrir:
        cfg.set("hud.abrir", "ninguno")

    if args.version:
        print(f"CORT {__version__}")
        return 0
    if args.doctor:
        from .doctor import diagnostico

        return diagnostico(cfg)

    app = Cort(cfg, voz=not args.sin_voz and not args.once)
    app.iniciar()
    servidor = None
    parar_voz = threading.Event()
    try:
        if args.once is not None:
            print(app.responder(args.once)["respuesta"])
            return 0

        if args.hud:
            from .hud.server import Servidor, abrir_hud

            servidor = Servidor(app)
            url = servidor.iniciar()
            print(f"CORT · HUD en {url}  (Ctrl+C para salir)")
            if args.voz and app.stt.disponible:
                threading.Thread(
                    target=_bucle_voz, args=(app, parar_voz), daemon=True, name="cort-wake"
                ).start()
            bloquea = abrir_hud(url, str(cfg.get("hud.abrir", "auto")))
            if bloquea:
                return 0
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                return 0

        print(f"CORT v{__version__} · asistente local")
        print("Escribí «ayuda» para ver los comandos o «salir» para terminar.")
        if args.voz:
            if app.stt.disponible:
                threading.Thread(
                    target=_bucle_voz, args=(app, parar_voz), daemon=True, name="cort-wake"
                ).start()
                print("Escucha activa: decí «CORT» o «Sofi».")
            else:
                print(f"Escucha no disponible: {app.stt.motivo}.")
        while True:
            try:
                texto = input("tú › ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if texto.lower() in {"salir", "exit", "quit", "adios"}:
                break
            if not texto:
                continue
            respuesta = app.responder(texto)
            print(f"CORT › {respuesta['respuesta']}")
            if app._apagar:
                break
        return 0
    finally:
        parar_voz.set()
        if servidor is not None:
            servidor.detener()
        app.cerrar()


if __name__ == "__main__":
    sys.exit(main())
