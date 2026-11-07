"""Rutas compartidas; REELS_KNOWLEDGE_HOME permite trasladar datos y configuración."""
import os
from pathlib import Path

ROOT = Path(os.environ.get("REELS_KNOWLEDGE_HOME", Path(__file__).resolve().parents[1])).expanduser().resolve()
CONFIG_PATH = ROOT / "config" / "config.json"
DB_PATH = ROOT / "data" / "reels.db"
TMP_ROOT = ROOT / "data" / "tmp"
VAULT = ROOT / "vault"
VENV_BIN = Path(__file__).resolve().parents[1] / ".venv" / "bin"
