"""Fixtures temporales y mocks: nunca se usan cuentas, modelos ni datos reales."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
import reel
import frames
import indexer


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for module, name, value in [(reel, 'ROOT', self.root), (reel, 'TMP_ROOT', self.root/'data/tmp'),
                                    (reel, 'DB_PATH', self.root/'data/reels.db'),
                                    (reel, 'VAULT', self.root/'vault'),
                                    (indexer, 'VAULT', self.root/'vault'),
                                    (indexer, 'REELS', self.root/'vault/Reels')]:
            p = patch.object(module, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.conn = reel.init_db()
        self.addCleanup(self.conn.close)

    def test_db_is_idempotent(self):
        url = 'https://example.invalid/video'
        self.assertEqual(reel.already_processed(self.conn, url), (False, None))
        self.conn.execute("INSERT INTO reels(url,processed_at,status,note_path) VALUES(?,?,'ok',?)", (url, 'date', 'note.md'))
        self.conn.commit()
        self.assertEqual(reel.already_processed(self.conn, url), (True, 'note.md'))
        other = reel.init_db()
        self.addCleanup(other.close)
        self.assertEqual(other.execute('SELECT count(*) FROM reels').fetchone()[0], 1)

    def run_pipeline(self, repair=False, failure=False):
        def download(url, folder):
            video = folder/'synthetic.mp4'
            video.write_bytes(b'synthetic fixture')
            return video, {}, 'mock'
        payload = reel.normalize_note_data({'title':'Linux parte 2', 'category':'Linux', 'note_kind':'curso', 'series':'Linux', 'part':2}, {})
        with patch.object(reel, 'download_reel', side_effect=download), \
             patch.object(reel, 'extract_audio'), patch.object(reel, 'extract_frames', return_value=[]), \
             patch.object(reel, 'transcribe', return_value=('texto', 'es/cpu')), \
             patch.object(reel, 'analyze_frames', return_value=[]), patch.object(reel, 'unload_ollama'), \
             patch.object(reel, 'synthesize', side_effect=RuntimeError('fixture failure') if failure else None, return_value=payload):
            reel.process_one(self.conn, 'https://example.invalid/video', {'web_search':False}, repair)

    def test_repair_backups_before_replace_and_cleans_temp(self):
        self.run_pipeline()
        path = Path(reel.already_processed(self.conn, 'https://example.invalid/video')[1])
        path.write_text('contenido original')
        self.run_pipeline(repair=True)
        backups = list((self.root/'data/backups').glob('*.md'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), 'contenido original')
        updated = Path(reel.already_processed(self.conn, 'https://example.invalid/video')[1])
        self.assertIn('source: "https://example.invalid/video"', updated.read_text())
        self.assertEqual(list((self.root/'data/tmp').iterdir()), [])

    def test_failed_repair_keeps_note_and_db(self):
        self.run_pipeline()
        path = Path(reel.already_processed(self.conn, 'https://example.invalid/video')[1])
        before = path.read_bytes()
        self.run_pipeline(repair=True, failure=True)
        self.assertEqual(path.read_bytes(), before)
        self.assertTrue(reel.already_processed(self.conn, 'https://example.invalid/video')[0])

    def test_index_orders_parts_and_preserves_notes(self):
        for part in (10, 2, 1):
            d = {'title':f'Linux parte {part}', 'category':'Linux', 'note_kind':'curso', 'series':'Linux', 'part':part}
            reel.save_note(d, reel.render_note('https://example.invalid/'+str(part), d, [], {}, 'mock', 'es'), 'https://example.invalid/'+str(part))
        before = {p:p.read_bytes() for p in (self.root/'vault').rglob('*.md')}
        paths = indexer.rebuild_all_indexes()
        body = paths[0].read_text()
        self.assertLess(body.index('|Linux parte 1]]'), body.index('|Linux parte 2]]'))
        self.assertLess(body.index('|Linux parte 2]]'), body.index('|Linux parte 10]]'))
        self.assertTrue(all(p.read_bytes()==b for p,b in before.items()))

    def test_download_fallback_and_domain_boundary(self):
        folder = self.root/'download'
        folder.mkdir()
        calls = []
        def run(cmd, **kwargs):
            calls.append(cmd)
            if 'yt-dlp' in cmd[0]:
                (folder/'fixture.mp4').write_bytes(b'video')
                (folder/'fixture.info.json').write_text('{"title":"fixture"}')
                return subprocess.CompletedProcess(cmd, 0, '', '')
            return subprocess.CompletedProcess(cmd, 1, '', 'synthetic failure')
        with patch.object(reel, 'run', side_effect=run), patch.object(reel, 'browser_spec', return_value='brave:synthetic'):
            _, meta, downloader = reel.download_reel('https://www.instagram.com/reel/fixture', folder)
            self.assertEqual(downloader, 'yt-dlp')
            self.assertEqual(meta['title'], 'fixture')
            self.assertEqual(len(calls), 2)
            calls.clear()
            reel.download_reel('https://evilinstagram.com/video', folder)
            self.assertNotIn('--cookies-from-browser', calls[0])

    def test_model_urls_must_exist_in_evidence(self):
        data = {'title':'Herramientas', 'resources':[{'name':'A','url_visible':'https://invented.invalid'}], 'links_visible':['https://invented.invalid']}
        with patch.object(reel, 'ollama_chat', return_value=json.dumps(data)):
            result = reel.synthesize_single('https://example.invalid/source', 'sin enlaces', [], {}, 'mock')
        self.assertEqual(result['resources'][0]['url_visible'], '')
        self.assertEqual(result['links_visible'], [])

    def test_visible_url_validation(self):
        for bad in ('javascript:alert(1)', 'https://', 'https://user:password@example.invalid', 'https://example.invalid/a)bad'):
            self.assertFalse(reel.valid_http_url(bad))

    def test_synthesis_keeps_resources_from_all_blocks(self):
        def synth(url, transcript, notes, meta, model):
            return reel.normalize_note_data({'title':'Lista', 'resources':[{'name':n} for n in notes]}, {})
        with patch.object(reel, 'synthesize_single', side_effect=synth):
            d = reel.synthesize('https://example.invalid', '', [str(i) for i in range(40)], {}, 'mock')
        self.assertEqual(len(d['resources']), 40)

    def test_whisper_cpu_and_auto_fallback_without_gpu(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        instance = Mock()
        instance.transcribe.return_value = ([SimpleNamespace(text=' texto ')], SimpleNamespace(language='es'))
        factory = Mock(return_value=instance)
        fake = SimpleNamespace(WhisperModel=factory)
        with patch.dict(sys.modules, {'faster_whisper':fake}):
            text, info = reel.transcribe(Path('fixture.wav'), 'base', 'cpu')
            self.assertEqual((text, info), ('texto', 'es/cpu'))
            self.assertEqual(factory.call_args.kwargs['device'], 'cpu')
            factory.reset_mock()
            factory.side_effect = [RuntimeError('sin CUDA'), instance]
            self.assertEqual(reel.transcribe(Path('fixture.wav'), 'base')[1], 'es/cpu')
            self.assertEqual(factory.call_count, 2)
            factory.side_effect = RuntimeError('sin CUDA')
            with self.assertRaises(RuntimeError):
                reel.transcribe(Path('fixture.wav'), 'base', 'cuda')

    def test_title_does_not_invent_a_resource(self):
        d = reel.normalize_note_data({'title':'Producto: guía', 'note_kind':'herramienta', 'resources':[]}, {})
        self.assertEqual(d['resources'], [])

    def test_config_defaults_merge_without_modifying_local(self):
        cfg = self.root/'config.json'
        original = '{"frames":{"interval_seconds":0.5},"custom":"keep"}'
        cfg.write_text(original)
        with patch.object(reel, 'CONFIG_PATH', cfg):
            data = reel.load_config()
        self.assertEqual(data['frames']['interval_seconds'], .5)
        self.assertEqual(data['frames']['mode'], 'hybrid')
        self.assertEqual(data['custom'], 'keep')
        self.assertEqual(cfg.read_text(), original)

    def test_supported_url_forms(self):
        for source, expected in [
            ('instagram.com/reel/FIXTURE/?igsh=test', 'https://instagram.com/reel/FIXTURE'),
            ('https://youtu.be/FIXTURE?si=abc', 'https://youtu.be/FIXTURE'),
            ('https://youtube.com/shorts/FIXTURE?si=abc', 'https://www.youtube.com/shorts/FIXTURE'),
            ('https://m.youtube.com/watch?v=FIXTURE&t=12', 'https://www.youtube.com/watch?v=FIXTURE'),
            ('https://www.tiktok.com/@fixture/video/123?necessary=1', 'https://tiktok.com/@fixture/video/123?necessary=1'),
        ]:
            with self.subTest(source=source):
                self.assertEqual(reel.normalize_url(source), expected)

    def test_failure_returns_false(self):
        with patch.object(reel, 'download_reel', side_effect=RuntimeError('fixture')):
            self.assertFalse(reel.process_one(self.conn, 'https://example.invalid', {}))
        self.assertEqual(self.conn.execute('SELECT status FROM reels').fetchone()[0], 'error')

    def test_new_heading_is_read_by_index(self):
        body = '## URLs vistas o mencionadas\n\n- https://example.invalid/resource\n'
        self.assertEqual(indexer._extract_links(body), [('example.invalid', 'https://example.invalid/resource')])


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Requiere FFmpeg')
class SyntheticVideoTests(unittest.TestCase):
    def test_rapid_changes_and_small_text_survive(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            video = folder/'fixture.mkv'
            # Tres pantallas, una solo difiere por un carácter de texto.
            subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',
                "color=white:s=320x180:r=10:d=1,drawtext=text='Texto 1':fontcolor=black:fontsize=16:x=10:y=10",
                '-f','lavfi','-i',"color=white:s=320x180:r=10:d=1,drawtext=text='Texto 2':fontcolor=black:fontsize=16:x=10:y=10",
                '-f','lavfi','-i','color=black:s=320x180:r=10:d=1',
                '-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0[out]', '-map','[out]', '-c:v','ffv1',str(video)], check=True)
            images, report = frames.capture(video, folder/'frames', {'mode':'hybrid','interval_seconds':.5})
            self.assertGreaterEqual(len(images), 3)
            self.assertGreaterEqual(report['scene_candidates'], 1)
            self.assertTrue(any('000000.250' in p.name for p in images))
            self.assertTrue(any('000001.250' in p.name for p in images))

    def test_subsecond_scene_changes(self):
        with tempfile.TemporaryDirectory() as td:
            video = Path(td)/'rapid.mkv'
            subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=white:s=160x90:r=20:d=0.2',
                            '-f','lavfi','-i','color=black:s=160x90:r=20:d=0.2',
                            '-f','lavfi','-i','color=white:s=160x90:r=20:d=0.2',
                            '-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0[out]',
                            '-map','[out]','-c:v','ffv1',str(video)], check=True)
            changes = frames.scene_change_times(video, 8)
            self.assertEqual(len(changes), 2)
            self.assertAlmostEqual(changes[0], .2, places=2)
            self.assertAlmostEqual(changes[1], .4, places=2)

    def test_invalid_threshold_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as td, patch.object(frames, 'probe_duration', return_value=10):
            with self.assertRaises(ValueError):
                frames.capture(Path('fixture'), Path(td), {'mode':'hybrid','scene_threshold':float('nan')})

    def test_scene_mode_long_video_does_not_use_interval_validation(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            def extract(cmd, **kwargs):
                Path(cmd[-1]).write_bytes(b'jpeg fixture')
                return subprocess.CompletedProcess(cmd, 0, '', '')
            with patch.object(frames, 'probe_duration', return_value=3600), \
                 patch.object(frames, 'scene_change_times', return_value=[]), \
                 patch.object(frames.subprocess, 'run', side_effect=extract):
                images, _ = frames.capture(folder/'video', folder/'frames', {'mode':'scene'})
            self.assertEqual(len(images), 1)

class InstallationTests(unittest.TestCase):
    def test_portable_launcher_and_safe_uninstall(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='portable space ') as td:
            root = Path(td)
            for folder in ('bin', 'scripts', 'app', 'config'):
                shutil.copytree(source/folder, root/folder)
            (root/'.venv/bin').mkdir(parents=True)
            (root/'.venv/bin/python').symlink_to(sys.executable)
            (root/'links').mkdir()
            (root/'links/reel').symlink_to(root/'bin/reel')
            (root/'vault').mkdir()
            note = root/'vault/personal.md'
            note.write_text('fixture privada sintética')
            env = dict(os.environ, REELS_KNOWLEDGE_HOME=str(root/'state'), REELS_KNOWLEDGE_BIN_DIR=str(root/'links'))
            result = subprocess.run([str(root/'links/reel'), 'config'], env=env, text=True, capture_output=True, check=True)
            self.assertIn(str(root/'state/config/config.json'), result.stdout)
            subprocess.run(['bash', str(root/'scripts/uninstall.sh')], env=env, capture_output=True, check=True)
            self.assertFalse((root/'links/reel').is_symlink())
            self.assertEqual(note.read_text(), 'fixture privada sintética')

    def test_installer_preserves_local_configuration(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for folder in ('scripts', 'config', 'bin'):
                shutil.copytree(source/folder, root/folder, ignore=shutil.ignore_patterns('config.json'))
            (root/'.venv/bin').mkdir(parents=True)
            (root/'.venv/bin/python').symlink_to(sys.executable)
            tools = root/'tools'
            tools.mkdir()
            for name in ('uv', 'ffmpeg', 'ffprobe'):
                p = tools/name
                p.write_text('#!/bin/sh\nexit 0\n')
                p.chmod(0o755)
            cfg = root/'config/config.json'
            cfg.write_text('{"custom": "keep"}')
            env = dict(os.environ, PATH=str(tools)+os.pathsep+os.environ['PATH'], REELS_KNOWLEDGE_HOME=str(root), REELS_KNOWLEDGE_BIN_DIR=str(root/'links'))
            subprocess.run(['bash',str(root/'scripts/install.sh'),'cpu'], env=env, capture_output=True, check=True)
            self.assertEqual(cfg.read_text(), '{"custom": "keep"}')
