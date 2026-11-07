# Borrador local de v0.1.0 — preliminar

Pipeline de Instagram, YouTube Shorts/vídeos accesibles y TikTok a notas Markdown
para Obsidian, con Faster-Whisper, Ollama, SQLite e índices por categorías y series.

- Instalación portable mediante uv, Python 3.12 y locks CPU/NVIDIA con hashes.
- Capturas híbridas por intervalo y FFmpeg `scdet`, sin límite global de imágenes.
- Síntesis por bloques para vídeos largos y enlaces restringidos a evidencia/resultados.
- Reparación con backup antes de reemplazar y desinstalación que conserva datos.
- Tests sintéticos sin cuentas, red ni GPU y configuración de CI.

Limitaciones: extractores sujetos a cambios, extracción visual no exhaustiva,
contexto y memoria dependientes del vídeo y modelos, inferencia CUDA y plataformas
adicionales sin validar. Objetivo Linux x86_64; instalación completa en Arch limpio
pendiente. No incluye datos, Vaults, cookies, bases de datos ni pesos.

Licencia elegida: GNU GPL v3.0 (`GPL-3.0-only`). Antes de publicar: comprobar
la copia con historial nuevo y metadatos públicos y obtener autorización explícita. Este archivo no crea una release ni una etiqueta.
