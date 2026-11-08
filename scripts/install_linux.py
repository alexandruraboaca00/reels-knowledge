#!/usr/bin/env python3
"""Instalación Linux por familias; no interpreta os-release como código."""
import argparse
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
UV_VERSION = '0.12.17'
FAMILIES = {
    'debian': [['apt-get', 'update'], ['apt-get', 'install', 'python3', 'curl', 'ca-certificates', 'git', 'ffmpeg', 'fonts-dejavu-core']],
    'fedora': [['dnf', 'install', 'python3', 'curl', 'ca-certificates', 'git', 'ffmpeg-free', 'dejavu-sans-fonts']],
    'arch': [['pacman', '-S', '--needed', 'python', 'curl', 'ca-certificates', 'git', 'ffmpeg', 'ttf-dejavu']],
    'opensuse': [['zypper', 'install', 'python3', 'curl', 'ca-certificates', 'git', 'ffmpeg', 'dejavu-fonts']],
}
ALIASES = {'ubuntu':'debian', 'linuxmint':'debian', 'pop':'debian', 'neon':'debian',
           'manjaro':'arch', 'endeavouros':'arch', 'opensuse-leap':'opensuse',
           'opensuse-tumbleweed':'opensuse', 'opensuse-slowroll':'opensuse'}


def read_release(path=Path('/etc/os-release')):
    result = {}
    for line in path.read_text().splitlines():
        key, sep, value = line.partition('=')
        if sep and key in {'ID', 'ID_LIKE', 'VERSION_ID', 'VARIANT_ID'}:
            words = shlex.split(value, comments=True)
            result[key] = ' '.join(words)
    return result


def detect_family(release):
    distro = release.get('ID', '').lower()
    # No tratar RHEL o derivados inmutables como Fedora convencional.
    if release.get('VARIANT_ID', '').lower() in {'silverblue','kinoite','sericea','onyx','coreos','iot'}:
        raise ValueError('Edición inmutable no automatizada; consulta la instalación manual')
    if distro in {'bazzite','bluefin','rhel', 'centos', 'rocky', 'almalinux', 'silverblue', 'nixos', 'alpine'}:
        raise ValueError('Distribución no automatizada; consulta la instalación manual')
    for candidate in [distro, *release.get('ID_LIKE', '').lower().split()]:
        family = ALIASES.get(candidate, candidate)
        if family in FAMILIES:
            return family
    raise ValueError('Familia no reconocida; consulta la instalación manual')


def run(cmd, env=None):
    print('+ ' + shlex.join([str(c) for c in cmd]), flush=True)
    subprocess.run([str(c) for c in cmd], env=env, check=True)


def install_uv(env):
    # Descarga oficial versionada, sin sudo, sin modificar perfiles del shell.
    with tempfile.TemporaryDirectory(prefix='reels-uv-') as td:
        installer = Path(td)/'install.sh'
        run(['curl', '--fail', '--location', '--proto', '=https', '--tlsv1.2',
             f'https://astral.sh/uv/{UV_VERSION}/install.sh', '--output', installer], env)
        run(['sh', installer], dict(env, UV_INSTALL_DIR=str(Path.home()/'.local/bin'), UV_NO_MODIFY_PATH='1'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', nargs='?', choices=['cpu','nvidia'], default='cpu')
    parser.add_argument('--distro', choices=sorted(FAMILIES), help='Selecciona familia explícitamente')
    parser.add_argument('--system', action='store_true', help='Instala requisitos del sistema con sudo')
    parser.add_argument('--install-uv', action='store_true', help='Instala uv oficial si no está disponible')
    parser.add_argument('--dry-run', action='store_true', help='Solo muestra el plan; no ejecuta comandos')
    args = parser.parse_args(argv)
    try:
        if platform.system() != 'Linux' or platform.machine() not in {'x86_64','AMD64'}:
            raise ValueError('Estos locks se validan para Linux x86_64; otras plataformas no están soportadas')
        if platform.libc_ver()[0] != 'glibc':
            raise ValueError('Se requiere Linux con glibc; musl/Alpine no están soportados')
        family = args.distro or detect_family(read_release())
        commands = FAMILIES[family] if args.system else []
        print(f'Familia: {family}; perfil: {args.profile}')
        if args.dry_run:
            for cmd in commands:
                print('+ ' + shlex.join(['sudo', *cmd]))
            if args.install_uv:
                print(f'uv {UV_VERSION}: instalador oficial HTTPS, solo si falta uv; sin sudo')
            print('+ ' + shlex.join(['bash',str(ROOT/'scripts/install.sh'),args.profile]))
            print('Se comprobarán ffmpeg, ffprobe y los filtros scdet/drawtext antes de instalar el entorno.')
            return 0
        if os.geteuid() == 0:
            raise ValueError('Ejecuta como usuario normal: solo los paquetes del sistema usan sudo')
        for cmd in commands:
            run(['sudo', *cmd])
        env = dict(os.environ)
        env['PATH'] = str(Path.home()/'.local/bin') + os.pathsep + env.get('PATH','')
        if not shutil.which('uv', path=env['PATH']):
            if not args.install_uv:
                raise ValueError('Falta uv; instálalo o añade --install-uv')
            install_uv(env)
        for binary in ('uv', 'ffmpeg', 'ffprobe'):
            if not shutil.which(binary, path=env['PATH']):
                raise ValueError(f'Falta {binary}; revisa los paquetes de tu distro (--system)')
        cp = subprocess.run(['ffmpeg','-hide_banner','-filters'], env=env, text=True, capture_output=True, check=True)
        filters = {line.split()[1] for line in cp.stdout.splitlines() if len(line.split()) >= 2}
        if not {'scdet','drawtext'} <= filters:
            raise ValueError('FFmpeg necesita scdet y drawtext; consulta los paquetes/codecs de tu distro')
        run(['bash',ROOT/'scripts/install.sh',args.profile], env)
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'Instalación detenida: {exc}', file=__import__('sys').stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
