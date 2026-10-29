# Análisis de HUD y plan multiplataforma

Fecha: 2026-10-28. Este documento resume las referencias que pidió Sandra, qué se
adaptó a CORT, qué se descartó y en qué orden conviene seguir. Todo lo que figura
como «hecho» está implementado y probado en local; lo que figura como «pendiente»
no se presenta como terminado.

## Resumen de decisiones

1. La referencia principal de interfaz es **eadmin2/jarvis_ai** (MIT). Se tomaron
   patrones de interacción y composición, no código.
2. CORT mantiene su identidad: orbe de filamentos, reloj de siete segmentos y
   paleta cian. No se copia el reactor de la referencia.
3. La prioridad inmediata es **funcionalidad real**: botones que ejecutan algo,
   actividad con datos verdaderos, STOP que corta el turno y capacidades leídas
   del registro de herramientas.
4. Android se aborda primero como **HUD web adaptable + PWA**, sin reescribir la
   interfaz. La instalación completa en el teléfono queda condicionada a HTTPS.
5. Los gestos con cámara y el avatar quedan para fases posteriores: primero hay
   que sostener el rendimiento en 2 núcleos y 1,8 GiB.

## 1. Referencias verificadas

### eadmin2/jarvis_ai

Asistente de voz con HUD estilo Iron Man construido sobre **Hermes Agent**
(NousResearch). Según su README y su licencia, verificados el 2026-10-28:

- Es **MIT**, copyright 2026 Chris Lassiter.
- HUD en el navegador de cualquier equipo de la LAN, más un cliente
  push-to-talk. La autenticación es un token por cookie.
- Funciones que muestra: actividad del agente con vista previa de comandos,
  botón **STOP** (también con `Esc`), tarjetas de aprobación para comandos
  peligrosos, interrupción a mitad de frase, paneles holográficos de medios,
  tableros embebidos (kanban y sesiones), uso de tokens, panel de máquinas
  (CPU/GPU local y remota), arranque cinematográfico y diseño para móvil con
  «Agregar a inicio».
- Voz: Whisper local para transcripción y ElevenLabs para síntesis. Los únicos
  servicios en la nube son el proveedor del modelo y ElevenLabs.
- Seguridad declarada: la clave de Hermes no llega al navegador, el HUD habla
  por un proxy con lista permitida, los endpoints exigen token, la API escucha
  sólo en loopback y los textos se redactan antes de salir a la nube.

En CORT **no** se usa Hermes, ni ElevenLabs, ni el sidecar GPU: el cerebro es
Ollama local, la voz es `espeak-ng` y la transcripción es Vosk opcional. La
referencia sirve para la forma del centro de control, no para su pila técnica.

### OpenClaw

Asistente open source (MIT) que corre en el equipo de la persona y se conecta a
canales que ya se usan —Discord, Telegram, WhatsApp, Slack, iMessage y más— con
apps nativas para macOS, iOS, Android, Windows y Linux. Su arquitectura separa
un **gateway** de confianza de la ejecución no confiable y aplica políticas por
código; el estado y las credenciales quedan en el hardware propio.

Lo aprovechable para CORT es la idea de **un núcleo con varias bocas** (HUD,
voz, más adelante notificaciones), no su runtime Node ni sus canales. CORT es
Python, local y con lista de herramientas cerrada; sumar canales externos
implicaría credenciales, permisos y una superficie de ataque que hoy no
necesitamos.

### «Jaredrhood»

No se encontró un proyecto relevante con ese nombre en las búsquedas hechas.
Queda **pendiente** hasta que Sandra pase los videos o el enlace. No se inventa
su alcance ni se promete compatibilidad.

## 2. Qué se adaptó de jarvis_ai

| Patrón de la referencia | Traducción en CORT | Estado |
|---|---|---|
| Rail de acciones siempre visible | Rail vertical a la derecha en escritorio; rejilla de 4×2 en teléfono | Hecho |
| STOP que corta el turno | `threading.Event` en el stream de Ollama, chequeos en el arnés y `POST /api/accion {"accion":"detener"}` | Hecho |
| Actividad del agente con detalle | Eventos con herramienta, argumentos recortados, milisegundos y error; se muestran los últimos 6 | Hecho |
| Panel de capacidades | `GET /api/capacidades` agrupa las 16 herramientas reales en 7 categorías, con riesgo y ejemplo | Hecho |
| Paleta de comandos | `Ctrl+K`/`⌘K`: 10 acciones del HUD + 16 ejemplos de herramientas, con filtro y teclado | Hecho |
| Arranque cinematográfico | Secuencia breve de líneas, se puede saltar y se recuerda en la sesión | Hecho |
| Diseño para móvil y «Agregar a inicio» | Reglas responsivas, manifest, iconos 192/512, `theme-color` y modo `standalone` | Hecho, sin probar aún en el A16 |
| Aprobaciones para acciones peligrosas | El registro ya marca `riesgo`, pero **no** hay tarjetas de ALLOW/DENY | Pendiente |
| Paneles holográficos de medios | No implementados | Pendiente |
| Uso de tokens y panel de máquinas remotas | CORT muestra CPU/RAM/batería locales; no hay workers remotos | Parcial |
| Filtro de secretos antes de la nube | CORT no manda texto a la nube; no hace falta hoy | No aplica |
| Barge-in real | La voz corta al empezar otro turno, pero no hay detección de habla superpuesta | Pendiente |
| Token de acceso al HUD | El HUD escucha en loopback por defecto; no hay token | Pendiente si se abre a la LAN |

## 3. Qué no se copió y por qué

- **Hermes Agent**: agrega un runtime y una API que CORT no necesita; el cerebro
  propio ya resuelve router, herramientas y memoria.
- **ElevenLabs**: es nube y tiene costo. La voz local `espeak-ng` funciona sin
  conexión y sin cuota.
- **Whisper/RealtimeSTT**: pesado para 2 núcleos; Vosk es la opción prevista y
  todavía no está instalado.
- **Sidecar GPU**: no hay GPU NVIDIA en este portátil.
- **Tableros embebidos**: CORT no tiene kanban ni sesiones de Hermes; forzar
  paneles vacíos sería decoración, no función.
- **Autenticación por token**: tiene sentido cuando el HUD se expone a la LAN;
  hoy el servidor abre en `127.0.0.1`. Se retoma junto con el acceso desde el
  teléfono.

## 4. Estado real del HUD v2

- **Rail**: hablar, detener (sólo durante un turno), modelos, capacidades,
  comandos, enfoque, voz y pantalla completa. En escritorio mide 62×50 px con
  etiqueta; en ≤1180 px pasa a fila horizontal; en ≤430 px se convierte en
  rejilla de cuatro columnas con etiqueta y zona táctil de 40 px.
- **Alturas cortas**: hasta 900 px de alto el rail se ancla bajo la telemetría y
  se compacta para no tapar el panel de actividad ni el chat. Verificado a
  1440×768.
- **Capacidades**: panel con buscador, estado («16 herramientas · 7 categorías ·
  lista permitida»), tarjetas por categoría y botón de ejemplo que **carga** el
  texto en el compositor sin enviarlo.
- **Paleta**: acciones y ejemplos, filtro sin distinguir tildes, navegación con
  flechas, `Enter` para ejecutar y `Esc` para cerrar.
- **Actividad**: la traza muestra herramienta, argumentos, duración y error; ya
  no es texto decorativo.
- **STOP**: detiene el stream de Ollama, la voz y el turno; el HUD recibe
  `detenido` y no guarda un episodio falso.
- **PWA**: manifest, iconos, `theme-color`, metadatos de Apple y arranque
  omitible.
- **Accesibilidad y rendimiento**: `aria-live` en la actividad, `role="timer"`
  en el reloj, foco visible, `prefers-reduced-motion` y calidad adaptativa del
  orbe.

## 5. Gestos con cámara: plan, no promesa

La meta es saludar, señalar o abrir la paleta con la mano, sin nube. El camino
razonable:

1. **Fase A — prototipo aislado**: `getUserMedia` + MediaPipe Tasks Vision
   (`HandLandmarker` en WASM) en una página aparte, con permiso explícito y un
   botón para apagar la cámara. Nada de frames fuera del equipo.
2. **Fase B — gestos mínimos**: mano abierta para despertar, pinza para
   seleccionar, palma para detener. Cada gesto con confirmación visual y una
   alternativa por teclado.
3. **Fase C — integración**: sólo si el prototipo mantiene el HUD fluido en este
   portátil. Presupuesto: cámara a 320×240 y 15 fps, detección cada 2–3 cuadros,
   apagado automático al perder foco.

Riesgos: la cámara sube CPU y batería; MediaPipe puede no rendir en 2 núcleos;
la iluminación cambia el resultado. Por eso los gestos serán opcionales y nunca
el único modo de usar CORT.

## 6. Multiplataforma

### PC (estado actual)

- HUD web servido por CORT en `127.0.0.1`; se abre en el navegador o en ventana.
- Escritorio verificado a 1440×768 y 1440×900; ventana angosta a 536 px; teléfono
  simulado a 390×844.
- Sin Electron, sin React y sin recursos remotos.

### Android (siguiente)

- El mismo HUD contra la PC por red local: sólo hay que abrir la IP y el puerto.
- La PWA ya tiene manifest e iconos. **Aviso honesto**: instalar como app y
  usar service worker requiere contexto seguro (HTTPS o `localhost`); por HTTP
  en la LAN el navegador puede limitar la instalación. No se probó todavía en el
  A16 de Sandra.
- Si hace falta HTTPS, la vía más simple es un proxy local con certificado
  propio aceptado una vez en el teléfono, o un túnel privado. Se decide cuando
  se pruebe el acceso real.
- Pendiente para esa fase: token de acceso, reconexión del polling, notificaciones
  y alarmas del teléfono.

### Windows y otros

- El núcleo es Python y las rutas están centralizadas; faltan TTS y rutas de
  Windows. No se toca hasta cerrar Android o hasta que lo pida el colaborador.

## 7. Orden recomendado

1. **Ahora**: cerrar la verificación del HUD v2, actualizar README y capturas, y
   dejar la suite en verde. (Hecho en esta tanda: 147 pruebas.)
2. **Después**: probar el HUD desde el A16 en la LAN; decidir token y HTTPS según
   lo que el navegador permita.
3. **Luego**: aprobaciones ALLOW/DENY para herramientas de riesgo alto; es la
   función de la referencia con más valor real para CORT.
4. **Más tarde**: barge-in y wake word continua (dependen de Vosk y de RAM).
5. **Al final**: gestos con cámara y avatar, con presupuesto de CPU medido.

## 8. Verificación de esta tanda

- `python3 -m unittest discover -s tests`: **147 pruebas OK** (2026-10-28).
- `node --check cort/hud/static/hud.js`: sin errores.
- Capturas reales: `docs/hud.png` (1440×768) y `docs/hud-movil.png` (390×844).
- Navegador: sin mensajes en consola; capacidades 16/7; paleta 26 entradas;
  filtro «clima» devuelve sólo la herramienta de clima.
- Límite: no se probó la instalación PWA en un teléfono real ni los gestos.

## Fuentes

- [eadmin2/jarvis_ai](https://github.com/eadmin2/jarvis_ai) — README y LICENSE
  (MIT, Chris Lassiter), consultados el 2026-10-28.
- [OpenClaw](https://github.com/openclaw/openclaw) y
  [openclaw.ai](https://openclaw.ai/) — README (MIT), consultado el 2026-10-28.
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — citado por
  jarvis_ai como su motor de agente.
- [MediaPipe Tasks Vision](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker)
  — referencia prevista para el prototipo de gestos; no implementado aún.

Atribución: de jarvis_ai se tomaron **ideas de interfaz e interacción**. No se
copió código; su licencia MIT se respeta igualmente y se cita aquí.
