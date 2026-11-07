# Contribuir

Lee `AGENTS.md` antes de modificar el proyecto. Mantén compatibles `reel`,
`--repair`, `--reindex`, `--file`, `doctor` y `config`. Documentación en español.

Cada corrección necesita una prueba unitaria con fixtures sintéticos, sin GPU ni
red. Ejecuta:

```bash
python3 -m unittest discover -s tests -v
bash -n bin/reel scripts/*.sh
python3 scripts/audit_privacy.py --current-only
```

Las pruebas no requieren las dependencias de inferencia. Instala FFmpeg con
`drawtext` y fuentes para ejecutar la prueba de vídeo. Añade casos de cambios
rápidos y texto al modificar capturas; no añadas límites globales ni umbrales de
deduplicación que pierdan texto pequeño. El modo fixed sigue siendo optativo.

Configura mediante `config/config.example.json`; no edites ni publiques el archivo
local del usuario. No descargues contenido de cuentas reales en tests ni incluyas
Vaults, SQLite, cookies, backups, logs o multimedia personal. Los archivos ignorados
pueden seguir en historial: la auditoría completa se ejecuta antes de publicar.

Describe problema, comportamiento resultante, pruebas y límites reales de hardware.
No declares soporte de plataformas ni modelos sin evidencia. Si cambias dependencias,
regenera locks con hashes y valida una instalación aislada. `av==18.1.0` se mantiene
hasta validar explícitamente una alternativa.

No reescribas historial, publiques repositorios o subas cambios sin autorización.
El proyecto usa GNU GPL v3.0, `GPL-3.0-only`; consulta [LICENSE](LICENSE).
