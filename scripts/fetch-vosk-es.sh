#!/usr/bin/env bash
# Descarga el modelo pequeño de Vosk en español (39 MB) para la escucha local.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATOS="${CORT_HOME:-$HOME/.local/share/cort}"
DESTINO="$DATOS/vosk-es"
URL="https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"

if [ -d "$DESTINO/am" ] && [ -d "$DESTINO/conf" ]; then
  if [ "${1:-}" != "--forzar" ]; then
    echo "El modelo ya está en $DESTINO"
    echo "Para descargarlo de nuevo: $0 --forzar"
    exit 0
  fi
  rm -rf "$DESTINO"
fi

for programa in curl unzip; do
  if ! command -v "$programa" >/dev/null 2>&1; then
    echo "Falta $programa. Instalalo con: sudo apt install $programa"
    exit 1
  fi
done

if ! python3 -c 'import vosk' >/dev/null 2>&1; then
  echo "Aviso: el paquete de Python «vosk» no está instalado; sin él CORT no podrá usar el modelo."
  echo "  Opción con venv:  python3 -m venv .venv && .venv/bin/pip install vosk"
  echo "  Opción de usuario: python3 -m pip install --user vosk"
  echo
fi

TMP="$(mktemp -d)"
limpiar() { rm -rf "$TMP"; }
trap limpiar EXIT

echo "Descargando $URL"
curl -fL --progress-bar -o "$TMP/modelo.zip" "$URL"

echo "Descomprimiendo…"
unzip -q "$TMP/modelo.zip" -d "$TMP"

ORIGEN="$(find "$TMP" -maxdepth 1 -type d -name 'vosk-model-*' | head -n 1)"
if [ -z "$ORIGEN" ] || [ ! -d "$ORIGEN/am" ] || [ ! -d "$ORIGEN/conf" ]; then
  echo "La descarga no tiene la estructura esperada del modelo. No instalé nada."
  exit 1
fi

mkdir -p "$DATOS"
rm -rf "$DESTINO"
mv "$ORIGEN" "$DESTINO"

echo "Modelo instalado en $DESTINO"
echo "Ahora podés arrancar con voz: ./scripts/run.sh --hud --voz"
