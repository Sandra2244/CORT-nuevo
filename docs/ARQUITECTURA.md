# Arquitectura de CORT

Este documento describe cómo está construido el código de la fase 1. Para la visión
completa, leer `PROMPT-MAESTRO.md`.

## 1. Forma general

Un solo proceso de Python con tres frentes:

1. **Núcleo** (`cort/app.py`): recibe texto, decide (router → arnés → LLM), ejecuta
   herramientas, guarda memoria y actualiza el estado.
2. **HUD** (`cort/hud/server.py` + `static/`): servidor HTTP local que sirve la
   interfaz y expone una API mínima. La ventana se abre con `pywebview` si está
   instalado, o con el navegador.
3. **Voz** (`cort/voice/`): hilos independientes para hablar (`espeak-ng`) y escuchar
   (`Vosk`, opcional). Nunca bloquean el núcleo.

```
texto/voz ──► App.responder() ──► Router ──► herramienta ──► respuesta
                                    │
                                    └──► Arnés ──► Ollama ──► herramienta ──► respuesta
                                                │
                                                └──► Persona + memoria + conocimiento
```

## 2. Módulos

| Ruta | Responsabilidad |
|---|---|
| `cort/__main__.py` | Punto de entrada; modos `--hud`, `--once`, `--doctor`, `--voz`, `--sin-voz`. |
| `cort/config.py` | Carga `config/cort.toml` + valores por defecto; expande `~`; rutas. |
| `cort/bus.py` | Estado compartido con lock: estado del orbe, log, mensajes, métricas, flags. |
| `cort/text.py` | Normalización (tildes, mayúsculas), similitud por tokens, extracción de horas. |
| `cort/router.py` | Intenciones deterministas en español. Devuelve `Intencion(nombre, args)` o `None`. |
| `cort/app.py` | Orquesta todo; construye la respuesta final y la guarda como episodio. |
| `cort/brain/ollama.py` | Cliente HTTP de Ollama: `tags`, `chat` con streaming, selección, descarga y respaldo de modelo. |
| `cort/brain/persona.py` | Prompt de sistema con fecha real, hechos y tono de CORT. |
| `cort/brain/memory.py` | SQLite: hechos, episodios, alarmas; consultas y poda. |
| `cort/brain/harness.py` | Bucle de agente con herramientas y JSON validado; trazas. |
| `cort/tools/base.py` | `Tool` (nombre, descripción, esquema, callable) y `Registro`. |
| `cort/tools/*.py` | Implementación de cada herramienta. |
| `cort/voice/tts.py` | Cola de frases, `espeak-ng`, silencio, barge-in. |
| `cort/voice/stt.py` | `arecord` en crudo + Vosk; VAD por energía. |
| `cort/voice/wake.py` | Escucha en segundo plano de «cort»/«sofi». |
| `cort/hud/server.py` | `ThreadingHTTPServer`, API y archivos estáticos. |
| `cort/hud/static/` | `index.html`, `hud.css`, `hud.js` (orbe en canvas). |
| `tests/` | Pruebas sin red con dobles de prueba. |

## 3. Flujo de una petición

1. El HUD hace `POST /api/chat` con `{"texto": "..."}`.
2. `app.responder()` normaliza y pasa por el **router**.
3. Si hay intención, ejecuta la herramienta, arma la respuesta y la devuelve.
4. Si no, intenta el **LLM** con persona + memoria + conocimiento + últimos turnos.
   Con modelos pequeños (`0.5b`, `0.6b`, `1b`) usa un prompt compacto y recorta
   `num_predict`; cada token se publica como texto parcial para el HUD. Si el LLM
   propone una herramienta (JSON), el **arnés** la ejecuta y vuelve a preguntar
   (máx. 3 pasos).
5. Si Ollama no está, responde con el mensaje honesto de «sin cerebro» y sugiere
   comandos que sí funcionan.
6. Se guarda el turno como episodio, se actualiza el estado y se devuelve el JSON.

## 4. API local

| Método | Ruta | Cuerpo / respuesta |
|---|---|---|
| GET | `/` | HUD. |
| GET | `/api/estado` | Estado, métricas, mensajes, log, modelo, memoria, descarga en curso y texto parcial del modelo. |
| GET | `/api/modelos` | Modelos instalados, activo, recomendados con tamaño y estado de descarga. |
| POST | `/api/modelos/seleccionar` | `{"nombre": str}` → valida, activa y persiste el modelo. |
| POST | `/api/modelos/descargar` | `{"nombre": str}` → NDJSON con estado, porcentaje agregado por capas, MB y velocidad; cierra con `activo`. |
| POST | `/api/modelos/cancelar` | Cierra la respuesta de `ollama pull` y deja el estado en reposo. |
| GET | `/api/capacidades` | Herramientas reales agrupadas por categoría, con riesgo y ejemplo; alimenta el panel y la paleta del HUD. |
| POST | `/api/chat` | `{"texto": str}` → `{"respuesta": str, "herramienta": str, "ms": int, "evento": {...}}`. |
| POST | `/api/accion` | `{"accion": "silencio"\|"pausa"\|"reanudar"\|"detener"}`. |
| GET | `/api/salud` | `{"ok": true, "version": "..."}`. |

Solo escucha en `127.0.0.1`. Para abrirlo al móvil hay que cambiar `hud.host` a
`0.0.0.0` **y** añadir un token; no es parte de esta entrega.

## 5. Estado y concurrencia

`Bus` guarda:

- `estado`: `idle | listening | thinking | executing | speaking | downloading | error | alert | offline`.
- `eventos`: últimos 8 eventos de herramienta para las animaciones del HUD.
- `mensajes`: últimos 40, con rol y hora.
- `log`: últimas 60 líneas del panel terminal.
- `metricas`: CPU, RAM, disco, batería (actualizadas cada 3 s).
- `voz_activa`, `silencio`, `modelo`, `ollama_ok`, `descargando`.
- `descarga`: estado del `pull` (porcentaje, capas, bytes, velocidad y error).
- `parcial`: últimos caracteres que genera el modelo, para mostrarlos en vivo.

La descarga corre en un hilo propio con `_pull_lock`; cancelar cierra la conexión,
lo que hace que Ollama aborte el `pull`. El progreso se guarda en la app, así que
sigue visible aunque se cierre el panel del HUD. El historial de conversación vive
en memoria (8 mensajes o 2400 caracteres) y se recorta antes de cada turno.

Todo acceso pasa por un `threading.RLock`. El HUD solo lee. Las tareas largas
(Ollama, clima, TTS) corren en hilos y nunca bloquean el servidor.

## 6. Persistencia

- Base de datos: `~/.local/share/cort/cort.db` (o `data/cort.db` si existe
  `CORT_HOME`). Tablas: `facts`, `episodes`, `alarms`, `meta`.
- Conocimiento: `knowledge/*.md|*.txt`, leído por bloques separados por líneas en
  blanco; puntuación por coincidencia de palabras.
- Configuración: `config/cort.toml`. Los valores ausentes usan los defaults de
  `cort/config.py`.
- Secretos: ninguno en la fase 1. Las APIs de clima no piden clave.

## 7. Degradación

| Falta | Qué pasa |
|---|---|
| Ollama apagado | Router y herramientas funcionan; conversación libre responde con aviso honesto. |
| Vosk ausente | Sin micrófono; el chat y el TTS siguen. |
| pywebview ausente | Se abre el navegador; si no hay entorno gráfico, el servidor queda en modo headless. |
| `playerctl` ausente | Medios con VLC y pausa por señal; se avisa de las limitaciones. |
| Red caída | Clima y búsquedas fallan con mensaje explícito; hora, memoria y sistema siguen. |
| RAM baja | El HUD reduce partículas y FPS; el LLM no se carga hasta que se pide. |
| Modelo lento | Prompt compacto, `num_predict` recortado, tiempo límite de 240 s y aviso de espera. |

## 8. Extensiones previstas

- `voice/piper.py` para voz neuronal.
- `brain/adapters/openclaw.py` y `brain/adapters/hermes.py` como subprocesos
  opcionales con el mismo contrato JSON del arnés.
- `hud/static/avatar/` para el avatar humanoide de la fase 5.
- `net/` para el puente PC ↔ A16 con token y descubrimiento local.
