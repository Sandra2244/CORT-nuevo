# CORT 2.0 — Arquitectura híbrida y autonomía

**Fecha:** 2026-10-29.
**Estado:** plano aprobado; la 2.0.1 está publicada como APK 3.1.2 y la 2.0.2 (voz propia)
está en `main`. Las fases 2.0.3 a 2.0.7 siguen sin código.
**Base:** CORT 1.7 (158 pruebas, HUD con orbe, APK `com.cort.ia` 3.0.1 firmado) + 2.0.1 y
2.0.2.
**Origen de las decisiones:** conversación con Claude del 29/10 (lectura en voz alta,
rol de asistente, Plan B), video de referencia `I Built a Real J.A.R.V.I.S` (HUD de
telemetría), y las cuatro respuestas de la encuesta de hoy.

---

## 1. Lo que se decidió

| Pregunta | Decisión |
| --- | --- |
| Cómo entra al teléfono | **Rol de asistente + overlay desde el día uno**, con tile del panel rápido como tercer camino |
| Dónde razona | **Híbrido real**: modelos en el teléfono *y* en la PC, elegidos por tarea, batería y red. La PC no es obligatoria |
| Primer incremento | **Modo estudio**: seleccionar texto → «Leer con CORT» → voz neuronal → sigue con la pantalla apagada |
| Voz | **Piper / sherpa-onnx** `es_ES` + `es_MX` calidad media, offline, precargada |

La segunda respuesta tiene una consecuencia que conviene decir en voz alta: si el
teléfono tiene que poder trabajar solo, **no puede ser un `WebView`**. Un `WebView` es
una ventana a la PC; un asistente híbrido es un programa con servicios, modelos y cola
de audio propios. El APK actual se queda como «modo espejo» y encima se construye el
CORT de verdad.

---

## 2. Principios (no se negocian)

1. **Verificar antes de afirmar.** Toda respuesta sobre la pantalla cita el fragmento
   leído; si el OCR falla o no hay texto, lo dice. Nunca inventa una imagen que no le
   llegó. Es la misma regla que ya rige las herramientas desde la fase 1.
2. **Local primero, nube nunca.** Nada de Claude, Gemini ni ElevenLabs en el camino
   crítico. Si un modelo no está, se descarga o se avisa; no se sustituye por uno remoto.
3. **Contratos antes que código.** Una habilidad es un manifiesto con permisos, no una
   función perdida en un `if`. Lo que sobrevive a los rediseños es el contrato.
4. **Degradación honesta.** Sin PC: modo local limitado, dicho en la interfaz. Sin
   modelo: lectura y OCR. Sin batería: aviso y pausa.
5. **Nada irreversible sin confirmación.** Riesgo alto (borrar, enviar, comprar, abrir
   cámara) exige aprobación explícita de Sandra, siempre.
6. **Presupuesto de equipo.** PC: 2 núcleos, 1,8 GiB. Teléfono: gama media. Ninguna
   animación ni modelo puede comerse el equipo. Todo con límite medido, no supuesto.

---

## 3. Las cuatro capas

```text
┌──────────────────────────── TELÉFONO (Kotlin) ────────────────────────────┐
│  Presencia        Rol de asistente · overlay · tile · «Leer con CORT»       │
│  Voz local        Piper/sherpa TTS · sherpa STT · cola + MediaSession       │
│  Modelo local     Qwen2.5-0.5B / Gemma-3-1B int4 (llama.cpp o MediaPipe)    │
│  Cliente          sincroniza memoria y skills con la PC cuando hay red      │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │ JSON-RPC 2.0 sobre HTTP + token
                                │ (LAN o Tailscale; nunca puertos abiertos)
┌───────────────────────────────┴───────────────────────────────────────────┐
│                        NÚCLEO (Python, ya existe)                          │
│  router · app · bus · brain/{memory, ollama, persona, harness}             │
│  + nuevo: skills/ (manifiestos) · agent/ (planificador) · telemetry/       │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │
┌───────────────────────────────┴───────────────────────────────────────────┐
│                          HUD (HTML/CSS/JS)                                 │
│  orbe + 9 estados + reloj  ·  paneles de telemetría 2.0  ·  trazas          │
└───────────────────────────────────────────────────────────────────────────┘
```

El teléfono **no** es un cliente tonto ni un segundo CORT: es el mismo CORT con menos
capacidad. Comparten contrato, memoria (sincronizada) y las mismas skills.

---

## 4. El contrato de skill

Hoy una herramienta es una función Python registrada a mano en `cort/tools/__init__.py`
con `nombre`, `descripcion`, `esquema`, `riesgo`, `categoria` y `ejemplo`. Eso ya es
media idea; falta convertirla en algo externo, versionable y ejecutable en otro lenguaje.

**Formato:** `skills/<id>/skill.json` + el ejecutable que sea.

```json
{
  "id": "leer.texto",
  "version": "1.0.0",
  "descripcion": "Lee en voz alta el texto recibido, troceado por frases.",
  "categoria": "estudio",
  "riesgo": "bajo",
  "permisos": ["audio.salida"],
  "entradas": {
    "texto": {"tipo": "string", "max": 20000},
    "voz": {"tipo": "enum", "valores": ["es_ES", "es_MX"], "defecto": "es_ES"}
  },
  "salidas": {"audio": "stream", "duracion_s": "number"},
  "ejemplo": "Seleccionar un párrafo en Notas y pulsar «Leer con CORT»",
  "timeout_s": 300,
  "plataformas": ["pc", "android"]
}
```

**Ejecución:** JSON-RPC 2.0, el mismo patrón del Model Context Protocol (especificación
abierta). Métodos: `skills.list`, `skills.describe`, `skills.call`, `skills.cancel`.
Transporte: `stdio` para skills locales del núcleo; HTTP+token para el teléfono.

**Qué gana Sandra con esto:** una skill nueva se escribe sin tocar el núcleo, en Python,
Kotlin o cualquier lenguaje que sepa hablar JSON-RPC. Migrar las 16 herramientas actuales
no rompe nada: se envuelven con un manifiesto generado y siguen siendo las mismas
funciones, con sus pruebas.

**Permisos:** cada skill declara lo que toca (`audio.salida`, `red`, `apps.abrir`,
`archivos.leer`, `pantalla.leer`, `memoria.escribir`). El registro rechaza la llamada si
el permiso no está concedido para esa skill. Esto es lo que evita que una skill nueva
pueda borrar archivos por accidente.

---

## 5. Ciclo de agente (la autonomía, con freno)

```text
objetivo → planificar → [paso 1..n] → verificar → reportar
                │            │
                │            └─ presupuesto: 8 pasos, 240 s, 1 modelo
                └─ cada paso: skill + argumentos + permiso + traza
```

- **Planificador:** el modelo propone pasos en JSON; el núcleo valida que la skill exista
  y que el permiso esté concedido antes de ejecutar. Si el JSON no valida, no se ejecuta
  nada y se pide otro plan (máximo 2 intentos).
- **Presupuesto:** 8 pasos y 240 s por objetivo en la PC; 4 pasos y 90 s en el teléfono.
  Al agotarse, CORT para y cuenta qué alcanzó a hacer. Nunca sigue «a ver si sale».
- **Aprobación:** riesgo medio o alto → tarjeta ALLOW/DENY en el HUD o notificación en el
  teléfono. Ya estaba planeada en la fase 1.6; pasa a ser obligatoria en 2.0.
- **Verificación:** tras ejecutar, un paso de comprobación (¿existe el archivo?, ¿responde
  el servicio?) antes de decir «listo».
- **Traza:** cada paso se guarda en SQLite (`runs`, `steps`) con duración, resultado y
  error. El HUD los muestra como línea de tiempo. Es lo que hace que se pueda depurar en
  vez de adivinar.

---

## 6. Router híbrido de modelos

Esta es la pieza que responde a «debe ser dinámico, adaptativo e híbrido».

**Inventario por dispositivo** (se descubre, no se supone):

| Capacidad | PC | Teléfono |
| --- | --- | --- |
| TTS | Piper (`es_ES`, `es_MX`) | Piper/sherpa ONNX |
| STT | whisper.cpp o Vosk | sherpa-onnx streaming |
| LLM | Ollama (qwen2.5:0.5b, gemma3:1b, …) | 0.5B–1B int4 (llama.cpp / MediaPipe) |
| Visión | modelo de visión en Ollama | ninguna: manda la imagen a la PC |

**Regla de decisión**, en este orden:

1. ¿La tarea es hablar o transcribir? → **local siempre**: la latencia de red arruina la
   conversación y el audio no sale del dispositivo.
2. ¿Es una skill determinista (hora, alarma, abrir app)? → **no usa modelo**.
3. ¿Hay PC alcanzable, batería > 20 % y la tarea es de razonamiento o visión? → **PC**.
4. Si no, ¿hay modelo local cargado y la tarea cabe en 4 pasos? → **local**, avisando
   «modo limitado».
5. Si no hay nada → lectura, OCR y respuesta por reglas; se dice qué falta y qué descargar.

**Sincronización:** la memoria viaja por eventos (hechos nuevos, episodios), no por copia
completa del archivo SQLite. Un `revision` incremental evita conflictos cuando el teléfono
estuvo sin red. Las skills se sincronizan por manifiesto y versión.

**Medición obligatoria** antes de dar esto por bueno: latencia por camino, tokens/s,
batería en 10 minutos de lectura con pantalla apagada, RAM del modelo cargado. Números
reales en `docs/MEDICIONES.md`; hasta entonces, cada cifra es estimación.

---

## 7. Android: las piezas y sus trampas

| Pieza | Para qué | Trampa real |
| --- | --- | --- |
| `ACTION_PROCESS_TEXT` | «Leer con CORT» al seleccionar en WhatsApp/Notas | Telegram a veces no lo muestra; queda «Compartir» |
| `Service` + `mediaPlayback` + `MediaSession` | leer con pantalla apagada y pausa desde audífonos | Android 14+ exige `foregroundServiceType` y permiso propio; One UI mata servicios |
| `VoiceInteractionService` | ser el asistente del botón lateral y recibir pantalla | One UI puede no listar terceros; hay que probarlo en el A16 |
| `TYPE_APPLICATION_OVERLAY` | el chat transparente tipo Gemini | requiere «mostrar sobre otras apps»; no puede leer apps con `FLAG_SECURE` |
| `TileService` | abrir CORT desde el panel rápido | es el Plan B que siempre funciona |
| `RecognizerIntent` / `SpeechRecognizer` | dictado rápido | depende del motor del sistema; sherpa es el respaldo offline |
| Piper/sherpa TTS | voz natural sin red | primera carga lenta: precargar al iniciar el servicio |
| Modelo local | razonar sin PC | RAM, calor y batería; límite de 1B int4 y aviso de consumo |

**Build:** el APK ligero sigue con `aapt2 ▸ javac ▸ d8` (sin Gradle). Cuando entren ML Kit
o sherpa-onnx como `.aar`, se añade un segundo pipeline con Gradle y se conserva el
primero. Dos pipelines, un solo `-firma.txt` con la misma llave y la misma huella.

**Ajustes guiados (pantalla de bienvenida):** batería sin restricciones, quitar de «apps
en suspensión», micrófono, notificaciones y «mostrar sobre otras apps». Con `PowerManager`
se detecta si sigue optimizado y se avisa. Sin esto, el servicio muere a los minutos y
parece un fallo del código.

---

## 8. HUD 2.0 (conservando el orbe)

Del video se toma **la estructura**, no el arte:

```text
┌──────────────┬───────────────────────────────────┬──────────────┐
│ 01 VOZ       │                                   │ 05 MODELOS   │
│ 02 ACTIVIDAD │        ORBE + ESTADO              │ 06 MÁQUINAS  │
│ 03 TURNOS    │        (centro, 420 px)           │ 07 SKILLS    │
│ 04 VISTAS    │        chat + entrada abajo       │ 08 DIAGNÓSTICO│
│    SESIÓN    │                                   │ 09 AUTOMATIZA│
└──────────────┴───────────────────────────────────┴──────────────┘
```

- **Orbe:** se conserva el de filamentos; se le añade el anillo de marcas y la palabra de
  estado en versalitas dentro (`EN ESPERA`, `PROCESANDO`, `ESCUCHANDO`), como en el video.
- **Paneles:** mismo lenguaje que ya tenés (borde fino, etiqueta en versalitas, número de
  panel a la derecha) pero con datos reales: latencias del turno, tokens/s del modelo
  activo, RAM y CPU de PC y teléfono, skills cargadas con su versión, salud y tareas.
- **Máquinas:** PC y teléfono en la misma lista con su estado. Es la pieza que hoy no
  existe y la que hace visible el híbrido.
- **Vistas:** chat, trazas (línea de tiempo de un objetivo) y tablero de tareas. Sin Kanban
  de adorno: columnas `pendiente / en curso / hecho / falló`.
- **Presupuesto de rendimiento:** 60 fps en la PC con el orbe activo; 30 fps y sin sombras
  en el teléfono; animación pausada cuando la pestaña no está visible. Se mide con el
  rendimiento real, no con la intención.

---

## 9. Memoria 2.0

Lo que hay: `facts`, `episodes`, `alarms`, `meta` y, desde la 2.0.2, `gaps`. Lo que se
añade:

| Tabla | Para qué |
| --- | --- |
| `gaps` *(ya está)* | lo que CORT no supo ni pudo hacer: pregunta normalizada, motivo, veces y última fecha. Alimenta «¿qué no sabés?» y, más adelante, las skills que faltan |
| --- | --- |
| `notes` + FTS5 | índice de `knowledge/*.md` con búsqueda por palabra y por frase |
| `runs` / `steps` | trazas del agente, con duración y error |
| `skills_seen` | qué skills usó, cuántas veces, cuánto tardaron, tasa de fallo |
| `devices` | PC y teléfono: última conexión, versión, modelos disponibles |
| `study_sessions` | qué se leyó, cuánto duró, dónde se quedó (para retomar) |

`study_sessions` no es decoración: es lo que permite que mañana CORT diga «seguimos por
el diafragma urogenital, donde lo dejaste», en vez de empezar de cero.

---

## 10. Fases, con criterio de aceptación

| Fase | Qué se construye | Se acepta cuando |
| --- | --- | --- |
| **2.0.1 Estudio** | `ACTION_PROCESS_TEXT`, TTS Piper, servicio en primer plano con `MediaSession`, bienvenida de permisos, cola por frases | Seleccionás un párrafo en Notas, suena en < 2 s, sigue 10 min con pantalla apagada y pausa desde los audífonos |
| **2.0.2 Voz propia** | `honesto.py` como única fuente de los fallos, persona cálida con protocolo de «no sé», tabla `gaps` y consulta «¿qué no sabés?» | Toda respuesta sin modelo o con error sale de `honesto.py`; una pregunta no respondida queda anotada con su motivo y se puede listar y borrar (177 pruebas) |
| **2.0.3 Presencia** | Overlay transparente, tile, rol de asistente, «¿qué ves?» con grounding | El overlay abre encima de WhatsApp; «¿qué ves?» cita el texto real o dice que no ve nada; el botón lateral abre CORT (o se documenta que One UI no lo permite) |
| **2.0.4 Skills** | Manifiestos, registro con permisos, JSON-RPC, migración de las 16 herramientas | Una skill nueva se escribe fuera del núcleo, se lista en el HUD y sus pruebas fallan si se le quita el permiso |
| **2.0.5 Agente** | Planificador, presupuesto, aprobación ALLOW/DENY, `runs`/`steps`, vista de trazas | Un objetivo de 3 pasos se ejecuta, se ve la traza y se detiene al agotar presupuesto sin efectos raros |
| **2.0.6 HUD 2.0** | Paneles del video, máquinas, skills, diagnóstico, tablero | 60 fps con el orbe activo; los datos son reales; el teléfono se ve como máquina conectada |
| **2.0.7 Híbrido** | Modelo local en el teléfono, router por tarea, sincronización de memoria | Con la PC apagada, el teléfono responde 2 de 3 consultas cortas sin mentir; la batería aguanta la lectura de 10 min |

Cada fase se publica con su etiqueta y su `-firma.txt`, como la 1.7. Nada se anuncia como
hecho sin la medición correspondiente.

---

## 11. Qué se descarga, de dónde y para qué

| Pieza | Origen | Licencia | Tamaño aprox. | Fase |
| --- | --- | --- | --- | --- |
| Piper (voces `es_ES`, `es_MX`) | rhasspy/piper | MIT | 60–90 MB por voz | 2.0.1 |
| sherpa-onnx (runtime Android) | k2-fsa/sherpa-onnx | Apache-2.0 | AAR + modelos | 2.0.1 / 2.0.6 |
| whisper.cpp | ggerganov/whisper.cpp | MIT | 75 MB (tiny q5) | 2.0.6 |
| llama.cpp (GGUF en Android/PC) | ggerganov/llama.cpp | MIT | binario + modelo | 2.0.6 |
| ML Kit Text Recognition | Google (on-device) | propietaria, gratis | ~10 MB | 2.0.2 |
| Especificación MCP | modelcontextprotocol | abierta | — | 2.0.3 |

**No se instala:** LangGraph, AutoGen, Letta/MemGPT, ni frameworks de agentes en la nube.
Arrastran cientos de megas, piden GPU o servicios externos y en 1,8 GiB congelan el equipo.
Se copian las ideas (memoria jerárquica, grafo de estados), no el runtime.

---

## 12. Riesgos y su freno

| Riesgo | Freno |
| --- | --- |
| One UI no lista CORT como asistente | Overlay + tile desde el día uno; el rol es un extra, no la base |
| El servicio muere en segundo plano | Bienvenida de batería, `PowerManager` y aviso; medir 10 min con pantalla apagada |
| El modelo local calienta el teléfono | 1B int4 máximo, presupuesto de 90 s, aviso de consumo y botón de parar |
| Gradle rompe el APK que funciona | Dos pipelines; la firma y la huella se comprueban igual en ambos |
| La sincronización pisa datos | Eventos con `revision` incremental, nunca copiar el `.db` completo |
| Se pierde el hilo y hay que empezar de cero | Contratos y manifiestos: lo escrito como skill sobrevive a cualquier rediseño |
| Medir mal y prometer de más | `docs/MEDICIONES.md` con números reales o la fila no se escribe |

---

## 13. Lo que este plano no incluye

- Avatar 3D o Live2D: el orbe se queda; un retrato por capas es fase posterior.
- Nube de ningún tipo: ni voz, ni modelo, ni sincronización.
- Reentrenar un modelo: CORT usa modelos existentes y apuntes; enseñarle anatomía es
  indexar `knowledge/`, no fine-tuning.
- Sustituir el HUD por una app de escritorio nativa: el navegador sigue siendo el lienzo.

---

*Estado al 2026-10-29: la 2.0.1 quedó publicada como APK `3.1.2` con la voz del sistema
(`es_ES` ▸ `es_MX`) y la tubería completa —`ACTION_PROCESS_TEXT`, servicio en primer plano
`mediaPlayback`, `MediaSession`, troceo por frase y reanudación por hash del texto—. Lo
medido está en `docs/MEDICIONES.md`. La sustitución por Piper es 2.0.1b y espera la prueba
en el A16: primero se valida la tubería, después se cambia el motor.

La 2.0.2 («Voz propia») está en `main`: `cort/brain/honesto.py` concentra los fallos, la
persona es cálida y dice el límite en la primera frase, y todo turno que no se pudo cerrar
queda en `gaps` con su motivo. Es el carácter de CORT lo que se probó ahí, no una animación:
177 pruebas en local, incluida la de que un turno cancelado por Sandra **no** se anota como
hueco.*
