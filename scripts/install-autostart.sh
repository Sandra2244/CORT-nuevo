#!/usr/bin/env bash
# Instala o quita el arranque automático de CORT con el HUD (XFCE/GNOME).
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESTINO="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/cort.desktop"

if [ "${1:-}" = "--quitar" ]; then
  if [ -f "$DESTINO" ]; then
    rm -f "$DESTINO"
    echo "Arranque automático quitado: $DESTINO"
  else
    echo "No había arranque automático instalado."
  fi
  exit 0
fi

mkdir -p "$(dirname "$DESTINO")"
cat > "$DESTINO" <<EOF
[Desktop Entry]
Type=Application
Name=CORT
Comment=Asistente personal local
Exec="$RAIZ/scripts/run.sh" --hud
Path=$RAIZ
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo "Arranque automático instalado: $DESTINO"
echo "CORT abrirá el HUD al iniciar sesión."
echo "Para quitarlo: $0 --quitar"
