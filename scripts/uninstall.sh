#!/usr/bin/env bash
set -euo pipefail
PROJECT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
LINK="${REELS_KNOWLEDGE_BIN_DIR:-$HOME/.local/bin}/reel"
if [[ -L "$LINK" && "$(readlink -f -- "$LINK")" == "$PROJECT/bin/reel" ]]; then
  unlink "$LINK"
  echo "Comando retirado: $LINK"
fi
echo "Se conserva el proyecto: $PROJECT"
echo 'No se borran el Vault, configuración, SQLite, backups, entorno, paquetes ni modelos.'
echo 'Puedes archivar o eliminar el código manualmente después de respaldar tus datos.'
