# Informe local de preparación para GitHub

Fecha: 2026-11-07. No se ha publicado nada, creado remoto, hecho push, commit,
etiqueta ni release. Se han conservado los cambios locales encontrados al empezar.
La única modificación del índice es retirar `config/config.json`; el archivo local
permanece intacto. No se ha reescrito historial.

## Cambios revisables

- Rutas compartidas en `app/paths.py`, launcher portable y variable
  `REELS_KNOWLEDGE_HOME` para configuración, Vault y datos.
- Instalador CPU/NVIDIA con Python 3.12, locks con hashes, conservación de
  configuración y protección del comando ya existente. Desinstalador sin borrado
  recursivo: solo retira su propio enlace.
- Capturas por intervalo y `scdet`, sin límite global; logs de detección en archivo
  temporal para no acumularlos en RAM. Corregido scene para vídeos de más de 120 s.
  Validación de umbral y gap; duplicados estrictamente idénticos.
- Síntesis por bloques y listas conservadas; eliminada la invención determinista
  de recursos desde el título y el truncado de recursos a 500. Los enlaces visibles
  del modelo deben tener sintaxis válida y aparecer literalmente en evidencia.
- Límite de dominio correcto para cookies de Instagram y filtro de YouTube.
- Correcciones de índice (regex y encabezado de URLs), creación de temporales en
  instalación limpia, backups con microsegundos y código CLI de error útil.
- Documentación española de instalación, configuración, arquitectura, modelos,
  problemas, contribución y propuesta de release/etiquetas; workflow de CI.

El motor de frames, indexador, parte de la síntesis y tests iniciales ya estaban
presentes como cambios locales previos. El diff contra HEAD incluye esos cambios
conservados junto a esta preparación; no se atribuyen todos a esta ejecución.

## Verificación

- 28 tests unitarios/sintéticos pasan, sin cuentas, red ni GPU durante las pruebas.
  Cubren URLs (incluido YouTube watch), notas/fuente, índice/series, SQLite,
  reparación y fallo con conservación, backup, descarga con mocks, configuración,
  instalación portable, retirada segura, Whisper simulado y reglas de auditoría.
- Vídeos FFmpeg sintéticos: texto que cambia un carácter y escenas cada 0,2 s.
- Entorno CPU aislado: 39 paquetes instalados con hashes y `uv pip check` correcto.
  Importaciones de av, faster_whisper, ollama, ddgs y requests correctas.
- Bash: `bash -n bin/reel scripts/*.sh` correcto. `git diff --check` correcto.
- Python 3.12.14, uv 0.12.17, FFmpeg n9.0.2 locales. Lock NVIDIA resuelto con
  hashes, sin instalar ni ejecutar inferencia NVIDIA.
- CI configurada, todavía no ejecutada en GitHub. La CI revisa archivos actuales;
  la auditoría completa del historial es un requisito adicional de publicación.

Dependencias directas/ejecución comprobadas en el entorno CPU:

- `faster-whisper==1.2.1`
- `av==18.1.0`
- `ollama==0.6.3`
- `gallery-dl==1.32.19`
- `yt-dlp==2026.10.26`
- `ddgs==9.16.1`
- `requests==2.34.2`
- `ctranslate2==4.8.5`

## Privacidad y bloqueo de publicación

Se consultaron `git status`, `git ls-files`, árboles, objetos y contenido histórico.
Auditoría completa: un commit, siete blobs históricos; se incluyen referencias,
reflogs y comprobación de objetos no alcanzables con `git fsck`.
No se detectaron Vaults, cookies, credenciales, perfiles ni SQLite en esos objetos.
Se revisaron también los archivos nuevos no ignorados para evitar añadirlos por error.
La auditoría es heurística y no demuestra ausencia absoluta de datos personales.

**Hallazgos históricos pendientes:** `config/config.json` del commit inicial
(modelos y preferencias; sin secretos detectados) e identidad del autor/committer.
La configuración se retiró del índice, pero `.gitignore` no limpia su versión histórica.
La auditoría actual queda sin hallazgos; la completa devuelve 1 deliberadamente
por esos dos puntos. No se debe publicar este historial tal cual sin decisión expresa.

Propuesta para aprobación: preparar una copia destinada a publicar con archivos
revisados e historial nuevo, preservando íntegro este repositorio y sus datos;
definir antes la identidad pública de los commits. Alternativa: limpieza autorizada
del historial existente. Ninguna se ha ejecutado. No hay credenciales detectadas
que justifiquen revocación en esta revisión.

## Pendientes reales

- Licencia resuelta posteriormente por el titular: GPL-3.0-only, igual que Europass.
  Se añadió el texto íntegro en LICENSE.
- Decisión sobre configuración histórica e identidad pública, seguida de nueva
  auditoría del contenido exacto a publicar y aprobación de repositorio/visibilidad.
- Arch limpio e inferencia real en CPU/NVIDIA; mediciones por hardware, modelo y
  cuantización. No se han descargado vídeos de cuentas reales ni modelos.
- macOS, Windows, ARM, ROCm y contextos audiovisuales largos no validados. Las
  listas y textos crecen con duración; la memoria total no es constante. Persistencia
  Markdown/SQLite/índices no es una transacción única ni admite escritores concurrentes.

La descripción, etiquetas y borrador local de v0.1.0 están en GITHUB_CHECKLIST.md y
RELEASE_DRAFT.md. Publicar requiere autorización explícita posterior.

## Continuación autorizada

El titular eligió GPL-3.0-only y autorizó preparar una copia para publicación sin
datos personales. Se usa el alias público de GitHub y su dirección noreply.
El estado final de esa copia se recoge en PUBLICATION_REPORT.md. El informe de
privacidad anterior corresponde al repositorio local original, que se conserva.
