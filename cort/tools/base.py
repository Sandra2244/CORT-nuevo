"""Contrato común de herramientas y contexto de ejecución."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Contexto:
    cfg: Any
    memoria: Any
    bus: Any
    ollama: Any = None
    tts: Any = None
    extra: dict = field(default_factory=dict)

    def hablar(self, texto: str) -> None:
        if self.tts is not None:
            self.tts.hablar(texto)

    def log(self, linea: str) -> None:
        self.bus.log(linea)


@dataclass
class Tool:
    nombre: str
    descripcion: str
    esquema: dict
    fn: Callable[..., str]
    riesgo: str = "bajo"
    categoria: str = "general"
    ejemplo: str = ""


class Registro:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def registrar(self, tool: Tool) -> None:
        self._tools[tool.nombre] = tool

    def obtener(self, nombre: str) -> Tool | None:
        return self._tools.get(nombre)

    def nombres(self) -> list[str]:
        return sorted(self._tools)

    def descripcion_prompt(self) -> str:
        return "; ".join(
            f"{t.nombre}({', '.join(t.esquema.get('properties', {}))}): {t.descripcion}"
            for t in self._tools.values()
        )

    def ejecutar(self, nombre: str, args: dict | None, ctx: Contexto) -> tuple[str, str]:
        tool = self.obtener(nombre)
        if tool is None:
            return f"No existe la herramienta «{nombre}».", "error"
        args = dict(args or {})
        permitidos = set(tool.esquema.get("properties", {}))
        limpios = {k: v for k, v in args.items() if k in permitidos}
        try:
            firma = inspect.signature(tool.fn)
            if "ctx" in firma.parameters:
                texto = tool.fn(ctx, **limpios)
            else:
                texto = tool.fn(**limpios)
            return str(texto), "ok"
        except TypeError as exc:
            return f"Argumentos inválidos para «{nombre}»: {exc}", "error"
        except Exception as exc:  # noqa: BLE001
            return f"La herramienta «{nombre}» falló: {type(exc).__name__}: {exc}", "error"
