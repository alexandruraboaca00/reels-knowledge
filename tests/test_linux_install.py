"""Planificación por distribución sin root, red ni gestores reales."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('linux_install', ROOT/'scripts/install_linux.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class LinuxInstallTests(unittest.TestCase):
    def test_distro_families(self):
        for distro, family in [('ubuntu','debian'),('linuxmint','debian'),('debian','debian'),
                              ('fedora','fedora'),('arch','arch'),('manjaro','arch'),
                              ('opensuse-leap','opensuse'),('opensuse-tumbleweed','opensuse')]:
            with self.subTest(distro=distro):
                self.assertEqual(installer.detect_family({'ID':distro}),family)
        self.assertEqual(installer.detect_family({'ID':'derivative','ID_LIKE':'ubuntu debian'}),'debian')

    def test_unsupported_and_immutable_fail(self):
        for release in ({'ID':'alpine'}, {'ID':'rocky','ID_LIKE':'fedora'}, {'ID':'nixos'},
                        {'ID':'unknown'}, {'ID':'fedora','VARIANT_ID':'silverblue'}):
            with self.assertRaises(ValueError):
                installer.detect_family(release)

    def test_os_release_is_data_not_shell(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'os-release'
            marker = Path(td)/'must-not-exist'
            path.write_text('ID=ubuntu\nID_LIKE="debian"\nNAME="$(touch '+str(marker)+')"\n')
            self.assertEqual(installer.read_release(path),{'ID':'ubuntu','ID_LIKE':'debian'})
            self.assertFalse(marker.exists())

    def test_all_shell_entrypoints_dry_run(self):
        for family, manager in [('debian','apt-get'),('fedora','dnf'),('arch','pacman'),('opensuse','zypper')]:
            cp = subprocess.run(['bash',str(ROOT/f'scripts/install-{family}.sh'),'nvidia','--system','--install-uv','--dry-run'],capture_output=True,text=True,check=True)
            self.assertIn(manager, cp.stdout)
            self.assertIn('nvidia', cp.stdout)
            self.assertIn('install.sh', cp.stdout)

    def test_dry_run_never_executes(self):
        with patch.object(installer,'run',side_effect=AssertionError('ejecución inesperada')), \
             patch.object(installer.subprocess,'run',side_effect=AssertionError('ejecución inesperada')), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(['cpu','--distro','debian','--system','--dry-run']),0)

    def test_missing_uv_stops_before_environment(self):
        with patch.object(installer.os,'geteuid',return_value=1000), \
             patch.object(installer.shutil,'which',return_value=None), \
             patch.object(installer,'run') as run, contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(['--distro','debian']),1)
            run.assert_not_called()

    def test_system_commands_and_environment_are_separate(self):
        with patch.object(installer.os,'geteuid',return_value=1000), \
             patch.object(installer.shutil,'which',return_value='/fixture/bin'), \
             patch.object(installer.subprocess,'run',return_value=subprocess.CompletedProcess([],0,' ... scdet V->V\n ... drawtext V->V','')), \
             patch.object(installer,'run') as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(['nvidia','--distro','fedora','--system']),0)
            self.assertEqual(run.call_args_list[0].args[0][:3], ['sudo','dnf','install'])
            self.assertEqual(run.call_args.args[0][0],'bash')
            self.assertEqual(run.call_args.args[0][-1],'nvidia')

    def test_missing_filters_abort(self):
        with patch.object(installer.os,'geteuid',return_value=1000), \
             patch.object(installer.shutil,'which',return_value='/fixture/bin'), \
             patch.object(installer.subprocess,'run',return_value=subprocess.CompletedProcess([],0,' ... scale V->V','')), \
             patch.object(installer,'run') as run, contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(['--distro','arch']),1)
            run.assert_not_called()

    def test_uv_bootstrap_is_user_only_and_versioned(self):
        with patch.object(installer,'run') as run:
            installer.install_uv({'PATH':'/fixture'})
        self.assertTrue(any(installer.UV_VERSION in str(arg) for arg in run.call_args_list[0].args[0]))
        self.assertEqual(run.call_args.args[0][0],'sh')
        self.assertEqual(run.call_args.args[1]['UV_NO_MODIFY_PATH'],'1')
        self.assertTrue(all('sudo' not in c.args[0] for c in run.call_args_list))
