# CORT — Prompt maestro del proyecto

> Documento de referencia único. Cualquier agente o copiloto que retome CORT debe leer
> este archivo antes de escribir código. La visión es de Sandra; la ingeniería se adapta
> a los recursos reales (portátil de 2 núcleos y 1,8 GiB de RAM, Samsung A16 de 4 GB,
> y el equipo de Askher Vargas con ~8 GB).
>
> Versión: 1.0 — 2026-10-27. Reconstrucción desde cero en `~/Vídeos/CORT`.

---

## 1. Qué es CORT

CORT es un asistente personal local, con voz, memoria persistente y una interfaz
holográfica. No es un chatbot dentro de una pestaña: es una presencia que vive en la
computadora, se activa al decir su nombre, ejecuta tareas reales y recuerda a su usuario.

El nombre es un acrónimo y también una declaración de intenciones:

| Letra | Significado | Qué obliga en el código |
|---|---|---|
| **C** | Cognitiva | Núcleo de razonamiento, memoria y aprendizaje; no solo reflejos de comandos. |
| **O** | Omnipresente | Corre en PC y móvil, arranca con el sistema, escucha cuando se le llama. |
| **R** | Rapsodia | Una pieza expresiva, libre y artística: el HUD, la voz y las animaciones no son decoración, son identidad. |
| **T** | Terminal | Scripts, línea de comandos y herramientas livianas; CORT es también un copiloto técnico. |

Palabras de activación: **«CORT»** y **«Sofi»** (esta última para el modo femenino
cercano). La voz de respuesta es femenina, en español, cálida y breve; nunca robótica
por elección, aunque `espeak-ng` sea el motor disponible al inicio.

### 1.1 Promesa al usuario

- Todo corre localmente por defecto. Nada de conversaciones se envía a la nube sin
  que el usuario lo pida.
- CORT **no inventa**. Si no sabe, no tiene red o una herramienta falla, lo dice con
  una frase honesta y explica qué falló.
- CORT **no ejecuta acciones destructivas** (borrar, apagar, enviar mensajes,
  publicar) sin confirmación explícita.
- CORT recuerda lo que el usuario le confía, y también sabe olvidar cuando se le pide.

---

## 2. Referencias visuales y funcionales

Estas son las referencias declaradas por Sandra. No son links: son archivos locales.

| Archivo | Qué aporta |
|---|---|
| `~/Escritorio/Referencias IA CORT/VID-20261024-WA0034.mp4` | HUD con orbe de partículas, reloj cian, panel de terminal, chat inferior, selector de agente (Gemini, Claude, Groq, Mistral, Grok); el orbe cambia a verde al activarse. |
| `~/Escritorio/Referencias IA CORT/f7d16b9e47ae45c813969bed77fedcf3.mp4` | Estética principal: esfera de puntos blanca/cian sobre negro, núcleo brillante, filamentos radiales, HUD minimalista, paneles translúcidos que se abren sobre el orbe. |
| `~/Escritorio/Referencias IA CORT/a074ef6a5fb08f4108de2d3934cd9d9e.mp4` | Capa de «arnés» de agentes: OpenClaw y HERMES-AGENT. Se implementa como adaptadores enchufables, no como dependencia obligatoria. |
| `~/Escritorio/Referencias IA CORT/Como crear un Asistente Virtual propio (J.A.R.V.I.S.) (Episodio 1)(480P).mp4` | Comandos por voz, apertura de apps, YouTube, Google, música, memoria, interfaz. |
| `~/Escritorio/Referencias IA CORT/Cómo crear un asistente Virtual Propio (J.A.R.V.I.S. casi muere a mitad de camino) _ (EPISODIO 2)(720P_HD).mp4` | Clima en tiempo real, capas de seguridad, HUD con partículas, errores de contexto al cambiar de modelo. |
| `~/Escritorio/Promp CORT Idea y Desarrollo` | Prompt original de Sandra; este documento lo expande sin contradecirlo. |

El CORT viejo (`~/Documentos/CORT`) **no se copia**: tiene fallas acumuladas y su
interfaz no alcanza la referencia. Se usa solo como memoria de errores a no repetir.

---

## 3. Experiencia objetivo

### 3.1 El HUD

Pantalla completa o ventana sin bordes, fondo casi negro con un degradado radial
levemente azulado. En el centro, un **orbe** de partículas:

- Esfera de puntos distribuida con espiral de Fibonacci, rotación lenta y ruido
  orgánico, no una esfera perfecta.
- Núcleo luminoso con halo, y **filamentos** que salen del centro hacia la superficie,
  como descargas de plasma.
- Puntos con estelas cortas y `shadowBlur` moderado; nunca un `blur()` de CSS sobre
  toda la pantalla (mata la CPU).
- Anillos orbitales finos, marcas de graduación y arcos que aparecen al pensar o hablar.
- Al activarse, una onda recorre la esfera y el color pasa del cian al verde.
- Al hablar, el orbe pulsa con la envolvente de la voz (amplitud simulada al inicio,
  luego amplitud real de `espeak`/Piper).

Elementos de interfaz, tomados de los videos:

| Zona | Contenido |
|---|---|
| Arriba al centro | Reloj digital `HH:MM:SS` y fecha en español, cian con resplandor suave. |
| Arriba a la izquierda | Bloque monoespaciado tipo terminal: 3–6 líneas de estado (modelo, memoria, última herramienta). |
| Arriba a la derecha | Widgets pequeños: batería, micrófono, red, CPU/RAM. |
| Bajo el orbe | Píldora de estado con iconos (escuchando, pensando, hablando, en silencio) y texto corto. |
| Abajo | Chat: mensajes del usuario en burbuja cálida (ámbar/rojo suave) y de CORT en cian translúcido; campo de texto con placeholder «Habla o escribe…». |
| Esquinas | Retícula tenue, coordenadas y versión; nada que compita con el orbe. |

Paleta base (variables CSS, no valores sueltos):

```
--bg:        #03060a
--bg-glow:   #071726
--cyan:      #6ff3ff
--cyan-soft: #2a93a8
--white:     #eafcff
--green:     #7dffb2   (activación / escucha)
--amber:     #ffc46b   (pensando)
--violet:    #b18cff   (herramientas / arnés)
--red:       #ff6b6b   (error / aviso)
--user:      #ff9a7a   (burbuja del usuario)
```

Estados y color:

1. `idle` — cian tenue, rotación lenta, respiración suave.
2. `listening` — verde, ondas concéntricas, micrófono activo.
3. `thinking` — ámbar/violeta, filamentos más rápidos, arcos girando.
4. `speaking` — cian brillante con pulsos ligados a la voz.
5. `error` — rojo contenido, una sola sacudida, sin dramatismo.
6. `offline` — gris azulado; el orbe sigue vivo pero apagado.

Rendimiento: el HUD debe mantenerse por debajo del **8 % de CPU** en el portátil y
usar menos de **120 MB** de RAM en el navegador. Para lograrlo:

- Partículas adaptativas: 900 puntos en escritorio, 380 en móvil, 220 si
  `prefers-reduced-motion` o batería baja.
- `requestAnimationFrame` con tope de 30 FPS; pausa total cuando la pestaña se oculta.
- Un solo canvas; sin librerías de animación; sin imágenes de fondo pesadas.
- El chat y los medidores se actualizan por sondeo cada 700 ms, no por frame.

### 3.2 El chat

No es una lista infinita: muestra los últimos ~40 mensajes, con desplazamiento suave.
Cada respuesta puede llevar una etiqueta discreta con la herramienta usada
(`clima`, `sistema`, `memoria`, `arnés`) y el tiempo de respuesta. Los errores se
muestran como mensajes normales, nunca como alertas del navegador.

### 3.3 La voz

- Palabra de activación: «CORT» o «Sofi», tolerante a acentos y ruido.
- Al escuchar la palabra, CORT responde con un tono corto y pasa a `listening`.
- Detección de fin de frase por silencio (VAD simple por energía) y límite de 8 s.
- **Barge-in**: si el usuario habla mientras CORT responde, se corta la voz y se escucha.
- TTS: `espeak-ng` (offline, ya instalado) con voz femenina española, velocidad ~165;
  Piper como mejora opcional cuando se descargue una voz `es_ES`/`es_MX`.
- STT: Vosk español (~50 MB, offline). Sin Vosk, CORT funciona por texto y lo dice.
- Modo silencioso: responde solo en el chat, sin voz.

---

## 4. Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│ HUD (HTML/CSS/JS, canvas)  ←→  servidor local (Python)      │
│   orbe · reloj · chat · medidores · estados                 │
└───────────────▲───────────────────────────────┬─────────────┘
                │ estado (sondeo 700 ms)        │ POST /api/chat
┌───────────────┴───────────────────────────────▼─────────────┐
│ Aplicación (cort/app.py)                                    │
│  · Router determinista (comandos en español)                │
│  · Arnés de agentes (bucle de herramientas)                 │
│  · Bus de eventos y estado compartido                       │
└───────┬───────────────┬───────────────┬───────────────┬─────┘
        │               │               │               │
┌───────▼─────┐ ┌───────▼─────┐ ┌───────▼─────┐ ┌───────▼─────┐
│ Memoria     │ │ Cerebro     │ │ Herramientas│ │ Voz         │
│ SQLite      │ │ Ollama      │ │ clima, hora │ │ espeak/Vosk │
│ hechos,     │ │ qwen3:0.6b  │ │ sistema,    │ │ wake word   │
│ episodios,  │ │ qwen2.5:0.5b│ │ apps, media │ │ barge-in    │
│ alarmas     │ │ 2b opcional │ │ web, alarma │ │             │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

Principios de ingeniería:

1. **El router va primero.** La mayoría de órdenes («qué hora es», «abre la
   calculadora», «clima en Caracas») se resuelven sin LLM: instantáneo, determinista y
   funciona con Ollama apagado.
2. **El LLM es para conversar y razonar**, no para elegir cómo abrir una app.
3. **Memoria en SQLite**, no en JSON: escrituras atómicas, sin archivos corruptos.
4. **Toda dependencia pesada es opcional** (`vosk`, `pywebview`, `piper`). Sin ellas,
   CORT degrada con dignidad.
5. **Un solo proceso** para núcleo, HUD y voz; hilos con locks para el estado.
6. **Nada de `shell=True`** con texto del usuario. Allowlist de apps y comandos.

---

## 5. Memoria

Tres capas, todas en `~/.local/share/cort/cort.db` (o `data/` en modo portátil):

- **Hechos** (`facts`): clave, valor, confianza, origen, fecha. Ejemplos: nombre del
  usuario, ciudad, materia, playlist favorita, nombres de familiares.
- **Episodios** (`episodes`): turnos de conversación recientes, con poda a 500.
- **Alarmas** (`alarms`): hora, texto, playlist opcional, estado.

Reglas:

- «Me llamo…», «mi hermana se llama…», «recuerda que…», «prefiero…», «vivo en…» se
  guardan de forma determinista, sin depender del modelo.
- «Olvida…» borra el hecho correspondiente y lo confirma.
- El prompt del sistema incluye fecha/hora reales y hasta 20 hechos relevantes.
  Esto corrige el bug clásico de CORT respondiendo un día al azar.
- El usuario puede ver y borrar todo con `recuerda` / `olvida` / `memoria` en el chat.
- El conocimiento documental vive en `knowledge/` (`.md`, `.txt`): se indexa por
  párrafos y se consulta por palabras clave, sin embeddings ni dependencias.

---

## 6. Herramientas (contrato)

Todas devuelven un texto breve en español y un estado (`ok`, `error`, `sin_datos`).
Nunca lanzan excepciones hacia el HUD.

| Herramienta | Frases de ejemplo | Comportamiento y fallos |
|---|---|---|
| `hora` | «qué hora es», «qué día es hoy» | Lee el reloj del sistema; nunca inventa. |
| `clima` | «clima», «va a llover», «temperatura en Maracaibo» | IP → ciudad (`ip-api.com`), luego `open-meteo.com`. Si falla la ubicación o la red: «No puedo consultar el clima real en este momento…». Cache 10 min. |
| `sistema` | «cómo está la PC», «cuánta RAM», «CPU» | `psutil`: CPU, RAM, disco, batería. Avisa si CPU > 85 % o RAM > 90 %. |
| `apps` | «abre la calculadora», «abre archivos» | Allowlist (`config/cort.toml`). App desconocida: lista las disponibles. |
| `media` | «reproduce X», «pausa», «reanuda», «siguiente», «+10 segundos» | MPRIS vía `playerctl` si existe; si no, VLC en segundo plano con pausa por señal; YouTube/Google en el navegador. |
| `buscar` | «busca en Google…», «busca en YouTube…» | Abre la búsqueda en el navegador; devuelve la URL. |
| `alarma` | «alarma a las 6:30 con…», «recuérdame…» | Guarda en SQLite, hilo comprobador cada 20 s, avisa con voz + notificación. |
| `conocimiento` | «qué sabes de…», «consulta mis apuntes» | Busca en `knowledge/`, devuelve fragmentos con su archivo. |
| `memoria` | «recuerda…», «olvida…», «qué sabes de mí» | Solo hechos del usuario. |

El arnés puede encadenar 2–3 herramientas, pero cada paso se registra y se muestra en
el panel de terminal del HUD. Las acciones con efecto externo (enviar mensaje, borrar,
apagar) exigen confirmación y quedan fuera de la primera entrega.

---

## 7. Arnés de agentes

El «arnés» es la capa que convierte un LLM en agente: recibe un objetivo, decide qué
herramienta usar, ejecuta, observa el resultado y repite hasta responder.

Diseño de CORT:

- Bucle máximo de **3 pasos**, presupuesto de 20 s por turno.
- Contrato JSON: `{"tool": "clima", "args": {"ciudad": "Caracas"}}` o
  `{"respuesta": "texto final"}`.
- Validación estricta: herramienta desconocida o argumentos inválidos → se corrige una
  vez y, si vuelve a fallar, se responde con el router o se pide aclaración.
- Registro de cada paso en el HUD (`arnés · paso 2 · sistema`).
- Adaptadores previstos (fase 2): **OpenClaw** y **HERMES-AGENT**, como procesos
  externos opcionales, nunca como requisito para arrancar. CORT debe seguir funcionando
  si no están instalados.

---

## 8. Automatizaciones y vida diaria

Ideas de Sandra que se incorporan al roadmap:

- Alarma de las 6:30 con mensaje leído: «Buenos días. Hoy toca MORFO 3, tema: ciclo de
  la urea», y opción de reproducir «Brooklyn Blood Pop» o una playlist.
- Playlists ordenadas por carpetas (`Dark Rose`, `looksmaxing`) y reproducción por
  número; pausa, reanudación, avance de 5/10 s.
- Recordatorios con hora y mensaje; en fase 2, envío a WhatsApp (requiere API o
  automatización del teléfono, no se promete en la primera entrega).
- Abrir calculadora, archivos, juegos y apps del sistema con allowlist.
- Escaneo de sistema en segundo plano con avisos suaves, sin robar foco.
- Arranque automático al iniciar sesión (Linux: `.desktop` en `~/.config/autostart`;
  Windows: `.vbs`/acceso directo en la carpeta de inicio; Android: fase 2).
- Conexión multi-dispositivo (PC ↔ A16): fase 2, mediante un pequeño servidor local
  con token; nunca expuesto a internet sin autenticación.

---

## 9. Plataformas y recursos

| Plataforma | Estado | Notas |
|---|---|---|
| Linux Debian (portátil de Sandra, 2 núcleos, 1,8 GiB) | **Fase 1** | Objetivo principal. HUD ligero, sin Electron. |
| Windows 10/11 (equipo de Askher, ~8 GB) | Fase 2 | Mismos módulos; `espeak`/SAPI y `.vbs` de arranque. |
| Android (Samsung A16, 4 GB) | Fase 2 | HUD en navegador + núcleo en Termux; o cliente que hable con la PC. |
| Hosting 24/7 | Futuro | Solo cuando haya recursos; no se promete ahora. |

Presupuesto de recursos en el portátil:

- Arranque en frío: < 6 s para el HUD, < 2 s para comandos sin LLM.
- RAM del proceso: < 150 MB sin modelo; el modelo se carga solo al conversar.
- CPU en reposo: < 5 %; con orbe animado: < 8 %.
- Ollama: `qwen3:0.6b` por defecto; `qwen2.5:0.5b` como respaldo; `qwen3.5:2b` solo si
  hay RAM libre. Nunca cargar dos modelos a la vez.

---

## 10. Honestidad y seguridad

- Frases de fallo ya definidas y no negociables:
  - «No puedo consultar el clima real en este momento, probablemente por falta de
    conexión a internet. Prefiero decirle esto antes que inventar un dato.»
  - «No encontré esa información en mis apuntes.»
  - «No tengo un modelo de lenguaje cargado; puedo ejecutar comandos, pero no conversar.»
- Prohibido inventar rutas, versiones, resultados de pruebas o enlaces.
- Toda afirmación de «funciona» debe venir de una ejecución real y de la salida
  completa, no de un `tail` que oculta el código de salida.
- Las pruebas nuevas se **mutan a propósito** para comprobar que pueden ponerse rojas.
- No se registran conversaciones fuera del equipo. Los logs locales se rotan.

---

## 11. Pruebas y criterios de aceptación

### Fase 1 (esta entrega)

1. `python3 -m cort --doctor` informa Python, Ollama, modelos, espeak, Vosk, HUD.
2. `python3 -m cort --once "¿qué hora es?"` responde con la hora real del sistema.
3. `python3 -m cort --once "¿qué día es hoy?"` responde con la fecha real.
4. «Me llamo …» y «¿cómo me llamo?» funcionan tras reiniciar el proceso.
5. El clima responde o falla con la frase honesta; nunca inventa.
6. «Abre la calculadora» abre una app de la allowlist o explica por qué no.
7. El HUD carga, muestra el orbe y el reloj, y el chat responde.
8. `python3 -m unittest discover -s tests` pasa por completo, sin red.
9. El HUD no supera el 8 % de CPU en reposo (medido con `psutil`).
10. Nada se publica en GitHub en esta entrega.

### Fases posteriores

- F2: voz completa (wake word + Vosk + barge-in), alarmas con audio.
- F3: Windows y `.vbs`, instructivo para Askher.
- F4: Android/Termux y puente PC ↔ móvil.
- F5: **avatar Cortana** humanoide holográfico (última rama), con capas, aberración
  cromática, líneas de escaneo, labios sincronizados por visemas y partículas.
- F6: publicación, badges, instalador y guía para colaboradores.

---

## 12. Lo que NO se hace en esta primera entrega

Para no vender humo:

- No se borra ninguna rama del repo `Sandra2244/CORT` ni se publica nada.
- No hay avatar humanoide todavía; el orbe de partículas es la base visual.
- No hay envío de WhatsApp ni integración con Discord.
- No hay app Android instalable; el HUD es web y puede abrirse en el móvil por red
  local cuando se configure.
- No hay voz neuronal Piper ni clonación de voz.
- No hay `ffmpeg` instalado; los fotogramas de referencia se extrajeron con VLC/GStreamer.

---

## 13. Glosario

- **HUD**: la interfaz holográfica (orbe, reloj, paneles).
- **Orbe**: esfera de partículas del centro.
- **Plasma**: filamentos y descargas que unen núcleo y superficie.
- **Arnés (harness)**: bucle que da herramientas y memoria a un modelo.
- **Wake word**: palabra que despierta a CORT («CORT», «Sofi»).
- **VAD**: detección de actividad de voz por energía.
- **MPRIS**: protocolo de control de reproductores en Linux.
- **Fail-closed**: ante la duda, no actuar y decirlo.

---

## 14. Registro de decisiones (2026-10-27)

| Tema | Decisión |
|---|---|
| Origen | Reconstrucción total desde cero en `~/Vídeos/CORT`; no se copia el CORT viejo. |
| GitHub | Solo local por ahora; no se toca ninguna rama ni se publica. |
| Interfaz | HUD web (HTML/CSS/JS) servido por Python y abierto en ventana nativa o navegador. |
| Voz | Vosk español offline cuando se instale; espeak-ng para responder; texto siempre disponible. |
| Alcance | PC Linux primero; Windows y Android en fase 2; avatar Cortana al final. |
| Memoria | SQLite, no JSON. |
| Cerebro | Ollama local con modelos pequeños ya presentes. |
