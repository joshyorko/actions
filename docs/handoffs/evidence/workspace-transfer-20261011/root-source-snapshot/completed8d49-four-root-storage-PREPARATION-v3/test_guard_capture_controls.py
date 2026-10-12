"""Pure actual-helper controls; no child, pytest plugin, provider or network."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
helper = {'__name__': 'private_actual_capture_helper'}
exec(compile((HERE / 'guard_capture.py').read_bytes(), str(HERE / 'guard_capture.py'), 'exec'), helper)


class Controls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='capture-control-', dir=HERE)
        self.parent = Path(self.temp.name)
        self.calls = []

    def tearDown(self):
        self.temp.cleanup()  # Only this test's newly authored fake capture files.

    def run(self, result=None):
        # unittest invokes TestCase.run; keep that protocol, use fake below.
        return super().run(result)

    def fake(self, *, returncode=0, error=None):
        def invoke(argv, **kw):
            self.calls.append((argv, kw))
            self.assertEqual(kw['timeout'], 60)
            self.assertTrue(kw['capture_output'])
            self.assertFalse(kw['check'])
            if error:
                raise error
            return subprocess.CompletedProcess(argv, returncode, b'fake-stdout\r\n', b'fake-stderr\n')
        return invoke

    def invoke(self, **kw):
        return helper['captured_guard_call'](['fake-metadata-only'], cwd=str(HERE), env={},
                                            phase=kw.pop('phase', 'before'), capture_parent=self.parent,
                                            run=kw.pop('run', self.fake()), **kw)

    def retained(self, phase='before'):
        p = self.parent / phase
        terminal = json.loads((p / 'terminal.json').read_bytes())
        for name, key in [('stdout.private.log', 'stdout'), ('stderr.private.log', 'stderr')]:
            raw = (p / name).read_bytes()
            self.assertEqual(terminal[key + '_bytes'], len(raw))
            self.assertEqual(terminal[key + '_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual((p / name).stat().st_mode & 0o777, 0o600)
        self.assertEqual(p.stat().st_mode & 0o777, 0o700)
        self.assertEqual((p / 'terminal.json').stat().st_mode & 0o777, 0o600)
        return terminal

    def test_success_is_retained_before_return(self):
        completed, terminal = self.invoke()
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(self.retained(), terminal)
        self.assertEqual(terminal['admission'], 'PASS')

    def test_nonzero_preserves_stdout_stderr_before_assertion(self):
        with self.assertRaisesRegex(AssertionError, 'CURRENT_DATA_ONLY_SOURCE_ENV_NATIVE_GUARD_FAIL'):
            self.invoke(run=self.fake(returncode=1))
        terminal = self.retained()
        self.assertEqual(terminal['returncode'], 1)
        self.assertEqual(terminal['admission'], 'FAIL')
        self.assertEqual((self.parent / 'before/stdout.private.log').read_bytes(), b'fake-stdout\r\n')

    def test_spawn_missing_poetry_keeps_original_exception_and_unknown_streams(self):
        original = FileNotFoundError(2, 'fake absent executable', 'poetry')
        with self.assertRaises(FileNotFoundError) as caught:
            self.invoke(run=self.fake(error=original))
        self.assertIs(caught.exception, original)
        terminal = self.retained()
        self.assertEqual(terminal['exception_type'], 'FileNotFoundError')
        self.assertIsNone(terminal['returncode'])
        self.assertFalse(terminal['stdout_available'])
        self.assertFalse(terminal['stderr_available'])

    def test_timeout_preserves_partial_original_capture(self):
        original = subprocess.TimeoutExpired(['fake-metadata-only'], 60, output=b'partial', stderr=b'partial-error')
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            self.invoke(run=self.fake(error=original))
        self.assertIs(caught.exception, original)
        terminal = self.retained()
        self.assertTrue(terminal['stdout_available'])
        self.assertEqual((self.parent / 'before/stdout.private.log').read_bytes(), b'partial')

    def test_timeout_missing_capture_is_unavailable_not_measured_empty(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            self.invoke(run=self.fake(error=subprocess.TimeoutExpired(['fake'], 60)))
        terminal = self.retained()
        self.assertFalse(terminal['stdout_available'])
        self.assertFalse(terminal['stderr_available'])

    def test_capture_failure_keeps_nonzero_primary_and_secondary_note(self):
        with patch.dict(helper, {'_write': lambda *a: (_ for _ in ()).throw(OSError('fake retention failure'))}):
            with self.assertRaises(AssertionError) as caught:
                self.invoke(run=self.fake(returncode=1))
        self.assertEqual(str(caught.exception), 'CURRENT_DATA_ONLY_SOURCE_ENV_NATIVE_GUARD_FAIL')
        self.assertEqual(caught.exception.__notes__, ['Guard capture retention also failed: OSError'])

    def test_capture_failure_keeps_spawn_primary(self):
        original = FileNotFoundError('fake spawn failure')
        with patch.dict(helper, {'_write': lambda *a: (_ for _ in ()).throw(OSError('fake retention failure'))}):
            with self.assertRaises(FileNotFoundError) as caught:
                self.invoke(run=self.fake(error=original))
        self.assertIs(caught.exception, original)
        self.assertEqual(caught.exception.__notes__, ['Guard capture retention also failed: OSError'])

    def test_success_with_capture_failure_fails_closed(self):
        with patch.dict(helper, {'_write': lambda *a: (_ for _ in ()).throw(OSError('fake retention failure'))}):
            with self.assertRaises(OSError):
                self.invoke()

    def test_duplicate_phase_refuses_second_launch(self):
        self.invoke()
        with self.assertRaises(FileExistsError):
            self.invoke()
        self.assertEqual(len(self.calls), 1)

    def test_before_after_are_separate_captures(self):
        self.invoke()
        self.invoke(phase='after')
        self.assertEqual(self.retained('before')['phase'], 'before')
        self.assertEqual(self.retained('after')['phase'], 'after')
        self.assertEqual(len(self.calls), 2)

    def test_unknown_phase_refuses_child(self):
        with self.assertRaises(AssertionError):
            self.invoke(phase='other')
        self.assertEqual(self.calls, [])

    def test_symlink_parent_refuses_child(self):
        link = self.parent / 'fake-link'
        link.symlink_to(self.parent)
        with self.assertRaises(AssertionError):
            helper['captured_guard_call'](['fake'], cwd=HERE, env={}, phase='before', capture_parent=link, run=self.fake())
        self.assertEqual(self.calls, [])

    def test_directory_fsync_failure_after_capture_remains_primary(self):
        original_write = helper['_write']
        observed = []
        def fail_after_created(path):
            observed.append(path)
            if len(observed) > 1:
                raise OSError('fake fsync failure')
        with patch.dict(helper, {'_fsync_dir': fail_after_created}):
            with self.assertRaises(AssertionError) as caught:
                self.invoke(run=self.fake(returncode=1))
        self.assertIn('Guard capture retention also failed: OSError', caught.exception.__notes__)
        self.assertEqual(self.retained()['returncode'], 1)

    def test_actual_new_guard_missing_cached_path_rejects_before_child(self):
        ns = {'__name__': 'actual_new_guard'}
        exec(compile((HERE / 'guard_readonly.py').read_bytes(), str(HERE / 'guard_readonly.py'), 'exec'), ns)
        cfg = ns['load_config'](Path('/workspace/engineering/completed8d49-four-root-storage-PREPARATION-v2/private-four-root-input-supplement.json'))
        code = json.loads(Path(cfg['source_guard_inputs']['path']).read_bytes())
        ns['exact'] = lambda row: None  # Model immutable input checking; no product command.
        ns['sys'] = SimpleNamespace(prefix=code['cached_toolkit_prefix'], flags=SimpleNamespace(optimize=0))
        with patch.dict(os.environ, {**code['expected_activation_exports'], 'PATH': '/workspace/actions-cloud/bin:/usr/bin'}, clear=True):
            with patch.object(subprocess, 'run', self.fake()):
                with self.assertRaisesRegex(AssertionError, 'CACHED_TOOLKIT_PATH1_REQUIRED'):
                    ns['protected'](cfg, phase='before', capture_parent=self.parent)
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
