"""Captura híbrida de vídeos: muestreo periódico + FFmpeg scdet.

No existe un límite global de fotogramas: el intervalo determina la cobertura.
El detector de escenas añade capturas al detectar cambios relevantes.
El tratamiento de imágenes es secuencial, no se cargan todas en memoria.
"""
from __future__ import annotations

import hashlib
import math
import re
import subprocess
import tempfile
from pathlib import Path

SCENE_RE = re.compile(r"lavfi\.scd\.time:\s*([0-9]+(?:\.[0-9]+)?)")


def probe_duration(video: Path) -> float:
    cp = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video),
    ], capture_output=True, text=True, check=True)
    try:
        duration = float(cp.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("No se ha podido obtener la duración del vídeo") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise RuntimeError("Duración de vídeo inválida")
    return duration


def periodic_times(duration: float, interval: float) -> list[float]:
    """Puntos 0.5*i, 1.5*i...; incluye primeros/últimos en clips cortos."""
    if not 0.1 <= interval <= 120:
        raise ValueError("interval_seconds debe estar entre 0.1 y 120")
    times = []
    k = 0
    while (k + .5) * interval < duration:
        times.append((k + .5) * interval)
        k += 1
    if not times:
        times = [min(duration * .5, max(.05, duration - .05))]
    return times


def scene_change_times(video: Path, threshold: float) -> list[float]:
    """FFmpeg scdet devuelve marcas temporales sin cargar fotogramas en RAM.

    Si falla el detector, la cobertura periódica del modo híbrido sigue disponible.
    """
    if not 0.0 < threshold <= 100.0:
        raise ValueError("scene_threshold debe estar entre 0 y 100")
    # El scale abarata el análisis. scdet detecta cambios intensos, NO todos los textos.
    # Los logs completos van a disco: no se acumulan en RAM para vídeos largos.
    with tempfile.TemporaryFile(mode="w+t") as log:
        cp = subprocess.run([
            "ffmpeg", "-hide_banner", "-nostats", "-loglevel", "info",
            "-threads", "2", "-i", str(video), "-an",
            "-vf", f"scale=320:-2,scdet=threshold={threshold}",
            "-f", "null", "-",
        ], stdout=subprocess.DEVNULL, stderr=log, text=True, check=False)
        if cp.returncode:
            log.seek(max(0, log.tell() - 4096))
            raise RuntimeError((log.read() or "FFmpeg scdet falló")[-700:])
        log.seek(0)
        return [float(m.group(1)) for line in log for m in SCENE_RE.finditer(line)]


def merge_times(periodic: list[float], scenes: list[float], duration: float,
                min_gap: float = 0.18) -> list[float]:
    if not math.isfinite(min_gap) or min_gap < 0 or min_gap > 5:
        raise ValueError("min_gap_seconds debe estar entre 0 y 5")
    # No se elimina un punto periódico por una escena, salvo si son casi idénticos.
    candidates = [
        (min(max(.02, t), max(.02, duration - .02)), priority)
        for priority, collection in ((0, periodic), (1, [s + .12 for s in scenes]))
        for t in collection if 0 <= t < duration
    ]
    candidates.sort()
    result: list[tuple[float, int]] = []
    for t, priority in candidates:
        if result and t - result[-1][0] < min_gap:
            # La escena posterior tiene prioridad sobre una captura periódica
            # anterior: evita perder una pantalla que cambia muy rápidamente.
            if priority > result[-1][1]:
                result[-1] = (t, priority)
            continue
        result.append((t, priority))
    return [t for t, _priority in result]


def capture(video: Path, folder: Path, settings: dict) -> tuple[list[Path], dict]:
    folder.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(video)
    mode = str(settings.get("mode", "hybrid"))
    if mode not in {"hybrid", "interval", "scene", "fixed"}:
        raise ValueError("frames.mode debe ser hybrid, interval, scene o fixed")
    interval = float(settings.get("interval_seconds", 1.0))
    threshold = float(settings.get("scene_threshold", 8.0))
    gap = float(settings.get("min_gap_seconds", 0.18))
    if not 0 < threshold <= 100:
        raise ValueError("scene_threshold debe estar entre 0 y 100")

    base = periodic_times(duration, interval) if mode in {"hybrid", "interval"} else []
    if mode == "fixed":
        count = int(settings.get("fixed_frames", 10))
        if not 1 <= count <= 100000:
            raise ValueError("fixed_frames debe ser positivo (<=100000)")
        base = [(k + .5) * duration / count for k in range(count)]
    changes = []
    if mode in {"hybrid", "scene"}:
        try:
            changes = scene_change_times(video, threshold)
        except Exception as exc:
            if mode == "scene":
                raise
            print(f"  Aviso: scdet falló ({exc}); se conserva el muestreo periódico")
    if mode == "scene":
        base = [duration / 2]

    times = merge_times(base, changes, duration, gap)
    images: list[Path] = []
    hashes = set()
    duplicates = 0
    for t in times:
        out = folder / f"frame_t{t:010.3f}.jpg"
        cp = subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-threads", "2",
            "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
            "-vf", "scale='min(1120,iw)':-2", "-q:v", "3", "-y", str(out),
        ], capture_output=True, text=True, check=False)
        if cp.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
            out.unlink(missing_ok=True)
            continue
        # Solo duplica si coincide exactamente el JPG; cambios pequeños de texto se preservan.
        if settings.get("remove_exact_duplicates", True):
            digest = hashlib.sha256(out.read_bytes()).digest()
            if digest in hashes:
                duplicates += 1
                out.unlink()
                continue
            hashes.add(digest)
        images.append(out)

    report = {
        "duration_seconds": round(duration, 2), "mode": mode,
        "interval_seconds": interval, "periodic_candidates": len(base),
        "scene_candidates": len(changes), "merged_candidates": len(times),
        "duplicate_images": duplicates, "images_selected": len(images),
    }
    return images, report
