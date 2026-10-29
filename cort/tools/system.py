"""Estado del sistema con psutil."""

from __future__ import annotations

import shutil

import psutil


def _gb(bytes_: float) -> float:
    return round(bytes_ / (1024 ** 3), 1)


def estado(ctx=None) -> str:
    cpu = psutil.cpu_percent(interval=0.3)
    ram = psutil.virtual_memory()
    disco = shutil.disk_usage("/")
    partes = [
        f"CPU al {cpu:.0f} %",
        f"RAM {_gb(ram.used)} de {_gb(ram.total)} GB ({ram.percent:.0f} %)",
        f"disco libre {_gb(disco.free)} GB de {_gb(disco.total)} GB",
    ]
    try:
        bateria = psutil.sensors_battery()
        if bateria is not None:
            estado_bat = "cargando" if bateria.power_plugged else "descargando"
            partes.append(f"batería {bateria.percent:.0f} % ({estado_bat})")
    except Exception:  # noqa: BLE001
        pass
    aviso = ""
    if ctx is not None:
        cpu_max = int(ctx.cfg.get("sistema.cpu_max", 85))
        ram_max = int(ctx.cfg.get("sistema.ram_max", 90))
        if cpu >= cpu_max:
            aviso = " El procesador está muy cargado."
        elif ram.percent >= ram_max:
            aviso = " La memoria RAM está casi llena."
    return ". ".join(partes) + "." + aviso


def metricas() -> dict:
    ram = psutil.virtual_memory()
    try:
        cpu = psutil.cpu_percent(interval=None)
    except Exception:  # noqa: BLE001
        cpu = 0.0
    bateria = None
    try:
        b = psutil.sensors_battery()
        if b is not None:
            bateria = {"porcentaje": round(b.percent), "enchufada": bool(b.power_plugged)}
    except Exception:  # noqa: BLE001
        bateria = None
    return {
        "cpu": round(float(cpu), 1),
        "ram": round(ram.percent, 1),
        "ram_usada_gb": _gb(ram.used),
        "ram_total_gb": _gb(ram.total),
        "bateria": bateria,
    }
