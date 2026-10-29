#!/usr/bin/env bash
# Arranca CORT desde cualquier carpeta.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

exec python3 -m cort "$@"
