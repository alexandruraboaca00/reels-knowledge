# Encargo para Codex CLI — preparación de GitHub

Eres el mantenedor técnico de este repositorio. Lee `AGENTS.md`, `README.md`,
`docs/`, `app/`, `bin/`, `scripts/` y `config/config.example.json` **antes de actuar**.
No asumas que los parches anteriores son correctos: audita el código y prueba.

## Objetivo

Convertir este prototipo local en un proyecto GitHub limpio, reproducible,
seguro, configurable y documentado. Conserva la funcionalidad existente:
reels de Instagram, YouTube Shorts, TikTok, y vídeos de YouTube descargables;
Faster-Whisper, FFmpeg `scdet` y muestreo periódico, modelos Ollama, DDGS,
Markdown/Obsidian, SQLite, índices y reparación.

## Trabajo técnico

1. Audita código y dependencias; detecta errores, duplicaciones y deuda técnica.
   Refactoriza por módulos sin romper comandos existentes ni borrar notas.
2. Haz portátil la ruta `~/Projects/reels-knowledge`: variable de entorno o
   directorio de configuración; instalación limpia, actualizaciones y desinstalación
   segura; perfiles sin NVIDIA y con NVIDIA. Jamás uses `sudo pip`.
3. Revisa el motor de fotogramas: modo híbrido, intervalos configurables,
   detector `scdet`, duplicados conservadores, memoria acotada y síntesis de
   bloques para vídeos largos. No restablezcas un límite global de fotogramas.
   Prueba con vídeos sintéticos de cambios rápidos y con texto.
4. Corrige calidad de notas: títulos significativos, fuente inmutable, recursos
   exhaustivos cuando exista evidencia, URLs validadas sin invención, categorías
   y series ordenadas, diferenciación de comandos reales y botones UI.
5. Tests automáticos (sin red ni GPU) para URLs (YouTube `watch?v=...` incluido),
   notas, índice, DB, backup de `--repair`, módulos de descarga con mocks y
   selección de frames. Agrega CI apropiada sin cuentas ni cookies.
6. Revisa dependencias con versiones compatibles (incluye `av==18.1.0` hasta
   validar otra). Genera lock reproducible con uv si es adecuado.
7. Mejora README con guía rápida, flujo de datos, demo con archivos sintéticos,
   compatibilidad por plataforma, capturas opcionales sin información privada,
   ejemplos de comandos y FAQ. Completa `docs/INSTALLATION.md`,
   `docs/CONFIGURATION.md`, `docs/ARCHITECTURE.md`, `docs/MODELS.md`,
   `docs/TROUBLESHOOTING.md` y CONTRIBUTING. En `MODELS.md`, comparar perfiles
   por hardware (CPU, 6–8 GB, 12–16 GB, ≥24 GB VRAM) y alternativas reales,
   marcando lo no probado y verificando compatibilidad, licencias y requisitos.
8. Consulta `git status`, `git ls-files` y, si procede, historial para asegurarte
   de que NO se han rastreado datos privados. `.gitignore` no desversiona archivos
   existentes. Nunca incluyas `vault/`, `data/`, cookies, perfiles, tokens,
   bases de datos ni backups. Si hubo secretos versionados, advierte y pide
   autorización antes de limpiar historial o revocar credenciales.
9. Propón licencia pero pide al usuario que elija antes de incluirla. Prepara una
   descripción breve del repositorio, etiquetas y una primera release si procede.

## Entrega y autorización

- Haz cambios de código, tests y documentación localmente; enséñame el diff,
  pruebas ejecutadas y cosas pendientes de verificar con hardware real.
- `gh auth status` solo para comprobar autenticación.
- NO hagas `gh repo create`, `git push`, releases ni cambies la visibilidad del
  repositorio sin mi aprobación explícita, tras enseñarme qué se publicará.
- Si algo exige credenciales, acceso a mi Instagram u operaciones destructivas,
  explica primero el impacto y pide permiso.
- Prioriza exactitud y privacidad sobre funciones adicionales.
