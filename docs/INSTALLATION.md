# Instalación, actualización y retirada

## Alcance comprobado

Linux x86_64, Bash y Python 3.12 son el objetivo reproducible. Se han ejecutado
pruebas locales y una instalación del lock CPU en un entorno temporal.
Una instalación completa en Arch recién instalado y la inferencia GPU están
pendientes. macOS, Windows, ARM y ROCm no se declaran compatibles.

FFmpeg debe incluir `scdet`; la prueba sintética usa `drawtext` y fuentes.
FFmpeg del sistema se utiliza incluso aunque PyAV incluya sus propias bibliotecas.
Ollama ≥0.12.7 es el mínimo indicado por su catálogo para Qwen3-VL.

## Arch Linux

```bash
sudo pacman -S --needed ffmpeg uv git
# Opcionales: obsidian, sqlite (la biblioteca SQLite ya viene con Python)
uv python install 3.12
bash scripts/install.sh cpu
# O bien: bash scripts/install.sh nvidia
export PATH="$HOME/.local/bin:$PATH"
```

El script no ejecuta pacman, sudo pip ni descarga modelos. Crea `.venv` cuando
falta e instala exactamente el lock elegido con hashes. Si ya existe un entorno,
`uv pip sync` lo sincroniza y puede retirar paquetes ajenos al perfil. No compartas
este entorno con otros proyectos. No sobrescribe comandos de otra instalación.

El perfil CPU nuevo fija Whisper `base`/CPU y modelos `qwen3-vl:2b`/`qwen3:1.7b`.
NVIDIA fija `turbo`/CUDA y `qwen3-vl:4b`/`qwen3:4b`; requiere driver NVIDIA,
CUDA 12 y cuDNN 9 compatibles con CTranslate2. Los paquetes de bibliotecas NVIDIA
quedan en `.venv`; el launcher expone sus rutas al proceso. Un fallo CUDA explícito
se informa; `whisper_device=auto` permite fallback a CPU al cargar el modelo.

Instala e inicia Ollama por separado y descarga los modelos elegidos:

```bash
ollama pull qwen3-vl:2b
ollama pull qwen3:1.7b
reel config
reel doctor
```

Whisper descarga pesos la primera vez que se utiliza; doctor no los descarga ni
comprueba su caché. Doctor consulta las herramientas, dependencias y modelos de
Ollama sin leer cookies ni descargar vídeos.

## Rutas

El código y `.venv` se resuelven desde el launcher real, incluso usando un enlace
o una ruta con espacios. Por defecto los datos quedan junto al código.
Para separarlos, usa la misma variable al instalar y ejecutar:

```bash
export REELS_KNOWLEDGE_HOME="$HOME/.local/share/reels-knowledge"
bash scripts/install.sh cpu
reel config
```

La variable no mueve datos antiguos: respalda y traslada los datos manualmente
antes de usarla sobre una instalación existente. `REELS_KNOWLEDGE_BIN_DIR`
permite cambiar el directorio del enlace (por defecto `~/.local/bin`).

## Actualizaciones

Respalda tu configuración, SQLite y Vault antes de actualizar código. Con el
proceso detenido, sustituye solo los archivos de código/documentación revisados y
repite el instalador del perfil elegido. No copies la plantilla sobre tu JSON.
Las claves nuevas usan valores de `config.example.json`; los valores locales tienen
prioridad. La configuración antigua `max_frames` ya no limita las capturas: utiliza
`frames` para ajustar la cobertura. No existe migración destructiva de la base.

Locks generados con uv 0.12.17 para Python 3.12; PyAV permanece en `av==18.1.0`.
Las versiones completas, dependencias transitivas y hashes están en los locks.
Para una actualización deliberada:

```bash
uv pip compile requirements.txt --python-version 3.12 --generate-hashes -o requirements-cpu.lock
uv pip compile requirements-gpu.txt --python-version 3.12 --generate-hashes -o requirements-nvidia.lock
```

Revisa ambos diffs y repite instalación aislada, `uv pip check` y tests. Resolver
paquetes no demuestra compatibilidad de inferencia ni licencias del conjunto.

## Desinstalación segura

```bash
bash scripts/uninstall.sh
```

Retira únicamente el enlace `reel` si apunta a este proyecto. Conserva código,
`.venv`, configuración, Vault, SQLite, backups, paquetes globales y modelos.
No hay borrado recursivo automático. Archiva tus datos antes de eliminar carpetas
manualmente. Una ruta de datos externa se conserva también.
