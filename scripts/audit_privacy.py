#!/usr/bin/env python3
"""Auditoría heurística sin imprimir contenido sensible; no modifica Git."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DENIED = re.compile(r'(?i)(^|/)(vault|data|backups?|profiles?|\.obsidian|\.aws|\.venv)(/|$)|(^|/)(\.env(?:\..*)?|cookies[^/]*|credentials[^/]*|config/config\.json)$|\.(db|sqlite3?|pem|key)(?:-|$)|(^|/)config/config\.json$')
PATTERNS = {
    'clave privada': re.compile(rb'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
    'token de proveedor': re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|sk-[A-Za-z0-9]{24,})'),
    'correo personal': re.compile(rb'(?i)[A-Z0-9._%+-]+@(?:gmail|googlemail|hotmail|outlook|live|yahoo|icloud|protonmail|proton)\.(?:com|es|net|me)'),
    'ruta personal absoluta': re.compile(rb'/(?:home|Users)/[^/\s"\x27]+/'),
    'credencial asignada': re.compile(rb'''(?i)(?:password|api_key|access_token|client_secret|token|secret)["']?\s*[=:]\s*["'][^"'\s]{8,}["']'''),
}

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def scan(current_only=False, public_login=None, public_email=None):
    if (public_login is None) != (public_email is None):
        raise ValueError("Indica juntos alias y correo público noreply")
    if public_login is not None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", public_login):
            raise ValueError("Alias público inválido")
        if not re.fullmatch(r"(?:[0-9]+\+)?" + re.escape(public_login) + r"@users\.noreply\.github\.com", public_email):
            raise ValueError("El correo público debe ser noreply de GitHub para ese alias")
    findings = []
    # Incluye referencias y reflogs locales; también revisa blobs no alcanzables.
    objects = {}
    for line in ([] if current_only else git('rev-list', '--objects', '--all', '--reflog').decode().splitlines()):
        oid, _, name = line.partition(' ')
        objects[oid] = name
    cp = subprocess.run(['git','fsck','--full','--no-reflogs','--unreachable'], cwd=ROOT, capture_output=True, text=True, check=True)
    for line in ([] if current_only else cp.stdout.splitlines()):
        bits = line.split()
        if len(bits) == 3 and bits[1] == 'blob':
            objects.setdefault(bits[2], '(objeto sin ruta)')
    blobs = 0
    for oid, name in objects.items():
        kind = git('cat-file', '-t', oid).strip()
        if kind == b'commit':
            # Solo se acepta la identidad pública expresamente indicada.
            identities = re.findall(rb'(?m)^(?:author|committer) (.*?) <([^>]+)>', git('cat-file','commit',oid))
            expected = (public_login.encode(), public_email.encode()) if public_login else None
            if len(identities) != 2 or any(identity != expected for identity in identities):
                findings.append({'scope':'historial', 'path':'(metadatos de commit)', 'reason':'identidad del autor/committer no aprobada'})
            for label, pattern in PATTERNS.items():
                if pattern.search(git('cat-file','commit',oid)):
                    findings.append({'scope':'historial', 'path':'(metadatos o mensaje de commit)', 'reason':label})
        if kind != b'blob':
            continue
        blobs += 1
        if DENIED.search(name):
            findings.append({'scope':'historial', 'path':name, 'reason':'archivo local o privado'})
        body = git('cat-file', 'blob', oid)
        for label, pattern in PATTERNS.items():
            if pattern.search(body):
                findings.append({'scope':'historial', 'path':name, 'reason':label})
    # Publicables actuales: versionados y nuevos no ignorados; no se leen Vaults locales.
    candidates = git('ls-files','--cached','--others','--exclude-standard','-z').decode().split('\0')
    for name in filter(None, candidates):
        path = ROOT/name
        if DENIED.search(name):
            findings.append({'scope':'actual', 'path':name, 'reason':'archivo local o privado'})
        if path.is_file():
            for label, pattern in PATTERNS.items():
                if pattern.search(path.read_bytes()):
                    findings.append({'scope':'actual', 'path':name, 'reason':label})
    return {'blobs_historicos_revisados':blobs, 'hallazgos':findings,
            'limite':'Heurística: no prueba ausencia total de secretos. Revisar diff, metadatos y objetos antes de publicar.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current-only', action='store_true')
    parser.add_argument('--public-login', help='Alias público autorizado como autor y committer')
    parser.add_argument('--public-email', help='Correo noreply autorizado de GitHub')
    args = parser.parse_args()
    try:
        report = scan(args.current_only, args.public_login, args.public_email)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    sys.exit(1 if report['hallazgos'] else 0)
