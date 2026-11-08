# Instalación en distintas distribuciones Linux

La instalación mantiene un único entorno Python 3.12 y los mismos locks CPU/NVIDIA.
Los scripts nuevos preparan requisitos por familia y delegan en `scripts/install.sh`:
no cambian la CLI, la configuración existente, los datos ni la desinstalación segura.

## Distribuciones y estado real

| Familia | Sistemas previstos | Script | Gestor y multimedia |
|---|---|---|---|
| Debian | Debian, Ubuntu, Linux Mint, Pop!_OS, KDE neon | `install-debian.sh` | apt-get, ffmpeg, fonts-dejavu-core |
| Fedora | Fedora tradicional con DNF | `install-fedora.sh` | dnf, ffmpeg-free, dejavu-sans-fonts |
| Arch | Arch Linux, Manjaro, EndeavourOS | `install-arch.sh` | pacman, ffmpeg, ttf-dejavu |
| openSUSE | Leap, Tumbleweed, Slowroll | `install-opensuse.sh` | zypper, ffmpeg, dejavu-fonts |

**Estado: planes y scripts probados con mocks, no instalaciones certificadas en cada
distribución.** La CI Ubuntu ejecuta pruebas sintéticas; no ejecuta el instalador con
sudo. No se afirma compatibilidad universal ni con todas las versiones históricas.
Objetivo: Linux x86_64 con glibc y Bash; Python 3 del sistema permite arrancar el
instalador, mientras uv proporciona Python 3.12 para la aplicación.

RHEL, Rocky, AlmaLinux, CentOS, Alpine/musl, NixOS y ediciones inmutables como
Silverblue/Kinoite no están automatizados. ARM y ROCm siguen sin validar. Las
versiones de distribución y repositorios disponibles determinan si los paquetes
existen; el script se detiene si el gestor falla, sin cambiar de proveedor.

## Uso recomendado

Desde una copia del repositorio, **como usuario normal**:

```bash
# Primero revisa el plan; no ejecuta comandos, descargas ni escrituras:
bash scripts/install-linux.sh cpu --system --install-uv --dry-run

# Después, si el plan es correcto:
bash scripts/install-linux.sh cpu --system --install-uv
# Perfil alternativo, con driver NVIDIA ya instalado:
# bash scripts/install-linux.sh nvidia --system --install-uv
```

`--system` autoriza invocar sudo únicamente para los requisitos del gestor de
paquetes. El gestor puede pedir su confirmación habitual. No se fuerza `-y`, no se
actualiza toda la distribución ni se añaden repositorios. En Arch mantén el sistema
actualizado previamente por sus procedimientos habituales; no se hace `pacman -Sy`.

`--install-uv` autoriza descargar y ejecutar como usuario el instalador oficial uv
0.12.17, solo si falta uv. Se descarga por HTTPS a un archivo temporal; no se ejecuta
con sudo ni modifica los perfiles del shell. El origen es Astral y sus artefactos
oficiales: esta descarga requiere confianza en ese proveedor. uv queda en
`~/.local/bin`. Si ya existe, se conserva su versión. El lock fija dependencias de
la aplicación; no fija versiones de los paquetes del sistema.

Sin esas dos opciones, el script comprueba requisitos existentes y prepara solo el
entorno del proyecto. Si no reconoce la distribución, se detiene. Puedes elegir
explícitamente una familia mediante los scripts específicos:

```bash
bash scripts/install-debian.sh cpu --system --install-uv
bash scripts/install-fedora.sh cpu --system --install-uv
bash scripts/install-arch.sh nvidia --system --install-uv
bash scripts/install-opensuse.sh cpu --system --install-uv
```

No ejecutes todos: elige el de tu sistema. El override explícito permite usar el
backend en un derivado compatible; no convierte una distribución no validada en
soportada. La detección analiza `/etc/os-release` como datos, sin ejecutarlo.

## Si falta Python para arrancar

Instálalo primero con el gestor de tu distribución:

```bash
# Debian/Ubuntu/Mint
sudo apt-get install python3
# Fedora
sudo dnf install python3
# Arch/Manjaro
sudo pacman -S --needed python
# openSUSE
sudo zypper install python3
```

No se usa pip global ni sudo pip. Para una distribución sin automatización,
instala por sus medios Bash, Python 3, uv, FFmpeg/ffprobe, fuentes y Git; después
usa `bash scripts/install.sh cpu`. Los locks requieren un entorno compatible.

## FFmpeg, codecs y Ollama

Antes de crear/sincronizar el entorno, se verifican `ffmpeg`, `ffprobe` y los filtros
`scdet` y `drawtext`. Eso no garantiza disponer de todos los codecs del vídeo de
entrada. Fedora ofrece `ffmpeg-free`; openSUSE también puede limitar codecs según
los repositorios configurados. No se instala RPM Fusion/Packman automáticamente ni
se intercambian paquetes. Resuelve cualquier codec ausente siguiendo la documentación
de tu distribución antes de procesar contenido real.

Ollama, los modelos y los drivers siguen siendo instalaciones separadas. Estos
scripts no crean servicios ni leen cookies. Sigue [INSTALLATION.md](INSTALLATION.md)
para iniciar Ollama, descargar modelos, configurar rutas y ejecutar `reel doctor`.
Para terminar añade `~/.local/bin` a PATH si hace falta. `REELS_KNOWLEDGE_HOME` y
`REELS_KNOWLEDGE_BIN_DIR` se conservan en todos los recorridos.

## Actualizar, retirar y verificar

Repite el script del perfil con el proceso detenido, respaldando antes tus datos.
La configuración local se conserva; cambiar de CPU a NVIDIA no reescribe modelos.
La sincronización del entorno puede retirar paquetes ajenos al perfil.
`bash scripts/uninstall.sh` sigue retirando solo el enlace del comando: no revierte
paquetes globales, uv, modelos ni datos.

Pruebas sin red/root/GPU:

```bash
python3 -m unittest discover -s tests -v
bash -n bin/reel scripts/*.sh
```

La suite comprueba detección, derivados, rechazo de sistemas no soportados,
simulación de los cuatro wrappers, separación sudo/entorno, ausencia de filtros,
uv versionado y conservación de los recorridos existentes.

Fuentes oficiales consultadas (2026-11-08):
[instalación uv](https://docs.astral.sh/uv/getting-started/installation/),
[opciones de su instalador](https://docs.astral.sh/uv/reference/installer/),
[ffmpeg-free en Fedora](https://packages.fedoraproject.org/pkgs/ffmpeg/ffmpeg-free/).
