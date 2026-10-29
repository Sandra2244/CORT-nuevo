"""Reproducción local con VLC y control por señales; MPRIS si existe playerctl."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
from pathlib import Path

from ..text import normalizar, similitud

EXT_AUDIO = {".mp3", ".ogg", ".wav", ".flac", ".m4a", ".opus", ".aac", ".wma"}
EXT_VIDEO = {".mp4", ".mkv", ".webm", ".avi", ".mov"}
EXT_TODO = EXT_AUDIO | EXT_VIDEO

_lock = threading.RLock()


def _ruta_estado(ctx) -> Path:
    return Path(ctx.cfg.datos_dir) / "media.json"


def _leer(ctx) -> dict:
    try:
        with _ruta_estado(ctx).open(encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return {}


def _guardar(ctx, datos: dict) -> None:
    try:
        with _ruta_estado(ctx).open("w", encoding="utf-8") as fh:
            json.dump(datos, fh, ensure_ascii=False)
    except Exception:  # noqa: BLE001
        pass


def _vivo(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:  # noqa: BLE001
        return False


def _matar(pid: int | None) -> None:
    if not _vivo(pid):
        return
    try:
        os.kill(int(pid), signal.SIGTERM)
    except Exception:  # noqa: BLE001
        pass


def _playerctl() -> str | None:
    from shutil import which

    return which("playerctl")


def _archivos_de(carpeta: Path) -> list[Path]:
    archivos = [p for p in carpeta.rglob("*") if p.is_file() and p.suffix.lower() in EXT_TODO]
    return sorted(archivos, key=lambda p: p.name.lower())


def _carpeta_por_nombre(ctx, consulta: str) -> Path | None:
    base = Path(ctx.cfg.playlists_dir)
    if not base.is_dir():
        return None
    consulta_n = normalizar(consulta)
    mejor, puntaje = None, 0.0
    for d in base.iterdir():
        if not d.is_dir():
            continue
        nombre = normalizar(d.name)
        puntos = similitud(consulta_n, nombre)
        if consulta_n and (consulta_n in nombre or nombre in consulta_n):
            puntos = max(puntos, 0.9)
        if puntos > puntaje:
            mejor, puntaje = d, puntos
    return mejor if puntaje >= 0.45 else None


def _archivos_por_nombre(ctx, consulta: str) -> list[Path]:
    base = Path(ctx.cfg.playlists_dir)
    if not base.is_dir():
        return []
    palabras = normalizar(consulta).split()
    if not palabras:
        return []
    encontrados = []
    for p in base.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in EXT_TODO:
            continue
        nombre = normalizar(p.stem)
        if all(pal in nombre for pal in palabras if len(pal) > 2):
            encontrados.append(p)
    return sorted(encontrados, key=lambda p: p.name.lower())


def _reproducir_archivos(ctx, archivos: list[Path], etiqueta: str) -> str:
    if not archivos:
        return "No encontré archivos para reproducir."
    _matar(_leer(ctx).get("pid"))
    solo_audio = all(p.suffix.lower() in EXT_AUDIO for p in archivos)
    cmd = ["cvlc", "--intf", "dummy", "--play-and-exit", "--no-video-title-show"]
    if solo_audio:
        cmd.append("--no-video")
    cmd += [str(p) for p in archivos]
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
        )
    except FileNotFoundError:
        return "No encontré VLC (cvlc) instalado, así que no puedo reproducir archivos locales."
    except Exception as exc:  # noqa: BLE001
        return f"No pude iniciar la reproducción: {type(exc).__name__}."
    _guardar(
        ctx,
        {
            "pid": proc.pid,
            "items": [str(p) for p in archivos],
            "index": 0,
            "etiqueta": etiqueta,
            "pausado": False,
        },
    )
    ctx.log(f"media · {etiqueta} · {len(archivos)} archivo(s)")
    return f"Reproduciendo {etiqueta} ({len(archivos)} archivo{'s' if len(archivos) != 1 else ''})."


def reproducir(ctx, consulta: str, playlist: bool = False) -> str:
    consulta = (consulta or "").strip()
    if not consulta:
        return "¿Qué querés que reproduzca?"
    with _lock:
        pedido = normalizar(consulta)
        if pedido in {"musica", "mi musica", "toda mi musica", "musiquita", "algo de musica"}:
            base = Path(ctx.cfg.playlists_dir)
            if base.is_dir():
                archivos = _archivos_de(base)[:50]
                if archivos:
                    return _reproducir_archivos(ctx, archivos, "tu música")
        carpeta = _carpeta_por_nombre(ctx, consulta)
        if carpeta:
            archivos = _archivos_de(carpeta)
            if archivos:
                return _reproducir_archivos(ctx, archivos, f"la playlist {carpeta.name}")
        if not playlist:
            archivos = _archivos_por_nombre(ctx, consulta)
            if archivos:
                return _reproducir_archivos(ctx, archivos[:1], f"«{archivos[0].stem}»")
        url = f"https://www.youtube.com/results?search_query={consulta.replace(' ', '+')}"
        try:
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as exc:  # noqa: BLE001
            return f"No pude abrir YouTube: {type(exc).__name__}."
        return (
            f"No encontré «{consulta}» en tus carpetas, así que abrí YouTube con la búsqueda. "
            "El play y la pausa los controlás en el navegador."
        )


def pausar(ctx) -> str:
    if _playerctl():
        subprocess.run(["playerctl", "pause"], check=False, capture_output=True)
        return "Pausé la reproducción."
    estado = _leer(ctx)
    pid = estado.get("pid")
    if _vivo(pid) and not estado.get("pausado"):
        try:
            os.kill(int(pid), signal.SIGSTOP)
            estado["pausado"] = True
            _guardar(ctx, estado)
            return "Pausé la reproducción."
        except Exception as exc:  # noqa: BLE001
            return f"No pude pausar: {type(exc).__name__}."
    return "No hay nada reproduciéndose que pueda pausar."


def reanudar(ctx) -> str:
    if _playerctl():
        subprocess.run(["playerctl", "play"], check=False, capture_output=True)
        return "Sigo reproduciendo."
    estado = _leer(ctx)
    pid = estado.get("pid")
    if _vivo(pid) and estado.get("pausado"):
        try:
            os.kill(int(pid), signal.SIGCONT)
            estado["pausado"] = False
            _guardar(ctx, estado)
            return "Sigo reproduciendo."
        except Exception as exc:  # noqa: BLE001
            return f"No pude reanudar: {type(exc).__name__}."
    return "No hay nada en pausa."


def _cambiar_pista(ctx, delta: int) -> str:
    estado = _leer(ctx)
    items = estado.get("items") or []
    if not items:
        return "No tengo una lista de reproducción activa."
    nuevo = int(estado.get("index", 0)) + delta
    if nuevo < 0 or nuevo >= len(items):
        return "No hay más pistas en esa dirección."
    estado["index"] = nuevo
    _guardar(ctx, estado)
    return _reproducir_archivos(ctx, [Path(items[nuevo])], Path(items[nuevo]).stem)


def siguiente(ctx) -> str:
    if _playerctl():
        subprocess.run(["playerctl", "next"], check=False, capture_output=True)
        return "Siguiente pista."
    return _cambiar_pista(ctx, 1)


def anterior(ctx) -> str:
    if _playerctl():
        subprocess.run(["playerctl", "previous"], check=False, capture_output=True)
        return "Pista anterior."
    return _cambiar_pista(ctx, -1)


def volumen(ctx, delta: int = 10) -> str:
    signo = "+" if delta >= 0 else "-"
    try:
        subprocess.run(
            ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{signo}{abs(int(delta))}%"],
            check=False,
            capture_output=True,
        )
        return f"Volumen {'subido' if delta >= 0 else 'bajado'}."
    except Exception as exc:  # noqa: BLE001
        return f"No pude cambiar el volumen: {type(exc).__name__}."


def buscar_segundos(ctx, segundos: int = 10) -> str:
    if not _playerctl():
        return "No puedo adelantar o atrasar con el reproductor actual; instalá playerctl para eso."
    signo = "+" if segundos >= 0 else "-"
    subprocess.run(
        ["playerctl", "position", f"{signo}{abs(int(segundos))}"],
        check=False,
        capture_output=True,
    )
    return f"{'Adelanté' if segundos >= 0 else 'Atrásé'} {abs(int(segundos))} segundos."
