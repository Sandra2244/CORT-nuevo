"""Diagnóstico del entorno de CORT."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import psutil


def _marca(ok: bool) -> str:
    return "✓" if ok else "✗"


def diagnostico(cfg) -> int:
    filas: list[tuple[bool, str]] = []

    version_ok = sys.version_info >= (3, 11)
    filas.append((version_ok, f"Python {sys.version.split()[0]} (se requiere 3.11+)"))

    for modulo in ("psutil", "requests"):
        filas.append((importlib.util.find_spec(modulo) is not None, f"módulo {modulo}"))

    for binario, etiqueta in (
        ("espeak-ng", "voz espeak-ng"),
        ("arecord", "micrófono arecord"),
        ("cvlc", "reproductor VLC"),
        ("pactl", "volumen pactl"),
        ("xdg-open", "abrir apps/URLs"),
        ("notify-send", "notificaciones"),
        ("playerctl", "control MPRIS (opcional)"),
    ):
        ruta = shutil.which(binario)
        filas.append((bool(ruta), f"{etiqueta}: {ruta or 'no instalado'}"))

    pywebview = importlib.util.find_spec("pywebview") is not None
    filas.append((pywebview, "pywebview para ventana nativa (opcional)"))

    try:
        import vosk  # type: ignore  # noqa: F401

        vosk_ok = True
    except Exception:  # noqa: BLE001
        vosk_ok = False
    filas.append((vosk_ok, "paquete vosk (opcional)"))

    ruta_modelo = Path(str(cfg.get("voz.modelo_vosk", "") or "") or (Path(cfg.datos_dir) / "vosk-es"))
    filas.append((ruta_modelo.is_dir(), f"modelo Vosk en {ruta_modelo}"))

    estaticos = Path(__file__).parent / "hud" / "static"
    filas.append(((estaticos / "index.html").is_file(), "HUD estático presente"))

    try:
        db_ok = cfg.db_path.parent.is_dir()
    except Exception:  # noqa: BLE001
        db_ok = False
    filas.append((db_ok, f"datos escribibles en {cfg.datos_dir}"))

    ram = psutil.virtual_memory()
    libre_mb = int(ram.available / (1024 ** 2))
    filas.append((libre_mb > 250, f"RAM libre: {libre_mb} MB de {int(ram.total / (1024 ** 2))} MB"))

    from .brain.ollama import Ollama

    cliente = Ollama(cfg)
    if shutil.which("ollama"):
        servidor = cliente.disponible()
        filas.append((servidor, "servidor Ollama en " + str(cfg.get("cerebro.url"))))
        if servidor:
            modelos = cliente.modelos()
            filas.append((bool(modelos), "modelos: " + (", ".join(modelos) or "ninguno")))
            elegido = cliente.elegir_modelo()
            filas.append((bool(elegido), f"modelo elegido: {elegido or 'ninguno'}"))
    else:
        filas.append((False, "binario ollama no instalado"))
        filas.append((False, "servidor Ollama (no comprobado)"))

    print("CORT · diagnóstico del entorno\n")
    for ok, texto in filas:
        print(f" {_marca(ok)} {texto}")
    print("\n" + cfg.describir())

    esenciales = [version_ok, db_ok, (estaticos / "index.html").is_file()]
    return 0 if all(esenciales) else 1
