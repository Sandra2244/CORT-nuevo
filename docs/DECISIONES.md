# Decisiones de arquitectura (ADR)

## ADR-001 — Reconstrucción desde cero

**Fecha:** 2026-10-27.
**Decisión:** el nuevo CORT vive en `~/Vídeos/CORT` y no reutiliza código de
`~/Documentos/CORT`.
**Motivo:** el proyecto viejo acumula fallas, es lento y su interfaz no alcanza la
referencia visual de los videos. Copiar piezas arrastra el problema.
**Consecuencia:** se reescriben todos los módulos; el repo de GitHub queda intacto.

## ADR-002 — HUD web en vez de Tkinter

**Fecha:** 2026-10-27.
**Decisión:** HTML/CSS/JS con canvas, servido por Python y abierto en `pywebview` o
navegador.
**Motivo:** permite el orbe de partículas, el plasma y las animaciones de los videos
con buen rendimiento; el mismo HUD sirve luego en el móvil. Tkinter no alcanza esa
estética y Electron consumiría demasiada RAM.
**Consecuencia:** hace falta un navegador/WebKit (ya instalado). Si no hay entorno
gráfico, el servidor funciona en modo headless.

## ADR-003 — Router determinista antes del LLM

**Fecha:** 2026-10-27.
**Decisión:** las órdenes frecuentes se resuelven con reglas en español; el LLM solo
para conversación y razonamiento.
**Motivo:** velocidad, funcionamiento con Ollama apagado y menos alucinaciones.
**Consecuencia:** hay que mantener el router y sus pruebas; el arnés queda para lo
complejo.

## ADR-004 — Memoria en SQLite

**Fecha:** 2026-10-27.
**Decisión:** hechos, episodios y alarmas en SQLite.
**Motivo:** el `memory.json` del proyecto viejo se corrompía. SQLite ofrece escrituras
atómicas y consultas.
**Consecuencia:** la base es un archivo portable; se puede respaldar y borrar.

## ADR-005 — Dependencias pesadas opcionales

**Fecha:** 2026-10-27.
**Decisión:** `vosk`, `pywebview` y `piper` se detectan; si faltan, CORT degrada.
**Motivo:** portátil de 1,8 GiB y cuota limitada; instalar todo de golpe rompe el equipo.
**Consecuencia:** el instalador es explícito y no descarga nada sin avisar.

## ADR-006 — Nada de GitHub en la fase 1

**Fecha:** 2026-10-27.
**Decisión:** no se borran ramas, no se empuja y no se publica.
**Motivo:** `gh` no tiene sesión; borrar ramas sin respaldo es irreversible. Sandra
eligió «solo local por ahora».
**Consecuencia:** la entrega se queda en disco; la decisión de publicar es suya.

## ADR-007 — Voz: espeak-ng + Vosk

**Fecha:** 2026-10-27.
**Decisión:** TTS con `espeak-ng` (ya instalado) y STT con Vosk español (~50 MB,
opcional).
**Motivo:** todo local y sin cuotas; `espeak` funciona hoy mismo.
**Consecuencia:** la voz inicial suena sintética; Piper queda como mejora.

## ADR-008 — APK de bolsillo: cliente `WebView` (fase 1.7)

**Fecha:** 2026-10-29.
**Decisión:** el primer APK es un `WebView` que abre el HUD de la PC, paquete
`com.cort.ia`, firmado con la llave de siempre.
**Motivo:** verificaba el camino teléfono↔PC sin duplicar el núcleo, y permitía probar
la firma, la actualización encima y la auditoría con el material que Sandra ya tenía.
**Consecuencia:** es una ventana, no un asistente: no tiene servicios, ni voz, ni
overlay. Se conserva como «modo espejo» y sobre él se construye la app real (ADR-010).

## ADR-009 — Contrato de skill y JSON-RPC

**Fecha:** 2026-10-29.
**Decisión:** cada habilidad se describe con un manifiesto (`skill.json`) que declara
versión, permisos, riesgo, entradas, salidas y plataformas; la ejecución habla JSON-RPC
2.0, con el mismo patrón del Model Context Protocol.
**Motivo:** las herramientas actuales son funciones registradas a mano en Python; eso no
se puede versionar, ni limitar por permisos, ni escribir en Kotlin. Con contrato, una
skill nueva vive fuera del núcleo y sobrevive a cualquier rediseño del HUD o del agente.
**Consecuencia:** hay que migrar las 16 herramientas (envoltorio con manifiesto generado,
mismas funciones y mismas pruebas) y el registro debe rechazar permisos no concedidos.

## ADR-010 — Rol de asistente **y** overlay, no uno u otro

**Fecha:** 2026-10-29.
**Decisión:** la app nativa implementa `VoiceInteractionService` (rol `ASSISTANT`) y a la
vez una ventana `TYPE_APPLICATION_OVERLAY` y un `TileService`.
**Motivo:** la captura del A16 muestra que One UI 7 solo lista a Google como asistente;
si el rol queda bloqueado, el overlay y el tile siguen funcionando. Depender solo del rol
es apostar el proyecto a que Samsung lo permita.
**Consecuencia:** tres formas de abrir CORT que hay que probar por separado en el A16, y
una pantalla de bienvenida que guíe permisos de batería, micrófono, notificaciones y
«mostrar sobre otras apps».

## ADR-011 — Híbrido real: modelos en el teléfono **y** en la PC

**Fecha:** 2026-10-29.
**Decisión:** el teléfono corre TTS/STT propio y un modelo de 0.5B–1B int4; la PC sigue
siendo el cerebro para razonamiento largo y visión. La elección se hace por tarea,
batería y red, y la memoria se sincroniza por eventos incrementales.
**Motivo:** Sandra lo pidió explícito —«conectar a un PC será tedioso, debe ser dinámico,
adaptativo e híbrido»— y porque depender de una PC encendida convierte el asistente en un
adorno cuando se corta la luz o se sale de casa.
**Consecuencia:** doble inventario de capacidades, router de decisión, medición obligatoria
de latencia y batería, y límite de 1B int4 con aviso de consumo. La sincronización nunca
copia el `.db` completo: eventos con `revision`.

## ADR-012 — Dos pipelines de compilación Android

**Fecha:** 2026-10-29.
**Decisión:** el APK ligero sigue con `aapt2 ▸ javac ▸ d8`; cuando entren dependencias
`.aar` (ML Kit, sherpa-onnx) se añade un pipeline con Gradle para la app completa.
**Motivo:** el build a mano fue lo que permitió publicar el 3.0.1 sin JDK local y es
fácil de auditar; pero resolver `.aar` a mano es frágil y no escala.
**Consecuencia:** dos artefactos, misma llave y misma huella verificada; el `-firma.txt`
y la auditoría se mantienen en ambos.
