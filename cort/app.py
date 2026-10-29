"""Orquestador de CORT: router, herramientas, LLM, memoria y voz."""

from __future__ import annotations

import threading
import time
from datetime import datetime

from . import __version__
from .brain import honesto
from .brain import persona
from .brain import ollama as ollama_mod
from .brain.harness import Arnes
from .brain.memory import Memoria
from .brain.ollama import Ollama
from .bus import Bus
from .config import Config
from .router import enrutar
from .text import fecha_larga, normalizar, recortar
from .tools import CATEGORIAS, construir_registro
from .tools import knowledge, media
from .tools import system as tool_system
from .tools.alarms import Programador
from .tools.base import Contexto
from .voice.stt import Stt
from .voice.tts import Tts

AYUDA = """Puedo hacer esto sin necesidad de modelo:
• «qué hora es» / «qué día es hoy»
• «clima» o «clima en Caracas»
• «cómo está la PC» (CPU, RAM, disco, batería)
• «abre calculadora / archivos / navegador / terminal / vscodium»
• «busca en Google …» / «busca en YouTube …»
• «reproduce …», «pausa», «reanuda», «siguiente», «anterior»
• «alarma a las 6:30 con …» / «recuérdame …»
• «me llamo …», «recuerda que …», «olvida …», «¿cómo me llamo?»
• «qué sabes de …» (lee la carpeta knowledge/)
• «qué no sabés» (lo que CORT no pudo responder)
• «silencio» / «habla»

Con Ollama encendido también converso y uso el arnés («investiga…», «compara…»)."""

SIN_CEREBRO = honesto.sin_modelo(
    ["la hora y la fecha", "el clima", "cómo está la PC", "abrir una calculadora",
     "una alarma a las 6:30", "recordar un dato"]
)


class Cort:
    def __init__(self, cfg: Config, voz: bool = True):
        if not voz:
            cfg.set("voz.tts", False)
        self.cfg = cfg
        self.bus = Bus()
        self.memoria = Memoria(cfg.db_path)
        self.ollama = Ollama(cfg)
        guardado = self.memoria.meta("modelo")
        if guardado:
            self.ollama.modelo = guardado
        self._descarga_lock = threading.Lock()
        self._descargando = ""
        self._progreso: dict = {}
        self._historial: list[dict] = []
        self._historial_lock = threading.Lock()
        self._parcial = ""
        self._parcial_lock = threading.Lock()
        self.tts = Tts(cfg, self.bus)
        self.stt = Stt(cfg, self.bus)
        self.ctx = Contexto(cfg, self.memoria, self.bus, self.ollama, self.tts)
        self.registro = construir_registro()
        self.arnes = Arnes(self.ollama, self.registro, cfg, self.bus)
        self.programador = Programador(self.ctx)
        self._parar = threading.Event()
        self._hilos: list[threading.Thread] = []
        self._apagar = False

    # --- ciclo de vida --------------------------------------------------
    def iniciar(self) -> None:
        self.bus.log(f"CORT v{__version__} · datos en {self.cfg.datos_dir}")
        self.bus.log(
            "voz · " + ("tts listo" if self.tts.disponible else "sin espeak-ng")
            + " · " + ("micrófono listo" if self.stt.disponible else f"sin micrófono ({self.stt.motivo})")
        )
        self.programador.start()
        hilo = threading.Thread(target=self._bucle_metricas, daemon=True, name="cort-metricas")
        hilo.start()
        self._hilos.append(hilo)
        threading.Thread(target=self._verificar_ollama, daemon=True, name="cort-ollama").start()

    def _bucle_metricas(self) -> None:
        contador = 0
        while not self._parar.wait(3):
            try:
                self.bus.metricas(tool_system.metricas())
            except Exception:  # noqa: BLE001
                pass
            contador += 1
            if contador % 20 == 0:
                self._verificar_ollama()

    def _verificar_ollama(self) -> None:
        ok = self.ollama.disponible()
        self.bus.flag("ollama_ok", ok)
        if ok:
            modelo = self.ollama.elegir_modelo()
            self.bus.flag("modelo", modelo)
            if modelo and self.memoria.meta("modelo") != modelo:
                self.memoria.meta("modelo", modelo)
            self.bus.log(f"cerebro · {modelo}")
        else:
            self.bus.log("cerebro · Ollama no responde")

    # --- modelos de Ollama ---------------------------------------------
    def listar_modelos(self) -> dict:
        info = self.ollama.modelos_info()
        disponible = not self.ollama.ultimo_error
        instalados = {m["nombre"] for m in info}
        recomendados = [
            dict(r, instalado=r["nombre"] in instalados)
            for r in ollama_mod.RECOMENDADOS
        ]
        return {
            "ok": disponible,
            "disponible": disponible,
            "activo": self.ollama.modelo,
            "modelos": info,
            "recomendados": recomendados,
            "motivo": "" if disponible else (self.ollama.ultimo_error or "Ollama no responde"),
            "url": self.ollama.url,
            "descargando": self._descargando,
            "progreso": dict(self._progreso),
        }

    def seleccionar_modelo(self, nombre: str) -> dict:
        nombre = (nombre or "").strip()
        if not self.ollama.nombre_valido(nombre):
            return {"ok": False, "error": "Nombre de modelo inválido; probá con qwen3:0.6b."}
        info = self.ollama.modelos_info()
        if not info and self.ollama.ultimo_error:
            return {
                "ok": False,
                "error": f"Ollama no responde en {self.ollama.url}: {self.ollama.ultimo_error}.",
            }
        nombres = {m["nombre"] for m in info}
        if nombre not in nombres:
            familia = nombre.split(":")[0]
            candidatos = sorted(n for n in nombres if n.split(":")[0] == familia)
            if len(candidatos) == 1:
                nombre = candidatos[0]
            else:
                return {
                    "ok": False,
                    "error": f"El modelo «{nombre}» no está instalado. Instalados: {', '.join(sorted(nombres)) or 'ninguno'}.",
                }
        self.ollama.modelo = nombre
        self.memoria.meta("modelo", nombre)
        self.bus.flag("modelo", nombre)
        self.bus.flag("ollama_ok", True)
        self.bus.log(f"modelo · {nombre}")
        self.bus.evento("modelo", nombre)
        return {"ok": True, "modelo": nombre}

    def descargar_modelo(self, nombre: str, al_progreso=None) -> dict:
        nombre = (nombre or "").strip()
        if not self.ollama.nombre_valido(nombre):
            return {"ok": False, "error": "Nombre de modelo inválido; probá con qwen3:0.6b."}
        with self._descarga_lock:
            if self._descargando:
                return {"ok": False, "error": f"Ya se está descargando {self._descargando}."}
            self._descargando = nombre
        self._progreso = {"estado": "iniciando", "porcentaje": None, "completado": 0, "total": 0}
        self.bus.estado("downloading")
        self.bus.evento("descarga", nombre)
        self.bus.log(f"modelos · descargando {nombre}")

        def reportar(avance: dict) -> None:
            self._progreso = dict(avance)
            if al_progreso:
                al_progreso(avance)

        try:
            resultado = self.ollama.descargar(nombre, reportar)
        finally:
            with self._descarga_lock:
                self._descargando = ""
        if resultado.get("cancelado"):
            self._progreso = dict(self._progreso, estado="cancelada", porcentaje=None)
            self.bus.log(f"modelos · descarga cancelada {nombre}")
            self.bus.estado("idle")
            self.bus.evento("descarga", f"{nombre} cancelada")
            return resultado
        if not resultado.get("ok"):
            self._progreso = dict(self._progreso, estado="error")
            self.bus.log(f"modelos · error: {resultado.get('error', 'sin detalle')}")
            self.bus.estado("error")
            self.bus.evento("error", f"descarga de {nombre}")
            return resultado
        self.bus.flag("ollama_ok", True)
        instalados = {m["nombre"] for m in self.ollama.modelos_info()}
        # Descargar un modelo es una señal clara de que se quiere usar: se activa.
        if nombre in instalados:
            self.ollama.modelo = nombre
            self.memoria.meta("modelo", nombre)
            self.bus.log(f"modelo · {nombre} activo")
        elif self.ollama.modelo not in instalados:
            self.ollama.modelo = self.ollama.elegir_modelo()
            if self.ollama.modelo:
                self.memoria.meta("modelo", self.ollama.modelo)
        self._progreso = dict(self._progreso, estado="lista", porcentaje=100.0)
        self.bus.flag("modelo", self.ollama.modelo)
        self.bus.log(f"modelos · listo {nombre}")
        self.bus.estado("idle")
        self.bus.evento("descarga", f"{nombre} lista")
        return dict(resultado, activo=self.ollama.modelo)

    def cancelar_descarga(self) -> dict:
        activo = self.ollama.cancelar_descarga()
        if not activo and not self._descargando:
            return {"ok": False, "error": "No hay ninguna descarga en curso."}
        self.bus.log("modelos · cancelando descarga")
        return {"ok": True, "mensaje": "Cancelé la descarga del modelo."}

    def descargar_en_segundo_plano(self, nombre: str) -> dict:
        nombre = (nombre or "").strip()
        if not self.ollama.nombre_valido(nombre):
            return {"ok": False, "error": "Nombre de modelo inválido; probá con qwen3:0.6b."}
        with self._descarga_lock:
            if self._descargando:
                return {"ok": False, "error": f"Ya se está descargando {self._descargando}."}
        threading.Thread(
            target=self.descargar_modelo,
            args=(nombre,),
            daemon=True,
            name="cort-descarga",
        ).start()
        return {
            "ok": True,
            "mensaje": (
                f"Empecé a descargar {nombre} en segundo plano. Puede tardar; "
                "el avance aparece en el panel de modelos del HUD."
            ),
        }

    def cerrar(self) -> None:
        self._parar.set()
        self.programador.detener()
        try:
            self.tts.detener()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.memoria.cerrar()
        except Exception:  # noqa: BLE001
            pass

    # --- respuesta ------------------------------------------------------
    def detener_turno(self) -> dict:
        """Corta la voz y el stream del modelo; el HUD usa esto como STOP."""
        cancelar = getattr(self.ollama, "cancelar_turno", None)
        if callable(cancelar):
            cancelar()
        self.tts.detener()
        self.bus.log("turno · detenido por el usuario")
        self.bus.estado("idle")
        return {"ok": True, "mensaje": "Turno detenido."}

    def responder(self, texto: str) -> dict:
        t0 = time.monotonic()
        texto = " ".join(str(texto or "").split())
        if not texto:
            return {"respuesta": "No te escuché. Repetí, por favor.", "herramienta": "", "ms": 0}
        limpiar = getattr(self.ollama, "limpiar_cancelacion", None)
        if callable(limpiar):
            limpiar()
        self.bus.mensaje("user", texto)
        self.bus.log(f"tú · {recortar(texto, 70)}")
        self.bus.estado("thinking")
        intento = enrutar(texto)
        fallo = False
        via = "chat"
        if intento is not None:
            via = "router"
            self.bus.estado("executing")
            respuesta, herramienta = self._intencion(intento, texto)
            fallo = herramienta in ("error", "sin_cerebro") or "(error)" in herramienta
        else:
            respuesta, herramienta = self._conversar(texto)
            fallo = herramienta in ("error", "sin_cerebro")
        cancelado = bool(getattr(self.ollama, "cancelado", False))
        if cancelado:
            fallo = False
            herramienta = "detenido"
            parcial = (respuesta or "").strip()
            respuesta = f"{parcial} … (turno detenido)" if parcial else "Turno detenido."
        # Un hueco no es un error más: es la lista de lo que le falta a CORT.
        # Se anota sólo lo que falló de verdad, nunca un turno detenido a propósito.
        if fallo and not cancelado:
            self.memoria.anotar_hueco(texto, herramienta or "error")
        respuesta = (respuesta or "").strip() or honesto.no_supe("no llegó ninguna respuesta")
        ms = int((time.monotonic() - t0) * 1000)
        self.bus.evento(
            "error" if fallo else ("detenido" if cancelado else "ejecucion"),
            herramienta or "acción",
            {
                "herramienta": herramienta or "chat",
                "ms": ms,
                "ok": not fallo and not cancelado,
                "via": via,
                "cancelado": cancelado,
            },
        )
        self.memoria.agregar_episodio("user", texto)
        if not cancelado:
            self.memoria.agregar_episodio("assistant", respuesta)
        self.bus.flag("ultima_herramienta", herramienta)
        self.bus.mensaje("cort", respuesta, herramienta, ms)
        self.bus.log(f"cort · {herramienta or 'chat'} · {ms} ms")
        if cancelado:
            self.bus.estado("idle")
        elif self.tts.activo and not self.tts.silencio:
            self.tts.hablar(respuesta)
            self.bus.estado("speaking")
        elif fallo:
            self.bus.estado("error")
        else:
            self.bus.estado("idle")
        return {
            "respuesta": respuesta,
            "herramienta": herramienta,
            "ms": ms,
            "evento": self.bus.instantanea().get("evento", {}),
        }

    # --- intenciones ----------------------------------------------------
    def _intencion(self, intento, texto: str = "") -> tuple[str, str]:
        nombre, args = intento.nombre, dict(intento.args or {})
        if nombre == "saludo":
            return "Hola. Te escucho.", ""
        if nombre == "ayuda":
            return AYUDA, "ayuda"
        if nombre == "apagar":
            self._apagar = True
            return "Hasta luego. Cierro la sesión.", "apagar"
        if nombre == "huecos":
            return self._huecos(), "huecos"
        if nombre == "huecos_olvidar":
            cuantos = self.memoria.olvidar_huecos()
            if cuantos:
                return f"Listo, borré {cuantos} hueco(s). Empiezo de nuevo a anotar lo que no sepa.", "huecos"
            return "No tenía huecos anotados.", "huecos"
        if nombre == "silencio":
            activar = bool(args.get("activar", True))
            self.tts.callar(activar)
            self.bus.flag("silencio", activar)
            return ("Listo, me callo." if activar else "Voz activada."), "voz"
        if nombre == "recordar":
            clave = str(args.get("clave", "")).strip() or "nota"
            valor = str(args.get("valor", "")).strip()
            if not valor:
                return "¿Qué querés que recuerde?", "memoria"
            self.memoria.recordar(clave, valor)
            if clave == "nombre":
                return f"Encantada, {valor.capitalize()}. Lo voy a recordar.", "memoria"
            if clave.startswith("nota"):
                return f"Guardé la nota: «{valor}».", "memoria"
            return f"Guardé que {clave} es {valor}.", "memoria"
        if nombre == "olvidar":
            clave = str(args.get("clave", "")).strip()
            if not clave:
                return "¿Qué querés que olvide?", "memoria"
            cuantos = self.memoria.olvidar(clave)
            if cuantos:
                return f"Borré {cuantos} hecho(s) relacionados con «{clave}».", "memoria"
            return f"No tenía nada guardado sobre «{clave}».", "memoria"
        if nombre == "consultar_memoria":
            hechos = self.memoria.hechos(20)
            if not hechos:
                return "Todavía no sé nada de vos. Podés decirme «me llamo…» o «recuerda que…».", "memoria"
            nombre_usr = self.memoria.hecho("nombre")
            inicio = f"Te llamas {nombre_usr.capitalize()}. " if nombre_usr else ""
            resto = "; ".join(
                (f"nota: {h['valor']}" if h["clave"].startswith("nota") else f"{h['clave']}: {h['valor']}")
                for h in hechos
                if h["clave"] != "nombre"
            )
            if resto:
                return inicio + "Recuerdo: " + resto + ".", "memoria"
            return (inicio.strip() or "No tengo más hechos guardados sobre vos."), "memoria"
        if nombre == "contexto_limpiar":
            self.limpiar_contexto()
            return "Listo, borré el hilo de esta conversación. Los hechos guardados siguen intactos.", "contexto"
        if nombre == "modelo_cancelar":
            datos = self.cancelar_descarga()
            if not datos.get("ok"):
                return datos.get("error", "No hay ninguna descarga en curso."), "modelos (error)"
            return datos["mensaje"], "modelos"
        if nombre == "arnes":
            objetivo = str(args.get("objetivo", "")).strip()
            respuesta, pasos = self.arnes.ejecutar(objetivo, self.ctx, self.memoria.episodios(6))
            etiqueta = "arnés" + (f" ({len(pasos)} pasos)" if pasos else "")
            return respuesta, etiqueta
        if nombre == "alarma_sin_hora":
            return "¿A qué hora la querés? Decime, por ejemplo, «alarma a las 6:30 con ir a MORFO 3».", "alarma"
        if nombre == "app":
            texto, _ = self.registro.ejecutar("abrir_app", {"nombre": args.get("nombre", "")}, self.ctx)
            return texto, "apps"
        if nombre == "modelos_listar":
            datos = self.listar_modelos()
            activo = datos.get("activo") or "ninguno"
            if not datos.get("ok"):
                return (
                    f"No puedo consultar Ollama en {datos.get('url')}: {datos.get('motivo') or 'sin detalle'}. "
                    "Encendé Ollama y volvé a intentar.",
                    "modelos (error)",
                )
            if not datos.get("modelos"):
                return (
                    "Ollama responde, pero no hay modelos instalados. Podés pedirme "
                    "«descarga el modelo qwen3:0.6b» o abrir el panel de modelos del HUD.",
                    "modelos",
                )
            lista = ", ".join(
                f"{m['nombre']} ({m['tamano_gb']} GB)" for m in datos["modelos"]
            )
            return f"Modelos instalados: {lista}. Activo: {activo}.", "modelos"
        if nombre == "modelo_usar":
            pedido = str(args.get("nombre", "")).strip()
            if not pedido:
                return "¿Qué modelo querés usar? Decime el nombre exacto, por ejemplo qwen3:0.6b.", "modelos"
            datos = self.seleccionar_modelo(pedido)
            if not datos.get("ok"):
                return f"No pude cambiar el modelo: {datos.get('error')}", "modelos (error)"
            return f"Listo, el modelo activo ahora es {datos['modelo']}.", "modelos"
        if nombre == "modelo_descargar":
            pedido = str(args.get("nombre", "")).strip()
            if not pedido:
                return (
                    "¿Qué modelo querés descargar? Decime el nombre, por ejemplo "
                    "«descarga el modelo qwen3:0.6b».",
                    "modelos",
                )
            datos = self.descargar_en_segundo_plano(pedido)
            if not datos.get("ok"):
                return f"No pude empezar la descarga: {datos.get('error')}", "modelos (error)"
            return datos["mensaje"], "modelos"

        # herramientas con el mismo nombre que la intención
        if nombre in {
            "hora", "fecha", "clima", "sistema", "buscar", "alarma", "conocimiento",
            "media_reproducir", "media_pausa", "media_reanudar", "media_siguiente",
            "media_anterior", "media_volumen", "media_buscar",
        }:
            if nombre == "alarma":
                args.setdefault("playlist", "")
            texto, estado = self.registro.ejecutar(nombre, args, self.ctx)
            return texto, nombre if estado == "ok" else f"{nombre} (error)"
        return honesto.orden_dudosa(texto), ""

    def _huecos(self) -> str:
        """Lo que CORT no supo, ordenado por cuántas veces le preguntaron."""
        lista = self.memoria.huecos(5)
        total = self.memoria.huecos_total()
        if not lista:
            return (
                "Todavía no tengo huecos anotados. Desde ahora guardo cada pregunta que no "
                "pueda responder, para no perder de vista lo que me falta."
            )
        partes = []
        for h in lista:
            veces = f" ({h['veces']} veces)" if h["veces"] > 1 else ""
            partes.append(f"«{h['pregunta']}»{veces}")
        cuerpo = "; ".join(partes)
        return (
            f"Esto es lo que todavía no sé: {cuerpo}. Son {total} preguntas anotadas. "
            "Si querés empiezo de cero, decime «olvidá lo que no sabés»."
        )

    # --- conversación libre --------------------------------------------
    def limpiar_contexto(self) -> None:
        with self._historial_lock:
            self._historial.clear()
        with self._parcial_lock:
            self._parcial = ""

    def _recordar_turno(self, pregunta: str, respuesta: str) -> None:
        """Guarda el hilo reciente con un tope de mensajes y de caracteres."""
        max_msgs = max(2, int(self.cfg.get("cerebro.historial_mensajes", 8)))
        max_chars = max(400, int(self.cfg.get("cerebro.historial_caracteres", 2400)))
        with self._historial_lock:
            self._historial.append({"role": "user", "content": pregunta})
            self._historial.append({"role": "assistant", "content": respuesta})
            self._historial = self._historial[-max_msgs:]
            while len(self._historial) > 2 and sum(
                len(m["content"]) for m in self._historial
            ) > max_chars:
                self._historial.pop(0)

    def _modelo_compacto(self) -> bool:
        """Los modelos de menos de ~1,5B necesitan un prompt corto para responder a tiempo."""
        nombre = (self.ollama.modelo or "").lower()
        return any(t in nombre for t in ("135m", "270m", "360m", "0.5b", "0.6b", "1b", "1.5b"))

    def _conversar(self, texto: str) -> tuple[str, str]:
        if not self.ollama.disponible():
            self.bus.flag("ollama_ok", False)
            return SIN_CEREBRO, "sin_cerebro"
        compacto = self._modelo_compacto()
        contexto = knowledge.contexto(self.ctx, texto)
        sistema = persona.construir(self.memoria, contexto, compacto=compacto)
        mensajes: list[dict] = [{"role": "system", "content": sistema}]
        with self._historial_lock:
            historial = list(self._historial)
        if historial:
            mensajes.extend(historial[-4:] if compacto else historial)
        else:
            for ep in self.memoria.episodios(4 if compacto else 6):
                rol = "assistant" if ep["rol"] in ("assistant", "cort") else "user"
                mensajes.append({"role": rol, "content": ep["texto"]})
        mensajes.append({"role": "user", "content": texto})
        with self._parcial_lock:
            self._parcial = ""

        def al_token(trozo: str) -> None:
            with self._parcial_lock:
                self._parcial = (self._parcial + trozo)[-700:]

        respuesta = self.ollama.conversar(
            mensajes, al_token=al_token, num_predict=120 if compacto else None
        )
        with self._parcial_lock:
            self._parcial = ""
        if getattr(self.ollama, "cancelado", False):
            return respuesta, "detenido"
        self.bus.flag("ollama_ok", True)
        self.bus.flag("modelo", self.ollama.modelo)
        if not respuesta:
            detalle = self.ollama.ultimo_error or "sin detalle"
            return honesto.fallo_modelo(detalle), "error"
        self._recordar_turno(texto, respuesta)
        return respuesta, "chat"

    # --- voz ------------------------------------------------------------
    def _parcial_texto(self) -> str:
        with self._parcial_lock:
            return self._parcial

    def escuchar_una_vez(self) -> dict:
        if not self.stt.disponible:
            return {"ok": False, "mensaje": f"El micrófono no está listo: {self.stt.motivo}."}
        texto = self.stt.escuchar()
        if not texto:
            return {"ok": False, "mensaje": "No te escuché. Probá de nuevo."}
        return {"ok": True, "mensaje": self.responder(texto)["respuesta"]}

    # --- estado para el HUD --------------------------------------------
    def capacidades(self) -> dict:
        """Herramientas reales agrupadas para el panel de capacidades del HUD."""
        grupos: dict[str, list[dict]] = {clave: [] for clave in CATEGORIAS}
        for nombre in self.registro.nombres():
            tool = self.registro.obtener(nombre)
            if tool is None:
                continue
            grupos.setdefault(tool.categoria, []).append(
                {
                    "nombre": tool.nombre,
                    "descripcion": tool.descripcion,
                    "riesgo": tool.riesgo,
                    "ejemplo": tool.ejemplo,
                }
            )
        categorias = [
            {"id": clave, "nombre": nombre, "herramientas": grupos[clave]}
            for clave, nombre in CATEGORIAS.items()
            if grupos.get(clave)
        ]
        return {"ok": True, "total": len(self.registro.nombres()), "categorias": categorias}

    def estado_hud(self) -> dict:
        snap = self.bus.instantanea()
        ahora = datetime.now()
        alarmas = []
        for a in self.memoria.proximas_alarmas(3):
            alarmas.append({"cuando": a.get("cuando"), "texto": a.get("texto")})
        snap.update(
            {
                "hora": ahora.strftime("%H:%M:%S"),
                "fecha": fecha_larga(ahora),
                "iso": ahora.isoformat(timespec="seconds"),
                "version": __version__,
                "alarmas": alarmas,
                "modelo": self.ollama.modelo,
                "descargando": self._descargando,
                "descarga": dict(self._progreso, modelo=self._descargando) if self._descargando else dict(self._progreso),
                "parcial": self._parcial_texto(),
                "huecos": self.memoria.huecos(5),
                "huecos_total": self.memoria.huecos_total(),
                "voz": {
                    "tts": self.tts.disponible,
                    "tts_activo": self.tts.activo,
                    "silencio": self.tts.silencio,
                    "stt": self.stt.disponible,
                    "motivo_stt": self.stt.motivo,
                },
            }
        )
        return snap
