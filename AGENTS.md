# AGENTS.md — instrucciones para cualquier agente que trabaje en CORT

Este archivo es obligatorio para copilotos y agentes. Si algo aquí contradice a un
mensaje suelto, manda este archivo y el `docs/PROMPT-MAESTRO.md`.

## Antes de tocar código

1. Leer `docs/PROMPT-MAESTRO.md`, `docs/ARQUITECTURA.md` y `docs/ROADMAP.md`.
2. Revisar el estado real: `git status --short`, `git log --oneline -5`,
   `python3 -m cort --doctor`.
3. No asumir que algo existe porque un resumen lo dice: leerlo o ejecutarlo.

## Reglas duras

- **No inventar** rutas, comandos, versiones, resultados de pruebas ni enlaces.
  Si no se puede comprobar, se dice «no lo puedo comprobar».
- **No tocar GitHub**: ni ramas, ni pushes, ni releases. La fase 1 es local.
- **No borrar** archivos de Sandra fuera de este proyecto.
- **No ejecutar** acciones destructivas ni envíos sin confirmación explícita.
- **Nada de `shell=True`** con texto del usuario. Allowlist para apps.
- **Recursos**: el portátil tiene 2 núcleos y 1,8 GiB. No lanzar Ollama + navegador
  + pruebas pesadas a la vez. Cerrar lo que se abra.
- **Pruebas**: toda comprobación nueva debe poder ponerse roja. Mutarla a propósito
  y verificar que falla exactamente donde debe.
- **Salida completa**: no usar `| tail` si el código de salida importa; guardar el
  log y leerlo.

## Cómo ejecutar

```bash
cd ~/Vídeos/CORT
python3 -m cort --doctor          # entorno
python3 -m cort                   # chat en terminal
python3 -m cort --hud             # HUD + chat
python3 -m cort --once "qué hora es"
python3 -m unittest discover -s tests -v
```

## Estilo

- Código e identificadores en inglés; comentarios, interfaz y documentación en español.
- Python 3.11+ (aquí 3.13), biblioteca estándar primero.
- Funciones pequeñas, sin dependencias nuevas sin justificarlo.
- Los errores se muestran al usuario en español y se registran en el log del HUD.

## Estado actual

Fase 1 en construcción (2026-10-27). Ver `docs/ROADMAP.md` para lo hecho y lo pendiente.
