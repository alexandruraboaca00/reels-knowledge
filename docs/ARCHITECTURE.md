# Arquitectura

`bin/reel` resuelve la ubicación del código y ejecuta Python desde `.venv`.
`app/paths.py` comparte rutas entre el pipeline y el indexador; los datos pueden
situarse fuera del checkout mediante `REELS_KNOWLEDGE_HOME`.

`app/reel.py` mantiene la CLI, normalización de URLs, descarga, transcripción,
análisis Ollama, síntesis por bloques, búsqueda de referencias y persistencia.
`app/frames.py` encapsula FFmpeg y selección temporal.
`app/indexer.py` lee Markdown y regenera índices por categoría y series.
No se introduce una API CLI incompatible.

## Procesamiento

1. La entrada se normaliza manteniendo el identificador `v` de YouTube y retirando
   trackers en los formatos reconocidos. SQLite consulta si ya terminó correctamente.
2. Instagram prueba gallery-dl y luego yt-dlp; YouTube y TikTok usan yt-dlp.
   Solo el dominio de Instagram o sus subdominios reciben cookies de Brave.
3. Una carpeta temporal por trabajo recibe vídeo, metadatos, audio mono 16 kHz y JPG.
   El directorio padre se crea también en una instalación nueva.
4. Faster-Whisper produce transcripción; el VLM describe cada captura de forma
   secuencial. Se solicita distinguir comandos copiables de acciones de interfaz.
5. Si hay más de 16 análisis o 5000 caracteres de transcripción, se sintetizan
   bloques y se fusionan recursos y listas por identidad de texto. No hay truncado
   global de recursos. No se trata de una alineación audiovisual por timestamps:
   las partes textuales y visuales se reparten por posición, con posibles pérdidas
   de contexto entre bloques. Un análisis individual muy largo puede exceder contexto.
6. Los enlaces visibles deben aparecer literalmente en la evidencia y tener forma
   HTTP(S). DDGS obtiene candidatos adicionales por recurso; las propuestas del
   modelo se aceptan solo si coinciden exactamente con esos resultados.
7. Se escribe Markdown mediante archivo temporal y reemplazo, después SQLite y los
   índices. El título y categoría se convierten en slugs; la fuente se conserva
   fuera de las decisiones del LLM. Series y partes ordenan los cursos en índices.
8. Reparación copia la nota anterior a `data/backups/` antes de escribir, con nombre
   temporal de microsegundos. Una inferencia fallida conserva la nota y ficha previas.
   Un cambio de título/categoría puede crear nueva ruta y retirar la antigua tras
   confirmar SQLite. Los backups permanecen locales.

## Memoria, fallos y límites

FFmpeg trata vídeo secuencialmente y el VLM recibe una imagen cada vez. Las listas
de marcas, hashes, rutas, transcripción y análisis crecen con la duración: no se
promete memoria constante del pipeline. El disco temporal crece con las capturas.
La síntesis por bloques evita concatenar toda la evidencia en una sola llamada,
pero la calidad y exhaustividad dependen del modelo y del muestreo.

La nota, SQLite e índices no forman una única transacción de filesystem: un fallo
de disco después de escribir una nota puede requerir reparación o reindexado.
No se admite procesamiento concurrente del mismo Vault. Un cierre forzado puede
conservar temporales. Los errores de procesamiento devuelven código CLI 1, y los
siguientes elementos del lote siguen procesándose.

Los tests aíslan rutas y utilizan SQLite temporal, vídeo sintético y mocks para
red/modelos. La CI comprueba archivos publicables actuales; la auditoría completa
con historial es un requisito independiente antes de publicar.
