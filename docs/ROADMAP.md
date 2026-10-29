# Roadmap de CORT

Fechas reales. La fase 1 se cierra el **2026-10-29**; lo demás no tiene promesa de
fecha hasta que la fase 1 esté verificada.

## Fase 1 — Núcleo, HUD y comandos (2026-10-27 → 2026-10-29)

Estado: completa en local y **publicada** en GitHub el 2026-10-29 (ver fase 1.7).

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

## Fase 1.7 — Publicación y APK de bolsillo (2026-10-29)

Estado: publicada y compilada en GitHub Actions; falta instalarla en el teléfono.

- [x] Llave del HUD: el servidor se niega a salir de `127.0.0.1` sin token, compara
      `X-CORT-Token` o `?token=` en bytes y deja públicos sólo `/static/*`, `/favicon.ico`
      y `/api/salud`. Medido por HTTP: 401 sin llave, 200 con ella, 401 con llave falsa.
- [x] `hud.js` guarda el token en `sessionStorage` y lo borra de la barra de direcciones.
- [x] `--host` y `--token` en la CLI; CORT imprime el enlace del teléfono con el token.
- [x] Repo público en GitHub con `main` como única rama; 158 pruebas y `--once` corren en
      Actions antes de dejar compilar el APK.
- [x] `apps/bolsillo/`: cliente `WebView` sin AndroidX, Gradle ni Kotlin, con aviso honesto
      cuando la PC no responde y permiso de micrófono en tiempo de ejecución.
- [x] Compilación a mano (`aapt2` ▸ `javac` ▸ `d8` ▸ `zipalign` ▸ `apksigner`) en Actions, con
      la misma llave que firmó el `CORT-IA-2.11.0-nucleo.apk` (huella `FA:AB:EF:46:…:19:77`)
      y `versionCode` 30001 > 21100: mismo paquete + misma llave + número más alto.
- [x] Releases `v3.0.0` y `v3.0.1` con el APK, `-firma.txt` y `-auditoria.txt`; la auditoría
      deja constancia de `minSdkVersion:'26'`, los 4 permisos, `resources.arsc` sin comprimir
      y el alineado de a 4. La 3.0.1 existe porque se corrigió el `grep` que no reportaba el
      mínimo: el artifact publicado sale del mismo código que está en `main`.
- [ ] Instalación real encima del 2.11.0 en el A16, sin perder la dirección guardada.
- [ ] Micrófono del HUD funcionando dentro del `WebView` (Android 16).
- [ ] Borrar el repo viejo y renombrar `CORT-nuevo` ▸ `CORT`: hace falta el alcance
      `delete_repo`, que aún no se ha aprobado.

## Fase 2.0 — Híbrido, autonomía y asistente Android (plan aprobado 2026-10-29)

Plano completo en `docs/ARQUITECTURA-2.0.md`. Decisiones en ADR-009 a ADR-013. Esta fase
absorbe lo que antes eran la fase 2 (voz) y la fase 4 (Android).

Lo que Sandra decidió en la encuesta de arquitectura: rol de asistente **y** overlay desde
el día uno; CORT híbrido con modelos en el teléfono *y* en la PC; primer incremento = modo
estudio; voz Piper/sherpa `es_ES` + `es_MX`.

Lo que decidió en la segunda encuesta (2026-10-29): la tanda arranca por **personalidad y
«no sé»** antes que por el HUD; el tono es **cálido y cercano**, que reconoce el límite y
ofrece acompañar; el HUD nuevo sigue los **paneles del video** (orbe al centro con la palabra
de estado, alrededor máquinas, skills, diagnóstico y trazas, con densidad de telemetría); y
el primer modelo dentro del teléfono es **Qwen2.5 0.5B int4** (≈400 MB).

- [ ] **2.0.1 Estudio** — «Leer con CORT» en el menú de selección, TTS Piper, servicio en
      primer plano con `MediaSession`, bienvenida de permisos y cola por frases.
      *Publicado* (2026-10-29) como APK 3.1.2: `LeerActivity`
      (`ACTION_PROCESS_TEXT` + `ACTION_SEND`), `LectorService` en primer plano
      `mediaPlayback`, troceo por frase con reanudación por hash del texto, controles en
      notificación, pantalla bloqueada y audífonos, voz `es_ES` ▸ `es_MX` del sistema y
      comprobación en la compilación de que los componentes llegaron al APK.
      *Falta*: probarlo en el A16 (menú, pantalla apagada, reanudar) y sustituir la voz
      del sistema por **Piper/sherpa** con los modelos `es_ES`/`es_MX`. Ese cambio es
      2.0.1b y va después de esa prueba.
- [x] **2.0.2 Voz propia** — una sola casa para fallar con honestidad (`honesto.py`),
      persona cálida y cercana con protocolo explícito de «no sé», y tabla `gaps` que
      guarda lo que CORT no pudo responder, con contador y pregunta rescatable
      («¿qué no sabés?» / «olvidá lo que no sabés»). 177 pruebas verdes en local
      (2026-10-29). *Falta*: correr la suite en Actions con `pruebas.yml` y escuchar
      la voz nueva en dos o tres conversaciones reales.
- [ ] **2.0.3 Presencia** — overlay transparente tipo Gemini, tile del panel rápido, rol
      de asistente y «¿qué ves?» con cita del texto leído (o negativa honesta).
- [ ] **2.0.4 Skills** — manifiestos `skill.json`, permisos por habilidad, JSON-RPC 2.0 y
      migración de las 16 herramientas actuales.
- [ ] **2.0.5 Agente** — planificador con presupuesto de pasos, aprobación ALLOW/DENY,
      tablas `runs`/`steps` y vista de trazas.
- [ ] **2.0.6 HUD 2.0** — paneles de telemetría del video, máquinas (PC y teléfono),
      skills, diagnóstico y tablero; orbe conservado con anillo de marcas.
- [ ] **2.0.7 Híbrido** — modelo local en el teléfono, router por tarea/batería/red y
      sincronización incremental de memoria.

Criterio de cierre de cada punto: la medición de [`docs/MEDICIONES.md`](MEDICIONES.md), no
la impresión.

## Fase 2 — Voz completa y alarmas (absorbida por 2.0)

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

Lo de la fase 1.7 es el principio de ésta: el cliente de bolsillo ya existe y ya se
compila firmado. Falta el teléfono delante.

- [x] Token de acceso al HUD por red local (negado si falta, medido por HTTP).
- [x] Cliente Android que abre ese HUD y recuerda la dirección.
- [ ] HUD en el navegador del A16 contra el servidor de la PC en red local.
- [ ] El núcleo en Termux con modelo pequeñísimo.
- [ ] Descubrimiento local (anuncio del servicio) y reconexión automática.
- [ ] Notificaciones y alarmas del teléfono (fase posterior).

## Fase 5 — Avatar Cortana (última, como pidió Sandra)

- Retrato holográfico por capas, no un modelo 3D pesado: imagen base + capas de luz.
- Aberración cromática, líneas de escaneo, glitch controlado, partículas de borde.
- Sincronización de labios por visemas aproximados a partir del texto.
- Estados de ánimo y mirada que sigue al cursor.
- Presupuesto: < 15 % CPU en el portátil; se degrada a retrato estático si no alcanza.

## Fase 6 — Publicación

El grueso se hizo en la fase 1.7; lo que queda es de acabado.

- [x] Repo público, `main` como única rama, y CI que corre las pruebas antes del APK.
- [x] `pruebas.yml`: la suite completa y `--once` en cada `push` a `main` y en cada
      `pull_request`. Antes sólo se mediaban las pruebas al etiquetar y un rojo podía
      quedarse días en `main` sin que nadie lo viera.
- [x] Etiquetas `v3.0.0` y `v3.0.1` con el APK firmado y sus dos archivos de evidencia.
- [ ] README con badges, índice y capturas nuevas (la guía de instalación ya está).
- [ ] Licencia y créditos (Sandra y Askher).
- [ ] Borrar el repo viejo y renombrar `CORT-nuevo` ▸ `CORT`, cuando Sandra apruebe el
      alcance `delete_repo`. Las ramas de respaldo del repo viejo ya no existen: se
      archivaron en el bundle y en el JSON de releases.

## Riesgos abiertos

| Riesgo | Mitigación |
|---|---|
| RAM de 1,8 GiB | Modelos pequeños, HUD sin Electron, carga diferida. |
| Modelos de 0.5–0.6B alucinan | Router primero; reglas de honestidad; herramientas verificadas. |
| Vosk no instalado | Modo texto por defecto; instalación guiada. |
| Falta de `ffmpeg` | Referencias extraídas con VLC/GStreamer; no bloquea el código. |
| Cuota de copilotos | Estado en archivos (`docs/`), no en el chat. |
| Publicación accidental | Ya no aplica: el repo es público a propósito desde 2026-10-29. La llave del APK sigue fuera del repo (`keystore/`, `*.jks` y `pass.txt` en `.gitignore`), y el HUD no sale del bucle sin token. |
