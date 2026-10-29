"""Registro central de herramientas de CORT."""

from __future__ import annotations

from .base import Contexto, Registro, Tool
from . import alarms, apps, clock, knowledge, media, system, weather, websearch

CATEGORIAS = {
    "tiempo": "Tiempo y clima",
    "sistema": "Sistema y aplicaciones",
    "web": "Búsqueda web",
    "medios": "Música y medios",
    "alarmas": "Alarmas",
    "memoria": "Memoria",
    "conocimiento": "Conocimiento local",
}


def _tool(
    nombre: str,
    descripcion: str,
    fn,
    ejemplo: str,
    categoria: str,
    propiedades: dict | None = None,
) -> Tool:
    return Tool(
        nombre=nombre,
        descripcion=descripcion,
        esquema={"type": "object", "properties": propiedades or {}},
        fn=fn,
        categoria=categoria,
        ejemplo=ejemplo,
    )


def _memoria_tool(ctx, accion: str = "consultar", clave: str = "", valor: str = "") -> str:
    accion = (accion or "consultar").lower()
    if accion in ("recordar", "guardar", "aprender"):
        if not clave or not valor:
            return "Necesito una clave y un valor para recordar algo."
        ctx.memoria.recordar(clave, valor)
        return f"Guardé que {clave} es {valor}."
    if accion in ("olvidar", "borrar"):
        cuantos = ctx.memoria.olvidar(clave)
        return f"Borré {cuantos} hecho(s) relacionados con «{clave}»." if cuantos else "No tenía nada guardado sobre eso."
    hechos = ctx.memoria.hechos(20)
    if not hechos:
        return "Todavía no tengo hechos guardados sobre vos."
    return "Recuerdo: " + "; ".join(f"{h['clave']}: {h['valor']}" for h in hechos) + "."


def construir_registro() -> Registro:
    r = Registro()
    r.registrar(_tool("hora", "hora actual del sistema", clock.hora, "¿qué hora es?", "tiempo"))
    r.registrar(_tool("fecha", "fecha actual del sistema", clock.fecha, "¿qué día es hoy?", "tiempo"))
    r.registrar(
        _tool(
            "clima",
            "clima real por ciudad o por IP; falla con mensaje honesto",
            weather.clima,
            "¿cómo está el clima en Córdoba?",
            "tiempo",
            {"ciudad": {"type": "string"}},
        )
    )
    r.registrar(_tool("sistema", "CPU, RAM, disco y batería", system.estado, "¿cómo está la PC?", "sistema"))
    r.registrar(
        _tool(
            "abrir_app",
            "abre una aplicación o sitio de la allowlist",
            apps.abrir,
            "abrí el navegador",
            "sistema",
            {"nombre": {"type": "string"}},
        )
    )
    r.registrar(
        _tool(
            "buscar",
            "busca en Google o YouTube abriendo el navegador",
            websearch.buscar,
            "buscá recetas de pan",
            "web",
            {"consulta": {"type": "string"}, "motor": {"type": "string"}},
        )
    )
    r.registrar(
        _tool(
            "media_reproducir",
            "reproduce una canción, playlist local o búsqueda de YouTube",
            media.reproducir,
            "reproducí música de Queen",
            "medios",
            {"consulta": {"type": "string"}, "playlist": {"type": "boolean"}},
        )
    )
    r.registrar(_tool("media_pausa", "pausa la reproducción", media.pausar, "pausá la música", "medios"))
    r.registrar(_tool("media_reanudar", "reanuda la reproducción", media.reanudar, "reanudá la música", "medios"))
    r.registrar(_tool("media_siguiente", "siguiente pista", media.siguiente, "pasá a la siguiente canción", "medios"))
    r.registrar(_tool("media_anterior", "pista anterior", media.anterior, "volvé a la canción anterior", "medios"))
    r.registrar(
        _tool(
            "media_volumen",
            "sube o baja el volumen del sistema",
            media.volumen,
            "subí el volumen",
            "medios",
            {"delta": {"type": "integer"}},
        )
    )
    r.registrar(
        _tool(
            "media_buscar",
            "adelanta o atrasa segundos (requiere playerctl)",
            media.buscar_segundos,
            "adelantá 30 segundos",
            "medios",
            {"segundos": {"type": "integer"}},
        )
    )
    r.registrar(
        _tool(
            "alarma",
            "programa una alarma con hora ISO, mensaje y playlist opcional",
            alarms.crear,
            "poné una alarma a las 7:30",
            "alarmas",
            {
                "cuando": {"type": "string"},
                "mensaje": {"type": "string"},
                "playlist": {"type": "string"},
            },
        )
    )
    r.registrar(
        _tool(
            "conocimiento",
            "consulta los apuntes locales de knowledge/",
            knowledge.buscar,
            "buscá en mis apuntes sobre Ollama",
            "conocimiento",
            {"tema": {"type": "string"}},
        )
    )
    r.registrar(
        _tool(
            "memoria",
            "consulta, guarda u olvida hechos del usuario",
            _memoria_tool,
            "¿qué recordás de mí?",
            "memoria",
            {
                "accion": {"type": "string"},
                "clave": {"type": "string"},
                "valor": {"type": "string"},
            },
        )
    )
    return r
