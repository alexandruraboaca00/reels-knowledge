#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if ! command -v python3 >/dev/null; then
  echo 'Instala primero Python 3 con el gestor de tu distribución (consulta docs/LINUX.md).' >&2
  exit 1
fi
exec python3 "$ROOT/scripts/install_linux.py" "$@"
