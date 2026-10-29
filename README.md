# CORT

**Cognitiva · Omnipresente · Rapsodia · Terminal**

Asistente personal local para Linux, con HUD propio, memoria persistente y voz en español.
Funciona sin conexión para los comandos del día a día y usa Ollama cuando está disponible para
conversar y razonar paso a paso.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Licencia](https://img.shields.io/badge/Licencia-MIT-7dffb2)
![Estado](https://img.shields.io/badge/Estado-fase%202.0-6ff3ff)

![HUD de CORT](docs/hud.png)

> Captura real del HUD. En una ventana de escritorio se suman el registro del sistema (izquierda),
> la telemetría (derecha) y el rail de acciones; en ventanas angostas se ocultan los paneles y el
> rail pasa a fila o a rejilla táctil.

![HUD de CORT en un teléfono](docs/hud-movil.png)

> La misma página a 390×844: el rail se convierte en una rejilla de cuatro columnas con etiqueta.

## Índice

- [Qué es](#qué-es)
- [Estado verificado](#estado-verificado)
- [Instalación paso a paso](#instalación-paso-a-paso)
- [Uso](#uso)
- [Comandos](#comandos)
- [Arquitectura](#arquitectura)
- [HUD](#hud)
- [Voz](#voz)
- [Arnés de agentes](#arnés-de-agentes)
- [Personalidad](#personalidad)
- [Memoria y datos](#memoria-y-datos)
- [Configuración](#configuración)
- [Pruebas](#pruebas)
- [Límites y seguridad](#límites-y-seguridad)
- [Hoja de ruta](#hoja-de-ruta)
- [Licencia](#licencia)

## Qué es

CORT es un asistente que corre en tu propia computadora. El router entiende frases cortas en
español y resuelve los comandos frecuentes sin depender de internet ni de un modelo de lenguaje:
hora, fecha, clima, estado del sistema, alarmas, memoria, apuntes locales, apps permitidas,
búsquedas, música y control de reproducción. Cuando la frase no es un comando conocido, consulta
Ollama; si Ollama no está encendido, lo dice con claridad en lugar de inventar. Cuando tampoco el
modelo puede, CORT admite el límite con calidez, ofrece salidas reales y anota la pregunta para
que no se pierda: «¿qué no sabés?» devuelve esa lista.

El HUD es una página local servida por CORT. Se puede abrir en el navegador o en una ventana
nativa si `pywebview` está instalado. La voz usa `espeak-ng` y la escucha es opcional con Vosk en
español; sin esos componentes, el chat escrito sigue funcionando.

Documentación de diseño: [PROMPT-MAESTRO](docs/PROMPT-MAESTRO.md),
[ARQUITECTURA](docs/ARQUITECTURA.md), [DECISIONES](docs/DECISIONES.md),
[ANÁLISIS DEL HUD](docs/ANALISIS-HUD.md) y [ROADMAP](docs/ROADMAP.md).

## Estado verificado

Comprobado en este equipo (Debian, Python 3.13.5, 2 núcleos, 1,8 GiB de RAM) entre el **28 y el 29
de octubre de 2026**:

| Comprobación | Resultado |
| --- | --- |
| Suite de pruebas | **177 pruebas unittest en verde** en local (101,8 s) |
| CLI | `--version`, `--once`, `--doctor`, `--hud`, `--no-abrir`, `--puerto`, `--host`, `--token` |
| HUD | reloj cinematográfico, orbe con 4 estilos, 9 estados, animación de ejecución, chat, rail de acciones, panel de capacidades, paleta de comandos, panel de modelos, arranque y diseño adaptable con PWA |
| Modelos Ollama | listado real, selección persistida, recomendados, descarga con progreso y cancelación, y auto-selección al terminar |
| HUD en la red local | arrancado con `--host 0.0.0.0 --token …`: 401 sin llave por página, API y `POST`; 200 con cabecera o `?token=`; estáticos y `/api/salud` abiertos; bucle local sin llave; rechazo honesto al intentar `0.0.0.0` sin token; medido entrando por la IP real de `wlan0` |
| Descarga real | `gemma3:270m`, 278 MB en 66 s, con porcentaje agregado por capas y verificación SHA-256 |
| Inferencia real | `qwen2.5:0.5b` respondió por CORT con el prompt compacto; tardó 269 s en este portátil |
| Clima real | por IP y por ciudad, con `ip-api.com` + `open-meteo.com` |
| Memoria | guardar nombre, consultar y sobrevivir entre ejecuciones (SQLite) |
| Alarmas | hora con `6:30`, mensaje y rechazo honesto si falta la hora |
| Apuntes | lectura de `knowledge/` con búsqueda por palabras |
| VLC real | reproducción de un WAV con `cvlc`, pausa con SIGSTOP y reanudación con SIGCONT |
| Apps reales | apertura de `galculator` desde la allowlist y cierre posterior |
| Diagnóstico | `scripts/install.sh` y `python3 -m cort --doctor` |
| CI y publicación | en GitHub Actions, no en este portátil: el job `pruebas` deja las 177 verdes y corre `--once`; sólo después el job `apk` compila, firma y publica. Además, `pruebas.yml` corre la suite en cada `push` a `main` y en cada `pull_request` |
| Personalidad y huecos (2.0.2) | toda salida de fallo sale de `cort/brain/honesto.py`; una pregunta sin respuesta queda en la tabla `gaps` con su motivo y `veces`, se lista con «¿qué no sabés?» y se borra con «olvidá lo que no sabés»; un turno cancelado por Sandra no se anota (medido en `tests/test_app.py`) |
| APK de bolsillo | `CORT-IA-3.1.2-bolsillo.apk` (201.965 bytes, sha256 `cee5d844…c4813a` verificado con `sha256sum` y coincidiendo con `-firma.txt`) en la Release `v3.1.2`, con `package='com.cort.ia'`, `versionCode 30102`, `minSdkVersion 26`, `targetSdkVersion 34`, 7 permisos, `resources.arsc` sin comprimir y alineado de a 4; la llave `FA:AB:EF:46:…:A3:19:77` es la misma del `CORT-IA-2.11.0-nucleo.apk`, medida con `keytool` sobre los dos archivos |
| Leer con CORT (2.0.1) | los cuatro componentes del lector están en el `AndroidManifest.xml` binario del APK publicado (`LeerActivity`, `LectorService`, `android.intent.action.PROCESS_TEXT`, `foregroundServiceType`), leídos de la tabla de cadenas en UTF-16; el run `40942914232` compiló con `javac`+`d8` después de las pruebas |

Lo que **no** se probó todavía, y por eso no se anuncia como funcionando:

- Inferencia cómoda: en este portátil (2 núcleos, 1,8 GiB) una respuesta de `qwen2.5:0.5b` puede
  tardar minutos si Qoder o el navegador están abiertos. Funciona, pero no es conversación fluida.
- Modelos diminutos: `gemma3:270m` descarga bien, pero respondió incoherencias; por eso no está en
  las recomendaciones del panel.
- Voz y palabra de activación: faltan el paquete `vosk` y el modelo en español.
- HUD en el teléfono: el acceso por red local ya está medido desde este equipo (el portal de
  `wlan0` responde a su propia IP), pero **falta abrirlo desde el A16 físico**, probar la
  instalación PWA y el micrófono dentro del navegador del móvil. Sin HTTPS, el navegador puede
  limitar «Agregar a inicio».
- Gestos con cámara: planificados, no implementados.
- El APK en la mano: está compilado, firmado y publicado, pero **nadie lo ha instalado todavía**
  encima del 2.11.0 en el A16, y el micrófono dentro del `WebView` tampoco se ha escuchado. La
  teoría (mismo paquete, misma llave, `versionCode` más alto) está medida en los archivos; la
  instalación real, no.
- Ventana nativa: falta `pywebview`; el HUD se abre en el navegador.
- `playerctl`: no está instalado; pausa, reanudación y cambio de pista usan señales y el estado
  guardado por CORT, lo que funciona con VLC pero no da posición exacta.

## Instalación paso a paso

Requisitos: Linux con Python 3.11 o superior. En Debian/Ubuntu:

```bash
sudo apt install python3 python3-psutil python3-requests \
                 espeak-ng vlc xdg-utils libnotify-bin alsa-utils
```

1. Entrá a la carpeta del proyecto:

   ```bash
   cd ~/Vídeos/CORT
   ```

2. Comprobá el entorno. Este guion **no instala nada**: sólo revisa y te dice qué falta.

   ```bash
   ./scripts/install.sh
   ```

3. Probá una respuesta sin abrir el HUD:

   ```bash
   ./scripts/run.sh --once "¿qué hora es?"
   ```

4. Arrancá el modo consola:

   ```bash
   ./scripts/run.sh
   ```

   Escribí `ayuda` para ver los comandos y `salir` para terminar.

5. Arrancá con el HUD:

   ```bash
   ./scripts/run.sh --hud
   ```

   Se abre en una ventana nativa si `pywebview` está instalado; si no, en el navegador. La dirección
   por defecto es `http://127.0.0.1:8765/`.

6. Opcional, arranque automático al iniciar sesión:

   ```bash
   ./scripts/install-autostart.sh
   ```

   Para quitarlo: `./scripts/install-autostart.sh --quitar`.

### Voz opcional

```bash
python3 -m venv .venv
.venv/bin/pip install vosk
./scripts/fetch-vosk-es.sh
./scripts/run.sh --hud --voz
```

El modelo pequeño de español pesa 39 MB y se descarga desde el sitio oficial de Vosk. Si usás el
entorno virtual, arrancá CORT con `.venv/bin/python -m cort --hud --voz` o activá el entorno antes
de `./scripts/run.sh`.

### Ollama opcional

Si Ollama ya está instalado y encendido en `http://127.0.0.1:11434`, CORT elige el modelo configurado
y, si no está, un respaldo o el más pequeño disponible. Los modelos se configuran en
`config/cort.toml`; por defecto: `qwen3:0.6b`, `qwen2.5:0.5b` y `qwen3.5:2b` como modelo profundo.

El chip **IA** del HUD abre un panel con los modelos instalados, cuatro recomendaciones según la
RAM, el modelo activo y una descarga con progreso real (`ollama pull`): porcentaje agregado por
capas, MB, velocidad, tiempo restante y botón **cancelar**. La descarga sigue en segundo plano si
cerrás el panel y, al terminar, CORT selecciona el modelo descargado. También se puede hacer por
chat:

| Frase | Qué hace |
| --- | --- |
| `¿qué modelos de Ollama tienes?` | lista nombre, tamaño y modelo activo |
| `descarga el modelo qwen3:0.6b` | descarga con progreso visible |
| `usa el modelo qwen2.5:0.5b` | valida que exista y lo deja activo |
| `cancela la descarga` | detiene la descarga en curso |

Para que un modelo pequeño alcance, CORT usa un prompt compacto cuando detecta nombres como
`0.5b`, `0.6b` o `1b`, recorta `num_predict` y reenvía los últimos turnos de la conversación
(configurable con `historial_mensajes`). El texto parcial del modelo aparece bajo el orbe mientras
se genera. Si el modelo no está, CORT prueba el respaldo y, si tampoco hay, responde con los
comandos directos en lugar de inventar.

> En este portátil conviene no tener Ollama, el navegador y pruebas pesadas al mismo tiempo: la
> memoria es limitada. CORT funciona igual para los comandos directos.

## Uso

- **Consola:** `./scripts/run.sh` y escribí tus frases.
- **HUD:** `./scripts/run.sh --hud`. El chat está abajo; los botones redondos activan el micrófono
  y el silencio de la voz.
- **Una sola frase:** `./scripts/run.sh --once "clima en Caracas"`.
- **Diagnóstico:** `./scripts/run.sh --doctor`.
- **Sin voz:** agregá `--sin-voz`.
- **Sin abrir ventana:** agregá `--no-abrir`; imprime la URL para abrirla a mano.
- **Otro puerto:** `--puerto 9000`.
- **Desde el teléfono:** `./scripts/run.sh --hud --host 0.0.0.0 --token tu-llave`; imprimí el
  enlace completo que sale (`http://192.168.1.19:8765/?token=…`) y abrilo en el móvil.
- **Otra configuración:** `--config ruta/a/cort.toml`.

## CORT en el teléfono

El cerebro vive en la PC; el teléfono es una ventana a ese HUD. Hay dos caminos, y el primero
no instala nada:

1. **PWA (sin APK).** Con la PC y el teléfono en el mismo wifi, abrí el enlace del paso anterior
   en Chrome del teléfono → menú → *«Añadir a pantalla principal»». Queda con su icono y entra a
   pantalla completa. Probado en el navegador de escritorio; **en su A16 todavía no se instaló**,
   así que lo anotamos como pendiente.
2. **APK de bolsillo (`apps/bolsillo/`).** Un WebView que abre ese mismo enlace y recuerda la
   dirección, con permiso de micrófono propio para que la escucha funcione dentro de la app; y
   desde la 3.1.2, **«Leer con CORT»**: seleccionar un párrafo en cualquier app y elegirlo en el
   menú de selección para que te lo lea en voz alta, sin la PC. Detalles en
   [`apps/bolsillo/README.md`](apps/bolsillo/README.md).
   Ya está compilado y publicado: en [Releases ▸ latest](https://github.com/Sandra2244/CORT-nuevo/releases/latest)
   está el `CORT-IA-<versión>-bolsillo.apk` con su `-firma.txt` y su `-auditoria.txt` al lado.
   Se instala encima de la CORT-IA anterior sin desinstalar ni perder datos — paquete
   `com.cort.ia`, la misma llave (huella `FA:AB:EF:46:…:A3:19:77`, medida con `keytool` sobre
   los dos archivos) y un `versionCode` más alto que el 21100 del 2.11.0. Antes de aceptar
   *Actualizar*, compará el renglón `llave sha256:` del `-firma.txt`: si no coincide, Android
   va a pedir desinstalar.

En los dos casos hace falta que el HUD esté abierto a la red con token: sin `--token`, CORT no
levanta el HUD fuera de `127.0.0.1` y lo dice en vez de exponer la PC al wifi. Y en los dos
queda la misma prueba pendiente, que sólo se hace con el teléfono en la mano: que la app entre
encima del 2.11.0 sin perder la dirección, y que el micrófono escuche dentro del `WebView`
en Android 16.

## Comandos

| Frase | Qué hace |
| --- | --- |
| `hola` | saludo |
| `¿qué hora es?` / `¿qué día es hoy?` | hora y fecha reales del sistema |
| `cómo está la PC` | CPU, RAM, disco y batería con `psutil` |
| `clima` / `clima en Caracas` | clima real; si no hay red, lo dice y no inventa |
| `me llamo Sandra` | guarda el nombre en SQLite |
| `mi hermana se llama Ana` / `vivo en Caracas` | guarda familiares y ciudad |
| `recuerda que la práctica es el jueves` | guarda una nota |
| `¿cómo me llamo?` / `memoria` | consulta lo guardado |
| `olvida mi color favorito` | borra hechos que coincidan |
| `¿qué no sabés?` / `huecos` | lista lo que CORT no pudo responder, con cuántas veces |
| `olvidá lo que no sabés` | borra ese registro para empezar de cero |
| `abre la calculadora` | abre sólo apps de la allowlist |
| `abre VLC` | abre VLC desde la allowlist |
| `abre YouTube` / `abre WhatsApp` | abre sitios permitidos |
| `busca en Google …` / `busca en YouTube …` | búsqueda en el navegador |
| `reproduce …` | busca en tus carpetas y, si no está, abre YouTube |
| `música` | reproduce hasta 50 archivos de `~/Música` |
| `pausa` / `reanuda` / `siguiente` / `anterior` | control de reproducción |
| `sube el volumen` / `baja el volumen` | volumen del sistema con `pactl` |
| `alarma a las 6:30 con ir a MORFO 3` | alarma con mensaje y notificación |
| `programa una alarma` | pide la hora en vez de suponerla |
| `¿qué sabes de la urea?` | busca en `knowledge/*.md` y `*.txt` |
| `¿qué modelos de Ollama tienes?` | lista modelos instalados y el activo |
| `descarga el modelo …` / `usa el modelo …` | descarga o cambia el modelo de Ollama |
| `usa el arnés para investigar …` | razonamiento por pasos (requiere Ollama) |
| `silencio` / `habla` | apaga o enciende la voz |

Las palabras de activación son **CORT** y **Sofi**; se pueden cambiar en `config/cort.toml`.

## Arquitectura

```text
cort/
├── __main__.py          CLI: --hud, --once, --doctor, --voz, --puerto, --host, --token
├── app.py               orquestador: router → herramienta → memoria → bus → voz
├── router.py            intenciones deterministas en español
├── text.py              normalización, horas, fechas y similitud
├── config.py            TOML + valores por defecto
├── bus.py               estado compartido entre núcleo, HUD y voz
├── brain/
│   ├── memory.py        SQLite: hechos, episodios, alarmas, meta y huecos
│   ├── ollama.py        cliente HTTP con streaming y respaldo de modelo
│   ├── persona.py       personalidad cálida, fecha real y protocolo de «no sé»
│   ├── honesto.py       la única casa de los fallos: sin modelo, sin pasos, no lo sé
│   └── harness.py       arnés de agentes con contrato JSON
├── tools/               clima, sistema, apps, medios, búsquedas, alarmas,
│                        apuntes y memoria
├── voice/               espeak-ng (TTS) y Vosk + arecord (STT)
└── hud/
    ├── server.py        HTTP con llave por token y API
    └── static/          index.html, hud.css, hud.js (canvas 2D)

apps/bolsillo/           el cliente Android (no es Python: se compila aparte)
├── AndroidManifest.xml  paquete com.cort.ia, minSdk 26, 7 permisos
├── src/com/cort/ia/     MainActivity (WebView y micrófono), LeerActivity
│                        (ACTION_PROCESS_TEXT / SEND) y LectorService en primer plano
├── res/mipmap-*/        iconos de launcher en 5 densidades
├── llave.sh             de dónde sale la llave de firma (secretos ▸ caché ▸ ~/cort-llave.jks)
├── compilar.sh          aapt2 ▸ javac ▸ d8 ▸ zip ▸ zipalign ▸ apksigner ▸ auditoría
└── keystore/            EN `.gitignore`: aquí nunca se guarda la llave

.github/workflows/
├── pruebas.yml          suite completa y `--once` en cada push a main y en cada PR
└── apk.yml              primero las pruebas y `--once`,
                         y sólo si salen verdes compila el APK firmado y publica la Release
```

Flujo de una frase:

```text
texto → normalizar → router → herramienta (sin LLM)
                              └→ Ollama / arnés (si hace falta)
     → memoria de episodios → bus → HUD (polling) + voz (cola espeak-ng)
```

El servidor expone:

- `GET /api/estado`: reloj, estado, mensajes, métricas, alarmas, voz, progreso de descarga y texto
  parcial del modelo.
- `GET /api/salud`: comprobación mínima.
- `GET /api/modelos`: modelos instalados, activo, recomendados y estado de descarga.
- `POST /api/modelos/seleccionar`: `{"nombre": "qwen3:0.6b"}`.
- `POST /api/modelos/descargar`: `{"nombre": "qwen3:0.6b"}`, responde NDJSON con el progreso y un
  cierre con `activo`.
- `POST /api/modelos/cancelar`: cierra la descarga en curso.
- `GET /api/capacidades`: herramientas reales agrupadas por categoría, con riesgo y ejemplo.
- `POST /api/chat`: `{"texto": "..."}`.
- `POST /api/accion`: `silencio`, `detener`, `escuchar`, `pausa`, `reanudar`.

## HUD

- Reloj de siete segmentos en cian, con bisel de esquinas técnicas, etiquetas CORT/LOCAL y fecha
  en español.
- Orbe de filamentos luminosos como estilo por defecto (**esfera**): brazos que nacen del núcleo y
  estallan hacia el borde, cáscara de arcos irregulares, hebras interiores, polvo y un destello
  central descentrado. El resto de estilos sigue disponible: **anillo** vortex, **cinta** de
  plasma y **enjambre**.
- Nueve estados con color propio: reposo, escuchando, procesando, ejecutando, hablando,
  descargando, error, alarma y sin conexión. El color tiñe el orbe, el reloj, los paneles y los
  indicadores; en reposo el rótulo de estado se oculta para dejar limpio el orbe.
- Animación de ejecución: ráfaga de anillos y rayos alrededor del orbe, arcos punteados que
  preceden, toro de partículas y estrella de rayos en el núcleo; una tarjeta muestra la
  herramienta, la latencia y el avance, y el texto parcial del modelo aparece debajo.
- **Rail de acciones** a la derecha: hablar, detener el turno, modelos, capacidades, comandos,
  enfoque, voz y pantalla completa. Se compacta bajo la telemetría en ventanas de poca altura,
  pasa a fila horizontal en tablet y a rejilla de cuatro columnas con etiqueta en el teléfono.
- **Actividad del agente**: la traza muestra la herramienta real, una vista previa de sus
  argumentos, la duración y el error si lo hubo. Se alimenta del bus, no de texto inventado.
- **Capacidades**: panel con buscador, 16 herramientas agrupadas en 7 categorías, nivel de riesgo
  y un ejemplo que se carga en el compositor sin enviarse solo. Sale de `GET /api/capacidades`.
- **Paleta de comandos** (`Ctrl+K`/`⌘K`): diez acciones del HUD más los ejemplos de herramientas,
  con filtro sin tildes, flechas, `Enter` y `Esc`.
- **STOP real**: cancela el stream de Ollama, corta la voz y cierra el turno; el HUD lo refleja y
  no guarda una respuesta a medias. Está en el rail y en la cabecera del chat.
- **Arranque cinematográfico**: cuatro líneas de estado, se puede saltar y no se repite en la
  misma sesión.
- Chat con burbujas, metadatos de herramienta, chips rápidos, botón de parada y modo enfoque. La
  altura está acotada y el rótulo de estado vive justo bajo el orbe, así nada tapa la conversación.
- Panel de modelos con lista, selección, recomendados, descarga con progreso, cancelación y aviso
  de descarga en segundo plano.
- **PWA**: manifest, iconos 192 y 512, `theme-color` y metadatos de Apple. La instalación completa
  en el teléfono depende de HTTPS; ver [`docs/ANALISIS-HUD.md`](docs/ANALISIS-HUD.md).
- Sin dependencias de frontend: HTML, CSS y JavaScript puro. El ovillo se dibuja por lotes
  (`Path2D` agrupado por profundidad) y la calidad baja sola si un cuadro tarda demasiado; DPR
  limitado y respeto a `prefers-reduced-motion`.
- Pensado para bajo consumo: sin Electron, sin React y sin recursos remotos.

## Voz

- **Salida:** `espeak-ng` con la voz `es-mx+f3`, en un hilo y una cola propios. Limpia URLs y
  marcas de Markdown antes de hablar.
- **Entrada:** opcional con Vosk en español y `arecord` a 16 kHz mono. Detecta el final de la frase
  por silencio. Sin Vosk, el botón del micrófono explica el motivo exacto.
- **Activación:** «CORT» o «Sofi»; si la frase trae más texto, se responde directamente.

## Arnés de agentes

El arnés es una capa enchufable sobre las herramientas. El modelo debe responder con un JSON:

```json
{"tool": "clima", "args": {"ciudad": "Caracas"}}
```

o cerrar con:

```json
{"respuesta": "Texto final para la persona"}
```

Reglas: máximo 3 pasos, cada resultado vuelve al modelo, y se registran las trazas en el HUD. Si el
modelo no está disponible, el arnés lo dice, sugiere los comandos directos y anota el hueco. Si un
paso falla en el último turno, se detiene ahí y dice qué falló antes de inventar un cierre. El diseño
está inspirado en la idea de OpenClaw y HERMES-AGENT de la referencia, sin copiar código de terceros.

## Personalidad

Cuando CORT no sabe, no rellena: dice el límite en la primera frase, con tono cálido, y ofrece salidas
reales (buscar en la web, mirar los apuntes, dejarlo anotado). Todas esas frases viven en
`cort/brain/honesto.py`, así que la voz no se contradice de un módulo a otro. La persona completa
—cómo habla, qué no inventa y qué reglas no se rompen— está en `cort/brain/persona.py`; el historial
de lo que no pudo responder queda en `gaps` y se consulta con «¿qué no sabés?».

## Memoria y datos

- Base de datos: `~/.local/share/cort/cort.db` (o `$CORT_HOME/cort.db`).
- Hechos con clave y valor; los episodios se podan a 500 para no crecer sin control.
- Huecos: cada pregunta que CORT no pudo responder (sin modelo, sin pasos o con error) queda
  anotada con su motivo y un contador. Se consulta con «¿qué no sabés?» y se borra con
  «olvidá lo que no sabés». No se anota lo que vos cancelás: un STOP no es un hueco de CORT.
- Alarmas con hora ISO, mensaje y playlist opcional; se comprueban cada 15 segundos.
- Apuntes: `knowledge/*.md` y `*.txt`; `README.md` se ignora a propósito.
- Música: `~/Música`, con búsqueda por carpeta y por nombre de archivo.

## Configuración

Todo se ajusta en [`config/cort.toml`](config/cort.toml): palabras de activación, modelo y respaldo
de Ollama, voz, puerto del HUD, umbrales de aviso, allowlist de apps, rutas y límites del arnés.
También se puede indicar otro archivo con `--config` o la variable `CORT_CONFIG`, y cambiar la
carpeta de datos con `CORT_HOME`.

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```

Cubren texto y horas, router, memoria SQLite (hechos, episodios, alarmas y huecos), clima con HTTP
simulado, apuntes, arnés, frases de honestidad y persona, medios, servidor del HUD, cliente de Ollama
(capas, cancelación, respaldo) y el flujo completo del núcleo. No necesitan internet, no abren
aplicaciones y usan carpetas temporales. La suite completa son 177 pruebas y tardó 101,8 s en este
equipo; en Actions corre en cada push a `main` y en cada `pull_request`.

## Límites y seguridad

- Las apps y sitios se abren sólo desde una allowlist; nunca se ejecuta texto libre ni `shell=True`.
- No hay acciones destructivas ni envío de mensajes en esta fase.
- El clima y la conversación fallan con mensajes explícitos; no se rellenan datos inventados.
- El servidor escucha sólo en `127.0.0.1` por defecto; para el teléfono hace falta `--host` **y**
  `--token`, y sin llave no sale del bucle local.
- El APK vive en este repo público, pero **la llave de firma no**: `keystore/`, `*.jks`,
  `*.keystore`, `pass.txt` y `cort-llave.*` están en `.gitignore`.
- No se modificó el CORT anterior de `/home/Sandra/Documentos/CORT`: se leyó, no se tocó.

## Hoja de ruta

- **F1 (hecha):** núcleo, router, memoria, herramientas, HUD, voz y pruebas.
- **F1.5–1.7 (hechas):** conversación con Ollama, HUD v2 con STOP real, repo público y APK firmado.
- **2.0.1 (hecha):** «Leer con CORT» en el menú de selección, con servicio en primer plano.
- **2.0.2 (hecha):** personalidad cálida, `honesto.py` y registro de huecos.
- **2.0.3–2.0.7:** presencia en el teléfono, skills, agente con aprobación, HUD de paneles y
  modelo híbrido. Detalle y criterios en [`docs/ROADMAP.md`](docs/ROADMAP.md).
- **Después:** voz completa con Vosk y palabra de activación, avatar holográfico y empaquetado
  para otras personas.

## Licencia

MIT. Copyright (c) 2026 Sandra López y Askher Vargas. Ver [LICENSE](LICENSE).
