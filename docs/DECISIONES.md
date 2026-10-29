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
