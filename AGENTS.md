# Instrucciones para asistentes de código

- Proyecto local: vídeo temporal → audio/transcripción + fotogramas → Ollama → notas Obsidian + SQLite.
- No ejecutar descargadores contra cuentas reales ni subir cookies, tokens, Vault, datos o bases SQLite al repositorio.
- No hacer `git push` ni crear repositorios públicos sin aprobación explícita.
- No cambiar la API CLI (`reel`, `--repair`, `--reindex`, `--file`, `doctor`, `config`) sin compatibilidad.
- Respetar `config/config.json` local: cambios nuevos mediante `config/config.example.json`.
- Reproducibilidad en Arch Linux: entorno `.venv` aislado, FFmpeg, yt-dlp/gallery-dl, Ollama.
- Capturas: sin límite global, seleccionar por intervalos y `scdet`; preservar cambios pequeños de texto.
- `--repair` debe respaldar la nota antes de reemplazar; nunca borrar el Vault al actualizar.
- Cada corrección necesita tests unitarios con fixtures sintéticos, sin GPU y sin red.
- Documentación en español. Indicar versiones y restricciones reales, no fingir compatibilidad.
