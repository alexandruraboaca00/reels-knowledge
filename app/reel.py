#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from paths import ROOT, CONFIG_PATH, DB_PATH, TMP_ROOT, VAULT, VENV_BIN

VIDEO_EXTS = {".mp4", ".webm", ".mov", ".mkv", ".m4v"}
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

def load_config() -> dict[str, Any]:
    example = Path(__file__).resolve().parents[1] / "config" / "config.example.json"
    defaults = json.loads(example.read_text(encoding="utf-8"))
    if CONFIG_PATH.exists():
        local = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        defaults.update({k: v for k, v in local.items() if k != "frames"})
        defaults["frames"].update(local.get("frames", {}))
    return defaults

def run(cmd: list[str], *, capture: bool = False, check: bool = True, binary: bool = False) -> subprocess.CompletedProcess:
    kwargs: dict[str, Any] = {"check": check}
    if not binary:
        kwargs["text"] = True
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    return subprocess.run(cmd, **kwargs)


def valid_http_url(url: str) -> bool:
    try:
        p = urlsplit(url)
        return (p.scheme in {"http", "https"} and bool(p.hostname)
                and not p.username and not p.password
                and not any(c.isspace() or c in "<>|()\\" for c in url))
    except ValueError:
        return False


def normalize_url(url: str) -> str:
    """Conserva parámetros esenciales de YouTube; limpia solo trackers conocidos."""
    from urllib.parse import parse_qsl, urlencode
    raw = url.strip()
    if not re.match(r"^https?://", raw):
        raw = "https://" + raw
    p = urlsplit(raw)
    host = p.netloc.lower().removeprefix("www.")
    path = re.sub(r"/+", "/", p.path).rstrip("/")
    if host in {"instagram.com", "m.instagram.com"}:
        m = re.fullmatch(r"/(p|reel|tv)/([^/]+)", path)
        if m:
            return urlunsplit(("https", "instagram.com", path, "", ""))
    if host in {"youtu.be", "youtube.com", "m.youtube.com", "music.youtube.com"}:
        if host == "youtu.be":
            return urlunsplit(("https", "youtu.be", path, "", ""))
        if path == "/watch":
            vid = dict(parse_qsl(p.query)).get("v", "")
            if vid:
                return "https://www.youtube.com/watch?v=" + vid
        if path.startswith(("/shorts/", "/live/", "/embed/")):
            return "https://www.youtube.com" + path
    # TikTok, redirects y otras webs: conserva su query (puede ser necesaria).
    return urlunsplit((p.scheme or "https", host, path or "/", p.query, ""))


def init_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reels (
            url TEXT PRIMARY KEY,
            content_hash TEXT,
            title TEXT,
            category TEXT,
            note_path TEXT,
            processed_at TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT
        )
    """)
    conn.commit()
    return conn

def already_processed(conn: sqlite3.Connection, url: str) -> tuple[bool, str | None]:
    row = conn.execute(
        "SELECT status, note_path FROM reels WHERE url = ?",
        (url,)
    ).fetchone()
    return bool(row and row[0] == "ok"), (row[1] if row else None)

def detect_brave_user_data() -> Path | None:
    base = Path.home() / ".config" / "BraveSoftware"
    candidates = [
        base / "Brave-Browser-Nightly",
        base / "Brave-Origin-Nightly",
        base / "Brave-Origin-Browser-Nightly",
        base / "Brave-Browser",
    ]
    for p in candidates:
        if p.exists():
            return p

    if base.exists():
        nightly = sorted(
            [p for p in base.iterdir() if p.is_dir() and "nightly" in p.name.lower()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if nightly:
            return nightly[0]
    return None

def browser_spec() -> str:
    user_data = detect_brave_user_data()
    if user_data:
        return f"brave:{user_data}"
    return "brave"

def find_largest_video(folder: Path) -> Path | None:
    files = [
        p for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS
    ]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_size)

def parse_gallery_metadata(folder: Path) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for p in folder.rglob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            merged.update(data)
    return merged

def download_reel(url: str, folder: Path) -> tuple[Path, dict[str, Any], str]:
    """Instagram: gallery-dl + yt-dlp. YouTube/TikTok: yt-dlp.

    Las cookies se usan solo para Instagram, sin exportarlas a disco.
    """
    gallery = str(VENV_BIN / "gallery-dl")
    ytdlp = str(VENV_BIN / "yt-dlp")
    host = urlsplit(url).netloc.lower()
    instagram = host == "instagram.com" or host.endswith(".instagram.com")
    spec = browser_spec()

    if instagram:
        cmd = [gallery, "--cookies-from-browser", spec, "-D", str(folder),
               "--write-metadata", "--no-input", url]
        try:
            proc = run(cmd, capture=True, check=False)
            video = find_largest_video(folder)
            if proc.returncode == 0 and video:
                return video, parse_gallery_metadata(folder), "gallery-dl"
        except Exception:
            pass
        for item in folder.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)

    cmd = [ytdlp, "--no-playlist", "-o", str(folder / "%(id)s.%(ext)s"),
           "--write-info-json", url]
    if instagram:
        cmd[1:1] = ["--cookies-from-browser", spec]
    proc = run(cmd, capture=True, check=False)
    video = find_largest_video(folder)
    if not video or proc.returncode:
        reason = (proc.stderr or proc.stdout or "sin detalle")[-1400:]
        raise RuntimeError(f"No se pudo descargar el vídeo ({host}). {reason}")
    meta: dict[str, Any] = {}
    for info in folder.glob("*.info.json"):
        try:
            meta = json.loads(info.read_text(encoding="utf-8"))
            break
        except Exception:
            continue
    return video, meta, "yt-dlp"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def extract_audio(video: Path, audio: Path) -> None:
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(audio),
    ])

def duration_seconds(video: Path) -> float:
    proc = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video),
    ], capture=True)
    try:
        return max(0.1, float(proc.stdout.strip()))
    except Exception:
        return 30.0

def _snapshot(video: Path, out: Path, t: float) -> bool:
    # Un solo fotograma a baja resolución; no conserva el vídeo.
    proc = run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-threads", "2", "-y",
        "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
        "-vf", "scale='min(1120,iw)':-2", "-q:v", "3", str(out),
    ], capture=True, check=False)
    return proc.returncode == 0 and out.exists() and out.stat().st_size > 0


def extract_frames(video: Path, folder: Path, settings: dict) -> list[Path]:
    from frames import capture
    frames, report = capture(video, folder, settings)
    print("  Fotogramas: {images_selected} analizados de {merged_candidates} candidatos "
          "(intervalo: {periodic_candidates}; escenas: {scene_candidates}; "
          "duplicados exactos: {duplicate_images})".format(**report))
    if not frames:
        print("  Aviso: no se extrajeron fotogramas válidos")
    return frames



def extra_frames(video: Path, folder: Path, existing: list[Path], max_extra: int = 8) -> list[Path]:
    """Segunda pasada: extrae imágenes en los huecos temporales más grandes."""
    duration = duration_seconds(video)
    times = []
    for p in existing:
        match = re.search(r"frame_t(\d+\.\d+)", p.name)
        if match:
            times.append(float(match.group(1)))
    points = [0.0] + sorted(times) + [duration]
    gaps = sorted(
        ((b-a, (a+b)/2) for a,b in zip(points, points[1:])),
        reverse=True,
    )
    result = []
    for gap, t in gaps:
        if len(result) >= max_extra:
            break
        if gap < 0.7:
            continue
        out = folder / f"frame_t{t:08.2f}.jpg"
        if out.exists():
            continue
        if _snapshot(video, out, t):
            result.append(out)
    return sorted(result)


def transcribe(audio: Path, model_name: str, device: str = "auto") -> tuple[str, str]:
    from faster_whisper import WhisperModel

    if device not in {"auto", "cpu", "cuda"}:
        raise ValueError("whisper_device debe ser auto, cpu o cuda")
    try:
        if device == "cpu":
            raise RuntimeError("CPU solicitada")
        model = WhisperModel(
            model_name,
            device="cuda",
            compute_type="int8_float16",
        )
        device_used = "cuda"
    except Exception:
        if device == "cuda":
            raise
        model = WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
        )
        device_used = "cpu"

    segments, info = model.transcribe(
        str(audio),
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=True,
    )
    text = " ".join(seg.text.strip() for seg in segments if seg.text.strip()).strip()
    language = getattr(info, "language", "unknown")

    del model
    gc.collect()
    return text, f"{language}/{device_used}"

def ollama_chat(model: str, prompt: str, *, image: Path | None = None, json_mode: bool = False) -> str:
    import ollama
    msg: dict[str, Any] = {"role": "user", "content": prompt}
    if image:
        msg["images"] = [str(image)]
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [msg],
        "options": {"temperature": 0.05, "num_ctx": 4096 if image else 8192},
        "keep_alive": "3m",
    }
    if json_mode:
        kwargs["format"] = "json"
    response = ollama.chat(**kwargs)
    return response.message.content.strip()


def unload_ollama(model: str) -> None:
    """Libera VRAM entre el modelo visual y el de texto."""
    try:
        import ollama
        ollama.generate(model=model, prompt="", keep_alive=0)
    except Exception as exc:
        print(f"  Aviso: no se pudo liberar {model}: {exc}", file=sys.stderr)


def analyze_frames(frames: list[Path], model: str) -> list[str]:
    analyses: list[str] = []
    prompt = """/no_think
Analiza con precisión este fotograma de un reel.
Transcribe todas las palabras legibles, priorizando nombres propios, enlaces,
listas numeradas, nombres de canales de YouTube, herramientas y comandos.
Distingue entre comandos de terminal REALES y botones/etiquetas de interfaces.
Si el fotograma parece un elemento de una lista, anota su número y nombre exacto.
NO infieras nombres ni URLs que no se vean. Si algo es ilegible, di 'ilegible'.
Respuesta breve y factual, sin explicaciones genéricas.
"""
    for i, frame in enumerate(frames, start=1):
        print(f"    visión {i}/{len(frames)}")
        try:
            result = ollama_chat(model, prompt, image=frame)
            analyses.append(f"[{frame.stem}] {result}")
        except Exception as exc:
            analyses.append(f"[{frame.stem}] Análisis no disponible: {exc}")
    return analyses


def extract_meta(meta: dict[str, Any]) -> dict[str, str]:
    def first(*keys: str) -> str:
        for k in keys:
            v = meta.get(k)
            if v is not None and str(v).strip():
                return str(v).strip()
        return ""

    return {
        "author": first("username", "owner_username", "uploader", "uploader_id", "channel"),
        "caption": first("description", "caption", "title"),
        "date": first("date", "timestamp", "upload_date"),
    }

def safe_json(text: str) -> dict[str, Any]:
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return {}
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

def synthesize_single(
    url: str, transcript: str, frame_notes: list[str], meta: dict[str, str], model: str,
) -> dict[str, Any]:
    payload = {
        "source_url": url,
        "author": meta.get("author", ""),
        "caption": meta.get("caption", ""),
        "transcript": transcript,
        "visual_evidence": frame_notes,
    }
    prompt = f"""/no_think
Convierte la evidencia de un reel en una nota de conocimiento, precisa y útil.
Responde SOLO con JSON válido usando estas claves:
{{
  "title": "título específico de máximo 90 caracteres; NUNCA Reel procesado",
  "category": "Ciberseguridad, Linux, Física, IA, Viajes, Programación, etc.",
  "note_kind": "curso|github|herramienta|comando|recursos|otro",
  "series": "nombre exacto de la serie si procede, sino vacío",
  "part": null,
  "index_description": "una frase útil de máximo 110 caracteres",
  "summary_es": "resumen en español",
  "summary_en": "summary in English",
  "key_points": ["ideas útiles"],
  "steps": ["pasos prácticos reales"],
  "commands": ["SOLO comandos reales y copiables de terminal, nunca texto de botones"],
  "ui_actions": ["acciones que se realizan pulsando botones o menús"],
  "resources_expected": null,
  "resources": [
    {{"name": "nombre exacto", "kind": "youtube_channel|github_repo|website|tool|course|other", "description": "para qué sirve", "url_visible": "URL completa visible o vacío"}}
  ],
  "links_visible": ["URL literal si aparece en pantalla o audio"],
  "tags": ["etiquetas cortas"],
  "warnings": ["dudas, lagunas o límites de la evidencia"]
}}

Reglas obligatorias:
- Si se anuncian 7 recursos, resources_expected=7, y lista CADA recurso visible una sola vez.
- Si solo identificas 5 de 7, devuelve 5 y di que faltan dos; NO inventes los restantes.
- Si es un reel de recursos de YouTube, título tipo '7 canales de YouTube para aprender física'.
- Los nombres propios deben coincidir con la evidencia (no los corrijas imaginando).
- Si el reel es un tutorial, usa pasos; si es lista, usa resources; no rellenes campos irrelevantes.
- No inventes URLs, cifras, comandos ni enlaces.
- Mantén el orden de los recursos cuando pueda deducirse por la evidencia.
- Si el reel enseña Windows o sus ajustes, usa la categoría Windows, no Programación.
- Incluye siempre la herramienta o recurso principal si se ve inequívocamente.
- No confundas un creador incidental o marca secundaria con el recurso principal.
- Usa descripciones breves y verificables de cada recurso en español.
- No consideres todos los objetos secundarios de la escena como recursos centrales.
- Si no hay evidencia de un número de parte usa null.
- Para listas sin datos utiliza [].

EVIDENCIA:
{json.dumps(payload, ensure_ascii=False)}
"""
    raw = ollama_chat(model, prompt, json_mode=True)
    data = safe_json(raw)
    if not data:
        data = {
            "title": "", "category": "Otros", "note_kind": "otro",
            "summary_es": raw[:2000], "summary_en": "",
            "resources": [], "resources_expected": None,
            "warnings": ["La IA no devolvió una estructura JSON completa."],
        }
    data = normalize_note_data(data, meta)
    # Solo enlaces literales en la evidencia; las búsquedas se resuelven aparte.
    evidence = " ".join([transcript, *frame_notes, meta.get("caption", "")])
    for resource in data["resources"]:
        candidate = resource["url_visible"]
        if not valid_http_url(candidate) or candidate not in evidence:
            resource["url_visible"] = ""
    data["links_visible"] = [u for u in data["links_visible"]
                             if isinstance(u, str) and valid_http_url(u) and u in evidence]
    return data


def synthesize(
    url: str, transcript: str, frame_notes: list[str], meta: dict[str, str], model: str,
) -> dict[str, Any]:
    """Resume por tramos cuando hay muchos fotogramas o texto; evita truncado silencioso.

    Cada tramo conserva entidades y listas. La fusión es determinista; no garantiza
    recuperar datos que el VLM no haya observado o transcrito correctamente.
    """
    if len(frame_notes) <= 16 and len(transcript) <= 5000:
        return synthesize_single(url, transcript, frame_notes, meta, model)

    import collections
    size = 16
    visual_chunks = [frame_notes[i:i + size] for i in range(0, len(frame_notes), size)]
    # Intenta cortar en espacios; se preserva todo el contenido textual.
    words = transcript.split()
    word_chunks: list[str] = []
    current: list[str] = []
    chars = 0
    for word in words:
        if chars + len(word) + 1 > 5000 and current:
            word_chunks.append(" ".join(current))
            current, chars = [], 0
        current.append(word)
        chars += len(word) + 1
    if current:
        word_chunks.append(" ".join(current))

    parts = []
    for i in range(max(len(visual_chunks), len(word_chunks))):
        print(f"    consolidando bloque {i+1}/{max(len(visual_chunks), len(word_chunks))}")
        block = synthesize_single(
            url, word_chunks[i] if i < len(word_chunks) else "",
            visual_chunks[i] if i < len(visual_chunks) else [],
            meta, model,
        )
        parts.append(block)

    def unique(values: list[Any], limit: int = 0) -> list[str]:
        seen, result = set(), []
        for value in values:
            clean = str(value).strip()
            if clean and clean.casefold() not in seen:
                seen.add(clean.casefold())
                result.append(clean)
        return result[:limit] if limit else result

    resources: list[dict[str, str]] = []
    found: set[str] = set()
    for part in parts:
        for resource in part.get("resources", []):
            name = str(resource.get("name") or "").strip()
            if name and name.casefold() not in found:
                found.add(name.casefold())
                resources.append(resource)
    kinds = [p.get("note_kind") for p in parts if p.get("note_kind") not in (None, "otro")]
    cats = [p.get("category") for p in parts if p.get("category") not in (None, "Otro", "Otros")]
    category = collections.Counter(cats).most_common(1)[0][0] if cats else "Otros"
    note_kind = collections.Counter(kinds).most_common(1)[0][0] if kinds else "otro"
    expected_values = [x.get("resources_expected") for x in parts
                       if isinstance(x.get("resources_expected"), int)]
    expected = max(expected_values) if expected_values else None

    # Conserva lista de tramos para no descartar lo visto en partes alejadas del vídeo.
    observations = [f"Bloque {i+1}: {p.get('summary_es','')}" for i,p in enumerate(parts)]
    merged = dict(parts[0])
    merged.update({
        "category": category, "note_kind": note_kind,
        "resources": resources, "resources_expected": expected,
        "summary_es": " ".join(p.get("summary_es", "") for p in parts[:3])[:1200],
        "summary_en": " ".join(p.get("summary_en", "") for p in parts[:3])[:1200],
        "key_points": unique(observations + [x for p in parts for x in p.get("key_points", [])]),
        "steps": unique([x for p in parts for x in p.get("steps", [])]),
        "commands": unique([x for p in parts for x in p.get("commands", [])]),
        "ui_actions": unique([x for p in parts for x in p.get("ui_actions", [])]),
        "links_visible": unique([x for p in parts for x in p.get("links_visible", [])]),
        "warnings": unique([x for p in parts for x in p.get("warnings", [])]),
        "tags": unique([x for p in parts for x in p.get("tags", [])]),
    })
    if expected is not None and len(resources) < expected:
        merged["warnings"].append(
            f"En el vídeo se indican {expected} recursos pero se identificaron {len(resources)}."
        )
    return merged


def normalize_note_data(data: dict[str, Any], meta: dict[str, str]) -> dict[str, Any]:
    for field in ("key_points", "steps", "commands", "ui_actions", "tags", "warnings", "links_visible"):
        if not isinstance(data.get(field), list):
            data[field] = []
    resources = data.get("resources", [])
    if not isinstance(resources, list):
        resources = []
    cleaned = []
    seen = set()
    for item in resources:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        key = name.casefold()
        if not name or key in seen:
            continue
        seen.add(key)
        cleaned.append({
            "name": name,
            "kind": str(item.get("kind") or "other").strip(),
            "description": str(item.get("description") or "").strip(),
            "url_visible": str(item.get("url_visible") or "").strip(),
        })
    if data.get("note_kind") == "herramienta":
        incidental = re.compile(r"(?:creador del contenido|creator|influencer|tiktoker)", re.I)
        cleaned = [r for r in cleaned if not incidental.search(r.get("description", ""))]
    data["resources"] = cleaned
    try:
        expected = int(data.get("resources_expected"))
    except (ValueError, TypeError):
        expected = None
    if expected is not None and not (1 <= expected <= 1000):
        expected = None
    data["resources_expected"] = expected

    title = str(data.get("title") or "").strip().strip('"')
    bad = {"reel", "reel procesado", "untitled", "sin título", "sin titulo", "resumen", "reel.md"}
    if not title or title.casefold() in bad:
        category = str(data.get("category") or "Temas generales").strip()
        if cleaned and all(r["kind"] == "youtube_channel" for r in cleaned):
            title = f"{expected or len(cleaned)} canales de YouTube para aprender {category.lower()}"
        elif cleaned and len(cleaned) > 1:
            title = f"{expected or len(cleaned)} recursos sobre {category.lower()}"
        elif cleaned:
            title = f"{cleaned[0]['name']}: guía y recursos"
        else:
            title = f"Guía práctica de {category.lower()}"
    # Categorías conservadoras: no confundir guía del sistema con programación.
    if re.search(r"\bwindows\s*11?\b", title, re.I):
        data["category"] = "Windows"
    if (str(data.get("category") or "").casefold() in {"otro", "otros", "misc"}
        and sum(r.get("kind") == "youtube_channel" for r in cleaned) >= 2):
        data["category"] = "Educación"
    data["title"] = title[:100]

    valid_kinds = {"curso", "github", "herramienta", "comando", "recursos", "otro"}
    if data.get("note_kind") not in valid_kinds:
        data["note_kind"] = "recursos" if len(cleaned) > 1 else "otro"

    if expected is not None and expected > len(cleaned):
        data["warnings"].append(
            f"Se mencionan {expected} recursos; solo se han identificado {len(cleaned)}."
        )
    return data


def web_search(queries: list[str]) -> list[dict[str, str]]:
    """Compatibilidad con funciones anteriores; búsquedas de referencias."""
    try:
        from ddgs import DDGS
    except Exception:
        return []
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for q in queries[:14]:
        if not q or not isinstance(q, str):
            continue
        try:
            hits = DDGS(timeout=8).text(q, max_results=5)
        except Exception:
            continue
        for hit in hits or []:
            url = str(hit.get("href") or hit.get("url") or "").strip()
            if not valid_http_url(url) or url in seen:
                continue
            seen.add(url)
            results.append({
                "query": q,
                "title": str(hit.get("title") or "").strip(),
                "url": url,
                "snippet": str(hit.get("body") or hit.get("snippet") or "").strip()[:450],
            })
    return results[:60]


def resolve_resource_links(resources: list[dict[str, str]], model: str) -> list[dict[str, str]]:
    """Busca y valida enlaces de cada recurso sin un máximo global."""
    results: list[dict[str, str]] = []
    from urllib.parse import urlsplit
    # Lotes pequeños evitan superar el contexto del LLM en listas grandes.
    for start in range(0, len(resources), 6):
        group = resources[start:start + 6]
        indexed: dict[str, list[dict[str, str]]] = {}
        for resource in group:
            name = str(resource.get("name", "")).strip()
            kind = resource.get("kind", "other")
            if not name:
                continue
            if kind == "youtube_channel":
                query = f'"{name}" YouTube official channel'
            elif kind == "github_repo":
                query = f'"{name}" site:github.com'
            else:
                query = f'"{name}" official website'
            hits = web_search([query])
            if kind == "youtube_channel":
                hits = [r for r in hits if (urlsplit(r['url']).hostname or '') in {'youtube.com', 'www.youtube.com', 'm.youtube.com'}]
            if kind == "github_repo":
                hits = [r for r in hits if (urlsplit(r['url']).hostname or '') == 'github.com']
            indexed[name] = hits[:4]
        if not any(indexed.values()):
            continue
        prompt = f"""/no_think
Devuelve JSON con links: lista de objetos name, url.
Asocia solo coincidencias claras y NO inventes URLs.
Si hay ambigüedad, omite el recurso.
Una URL por nombre; copia literalmente una URL de los resultados.
{json.dumps(indexed, ensure_ascii=False)}"""
        try:
            payload = safe_json(ollama_chat(model, prompt, json_mode=True))
            proposed = payload.get('links', [])
            if not isinstance(proposed, list):
                continue
            for item in proposed:
                if not isinstance(item, dict):
                    continue
                name, candidate = str(item.get('name','')), str(item.get('url',''))
                if name in indexed and candidate in {r['url'] for r in indexed[name]}:
                    results.append({'name': name, 'url': candidate})
        except Exception as exc:
            print(f"  Aviso: no se pudieron comprobar enlaces de este lote: {exc}")
    return results



def select_links(data: dict[str, Any], search_results: list[dict[str, str]], model: str) -> list[dict[str, str]]:
    if not search_results:
        return []

    prompt = f""" /no_think
Selecciona enlaces útiles para una nota creada a partir de un reel.

ENTIDADES:
{json.dumps(data.get("tools_entities", []), ensure_ascii=False)}

RESULTADOS REALES DE BÚSQUEDA:
{json.dumps(search_results, ensure_ascii=False)}

Devuelve JSON:
{{
  "links": [
    {{
      "name": "nombre",
      "url": "URL EXACTA tomada de RESULTADOS REALES DE BÚSQUEDA",
      "reason": "por qué sirve",
      "official": true
    }}
  ]
}}

Reglas:
- NO inventes ni modifiques URLs.
- Elige como máximo 8.
- official=true solo si el dominio y resultado dejan claro que es la web oficial.
- Si no estás seguro, official=false.
"""
    raw = ollama_chat(model, prompt, json_mode=True)
    parsed = safe_json(raw)
    allowed = {r["url"] for r in search_results}
    links = []
    for item in parsed.get("links", []) if isinstance(parsed.get("links"), list) else []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        if url not in allowed:
            continue
        links.append({
            "name": str(item.get("name", "")).strip() or url,
            "url": url,
            "reason": str(item.get("reason", "")).strip(),
            "official": bool(item.get("official", False)),
        })
    return links[:8]

def slugify(text: str, max_len: int = 80) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return (text[:max_len].rstrip("-") or "reel")

def md_escape(s: Any) -> str:
    return str(s).replace("\n", " ").strip()

def render_note(
    url: str, data: dict[str, Any], links: list[dict[str, str]],
    meta: dict[str, str], downloader: str, transcript_info: str,
) -> str:
    from urllib.parse import quote

    def esc(value: Any) -> str:
        return str(value or "").replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").strip()

    def fm(value: Any) -> str:
        return json.dumps(str(value or ""), ensure_ascii=False)

    title = str(data.get("title") or "Nota sin título").replace("\n", " ").strip()
    tags = [slugify(str(t), 40) for t in data.get("tags", []) if str(t).strip()]
    lines = [
        "---", f"title: {fm(title)}", f"source: {fm(url)}",
        f"author: {fm(meta.get('author'))}",
        f"processed: {fm(datetime.now(timezone.utc).isoformat())}",
        f"category: {fm(data.get('category') or 'Otros')}",
        f"index_group: {fm(data.get('note_kind') or 'otro')}",
        f"index_series: {fm(data.get('series'))}",
        f"index_part: {data['part'] if isinstance(data.get('part'), int) else 'null'}",
        f"index_description: {fm(data.get('index_description') or str(data.get('summary_es', ''))[:110])}",
        "tags:",
    ]
    lines += [f"  - {t}" for t in tags] or ["  - reel"]
    lines += ["---", "", f"# {title}", "", "## Resumen", "",
              esc(data.get("summary_es", "")), "", "## Summary", "",
              esc(data.get("summary_en", "")), ""]

    def bullets(label: str, values: Any):
        if not isinstance(values, list):
            return
        items = [esc(v) for v in values if str(v).strip()]
        if items:
            lines.extend([f"## {label}", ""])
            lines.extend(f"- {v}" for v in items)
            lines.append("")

    bullets("Información importante", data.get("key_points"))
    steps = [str(s).strip() for s in data.get("steps", []) if str(s).strip()]
    bullets("Pasos", steps)
    commands = [str(c).strip() for c in data.get("commands", []) if str(c).strip()]
    if commands:
        lines += ["## Comandos / código", ""]
        for cmd in commands:
            lines += ["```bash", cmd, "```", ""]
    step_norm = {re.sub(r"\s+", " ", s).casefold() for s in steps}
    actions = [a for a in data.get("ui_actions", [])
               if re.sub(r"\s+", " ", str(a).strip()).casefold() not in step_norm]
    bullets("Acciones en interfaces", actions)

    resources = data.get("resources", [])
    resolved = {str(r.get("name", "")).casefold(): str(r.get("url", "")) for r in links}
    if resources:
        lines += ["## Recursos mencionados", ""]
        expected = data.get("resources_expected")
        count_links = sum(bool(str(r.get("url_visible") or "").startswith(("https://", "http://"))
                               or resolved.get(str(r.get("name") or "").casefold())) for r in resources)
        if isinstance(expected, int):
            lines += [f"**Recursos identificados: {len(resources)} de {expected}. "
                      f"Enlaces encontrados: {count_links} de {len(resources)}.**", ""]
        else:
            lines += [f"**Recursos identificados: {len(resources)}. "
                      f"Enlaces encontrados: {count_links}.**", ""]
        lines += ["| Recurso | Para qué sirve | Enlace |", "|---|---|---|"]
        for item in resources:
            name = str(item.get("name") or "").strip()
            resource_url = str(item.get("url_visible") or "").strip()
            if not valid_http_url(resource_url):
                resource_url = resolved.get(name.casefold(), "")
            if valid_http_url(resource_url):
                link = f"[Abrir]({resource_url})"
            elif item.get("kind") == "youtube_channel":
                link = f"[Buscar en YouTube](https://www.youtube.com/results?search_query={quote(name)})"
            elif item.get("kind") == "github_repo":
                link = f"[Buscar en GitHub](https://github.com/search?q={quote(name)}&type=repositories)"
            else:
                link = "Pendiente de localizar"
            lines.append(f"| {esc(name)} | {esc(item.get('description', ''))} | {link} |")
        lines.append("")

    bullets("URLs vistas o mencionadas", data.get("links_visible", []))
    if links:
        lines += ["> Las referencias encontradas automáticamente pueden no ser oficiales. Verifica la identidad del recurso.", ""]
    bullets("Advertencias / dudas", data.get("warnings", []))
    lines += ["## Fuente", "", f"- Vídeo original: {url}",
              f"- Descargador: `{downloader}`", f"- Transcripción: `{transcript_info}`", "",
              "> El vídeo, audio, fotogramas y transcripción completa se eliminan después del procesamiento.", ""]
    return "\n".join(lines)



def save_note(data: dict[str, Any], content: str, url: str) -> Path:
    category = slugify(str(data.get("category") or "Otros"), 50)
    title = slugify(str(data.get("title") or "guia"), 90)
    folder = VAULT / "Reels" / category
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{title}.md"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if f'source: "{url}"' not in existing:
            suffix = hashlib.sha256(url.encode()).hexdigest()[:8]
            path = folder / f"{title}-{suffix}.md"
    tmp = folder / (path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
    return path


def process_one(conn: sqlite3.Connection, raw_url: str, cfg: dict[str, Any], repair: bool = False) -> bool:
    url = normalize_url(raw_url)
    done, old_note = already_processed(conn, url)
    if done and not repair:
        print(f"↷ Ya procesado: {url}")
        if old_note:
            print(f"  {old_note}")
        return True

    print(f"\n▶ {url}" + (" [REPARAR]" if repair else ""))
    # Si es reparación, no alteres la ficha anterior hasta finalizar con éxito.
    if not done:
        conn.execute(
            """INSERT INTO reels(url, processed_at, status)
               VALUES(?, ?, 'processing')
               ON CONFLICT(url) DO UPDATE SET processed_at=excluded.processed_at, status='processing', error=NULL""",
            (url, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()

    vision_model = str(cfg.get("vision_model", "qwen3-vl:4b"))
    text_model = str(cfg.get("text_model", "qwen3:4b"))
    try:
        TMP_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="reel-", dir=TMP_ROOT) as td:
            tmp = Path(td)
            print("  [1/6] Descargando...")
            video, raw_meta, downloader = download_reel(url, tmp)
            digest = sha256(video)
            meta = extract_meta(raw_meta)

            print("  [2/6] Extrayendo audio y fotogramas inteligentes...")
            audio = tmp / "audio.wav"
            extract_audio(video, audio)
            frames = extract_frames(video, tmp / "frames", cfg.get("frames", {}))

            print("  [3/6] Transcribiendo...")
            transcript, transcript_info = transcribe(audio, str(cfg.get("whisper_model", "turbo")), str(cfg.get("whisper_device", "auto")))
            print(f"  [4/6] Analizando {len(frames)} fotogramas...")
            try:
                frame_notes = analyze_frames(frames, vision_model)
                print("  [5/6] Organizando la información...")
                # El modelo textual se carga DESPUÉS de liberar el visual.
            finally:
                unload_ollama(vision_model)

            data = synthesize(url, transcript, frame_notes, meta, text_model)
            expected = data.get("resources_expected")
            if isinstance(expected, int) and expected > len(data.get("resources", [])):
                print(f"  Aviso: {len(data.get('resources', []))}/{expected} recursos identificados; segunda revisión visual...")
                unload_ollama(text_model)
                additions = extra_frames(video, tmp / "frames", frames, max(8, 4 * (expected - len(data.get("resources", [])))))
                if additions:
                    try:
                        frame_notes.extend(analyze_frames(additions, vision_model))
                    finally:
                        unload_ollama(vision_model)
                    data = synthesize(url, transcript, frame_notes, meta, text_model)

            try:
                links = []
                if cfg.get("web_search", True) and data.get("resources"):
                    print("       Buscando enlaces por cada recurso...")
                    links = resolve_resource_links(data["resources"], text_model)
            finally:
                unload_ollama(text_model)

            print("  [6/6] Guardando nota e índice...")
            note_text = render_note(url, data, links, meta, downloader, transcript_info)

            # Backup de la nota antigua antes de reparar. No elimina otros datos.
            if repair and old_note and Path(old_note).is_file():
                backup_dir = ROOT / "data" / "backups"
                backup_dir.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                backup_path = backup_dir / f"{Path(old_note).stem}-{stamp}.md"
                shutil.copy2(old_note, backup_path)
                print(f"       Copia de la nota anterior: {backup_path}")

            note_path = save_note(data, note_text, url)
            conn.execute(
                """UPDATE reels
                   SET content_hash=?, title=?, category=?, note_path=?, processed_at=?, status='ok', error=NULL
                   WHERE url=?""",
                (digest, data["title"], data.get("category", ""), str(note_path),
                 datetime.now(timezone.utc).isoformat(), url),
            )
            conn.commit()

            if repair and old_note and Path(old_note).is_file() and Path(old_note) != note_path:
                Path(old_note).unlink()
            from indexer import rebuild_all_indexes
            paths = rebuild_all_indexes()
            print(f"✓ Nota: {note_path}")
            print(f"✓ Índices actualizados: {len(paths)}")
            print("✓ Vídeo, audio y fotogramas temporales eliminados.")
        return True
    except Exception as exc:
        if not done:
            conn.execute(
                "UPDATE reels SET status='error', error=?, processed_at=? WHERE url=?",
                (str(exc), datetime.now(timezone.utc).isoformat(), url),
            )
            conn.commit()
        print(f"✗ Error: {exc}", file=sys.stderr)
        return False


def print_status(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT status, COUNT(*) FROM reels GROUP BY status ORDER BY status"
    ).fetchall()
    total = sum(r[1] for r in rows)
    print(f"Total registrados: {total}")
    for status, count in rows:
        print(f"  {status}: {count}")

def print_list(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT processed_at, status, title, url, note_path FROM reels ORDER BY processed_at DESC"
    ).fetchall()
    for processed_at, status, title, url, note in rows:
        print(f"[{status}] {title or '(sin título)'}")
        print(f"  {url}")
        if note:
            print(f"  {note}")
        print(f"  {processed_at}")

def doctor(cfg: dict[str, Any]) -> int:
    """Diagnóstico sin descargas, instalaciones ni escritura de archivos."""
    import importlib.util
    ok = True
    for binary in ("ffmpeg", "ffprobe"):
        found = shutil.which(binary)
        print(f"{'✓' if found else '✗'} {binary}: {found or 'no encontrado'}")
        ok &= bool(found)
    for binary in ("gallery-dl", "yt-dlp"):
        found = (VENV_BIN / binary).is_file()
        print(f"{'✓' if found else '✗'} {binary}: {'disponible' if found else 'no encontrado'}")
        ok &= found
    for module in ("faster_whisper", "ollama", "ddgs"):
        found = importlib.util.find_spec(module) is not None
        print(f"{'✓' if found else '✗'} {module}: {'importable' if found else 'no encontrado'}")
        ok &= found
    print(f"{'✓' if (VAULT / 'Reels').is_dir() else '✗'} Vault: {VAULT}")
    ok &= (VAULT / 'Reels').is_dir()
    print(f"Brave cookies: {browser_spec()} (no se leen en doctor)")
    try:
        cp = run(["ollama", "list"], capture=True)
        available = cp.stdout
        for name in (cfg.get("vision_model"), cfg.get("text_model")):
            exists = bool(name and name in available)
            print(f"{'✓' if exists else '✗'} Ollama {name}")
            ok &= exists
    except Exception as exc:
        print(f"✗ Ollama: {exc}")
        ok = False
    if shutil.which("nvidia-smi"):
        cp = run(["nvidia-smi", "--query-gpu=memory.total,memory.used", "--format=csv,noheader"],
                 capture=True, check=False)
        print("NVIDIA: " + (cp.stdout.strip() or "no disponible"))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="reel", description="Vídeos a notas Markdown locales")
    parser.add_argument("urls", nargs="*", help="URL(s) de Instagram, YouTube, TikTok")
    parser.add_argument("--file", type=Path, help="Archivo con una URL por línea")
    parser.add_argument("--status", action="store_true", help="Resumen de los registros")
    parser.add_argument("--list", action="store_true", help="Lista registros")
    parser.add_argument("--reindex", action="store_true", help="Reconstruye índices")
    parser.add_argument("--repair", action="store_true", help="Reprocesa y respalda una nota")
    parser.add_argument("--frame-mode", choices=["hybrid", "interval", "scene", "fixed"],
                        help="Modo visual para esta ejecución")
    parser.add_argument("--interval-seconds", type=float, help="Segundos entre capturas periódicas")
    parser.add_argument("--scene-threshold", type=float, help="Sensibilidad del detector scdet (0..100)")
    parser.add_argument("--fixed-frames", type=int, help="Solo para modo fixed")
    args = parser.parse_args()
    cfg = load_config()

    if args.urls == ["config"] and not args.file:
        print(f"Configuración: {CONFIG_PATH}")
        print(json.dumps(cfg.get("frames", {}), indent=2, ensure_ascii=False))
        return 0
    if args.urls == ["doctor"] and not args.file:
        return doctor(cfg)

    frames_cfg = dict(cfg.get("frames", {}))
    overrides = {
        "mode": args.frame_mode, "interval_seconds": args.interval_seconds,
        "scene_threshold": args.scene_threshold, "fixed_frames": args.fixed_frames,
    }
    frames_cfg.update({k: v for k, v in overrides.items() if v is not None})
    cfg["frames"] = frames_cfg

    conn = init_db()
    if args.reindex:
        from indexer import rebuild_all_indexes
        indexes = rebuild_all_indexes()
        print(f"✓ {len(indexes)} índices actualizados")
        return 0
    if args.status:
        print_status(conn)
        return 0
    if args.list:
        print_list(conn)
        return 0

    urls = list(args.urls)
    if args.file:
        urls.extend(line.strip() for line in args.file.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.lstrip().startswith("#"))
    if not urls:
        parser.print_help()
        return 1
    success = True
    try:
        for url in urls:
            success = process_one(conn, url, cfg, repair=args.repair) and success
    finally:
        conn.close()
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
