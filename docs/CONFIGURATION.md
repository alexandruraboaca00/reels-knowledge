# Configuración

El archivo local `config/config.json` permite elegir modelos y selección visual.
Consulta la plantilla distribuible `config/config.example.json`.

## Capturas

- `mode=hybrid` (predeterminado): cada `interval_seconds` más cambios detectados por FFmpeg `scdet`.
- `mode=interval`: solo periodicidad.
- `mode=scene`: detección de escena + al menos una imagen de cobertura; los cambios sutiles pueden perderse.
- `mode=fixed`: `fixed_frames` muestras repartidas, solo si lo solicita expresamente el usuario.
- `scene_threshold`: sensibilidad de FFmpeg scdet; valores 8–14 suelen ser punto de partida.
- `min_gap_seconds`: evita extraer varias capturas prácticamente en el mismo instante.
- `remove_exact_duplicates`: descarta solo JPGs **idénticos** para no perder textos pequeños.

No hay tope global para los modos hybrid/interval/scene. Un clip de una hora con `interval_seconds=1` puede requerir ~3600 análisis visuales. Con modelos pequeños en GPU puede tardar muchísimo y requerir bastante almacenamiento temporal. Se recomienda empezar con 1 s para shorts y ampliar el intervalo para vídeos largos.

Prueba temporal sin editar el JSON:

```bash
reel --frame-mode hybrid --interval-seconds 0.5 --scene-threshold 8 "URL"
```

Cada marca temporal se analiza con Qwen3-VL de forma secuencial; FFmpeg procesa la señal de vídeo sin acumular todas las muestras en RAM.

La detección de escenas no garantiza identificar texto que aparezca y desaparezca entre dos muestreos. Se puede reducir `interval_seconds` a 0.5 para reels especialmente rápidos. Ningún muestreo discreto garantiza recuperar el 100 % de contenido visual.

## Rutas y valores iniciales

`REELS_KNOWLEDGE_HOME` selecciona la raíz de configuración, Vault, SQLite,
backups y temporales. Por defecto es la carpeta del código. El entorno `.venv`
permanece junto al código. Los módulos del pipeline e indexador usan la misma raíz.

`config/config.json` tiene prioridad sobre `config.example.json`; las claves
`frames` se fusionan individualmente. Si falta el JSON local se usa la plantilla
sin escribirla. El instalador solo crea configuración cuando aún no existe.
No modifica archivos locales al cambiar el perfil de dependencias.

- `vision_model` y `text_model`: nombres exactos disponibles en Ollama.
- `whisper_model`: `base`, `small`, `turbo`, `large-v3`, etc. de Faster-Whisper.
- `whisper_device`: `auto` (intenta CUDA, fallback al cargar), `cpu` o `cuda`.
- `web_search`: habilita DDGS, que recibe nombres de recursos buscados. `false`
  evita consultas del buscador, pero las descargas siguen necesitando red.

`interval_seconds`: 0.1–120 s; `scene_threshold`: mayor que 0 y hasta 100;
`min_gap_seconds`: 0–5 s. Un gap mayor que el intervalo puede reducir cobertura;
las escenas cercanas pueden sustituir capturas periódicas. Usa gaps pequeños para
texto rápido. `fixed_frames` solo afecta al modo fixed. La clave antigua
`max_frames` se tolera en el JSON pero no impone límite global.

El JSON local contiene datos de tu entorno y está excluido de Git. Nunca adjuntes
cookies, tokens ni rutas privadas a la plantilla pública.
