"""Arnés de agentes: bucle de herramientas con contrato JSON."""

from __future__ import annotations

import json
import time
from typing import Any

from . import honesto
from . import persona
from ..text import recortar
from ..tools.base import Contexto


def _extraer_json(texto: str) -> dict | None:
    for i, c in enumerate(texto):
        if c != "{":
            continue
        try:
            dato, _ = json.JSONDecoder().raw_decode(texto[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(dato, dict) and any(k in dato for k in ("tool", "herramienta", "respuesta")):
            return dato
    return None


class Arnes:
    def __init__(self, ollama, registro, cfg, bus):
        self.ollama = ollama
        self.registro = registro
        self.max_pasos = int(cfg.get("arnes.max_pasos", 3))
        self.bus = bus

    def ejecutar(self, objetivo: str, ctx: Contexto, historial: list[dict] | None = None) -> tuple[str, list[str]]:
        pasos: list[str] = []
        if not self.ollama.elegir_modelo():
            ctx.memoria.anotar_hueco(objetivo, "arnés sin modelo")
            return (
                honesto.sin_modelo(
                    ["la hora", "el clima", "cómo está la PC", "abrir una app de la lista",
                     "buscar en la web"]
                ),
                pasos,
            )
        sistema = persona.construir(
            ctx.memoria,
            conocimiento="",
            herramientas=self.registro.nombres(),
        )
        mensajes: list[dict] = [{"role": "system", "content": sistema}]
        for m in (historial or [])[-6:]:
            mensajes.append({"role": m.get("rol", "user"), "content": m.get("texto", "")})
        mensajes.append({"role": "user", "content": objetivo})

        for paso in range(1, self.max_pasos + 1):
            if getattr(self.ollama, "cancelado", False):
                return "Turno detenido.", pasos
            respuesta = self.ollama.conversar(mensajes)
            if getattr(self.ollama, "cancelado", False):
                return "Turno detenido.", pasos
            if not respuesta:
                ctx.memoria.anotar_hueco(objetivo, "arnés sin respuesta")
                return honesto.fallo_modelo(self.ollama.ultimo_error or ""), pasos
            dato = _extraer_json(respuesta)
            if not dato:
                return respuesta.strip(), pasos
            if "respuesta" in dato and "tool" not in dato and "herramienta" not in dato:
                return str(dato["respuesta"]).strip(), pasos
            nombre = str(dato.get("tool") or dato.get("herramienta") or "")
            args = dato.get("args") or {}
            if not isinstance(args, dict):
                args = {}
            etiqueta = f"paso {paso} · {nombre}"
            pasos.append(etiqueta)
            self.bus.log(f"arnés · {etiqueta}")
            self.bus.estado("executing")
            t0 = time.monotonic()
            texto, estado = self.registro.ejecutar(nombre, args, ctx)
            ms = int((time.monotonic() - t0) * 1000)
            self.bus.evento(
                "ejecucion" if estado == "ok" else "error",
                etiqueta,
                {
                    "herramienta": nombre,
                    "paso": paso,
                    "ms": ms,
                    "ok": estado == "ok",
                    "args": recortar(json.dumps(args, ensure_ascii=False), 120),
                },
            )
            mensajes.append({"role": "assistant", "content": respuesta})
            mensajes.append(
                {"role": "user", "content": f"Resultado de la herramienta {nombre} ({estado}): {texto}"}
            )
            if estado == "error" and paso == self.max_pasos:
                ctx.memoria.anotar_hueco(objetivo, f"arnés: {nombre} falló")
                return (
                    f"Me detuve en el paso {paso} porque {nombre} falló: {texto} "
                    "No sigo a ciegas; ¿lo intentamos por otro lado o lo dejamos anotado?",
                    pasos,
                )
        ctx.memoria.anotar_hueco(objetivo, "arnés sin pasos")
        return honesto.sin_pasos(pasos[-1] if pasos else ""), pasos
