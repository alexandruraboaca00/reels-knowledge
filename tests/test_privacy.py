"""Reglas de auditoría con nombres y credenciales ficticios."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('privacy_audit', Path(__file__).resolve().parents[1]/'scripts/audit_privacy.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class PrivacyTests(unittest.TestCase):
    def test_private_paths_are_rejected(self):
        for path in ('vault/nota.md', 'data/reels.db', 'config/config.json', '.env',
                     'nested/cookies.txt', 'backups/note.md', 'profiles/browser/file', 'nested/key.pem'):
            with self.subTest(path=path):
                self.assertIsNotNone(audit.DENIED.search(path))
        self.assertIsNone(audit.DENIED.search('config/config.example.json'))
        self.assertIsNone(audit.DENIED.search('app/frames.py'))

    def test_json_and_assignment_credentials_are_detected(self):
        pattern = audit.PATTERNS['credencial asignada']
        self.assertIsNotNone(pattern.search(b'"api_' + b'key": "synthetic-fixture-value"'))
        self.assertIsNotNone(pattern.search(b'access_' + b'token' + b' = "synthetic-fixture-value"'))

    def test_public_identity_must_match_github_noreply(self):
        with self.assertRaises(ValueError):
            audit.scan(public_login='fixture-user', public_email='private@example.invalid')
        with self.assertRaises(ValueError):
            audit.scan(public_login='fixture-user', public_email='123+another@users.noreply.github.com')

    def test_synthetic_history_accepts_only_public_identity(self):
        import os
        import subprocess
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env = dict(os.environ, GIT_AUTHOR_NAME='fixture-user', GIT_COMMITTER_NAME='fixture-user',
                       GIT_AUTHOR_EMAIL='123+fixture-user@users.noreply.github.com',
                       GIT_COMMITTER_EMAIL='123+fixture-user@users.noreply.github.com',
                       GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
            def git(*args):
                return subprocess.run(['git',*args], cwd=root, env=env, capture_output=True, check=True)
            git('init','--initial-branch=main')
            (root/'README.md').write_text('fixture sintética')
            git('add','README.md')
            git('-c','commit.gpgsign=false','commit','-m','Fixture')
            with patch.object(audit,'ROOT',root):
                self.assertEqual(audit.scan(public_login='fixture-user',public_email=env['GIT_AUTHOR_EMAIL'])['hallazgos'], [])
                self.assertTrue(audit.scan(public_login='other', public_email='other@users.noreply.github.com')['hallazgos'])
                (root/'config').mkdir()
                (root/'config/config.json').write_text('{}')
                git('add','config/config.json')
                git('-c','commit.gpgsign=false','commit','-m','Configuración ficticia')
                findings = audit.scan(public_login='fixture-user',public_email=env['GIT_AUTHOR_EMAIL'])['hallazgos']
                self.assertTrue(any(f['scope']=='historial' and f['path']=='config/config.json' for f in findings))
