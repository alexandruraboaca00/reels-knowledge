"""Generador local de índices Markdown de Reels Knowledge (sin dependencias)."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from paths import ROOT, VAULT
REELS = VAULT / "Reels"
INDEX_NAME = "00-Índice.md"

HEADINGS = {
    "curso": "Cursos y series",
    "github": "Herramientas de GitHub",
    "herramienta": "Otras herramientas y recursos",
    "recursos": "Listas y recomendaciones",
    "comando": "Comandos y terminal",
    "otro": "Otros reels",
}


@dataclass
class Note:
    path: Path
    title: str
    summary: str
    kind: str
    series: str
    part: int | None
    source: str
    links: list[tuple[str, str]]
    commands: list[tuple[str, str]]


def _meta(body: str) -> dict[str, object]:
    if not body.startswith("---\n"):
        return {}
    cut = body.find("\n---\n", 4)
    if cut < 0:
        return {}
    result: dict[str, object] = {}
    for line in body[4:cut].splitlines():
        match = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        if value.startswith('"') and value.endswith('"'):
            try:
                result[key] = json.loads(value)
                continue
            except ValueError:
                pass
        result[key] = value.strip('"\'')
    return result


def _section(body: str, heading: str) -> str:
    match = re.search(
        rf"(?ms)^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)", body
    )
    return match.group(1).strip() if match else ""


def _plain(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[`*_#]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _short(text: str, maximum: int = 118) -> str:
    clean = _plain(text).replace("|", "/")
    if len(clean) <= maximum:
        return clean
    return clean[:maximum].rsplit(" ", 1)[0].rstrip(".,;: ") + "…"


def _sort_key(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text)
    return "".join(c for c in norm if not unicodedata.combining(c)).casefold()


def _detect_part(text: str) -> int | None:
    match = re.search(
        r"(?i)\b(?:parte|part|ep(?:isodio)?|lecci[oó]n|lesson|cap[ií]tulo|m[oó]dulo|clase)"
        r"\s*[#:.\-]?\s*(\d{1,3})\b", text
    )
    if match:
        return int(match.group(1))
    match = re.search(r"^\s*(\d{1,3})\s*[.):-]\s+", text)
    return int(match.group(1)) if match else None


def _guess_series(title: str) -> str:
    cleaned = re.sub(
        r"(?i)[\s\-:|()]*\b(?:parte|part|ep(?:isodio)?|lecci[oó]n|lesson|cap[ií]tulo|m[oó]dulo|clase)"
        r"\s*[#:.\-]?\s*\d{1,3}\b[\s\-:|()]*",
        " ", title,
    )
    return re.sub(r"\s+", " ", cleaned).strip(" -:|")


def _valid_http(url: str) -> bool:
    try:
        u = urlsplit(url)
        return u.scheme in ("http", "https") and bool(u.netloc)
    except ValueError:
        return False


def _source_link(url: str) -> str:
    if not _valid_http(url):
        return ""
    return f"[Reel]({url})"


def _extract_links(body: str) -> list[tuple[str, str]]:
    refs = _section(body, "Referencias web encontradas")
    seen: set[str] = set()
    results = []
    for label, url in re.findall(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", refs):
        if _valid_http(url) and url not in seen:
            seen.add(url)
            results.append((_short(label, 40), url))

    if len(results) < 2:
        resource_section = _section(body, "Recursos mencionados")
        for name, url in re.findall(r"(?m)^\|\s*([^|]+)\|[^|]*\|\s*\[Abrir\]\((https?://[^)]+)\)", resource_section):
            if _valid_http(url) and url not in seen:
                seen.add(url)
                results.append((_short(name, 32), url))
    if len(results) < 2:
        direct = _section(body, "URLs vistas o mencionadas") or _section(body, "Enlaces vistos o mencionados")
        for raw in re.findall(r"https?://[^\s<>\])]+", direct):
            url = raw.rstrip(".,;:")
            if _valid_http(url) and url not in seen:
                seen.add(url)
                results.append((urlsplit(url).hostname or "Web", url))
    return results[:3]


def _extract_commands(body: str) -> list[tuple[str, str]]:
    explanations = _section(body, "Qué hace cada comando")
    explained: dict[str, str] = {}
    for cmd, purpose in re.findall(r"(?m)^\s*-\s*`([^`]+)`\s*[—–-]\s*(.+)$", explanations):
        explained[cmd.strip()] = _short(purpose, 90)

    commands: list[tuple[str, str]] = []
    code_section = _section(body, "Comandos / código")
    for block in re.findall(r"(?ms)^```[^\n]*\n(.*?)\n```", code_section):
        # Un bloque con varias líneas puede ser un script entero: no lo resumimos como comando.
        lines = [line.strip() for line in block.splitlines() if line.strip() and not line.lstrip().startswith("#")]
        if len(lines) == 1 and len(lines[0]) <= 110:
            cmd = lines[0]
            if not any(old == cmd for old, _ in commands):
                commands.append((cmd, explained.get(cmd, "")))
    return commands[:4]


def _detect_kind(title: str, body: str, metadata: dict[str, object], commands: list[tuple[str, str]], links: list[tuple[str, str]]) -> str:
    explicit = str(metadata.get("index_group") or "").lower().strip()
    aliases = {"curso": "curso", "cursos": "curso", "github": "github",
               "herramienta": "herramienta", "herramientas": "herramienta",
               "recursos": "recursos", "lista": "recursos",
               "comando": "comando", "comandos": "comando", "otro": "otro"}
    if explicit in aliases:
        return aliases[explicit]

    tags_section = body.split("\n---\n", 1)[0] if body.startswith("---") else ""
    terms = _sort_key(f"{title} {tags_section}")
    if re.search(r"\b(curso|cursos|course|bootcamp|masterclass|serie|leccion|lecciones|episodio|capitulo)\b", terms):
        return "curso"
    if re.search(r"\b(github|repositorio|repository|repos|open.source)\b", terms) or any("github.com" in urlsplit(u).netloc for _, u in links):
        return "github"
    if commands and re.search(r"\b(comando|comandos|terminal|bash|shell|cli)\b", terms):
        return "comando"
    if _section(body, "Recursos mencionados"):
        return "recursos"
    if re.search(r"(?i)\b(recomienda|recomendaciones|lista|canales de youtube|recursos educativos)\b", _section(body, "Resumen")):
        return "recursos"
    if _section(body, "Herramientas y conceptos") or re.search(r"\b(tool|herramienta|app|software)\b", terms):
        return "herramienta"
    if commands:
        return "comando"
    return "otro"


def load_note(path: Path) -> Note | None:
    try:
        body = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    metadata = _meta(body)
    title = str(metadata.get("title") or "").strip() or _plain(path.stem.replace("-", " ")).capitalize()
    summary = str(metadata.get("index_description") or "").strip() or _section(body, "Resumen")
    if title.casefold() in {"reel procesado", "reel", "reel.md"} and summary:
        # Affects only display title in index; original note remains untouched.
        first_sentence = re.split(r"[.!?]\s", summary.strip(), 1)[0]
        if len(first_sentence) > 75:
            first_sentence = first_sentence[:75].rsplit(" ", 1)[0]
        title = first_sentence[:85] or title
        match = re.search(r"(?i)(\d+) canales de YouTube para aprender (\w+)", summary)
        if match:
            title = f"{match.group(1)} canales de YouTube para aprender {match.group(2)}"
    summary = _short(summary.split("\n\n")[0].strip()) if summary else "Descripción disponible en la nota"
    links = _extract_links(body)
    commands = _extract_commands(body)
    kind = _detect_kind(title, body, metadata, commands, links)
    series = str(metadata.get("index_series") or "").strip()
    part_raw = str(metadata.get("index_part") or "").strip()
    part = int(part_raw) if part_raw.isdigit() else _detect_part(title)
    if kind == "curso" and not series:
        series = _guess_series(title)
    source = str(metadata.get("source") or "").strip()
    if not _valid_http(source):
        match = re.search(r"(?m)^- Reel original:\s*(https?://\S+)", body)
        source = match.group(1) if match else ""
    return Note(path=path, title=title, summary=summary, kind=kind,
                series=series, part=part, source=source, links=links,
                commands=commands)


def _wikilink(note: Note) -> str:
    rel = note.path.relative_to(VAULT).with_suffix("").as_posix()
    title = note.title.replace("|", "/").replace("[", "(").replace("]", ")")
    return f"[[{rel}|{title}]]"


def _resource_links(note: Note) -> str:
    result = [f"[{label.replace('|','/')}]({url})" for label, url in note.links]
    original = _source_link(note.source)
    if original:
        result.append(original)
    return " · ".join(result)


def _entry(note: Note, numbered: bool = False) -> str:
    label = "1." if numbered else "-"
    start = f"{label} {_wikilink(note)} — {note.summary}"
    if note.kind == "comando" and note.commands:
        cmd, purpose = note.commands[0]
        clean_cmd = cmd.replace("`", "'")
        # El resumen es contexto de la nota; no se atribuye al comando sin evidencia.
        start += f" · `{clean_cmd}`"
        if purpose:
            start += f": {purpose}"
        if len(note.commands) > 1:
            start += f" (+{len(note.commands)-1} más)"
    links = _resource_links(note)
    if links:
        start += f" · {links}"
    return start


def rebuild_category_index(category_dir: Path) -> Path | None:
    if not category_dir.is_dir() or category_dir.parent.resolve() != REELS.resolve():
        raise ValueError("La ruta debe ser una carpeta de categoría dentro de vault/Reels")

    notes = []
    for path in category_dir.glob("*.md"):
        if path.name.casefold() in {INDEX_NAME.casefold(), "index.md", "readme.md"}:
            continue
        note = load_note(path)
        if note is not None:
            notes.append(note)

    index = category_dir / INDEX_NAME
    if not notes:
        if index.exists():
            index.unlink()
        return None

    groups: dict[str, list[Note]] = {name: [] for name in HEADINGS}
    for note in notes:
        groups[note.kind].append(note)

    lines = [
        f"# Índice · {str(_meta(notes[0].path.read_text(encoding='utf-8')).get('category') or category_dir.name.replace('-', ' ').capitalize())}", "",
        f"{len(notes)} {'nota' if len(notes) == 1 else 'notas'} organizadas por tema. Este archivo se genera automáticamente.", "",
    ]

    for group, heading in HEADINGS.items():
        entries = groups[group]
        if not entries:
            continue
        lines += [f"## {heading}", ""]
        if group == "curso":
            series: dict[str, list[Note]] = {}
            for note in entries:
                series.setdefault(note.series or "Cursos sin serie identificada", []).append(note)
            for name in sorted(series, key=_sort_key):
                lines += [f"### {name}", ""]
                ordered = sorted(series[name], key=lambda n: (
                    n.part is None, n.part if n.part is not None else 99999, _sort_key(n.title)
                ))
                lines.extend(_entry(note, numbered=True) for note in ordered)
                lines.append("")
        else:
            for note in sorted(entries, key=lambda n: _sort_key(n.title)):
                lines.append(_entry(note))
            lines.append("")

    lines += [
        "---", "",
        "*Para corregir el grupo, la serie o el orden de una nota, edita en su cabecera "
        "`index_group`, `index_series` o `index_part` y ejecuta `reel --reindex`.*", "",
    ]
    content = "\n".join(lines)
    if not index.exists() or index.read_text(encoding="utf-8") != content:
        tmp = category_dir / (INDEX_NAME + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(index)
    return index


def rebuild_all_indexes() -> list[Path]:
    if not REELS.is_dir():
        return []
    result = []
    for folder in sorted(REELS.iterdir(), key=lambda p: _sort_key(p.name)):
        if folder.is_dir():
            made = rebuild_category_index(folder)
            if made is not None:
                result.append(made)
    return result

