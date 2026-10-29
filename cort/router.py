"""Router determinista: convierte frases en español en intenciones.

Se ejecuta antes que el LLM para que los comandos frecuentes sean instantáneos y
funcionen incluso con Ollama apagado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .text import (
    contiene,
    despues_de,
    hora_desde_texto,
    normalizar,
    proxima_ocurrencia,
)

ARTICULOS = {"la", "el", "los", "las", "un", "una", "mi", "mis", "de", "del", "al"}

_RE_MODELO_TEXTO = re.compile(
    r"(?i)\bmodelo\s+([a-z0-9][a-z0-9._:/-]{1,99})"
)
_RE_MODELO_VERBO = re.compile(
    r"(?i)\b(?:descarga|descargar|instala|instalar|baja|bajar|usa|usar|cambia|cambiar|"
    r"selecciona|seleccionar|activa|activar)\s+(?:el\s+|un\s+)?(?:modelo\s+)?"
    r"([a-z0-9][a-z0-9._:/-]*:[a-z0-9._-]+|[a-z]+[0-9][a-z0-9._:-]*)"
)


def _modelo_desde_texto(texto: str) -> str:
    """Extrae el nombre del texto original para no perder puntos ni dos puntos."""
    for patron in (_RE_MODELO_TEXTO, _RE_MODELO_VERBO):
        m = patron.search(texto or "")
        if m:
            return m.group(1).strip(".,;:¡!¿?")
    return ""


_RE_NOTA = re.compile(
    r"(?i)\b(?:recuerda|acuerdate|acu[eé]rdate|no olvides|apunta)\s+que\s+(.+)"
)


@dataclass
class Intencion:
    nombre: str
    args: dict = field(default_factory=dict)
    texto: str = ""


def _limpiar_wake(norm: str) -> str:
    norm = re.sub(r"^(hey|oye|hola)\s+", "", norm)
    norm = re.sub(r"^(cort|sofi)\b[\s,]*", "", norm)
    return norm.strip()


def _sin_articulos(texto: str) -> str:
    palabras = [p for p in texto.split() if p not in ARTICULOS]
    return " ".join(palabras).strip()


def _mensaje_alarma(norm: str) -> str:
    texto = norm
    for basura in (
        r"\b(pon|ponme|crea|programa|poner)\b",
        r"\b(alarma|recordatorio|recordar|recuerdame|recuerda me|despiertame|despertarme)\b",
        r"\ba\s+las?\s+\d{1,2}([:.]\d{2})?(\s*(am|pm|a m|p m))?",
        r"\b\d{1,2}[:.]\d{2}\b",
        r"\b\d{1,2}\s+y\s+(media|cuarto)\b",
        r"\b(con|mensaje|que diga|para|diciendo)\b",
    ):
        texto = re.sub(basura, " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip(" ,.;:¡!¿?")
    return texto


def enrutar(texto: str) -> Intencion | None:
    bruto = normalizar(texto)
    if bruto in {"hola", "hola cort", "buenas", "buenos dias", "buenas tardes", "buenas noches"}:
        return Intencion("saludo", {}, texto)
    norm = _limpiar_wake(bruto)
    if not norm:
        return Intencion("saludo", {}, texto)

    if contiene(norm, "usa el arnes", "usar el arnes", "modo agente", "con el arnes"):
        objetivo = despues_de(norm, "usa el arnes", "usar el arnes", "con el arnes", "modo agente")
        objetivo = re.sub(r"^para\s+", "", objetivo).strip()
        return Intencion("arnes", {"objetivo": objetivo or norm}, texto)

    # --- ayuda y control -------------------------------------------------
    if norm in {"ayuda", "comandos", "que puedes hacer", "que sabes hacer", "help"}:
        return Intencion("ayuda", {}, texto)

    # Antes de «qué sabes de…»: acá pregunta por lo que CORT no supo.
    if contiene(norm, "olvida lo que no sabes", "borra los huecos", "olvida los huecos"):
        return Intencion("huecos_olvidar", {}, texto)
    if contiene(norm, "que no sabes", "que no supiste", "que te falta saber", "huecos"):
        return Intencion("huecos", {}, texto)

    if any(norm.startswith(p) for p in ("apagate", "cierrate", "adios cort", "hasta luego cort")):
        return Intencion("apagar", {}, texto)

    if contiene(norm, "silencio", "callate", "no hables", "modo silencioso"):
        return Intencion("silencio", {"activar": True}, texto)
    if norm in {"habla", "voz", "activa la voz", "puedes hablar"}:
        return Intencion("silencio", {"activar": False}, texto)

    # --- modelos de Ollama ------------------------------------------------
    if contiene(
        norm,
        "cancela la descarga", "cancelar la descarga", "cancela descarga",
        "deten la descarga", "detener la descarga", "para la descarga",
    ):
        return Intencion("modelo_cancelar", {}, texto)
    modelo_pedido = _modelo_desde_texto(texto)
    if (contiene(norm, "modelo", "modelos") or modelo_pedido) and contiene(
        norm,
        "ollama", "descarga", "descargar", "instala", "instalar", "baja", "bajar",
        "lista", "cuales", "tienes", "actual", "cambia", "usar", "usa",
        "selecciona", "activa",
    ):
        if contiene(norm, "descarga", "descargar", "instala", "instalar", "baja", "bajar"):
            return Intencion("modelo_descargar", {"nombre": modelo_pedido}, texto)
        if contiene(norm, "cambia", "cambiar", "selecciona", "seleccionar", "activa", "activar", "usa", "usar"):
            if modelo_pedido:
                return Intencion("modelo_usar", {"nombre": modelo_pedido}, texto)
        return Intencion("modelos_listar", {}, texto)

    # --- fecha y hora ----------------------------------------------------
    if contiene(norm, "que hora", "hora es", "dime la hora", "la hora", "hora actual"):
        return Intencion("hora", {}, texto)
    if contiene(norm, "que dia", "que fecha", "fecha es", "dia es hoy", "a que dia estamos", "fecha de hoy"):
        return Intencion("fecha", {}, texto)

    # --- sistema (antes que 'memoria' para no confundir RAM) -------------
    if contiene(
        norm,
        "cpu", "ram", "memoria ram", "disco", "bateria", "sistema",
        "como esta la pc", "como va la pc", "como esta el pc", "recursos",
        "procesador", "temperatura del cpu", "uso de memoria",
    ):
        return Intencion("sistema", {}, texto)

    # --- alarmas ---------------------------------------------------------
    if contiene(norm, "alarma", "recuerdame", "recordatorio", "despiertame"):
        hora = hora_desde_texto(norm)
        if hora:
            cuando = proxima_ocurrencia(*hora)
            return Intencion(
                "alarma",
                {"cuando": cuando.isoformat(), "mensaje": _mensaje_alarma(norm), "hora": hora},
                texto,
            )
        return Intencion("alarma_sin_hora", {}, texto)

    # --- control de medios ----------------------------------------------
    if contiene(norm, "pausa", "pausar", "pausalo", "deten la musica", "para la musica"):
        return Intencion("media_pausa", {}, texto)
    if contiene(norm, "reanuda", "continua la musica", "sigue la musica", "quita pausa"):
        return Intencion("media_reanudar", {}, texto)
    if contiene(norm, "siguiente cancion", "otra cancion", "siguiente tema", "siguiente"):
        return Intencion("media_siguiente", {}, texto)
    if contiene(norm, "cancion anterior", "anterior", "vuelve a la anterior"):
        return Intencion("media_anterior", {}, texto)
    if contiene(norm, "sube el volumen", "subir volumen", "mas volumen"):
        return Intencion("media_volumen", {"delta": 10}, texto)
    if contiene(norm, "baja el volumen", "bajar volumen", "menos volumen"):
        return Intencion("media_volumen", {"delta": -10}, texto)
    if contiene(norm, "adelanta", "avanza", "atrasa", "retrocede"):
        m = re.search(r"(\d{1,3})\s*(segundo|seg|minuto|min)", norm)
        cantidad = int(m.group(1)) if m else 10
        if m and m.group(2).startswith("min"):
            cantidad *= 60
        signo = -1 if contiene(norm, "atrasa", "retrocede") else 1
        return Intencion("media_buscar", {"segundos": signo * cantidad}, texto)

    # --- reproducir ------------------------------------------------------
    if contiene(norm, "reproduce", "ponme", "pon ", "play "):
        consulta = despues_de(norm, "reproduce", "ponme", "pon ", "play ")
        if consulta:
            playlist = contiene(norm, "playlist", "carpeta")
            consulta = re.sub(r"^(la|el|una|un)\s+", "", consulta)
            return Intencion("media_reproducir", {"consulta": consulta, "playlist": playlist}, texto)

    # --- búsqueda --------------------------------------------------------
    if contiene(norm, "busca", "buscar", "googlea"):
        if "youtube" in norm:
            consulta = despues_de(norm, "busca en youtube", "buscar en youtube", "youtube")
            return Intencion("buscar", {"consulta": consulta, "motor": "youtube"}, texto)
        consulta = despues_de(norm, "busca en google", "buscar en google", "busca", "buscar", "googlea")
        return Intencion("buscar", {"consulta": consulta, "motor": "google"}, texto)

    # --- abrir apps ------------------------------------------------------
    if contiene(norm, "abre", "abreme", "abrir", "lanza", "ejecuta"):
        app = despues_de(norm, "abreme", "abre", "abrir", "lanza", "ejecuta")
        app = _sin_articulos(app)
        if app:
            return Intencion("app", {"nombre": app}, texto)

    # --- memoria ---------------------------------------------------------
    if contiene(
        norm,
        "olvida la conversacion", "olvidar la conversacion", "borra el contexto",
        "borrar el contexto", "limpia el contexto", "olvida el contexto",
        "nueva conversacion", "empecemos de cero",
    ):
        return Intencion("contexto_limpiar", {}, texto)
    m = re.search(r"\bme llamo\s+([a-zñ]+(?:\s+[a-zñ]+)?)", norm)
    if m:
        return Intencion("recordar", {"clave": "nombre", "valor": m.group(1).strip()}, texto)
    m = re.search(r"\bmi nombre es\s+([a-zñ]+(?:\s+[a-zñ]+)?)", norm)
    if m:
        return Intencion("recordar", {"clave": "nombre", "valor": m.group(1).strip()}, texto)
    m = re.search(r"\bmi\s+([a-zñ]+)\s+se llama\s+([a-zñ]+(?:\s+[a-zñ]+)?)", norm)
    if m:
        return Intencion("recordar", {"clave": m.group(1), "valor": m.group(2).strip()}, texto)
    m = re.search(r"\bmi\s+([a-zñ]+(?:\s+[a-zñ]+)?)\s+favorit[oa]\s+es\s+(.+)$", norm)
    if m:
        valor = _sin_articulos(m.group(2).strip())
        return Intencion("recordar", {"clave": f"{m.group(1)} favorito", "valor": valor}, texto)
    m = re.search(r"\bvivo en\s+(.+)$", norm)
    if m:
        return Intencion("recordar", {"clave": "ciudad", "valor": m.group(1).strip()}, texto)
    m = _RE_NOTA.search(texto)
    if m:
        valor = m.group(1).strip(" .,;:¡!¿?")
        palabras = [p for p in normalizar(valor).split() if p not in ARTICULOS]
        clave = f"nota {palabras[0]}" if palabras else "nota"
        return Intencion("recordar", {"clave": clave, "valor": valor}, texto)
    if contiene(norm, "olvida", "borra de tu memoria", "olvidalo"):
        clave = despues_de(norm, "borra de tu memoria", "olvida", "olvidalo")
        return Intencion("olvidar", {"clave": _sin_articulos(clave)}, texto)
    if contiene(norm, "como me llamo", "quien soy", "que sabes de mi"):
        return Intencion("consultar_memoria", {}, texto)
    if norm in {"memoria", "que recuerdas", "tus recuerdos"}:
        return Intencion("consultar_memoria", {}, texto)

    # --- clima -----------------------------------------------------------
    if contiene(norm, "clima", "tiempo hace", "temperatura", "va a llover", "lluvia", "pronostico"):
        ciudad = despues_de(norm, "clima en", "tiempo en", "temperatura en", "clima de")
        if not ciudad:
            m = re.search(r"\ben\s+([a-zñ\s]+)$", norm)
            ciudad = m.group(1).strip() if m else ""
        return Intencion("clima", {"ciudad": ciudad}, texto)

    # --- conocimiento ----------------------------------------------------
    if contiene(norm, "que sabes de", "consulta mis apuntes", "busca en mis apuntes", "conocimiento"):
        tema = despues_de(norm, "que sabes de", "consulta mis apuntes", "busca en mis apuntes", "conocimiento")
        return Intencion("conocimiento", {"tema": tema}, texto)

    # --- arnés -----------------------------------------------------------
    if contiene(norm, "investiga", "averigua", "compara", "planifica"):
        objetivo = despues_de(norm, "investiga", "averigua", "compara", "planifica")
        return Intencion("arnes", {"objetivo": objetivo or norm}, texto)

    return None
