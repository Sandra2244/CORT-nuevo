# Roadmap de CORT

Fechas reales. La fase 1 se cierra el **2026-10-29**; lo demás no tiene promesa de
fecha hasta que la fase 1 esté verificada.

## Fase 1 — Núcleo, HUD y comandos (2026-10-27 → 2026-10-29)

Estado: completa en local; publicación pendiente de autorización de Sandra.

- [x] Documento maestro, arquitectura y decisiones.
- [x] Configuración, bus, memoria SQLite.
- [x] Router en español sin tildes.
- [x] Cliente Ollama con modelos pequeños ya instalados.
- [x] Gestor de modelos: listar, elegir y descargar con progreso en el HUD.
- [x] Herramientas: hora, fecha, clima, sistema, apps, medios, búsqueda, alarmas,
      conocimiento, memoria.
- [x] Arnés de agentes con trazas.
- [x] HUD con orbe de filamentos luminosos, reloj de siete segmentos, estados, chat y medidores.
- [x] Voz: espeak-ng y Vosk opcional (Vosk queda sin instalar).
- [x] Pruebas sin red y verificación real de VLC, apps y modelos.
- [x] README e instructivo de instalación.

Criterio de cierre: los 10 puntos de aceptación de `PROMPT-MAESTRO.md` §11.

## Fase 1.5 — Modelo conversacional (2026-10-28)

Estado: completa y verificada en local.

- [x] Descarga real de `gemma3:270m` (278 MB, 66 s) con porcentaje por capas.
- [x] Auto-selección del modelo descargado y persistencia de la elección.
- [x] Cancelar descarga cerrando la conexión de `ollama pull`.
- [x] Recomendados por RAM (qwen2.5:0.5b, qwen3:0.6b, gemma3:1b, llama3.2:1b).
- [x] Prompt compacto, recorte de `num_predict` e historial de 8 turnos.
- [x] Texto parcial del modelo en el HUD y tiempo límite de 240 s.
- [x] Conversación real con `qwen2.5:0.5b` (269 s en este portátil).
- [ ] Conversación fluida: depende de liberar RAM o de un equipo más potente.

## Fase 1.6 — HUD v2 y control real (2026-10-28)

Estado: completa en local; falta la prueba en el teléfono.

- [x] Rail de acciones adaptativo (escritorio, tablet y rejilla táctil).
- [x] Panel de capacidades con las 16 herramientas reales y 7 categorías.
- [x] Paleta de comandos con acciones, ejemplos, filtro y teclado.
- [x] STOP real: cancela el stream de Ollama, la voz y el turno.
- [x] Actividad con herramienta, argumentos, duración y error.
- [x] Arranque cinematográfico omitible.
- [x] Manifest, iconos 192/512 y metadatos PWA.
- [x] Análisis de jarvis_ai y OpenClaw en `docs/ANALISIS-HUD.md`.
- [ ] PWA instalada y probada en el A16 por red local.
- [ ] Tarjetas de aprobación ALLOW/DENY para herramientas de riesgo alto.
- [ ] Gestos con cámara (prototipo aislado antes de integrar).

## Fase 2 — Voz completa y alarmas (después de F1)

- Wake word continua con Vosk en hilo propio y consumo < 3 % CPU.
- VAD por energía, barge-in real, frases de confirmación.
- Alarmas con playlist y mensaje leído; recordatorios recurrentes.
- Modo silencioso persistente y atajo de teclado global.

## Fase 3 — Windows y colaborador

- Adaptación de TTS (SAPI o espeak) y rutas.
- `.vbs` de arranque y acceso directo en la carpeta de inicio.
- Instructivo paso a paso para el equipo de Askher (8 GB).
- Prueba de instalación limpia en una carpeta nueva y ZIP de la etiqueta.

## Fase 4 — Android y multi-dispositivo

- HUD en el navegador del A16 contra el servidor de la PC en red local.
- O núcleo en Termux con modelo pequeñísimo.
- Token de acceso, descubrimiento local y reconexión.
- Notificaciones y alarmas del teléfono (fase posterior).

## Fase 5 — Avatar Cortana (última, como pidió Sandra)

- Retrato holográfico por capas, no un modelo 3D pesado: imagen base + capas de luz.
- Aberración cromática, líneas de escaneo, glitch controlado, partículas de borde.
- Sincronización de labios por visemas aproximados a partir del texto.
- Estados de ánimo y mirada que sigue al cursor.
- Presupuesto: < 15 % CPU en el portátil; se degrada a retrato estático si no alcanza.

## Fase 6 — Publicación

- README con badges, índice, capturas y guía de instalación.
- Licencia y créditos (Sandra y Askher).
- Etiqueta `v0.1.0` solo cuando la fase 1 pase entera.
- Conservar las ramas actuales como respaldo hasta que Sandra decida lo contrario.

## Riesgos abiertos

| Riesgo | Mitigación |
|---|---|
| RAM de 1,8 GiB | Modelos pequeños, HUD sin Electron, carga diferida. |
| Modelos de 0.5–0.6B alucinan | Router primero; reglas de honestidad; herramientas verificadas. |
| Vosk no instalado | Modo texto por defecto; instalación guiada. |
| Falta de `ffmpeg` | Referencias extraídas con VLC/GStreamer; no bloquea el código. |
| Cuota de copilotos | Estado en archivos (`docs/`), no en el chat. |
| Publicación accidental | Nada de GitHub en F1; `gh` sin sesión. |
