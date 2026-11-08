# Reels Knowledge

Convierte vídeos de Instagram, YouTube (Shorts y `watch?v=…`) y TikTok en notas
Markdown para Obsidian, con transcripción, evidencia visual, enlaces e índices.
Procesamiento con Faster-Whisper y Ollama en tu equipo; SQLite evita repetir trabajos.

## Inicio rápido en Linux

Requiere Bash, Python 3.12 mediante uv, FFmpeg/ffprobe y Ollama ≥0.12.7 para Qwen3-VL.
Hay scripts para Debian/Ubuntu/Mint, Fedora, Arch/Manjaro y openSUSE.
Consulta [Instalación Linux](docs/LINUX.md) para detección automática, simulación
y restricciones. No se han validado instalaciones completas en cada distro;
Windows y macOS no están validados.

Cada familia instala los requisitos del sistema con su **gestor de paquetes nativo**:

| Distribución | Gestor | Script específico |
|---|---|---|
| Debian, Ubuntu, Linux Mint | `apt-get` | `scripts/install-debian.sh` |
| Fedora | `dnf` | `scripts/install-fedora.sh` |
| Arch, Manjaro, EndeavourOS | `pacman` | `scripts/install-arch.sh` |
| openSUSE | `zypper` | `scripts/install-opensuse.sh` |

`pacman` solo se usa en Arch y derivados. En todas las familias, las dependencias
Python se instalan con **uv dentro de `.venv`**, sin pip global ni `sudo pip`.
El instalador común detecta la distribución; `--system` habilita los paquetes del
sistema con sudo y `--install-uv` instala uv como usuario si falta. Ollama, sus
modelos y los drivers se preparan por separado.

Ejemplo específico para Arch, desde una copia local del proyecto:

```bash
# Arch: instala los requisitos del sistema si faltan
sudo pacman -S --needed ffmpeg uv git
bash scripts/install.sh cpu
# Alternativa NVIDIA con driver compatible con CUDA 12/cuDNN 9:
# bash scripts/install.sh nvidia
export PATH="$HOME/.local/bin:$PATH"
# Perfil CPU de una instalación nueva:
ollama pull qwen3-vl:2b
ollama pull qwen3:1.7b
reel doctor
reel "https://www.youtube.com/watch?v=ID_DEL_VIDEO"
```

Inicia el servidor Ollama según su instalación. Para NVIDIA descarga los modelos
`qwen3-vl:4b` y `qwen3:4b`. El instalador conserva una configuración existente;
comprueba sus modelos antes de descargarlos. Detalles en [Instalación](docs/INSTALLATION.md).

Para otras distribuciones, revisa primero el plan y después ejecútalo:

```bash
bash scripts/install-linux.sh cpu --system --install-uv --dry-run
bash scripts/install-linux.sh cpu --system --install-uv
```

## Comandos

```bash
reel "URL_1" "URL_2"
reel --file urls.txt             # Una URL por línea; admite comentarios con #
reel --status
reel --list
reel --reindex                   # Solo regenera índices; no descarga vídeos
reel --repair "URL"              # Copia la nota anterior a data/backups antes de reemplazarla
reel config
reel doctor
reel --frame-mode hybrid --interval-seconds 0.5 --scene-threshold 8 "URL"
```

`--file` recibe una lista de URLs, no un vídeo local. Abre `vault/` como Vault de
Obsidian. Configura modelos y captura en `config/config.json`, ignorado por Git.
La plantilla pública es [config/config.example.json](config/config.example.json).
`REELS_KNOWLEDGE_HOME` permite situar configuración, Vault y datos en otra carpeta.

## Flujo y datos

URL → descarga temporal → audio + fotogramas periódicos y `scdet` → transcripción
+ análisis visual → síntesis por bloques → Markdown + SQLite + índices.

Se guardan la fuente normalizada, hash del vídeo, título, categoría, fechas,
estado y ruta de la nota. La fuente se fija desde la entrada y no la decide el LLM.
Los temporales, incluida la transcripción completa, se retiran al terminar o fallar
normalmente; un cierre forzado puede dejar residuos en `data/tmp/`.
Las notas pueden contener información privada extraída del vídeo.

Las descargas y DDGS requieren red; los modelos necesitan una descarga inicial.
DDGS recibe nombres de recursos buscados: usa `"web_search": false` para evitar
esas consultas. Instagram intenta leer las cookies de Brave localmente; no se
exportan a un archivo del proyecto. Usa únicamente contenidos a los que tengas
acceso autorizado. No se han probado cuentas reales para esta preparación.

## Demo y pruebas sin cuentas ni GPU

```bash
.venv/bin/python -m unittest discover -s tests -v
```

La suite genera vídeo sintético con tres pantallas, incluidas dos que difieren
por un carácter, y crea notas, índices, backups y SQLite únicamente en carpetas
temporales. Simula descargas y respuestas de los modelos: no conecta con cuentas,
Ollama ni buscadores. Requiere FFmpeg con `drawtext` y una fuente instalada para
la prueba visual; los tests de vídeo se omiten si falta FFmpeg. No se incluyen
capturas de Vaults reales.

## Límites y preguntas frecuentes

- **¿Se conservan todos los fotogramas?** No hay límite global de capturas en
  hybrid/interval/scene. Se usa un intervalo configurable y cambios de escena,
  descartando solo JPG idénticos. Texto que aparezca entre muestras puede perderse.
- **¿Vídeos largos?** La síntesis reparte la evidencia en bloques y fusiona listas.
  El coste temporal, las marcas y los resultados crecen con la duración. No se
  garantiza que un LLM pequeño extraiga todos los recursos ni respete todo el contexto.
- **¿Enlaces oficiales?** Se aceptan URLs literales de evidencia o resultados de
  búsqueda. No se comprueba por HTTP que sigan disponibles ni su oficialidad.
- **¿Descarga fallida?** Los extractores, permisos y restricciones de plataforma
  cambian. Consulta [Solución de problemas](docs/TROUBLESHOOTING.md).
- **¿Actualizar o desinstalar?** El instalador conserva la configuración y datos;
  `scripts/uninstall.sh` solo retira el enlace del comando creado por este proyecto.
- **¿Licencia?** [GNU GPL v3.0, GPL-3.0-only](LICENSE), elegida por el titular.

Documentación: [Configuración](docs/CONFIGURATION.md),
[Arquitectura](docs/ARCHITECTURE.md), [Modelos](docs/MODELS.md),
[Contribuir](CONTRIBUTING.md) y [revisión antes de publicar](docs/GITHUB_CHECKLIST.md).
