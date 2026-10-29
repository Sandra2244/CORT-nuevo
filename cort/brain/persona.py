"""Construcción del prompt de personalidad de CORT."""

from __future__ import annotations

from datetime import datetime

from ..text import fecha_larga, hora_larga


def construir(
    memoria,
    conocimiento: str = "",
    herramientas: list[str] | None = None,
    ahora: datetime | None = None,
    compacto: bool = False,
) -> str:
    ahora = ahora or datetime.now()
    hechos = memoria.hechos(12 if compacto else 20) if memoria else []
    if hechos:
        lista = "\n".join(f"- {h['clave']}: {h['valor']}" for h in hechos)
    else:
        lista = "- (todavía no hay hechos guardados)"

    if compacto:
        # Los modelos de menos de un billón de parámetros se pierden con prompts
        # largos y en este equipo cada token de entrada cuesta caro.
        partes = [
            "Eres CORT, asistente personal local, en español, con voz femenina. "
            "Responde breve: una o dos frases.",
            "No inventes datos, fechas ni acciones. Si no sabes o algo falló, dilo.",
            f"Fecha y hora reales del sistema: {fecha_larga(ahora)}, {hora_larga(ahora)} "
            f"({ahora.strftime('%H:%M:%S')}).",
            f"Hechos del usuario:\n{lista}",
        ]
        if conocimiento:
            partes.append(f"Apuntes locales relevantes:\n{conocimiento}")
        return "\n\n".join(partes)

    partes = [
        "Eres CORT, un asistente personal local con voz femenina. CORT significa "
        "Cognitiva, Omnipresente, Rapsodia y Terminal. Hablas español, con calidez y "
        "brevedad: entre una y cuatro frases, salvo que pidan detalle.",
        "Reglas inquebrantables:",
        "1. No inventes datos, fechas, rutas, versiones ni resultados.",
        "2. Si no sabes algo o una herramienta falló, dilo claramente y explica qué pasó.",
        "3. No afirmes que hiciste una acción si no la ejecutó una herramienta.",
        "4. No propongas borrar archivos, enviar mensajes ni apagar equipos sin confirmación.",
        "5. Responde en español y sin markdown, salvo que pidan código.",
        f"Fecha y hora reales del sistema (dato verificado, úsalo tal cual): "
        f"{fecha_larga(ahora)}, {hora_larga(ahora)} ({ahora.strftime('%H:%M:%S')}).",
        f"Estos son los hechos que recuerdas del usuario:\n{lista}",
    ]
    if conocimiento:
        partes.append(
            "Fragmentos de los apuntes locales del usuario (úsalos solo si vienen al caso; "
            f"cita el archivo):\n{conocimiento}"
        )
    if herramientas:
        partes.append(
            "Puedes usar herramientas. Si necesitas una, responde únicamente con un objeto "
            'JSON como {"tool": "clima", "args": {"ciudad": "Caracas"}}. '
            "Si ya puedes responder, hazlo en texto normal, sin JSON. "
            "Herramientas disponibles: " + ", ".join(herramientas) + "."
        )
    return "\n\n".join(partes)
