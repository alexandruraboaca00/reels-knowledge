#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${1:-cpu}"
case "$PROFILE" in cpu|nvidia) ;; *) echo 'Uso: scripts/install.sh [cpu|nvidia]' >&2; exit 2;; esac
command -v uv >/dev/null
command -v ffmpeg >/dev/null
command -v ffprobe >/dev/null
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  uv venv --python 3.12 "$ROOT/.venv"
fi
if ! "$ROOT/.venv/bin/python" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)'; then
  echo 'Se requiere Python 3.12. Conserva el entorno existente y crea uno compatible antes de instalar.' >&2
  exit 1
fi
LOCK="$ROOT/requirements-cpu.lock"
[[ "$PROFILE" == nvidia ]] && LOCK="$ROOT/requirements-nvidia.lock"
uv pip sync --python "$ROOT/.venv/bin/python" --require-hashes "$LOCK"
STATE="${REELS_KNOWLEDGE_HOME:-$ROOT}"
mkdir -p "$STATE/config" "$STATE/data/tmp" "$STATE/vault/Reels"
if [[ ! -e "$STATE/config/config.json" ]]; then
  "$ROOT/.venv/bin/python" - "$ROOT" "$STATE" "$PROFILE" <<'PY'
import json, sys
from pathlib import Path
root, state = map(Path, sys.argv[1:3])
cfg = json.loads((root / 'config/config.example.json').read_text())
if sys.argv[3] == 'cpu':
    cfg.update(whisper_model='base', whisper_device='cpu', vision_model='qwen3-vl:2b', text_model='qwen3:1.7b')
else:
    cfg['whisper_device'] = 'cuda'
(state / 'config/config.json').write_text(json.dumps(cfg, indent=2)+'\n')
PY
fi
LINK="${REELS_KNOWLEDGE_BIN_DIR:-$HOME/.local/bin}/reel"
mkdir -p "$(dirname -- "$LINK")"
if [[ -e "$LINK" || -L "$LINK" ]]; then
  if [[ "$(readlink -f -- "$LINK")" != "$ROOT/bin/reel" ]]; then
    echo "Instalado, pero se conserva el comando existente: $LINK" >&2
    exit 1
  fi
else
  ln -s "$ROOT/bin/reel" "$LINK"
fi
echo "Instalado en $ROOT. Añade $(dirname -- "$LINK") a PATH."
echo 'Instala/inicia Ollama y descarga los modelos indicados en tu configuración. Ejecuta reel doctor.'
