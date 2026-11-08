# Manifiesto de instalación

El instalador actual es `scripts/install.sh [cpu|nvidia]`. No instala paquetes del
sistema ni modelos y no usa sudo. Ejecuta uv para crear/sincronizar `.venv` Python
3.12 desde el lock del perfil con hashes. Las dependencias NVIDIA permanecen en el
entorno aislado. `requirements*.txt` son entradas de resolución; los locks son las
versiones completas reproducibles.

Crea si faltan:

- `.venv/` dentro de la copia del código.
- `config/config.json` a partir de la plantilla, ajustado al perfil inicial.
- `data/tmp/` y `vault/Reels/`.
- `~/.local/bin/reel`, enlace al launcher, si no existe otro comando.

`REELS_KNOWLEDGE_HOME` cambia la raíz de datos/configuración y
`REELS_KNOWLEDGE_BIN_DIR` la carpeta del enlace. La configuración existente se
conserva, incluso al cambiar de perfil. No se modifica el Vault al actualizar.
SQLite `data/reels.db` se crea al usar comandos que necesitan el registro; las
reparaciones guardan copias en `data/backups/`. No se versionan datos persistentes.

`uninstall.sh` solo retira el enlace que apunta al launcher de esta copia. Conserva
código, entorno, configuración, datos, modelos y paquetes globales. La retirada
manual de carpetas queda a cargo del usuario después de respaldarlas.

El instalador anterior asumía `~/Projects/reels-knowledge` y su desinstalador
borraba todo el proyecto. Esos comportamientos se sustituyen para proteger datos.
La configuración local histórica fue retirada del índice durante la preparación,
pero permanece en el commit inicial hasta una decisión autorizada sobre el historial.

## Preparación por familia Linux

`install-linux.sh` y los wrappers Debian/Fedora/Arch/openSUSE delegan en
`install_linux.py`. Con `--system` instalan requisitos mediante sudo; con
`--install-uv` pueden añadir uv 0.12.17 en `~/.local/bin` si falta. El modo
`--dry-run` solo muestra el plan. No instalan drivers, servicios Ollama, modelos
ni repositorios adicionales. Esos paquetes y uv se conservan al desinstalar.
Consulta docs/LINUX.md para alcance y comandos.
