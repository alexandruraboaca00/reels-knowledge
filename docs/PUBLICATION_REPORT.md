# Copia local preparada para publicación

Fecha: 2026-11-07. Licencia elegida por el titular: **GPL-3.0-only**, igual que
su proyecto Europass. LICENSE contiene el mismo texto íntegro GNU GPL versión 3.

## Alcance

La copia de publicación contiene únicamente código, pruebas sintéticas, configuración
de ejemplo, locks, licencia, instrucciones y documentación revisados. Se prepara
con historial nuevo y rama `main`, sin importar `.git` del repositorio original.
No contiene Vault, configuración local, bases SQLite, cookies, credenciales,
perfiles de navegador, logs, copias de seguridad, entorno ni multimedia personal.
El repositorio original y todos sus datos se conservan.

La identidad pública prevista para autor y committer es:

- Alias: `alexandruraboaca00`.
- Correo: `326949311+alexandruraboaca00@users.noreply.github.com`.

Se comprobó su correspondencia con el identificador público de la cuenta GitHub y
la configuración noreply usada en Europass. No se utiliza el nombre completo ni
el correo personal del perfil. La configuración de identidad es local a la copia;
no se cambia la configuración global de Git ni la de otros proyectos.

## Verificaciones

30 tests pasan, incluidos nuevos casos de auditoría con repositorios sintéticos:
solo se acepta la identidad pública explícita y se detecta configuración privada
versionada. Se mantienen las verificaciones previas de instalación del lock CPU,
importaciones, backups, índices, descargas simuladas y vídeo sintético.

Antes de publicar, verificar en la copia exacta:

```bash
python3 scripts/audit_privacy.py --public-login alexandruraboaca00 --public-email 326949311+alexandruraboaca00@users.noreply.github.com
git status --short
git log --all --format=fuller
git ls-files
```

La auditoría debe terminar con cero hallazgos. Las identidades privadas y mensajes
se revisan sin imprimir sus valores; el escaneo heurístico no constituye una garantía
absoluta frente a cualquier clase de dato personal. Los informes históricos de
PREPARATION_REPORT.md describen el repositorio original, no el historial nuevo.

## Publicación pendiente

No hay remoto configurado, push ni release. Destino propuesto:
`alexandruraboaca00/reels-knowledge`, visibilidad pública, rama `main`.
La creación del repositorio y el push requieren autorización final del titular.
No se publica el repositorio original ni se usa push forzado.

Continúan pendientes la inferencia real CPU/NVIDIA, benchmarks e instalación en
Arch limpio. La CI está preparada, pero solo podrá ejecutarse en GitHub tras publicar.
