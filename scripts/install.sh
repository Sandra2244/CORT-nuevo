#!/usr/bin/env bash
# Comprueba el entorno de CORT y dice qué falta. No instala nada por su cuenta.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"
DATOS="${CORT_HOME:-$HOME/.local/share/cort}"

echo "CORT · comprobación de instalación"
echo "proyecto: $RAIZ"
echo

fallos=0
aviso() { echo "  ✗ $1"; fallos=$((fallos + 1)); }
ok() { echo "  ✓ $1"; }
opcional() { echo "  · $1"; }

echo "Python"
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
  ok "$(python3 --version) (se necesita 3.11 o más)"
else
  aviso "falta Python 3.11+ (probá: sudo apt install python3)"
fi

echo
echo "Bibliotecas de Python"
for modulo in psutil requests; do
  if python3 -c "import $modulo" >/dev/null 2>&1; then
    ok "$modulo"
  else
    aviso "falta $modulo (probá: sudo apt install python3-$modulo)"
  fi
done

echo
echo "Programas del sistema"
for programa in espeak-ng cvlc xdg-open notify-send; do
  if command -v "$programa" >/dev/null 2>&1; then
    ok "$programa"
  else
    aviso "falta $programa (probá: sudo apt install espeak-ng vlc xdg-utils libnotify-bin)"
  fi
done

echo
echo "Opcionales"
command -v arecord >/dev/null 2>&1 && ok "arecord (micrófono)" || opcional "arecord: sin micrófono (sudo apt install alsa-utils)"
command -v playerctl >/dev/null 2>&1 && ok "playerctl (control de música)" || opcional "playerctl: pausa/avance de música (sudo apt install playerctl)"
python3 -c 'import webview' >/dev/null 2>&1 && ok "pywebview (ventana nativa)" || opcional "pywebview: el HUD se abrirá en el navegador"
if python3 -c 'import vosk' >/dev/null 2>&1; then
  ok "vosk (voz)"
  if [ -d "$DATOS/vosk-es" ]; then
    ok "modelo de voz en $DATOS/vosk-es"
  else
    opcional "modelo de voz: ejecutá scripts/fetch-vosk-es.sh"
  fi
else
  opcional "vosk: sin reconocimiento de voz (ver requirements-optional.txt)"
fi

mkdir -p "$DATOS"
echo
echo "Datos: $DATOS"

echo
echo "Diagnóstico de CORT"
set +e
python3 -m cort --doctor
estado_doctor=$?
set -e

echo
if [ "$fallos" -gt 0 ]; then
  echo "Faltan $fallos dependencia(s) obligatoria(s). Corregí lo marcado con ✗ y volvé a ejecutar este guion."
  exit 1
fi
if [ "$estado_doctor" -ne 0 ]; then
  echo "Lo obligatorio está listo; el doctor marcó avisos opcionales (arriba)."
else
  echo "Todo listo. Probá: ./scripts/run.sh --once \"¿qué hora es?\""
fi
