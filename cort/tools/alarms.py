"""Alarmas y recordatorios con hilo comprobador."""

from __future__ import annotations

import subprocess
import threading
from datetime import datetime

from ..text import hora_larga


def crear(ctx, cuando: str, mensaje: str = "", playlist: str = "") -> str:
    try:
        momento = datetime.fromisoformat(cuando)
    except Exception:  # noqa: BLE001
        return "No entendí la hora de la alarma. Decime algo como «alarma a las 6:30»."
    alarma_id = ctx.memoria.crear_alarma(momento, mensaje or "Es hora", playlist)
    ctx.log(f"alarma #{alarma_id} · {momento.strftime('%H:%M')}")
    extra = f" con el mensaje «{mensaje}»" if mensaje else ""
    return f"Listo: alarma #{alarma_id} para {hora_larga(momento)}{extra}."


def listar(ctx) -> str:
    alarmas = ctx.memoria.proximas_alarmas(5)
    if not alarmas:
        return "No hay alarmas programadas."
    lineas = []
    for a in alarmas:
        try:
            hora = datetime.fromisoformat(a["cuando"]).strftime("%d/%m %H:%M")
        except Exception:  # noqa: BLE001
            hora = a["cuando"]
        lineas.append(f"{hora} · {a['texto']}")
    return "Alarmas: " + "; ".join(lineas) + "."


class Programador(threading.Thread):
    """Comprueba alarmas cada 15 s y avisa con voz + notificación."""

    def __init__(self, ctx, intervalo: float = 15.0):
        super().__init__(daemon=True, name="cort-alarmas")
        self.ctx = ctx
        self.intervalo = intervalo
        self._parar = threading.Event()

    def detener(self) -> None:
        self._parar.set()

    def run(self) -> None:
        while not self._parar.wait(self.intervalo):
            try:
                pendientes = self.ctx.memoria.alarmas_pendientes()
            except Exception:  # noqa: BLE001
                continue
            for alarma in pendientes:
                texto = alarma.get("texto") or "Es hora"
                self.ctx.log(f"alarma · {texto}")
                self.ctx.bus.estado("alert")
                self.ctx.bus.evento("alarma", texto)
                self.ctx.hablar(f"Alarma: {texto}")
                threading.Timer(
                    8.0,
                    lambda: self.ctx.bus.estado("idle")
                    if self.ctx.bus.estado_actual() == "alert"
                    else None,
                ).start()
                try:
                    subprocess.Popen(
                        ["notify-send", "CORT", texto],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception:  # noqa: BLE001
                    pass
                playlist = alarma.get("playlist") or ""
                if playlist:
                    try:
                        from . import media

                        media.reproducir(self.ctx, playlist, playlist=True)
                    except Exception:  # noqa: BLE001
                        pass
                self.ctx.memoria.marcar_alarma(int(alarma["id"]))
