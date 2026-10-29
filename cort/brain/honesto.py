"""La voz de CORT cuando no sabe, no puede o algo falla.

Un asistente que inventa cuando no sabe es peor que uno que se calla: la dueña
no puede distinguir lo comprobado de lo plausible. Todas las respuestas
«honestas» viven acá, en un solo lugar, para que no se repartan en frases
sueltas por el orquestador, el arnés y el router.

Todas comparten la misma forma, que también es la personalidad:

1. Reconocen el límite en la primera frase, sin dar vueltas ni disculparse tres
   veces.
2. Ofrecen dos o tres salidas **reales** —cosas que CORT puede hacer de verdad
   en ese estado—, no un «intentá de nuevo» vacío.
3. No echan la culpa a nadie ni suenan a página de error.
4. Son cercanas: le hablan a Sandra de vos, como el resto de la aplicación.
"""

from __future__ import annotations

# Salidas que existen siempre: son comandos directos del router, no promesas.
SALIDAS = (
    "buscar en la web («busca en Google …»)",
    "mirar tus apuntes («qué sabes de …»)",
    "dejarlo anotado para que no se pierda",
)

# Lo que queda disponible con Ollama apagado: todo lo del router sin modelo.
SIN_MODELO = (
    "la hora y la fecha",
    "el clima",
    "cómo está la PC",
    "abrir una app de la lista",
    "reproducir, pausar o pasar un tema",
    "una alarma",
    "recordar un dato",
)


def _como_lista(items) -> str:
    items = [str(i).strip() for i in items if str(i).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " o " + items[-1]


def sin_modelo(ejemplos: list[str] | None = None) -> str:
    """No hay modelo cargado: se dice, y se recuerda lo que sí funciona."""
    lista = _como_lista(ejemplos or SIN_MODELO[:4])
    return (
        "Ahora mismo no tengo el modelo de lenguaje encendido, y prefiero decírtelo "
        f"antes que inventarte una respuesta que suene bien. Puedo hacer esto sin él: {lista}. "
        "Cuando Ollama esté arriba vuelvo a razonar contigo, con todo lo demás."
    )


def no_supe(motivo: str = "", salidas=None) -> str:
    """El caso general: no hay respuesta fiable.

    `motivo` es para Sandra, no para el registro: una frase corta y concreta
    («no me alcanzó el tiempo del modelo», «esa orden no la reconozco»). Si no
    hay motivo, se omite en vez de rellenar con humo.
    """
    motivo = " ".join(str(motivo or "").split()).strip().rstrip(".")
    entrada = "No lo sé" + (f": {motivo}" if motivo else "")
    return (
        f"{entrada}. No quiero adivinar para que no te quede una respuesta falsa. "
        f"Puedo {_como_lista(salidas or SALIDAS)}, y si me lo contás de otra forma "
        "también lo intento."
    )


def fallo_modelo(detalle: str = "") -> str:
    """El modelo no devolvió nada, o devolvió error."""
    detalle = " ".join(str(detalle or "").split()).strip()
    cola = f" ({detalle})" if detalle else ""
    return (
        f"No logré que el modelo me diera una respuesta{cola}, así que no tengo nada "
        "confiable que decirte. Puedo reintentarlo, buscarlo en la web o dejarlo anotado "
        "para cuando el cerebro esté más despierto."
    )


def sin_pasos(ultimo: str = "") -> str:
    """El arnés gastó sus pasos sin llegar a una respuesta."""
    ultimo = " ".join(str(ultimo or "").split()).strip()
    if ultimo:
        return (
            f"Me quedé sin pasos antes de cerrar esto; lo último que sí hice fue {ultimo}. "
            "No voy a presentarte eso como respuesta final. ¿Seguimos desde ahí, lo busco "
            "en la web o lo dejamos anotado?"
        )
    return (
        "Me quedé sin pasos antes de llegar a una respuesta y no quiero inventar el final. "
        "¿Lo intentamos otra vez con un objetivo más chico, o lo dejo anotado?"
    )


def orden_dudosa(orden: str = "") -> str:
    """El router reconoció una intención pero no supo resolverla."""
    orden = " ".join(str(orden or "").split()).strip()
    pista = f" «{orden}»" if orden else ""
    return (
        f"No supe cómo resolver eso{pista}, y no quiero adivinar una orden que toca tu "
        "equipo. Decímelo de otra forma, o empecemos por algo que sí tengo a mano: "
        f"{_como_lista(SALIDAS)}."
    )
