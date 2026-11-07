# Modelos y hardware

Perfiles orientativos, **sin benchmarks ni inferencia validados en esta preparación**.
El instalador define dos perfiles de dependencias (CPU/NVIDIA), no una garantía de
que todos los modelos quepan en cualquier GPU del rango. Comprueba RAM disponible,
cuantización, contexto y memoria de otros procesos antes de elegir.

| Hardware orientativo | Faster-Whisper | Visión Ollama | Texto Ollama | Estado |
|---|---|---|---|---|
| CPU, sin NVIDIA | `base` o `small`, CPU/int8 | `qwen3-vl:2b` | `qwen3:1.7b` | CPU es muy lenta para muchos frames; sin medición de RAM/tiempos |
| 6–8 GB VRAM | `turbo`, CUDA/int8_float16 | `qwen3-vl:4b` | `qwen3:4b` | Perfil inicial NVIDIA; falta validar inferencia real |
| 12–16 GB VRAM | `turbo` o `large-v3` | `qwen3-vl:8b` | `qwen3:8b` | Alternativa de mayor tamaño, no probada |
| ≥24 GB VRAM | `large-v3` o `turbo` | `qwen3-vl:8b`; 32B puede exceder memoria | `qwen3:14b` | Contexto y carga visual pueden impedir usar modelos mayores; no probado |

Los pesos de Qwen3-VL en el catálogo de Ollama ocupan aproximadamente 1.9 GB (2B),
3.3 GB (4B), 6.2 GB (8B) y 21 GB (32B). Son tamaños de descarga, **no requisitos de
VRAM**. Qwen3-VL requiere Ollama ≥0.12.7 según su [catálogo oficial](https://ollama.com/library/qwen3-vl).
Los tamaños y etiquetas pueden cambiar; registra `ollama list` y versión en tus
mediciones. El pipeline configura contexto 4096 para imagen y 8192 para texto,
aunque el modelo admita ventanas mayores.

Faster-Whisper usa CTranslate2; su [documentación oficial](https://github.com/SYSTRAN/faster-whisper)
indica CUDA 12 y cuDNN 9 para las versiones actuales. La ruta CPU usa int8;
NVIDIA usa int8_float16. Las bibliotecas del lock NVIDIA no sustituyen el driver.
`whisper_device=auto` intenta cargar CUDA y retrocede a CPU; `cpu` evita CUDA y
`cuda` exige GPU. Whisper y el VLM se ejecutan por etapas y se intenta descargar
cada modelo Ollama antes de cargar el siguiente. La liberación puede fallar y se
informa: no se garantiza ausencia de solapamiento de memoria.

## Licencias y alternativas

Las fichas oficiales de [Qwen3-VL-4B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct)
y [Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B) declaran Apache-2.0.
[Whisper large-v3-turbo](https://huggingface.co/openai/whisper-large-v3-turbo) declara
MIT. Verifica también la licencia y procedencia del artefacto cuantizado concreto
que descargues; el proyecto no redistribuye pesos ni adopta esas licencias como
licencia propia. Las variantes de otras familias pueden tener condiciones distintas.

El [catálogo Qwen3](https://ollama.com/library/qwen3) ofrece las variantes de texto
1.7B, 4B, 8B y 14B citadas. Cambiar tamaños dentro de Qwen3/Qwen3-VL o `base`/`small`/`large-v3` en Whisper es
la alternativa más cercana al flujo actual. Un modelo solo textual no sirve como
`vision_model`: debe aceptar imágenes mediante Ollama. Otros VLM de Ollama no se
han probado con estos prompts ni con extracción exhaustiva de texto/listas.
No se afirma soporte de backends Transformers directos, AMD/ROCm o Metal.

## Validación pendiente

Usa el mismo vídeo sintético, versiones, cuantización e intervalo en cada prueba.
Mide tiempo de transcripción, análisis por imagen, memoria máxima y recursos/texto
identificados frente al fixture; compara CPU, 6–8 GB, 12–16 GB y ≥24 GB por separado.
Una instalación resuelta o importable no es un benchmark ni confirma CUDA.
Consulta de las fuentes: 2026-11-07.
