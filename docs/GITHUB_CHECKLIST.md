# Control antes de publicar

## Estado de esta preparación

Los cambios permanecen locales. No se ha creado remoto, hecho push ni publicado
release. En el repositorio original, `config/config.json` está retirado del índice y
conservado en disco. Su commit inicial contiene configuración local; sus campos
son modelos, parámetros y preferencias, sin credenciales detectadas. Los commits
contienen también identidad del autor/committer, que debe aprobarse o anonimizarse.
**Ese historial original no se publicará.** Se prepara una copia con historial nuevo,
alias público y correo noreply; véase [PUBLICATION_REPORT.md](PUBLICATION_REPORT.md).

La auditoría completa revisa blobs de referencias, reflogs y blobs no alcanzables
mediante `git fsck`. Es heurística: ninguna búsqueda de patrones demuestra ausencia
absoluta de información personal. No muestra valores de posibles secretos.

```bash
git status --short
git ls-files
python3 scripts/audit_privacy.py --current-only
python3 scripts/audit_privacy.py
```

La primera auditoría debe terminar sin hallazgos. La completa devuelve 1 mientras
haya archivos locales históricos o metadatos pendientes. La CI usa `--current-only`;
por eso una CI verde no aprueba el historial. No ignores el segundo resultado.

## Revisión y decisiones necesarias

1. Revisar todos los archivos que se añadirían, incluidos los nuevos, el diff y
   metadatos. Nunca usar `git add .` sin revisar. No añadir Vault, SQLite, cookies,
   perfiles, tokens, backups, `.env`, logs, medios o configuración local.
2. Decisión del titular: preparar una copia con historial nuevo, conservando
   el repositorio original. Solo el alias de GitHub y el correo noreply se
   aceptan en autor/committer. Verificar la auditoría de esa copia antes del push.
3. Licencia elegida por el titular: GPL-3.0-only, con texto íntegro en LICENSE.
   Revisar por separado licencias de dependencias y modelos; no se redistribuyen pesos.
4. Ejecutar tests sintéticos, sintaxis Bash, instalación aislada del lock y `uv pip check`.
   Revisar todo el contenido final de nuevo después de cualquier cambio.
5. Validar en Arch limpio y hardware real antes de presentar perfiles como soportados.
   No usar cuentas personales para pruebas públicas ni CI.
6. Mostrar alcance final, visibilidad deseada e historial que se publicaría al titular.
   Solicitar autorización explícita antes de `gh repo create`, `git push` o release.

## Metadatos propuestos para GitHub

Descripción: «Pipeline local de vídeo a notas Obsidian con Whisper, FFmpeg, Ollama,
índices Markdown y SQLite».

Etiquetas: `python`, `obsidian`, `ollama`, `faster-whisper`, `ffmpeg`, `sqlite`,
`local-first`, `video-to-notes`.

Primera versión propuesta: `v0.1.0`, preliminar, con notas en
[RELEASE_DRAFT.md](RELEASE_DRAFT.md). No existe etiqueta Git ni release creada.
Licencia resuelta: GPL-3.0-only. El estado de la copia nueva se documenta en
PUBLICATION_REPORT.md; la inferencia real sigue pendiente.
