# Solución de problemas

- **Falta `.venv`:** ejecuta `bash scripts/install.sh cpu` o `nvidia` desde la copia
  del proyecto; el launcher ya no depende de `~/Projects/reels-knowledge`.
- **`reel` no aparece:** añade `~/.local/bin` a PATH, o usa `bin/reel` directamente.
  El instalador se niega a reemplazar un comando de otro proyecto.
- **Ollama o modelo ausente:** inicia el servidor local, revisa `ollama list`,
  descarga los nombres exactos de tu configuración y ejecuta `reel doctor`.
  Qwen3-VL requiere Ollama ≥0.12.7 según su catálogo.
- **CUDA/cuDNN o memoria:** el perfil NVIDIA necesita un driver compatible y las
  bibliotecas CUDA 12/cuDNN 9. Cierra otros consumidores de VRAM, reduce los modelos
  o configura `whisper_device: "cpu"`. `auto` intenta CUDA y luego CPU al cargar.
  Un error durante la inferencia CUDA no garantiza fallback automático.
- **Falla Instagram:** verifica disponibilidad/permisos del contenido y la versión
  del extractor. Se intenta leer Brave localmente; doctor no verifica acceso a
  cookies. No pegues cookies ni logs sensibles en issues. No se garantiza acceso
  privado, autenticación ni evasión de restricciones de plataformas.
- **Falla YouTube/TikTok:** los extractores cambian y algunos vídeos requieren
  autenticación no implementada por este perfil. No se prueba descargando cuentas
  reales en CI. Actualiza dependencias deliberadamente y revisa los locks.
- **Faltan palabras o recursos:** reduce `--interval-seconds` o el umbral de escena,
  usa hybrid y revisa la evidencia. Cambios de texto pequeños no siempre disparan
  `scdet`; no se usa deduplicación perceptual. El LLM puede omitir o confundir texto.
- **Tarda demasiado:** aumenta intervalo para vídeos largos. No hay tope global de
  capturas. Eliminar duplicados exactos ahorra análisis solo de JPG idénticos.
- **Enlace incorrecto:** la validación sintáctica y coincidencia con resultados no
  prueban identidad ni disponibilidad de la web. Corrige la nota manualmente;
  desactiva `web_search` si no quieres enviar consultas DDGS.
- **Índice desordenado:** edita `index_group`, `index_series` e `index_part` en la
  cabecera de la nota y ejecuta `reel --reindex`. Se conservan las notas.
- **Interrupción brusca:** inspecciona `data/tmp/` con los procesos detenidos y retira
  solo residuos identificados. No borres Vault ni SQLite para actualizar.
- **Auditoría completa devuelve 1:** inspecciona los motivos sin publicar el
  contenido. La configuración inicial sigue en el historial y los metadatos de
  autor necesitan revisión; no se limpian automáticamente. La comprobación
  `--current-only` solo cubre archivos actuales, no autoriza publicar el historial.

Para reportar problemas incluye versiones de Python, uv, FFmpeg, sistema y modelos,
comando reproducible con URLs ficticias y fixtures sintéticos. Nunca adjuntes la
base SQLite, Vault, cookies, perfiles de navegador o configuración privada.
