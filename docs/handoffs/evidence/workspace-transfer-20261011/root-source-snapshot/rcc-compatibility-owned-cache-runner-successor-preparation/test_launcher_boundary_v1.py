"""Synthetic CompletedProcess controls; never invoke commands/product/native."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import launch_one_version_v1 as L
from runner_contracts_v3 import AdmissionFailure


class LauncherBoundary(unittest.TestCase):
    def run_fixture(self, codes, *, fail_write=None):
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)/'config.json'; config.write_text('{"source_root":"/synthetic/source"}')
            release = Path(directory)/'release.json'; release.write_text('{}')
            marker = tempfile.mkdtemp(prefix='root-rcc-owned-cache-one-SYNTHETIC-', dir='/workspace/engineering')
            logs = Path(marker); logs.rmdir()  # Once-owned synthetic logging only.
            argv = ['synthetic', '--config', str(config), '--config-sha256', L.content_sha(config.read_bytes()),
                    '--release', str(release), '--release-sha256', L.content_sha(release.read_bytes()),
                    '--label', 'control3', '--log-root', str(logs)]
            def run(command, **kwargs):
                calls.append((command, kwargs))
                return subprocess.CompletedProcess(command, codes[len(calls)-1], b'completed original stdout', b'completed original stderr')
            real_write = L.write_private
            def write(path, raw):
                if path.name == fail_write: raise OSError('SYNTHETIC_PRIVATE_WRITE_FAILURE')
                real_write(path, raw)
            try:
                with patch.object(L, 'CACHED', sys.executable), patch.object(L, 'require_release'), \
                     patch.object(L.subprocess, 'run', side_effect=run), \
                     patch.object(L.os, 'statvfs', return_value=types.SimpleNamespace(f_bavail=5_000_000_000, f_frsize=1)), \
                     patch.object(L.sys, 'argv', argv), patch.object(L, 'write_private', side_effect=write):
                    result = L.main()
                saved = {path.name: path.read_bytes() for path in logs.iterdir()}
                return result, calls, saved
            finally:
                if logs.exists(): shutil.rmtree(logs)  # Only this test's synthetic temp.

    def test_exact_single_gateway_and_pre_post_bounds(self):
        result, calls, saved = self.run_fixture([0, 0, 0])
        self.assertEqual(result, 0)
        self.assertEqual(len(calls), 3)
        self.assertEqual([call[0][3] for call in calls], ['120s', '660s', '120s'])
        self.assertEqual(calls[1][0][4:7], ['/workspace/actions-cloud/bin/rcc', 'task', 'script'])
        self.assertEqual(saved['primary.stdout'], b'completed original stdout')

    def test_failed_preflight_runs_post_but_never_gateway(self):
        result, calls, saved = self.run_fixture([4, 0])
        self.assertEqual(result, 1); self.assertEqual(len(calls), 2)
        self.assertEqual(json.loads(saved['launcher-terminal.json'])['gateway'], 'NOT_RUN_PREFLIGHT_FAILED')
        self.assertNotIn('primary.stdout', saved)

    def test_nonzero_primary_original_stdout_and_post_return_separate(self):
        result, calls, saved = self.run_fixture([0, 7, 3])
        self.assertEqual(result, 1); self.assertEqual(len(calls), 3)
        self.assertEqual(json.loads(saved['primary-returncode.json'])['returncode'], 7)
        self.assertEqual(saved['primary.stderr'], b'completed original stderr')
        self.assertEqual(json.loads(saved['launcher-terminal.json'])['post_returncode'], 3)

    def test_completed_primary_code_survives_retention_failure_and_post_still_runs(self):
        result, calls, saved = self.run_fixture([0, 0, 0], fail_write='primary.stdout')
        self.assertEqual(result, 1); self.assertEqual(len(calls), 3)
        self.assertEqual(json.loads(saved['primary-returncode.json'])['returncode'], 0)
        self.assertEqual(json.loads(saved['launcher-terminal.json'])['primary_exception_class'], 'OSError')
        self.assertNotIn('primary.stdout', saved)

    def test_post_retention_failure_cannot_admit_primary_success(self):
        result, _, saved = self.run_fixture([0, 0, 0], fail_write='post.stdout')
        self.assertEqual(result, 1)
        self.assertEqual(saved['primary.stdout'], b'completed original stdout')
        self.assertEqual(json.loads(saved['launcher-terminal.json'])['post_exception_class'], 'OSError')

    def test_inherited_cache_config_rejected_before_logging_or_process(self):
        with patch.object(L, 'CACHED', sys.executable), patch.object(L.sys, 'argv',
                ['synthetic', '--config', '/missing', '--config-sha256', 'a'*64, '--release', '/missing',
                 '--release-sha256', 'b'*64, '--label', 'control3', '--log-root', '/missing']), \
             patch.dict(os.environ, {'ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG': '{}'}), \
             patch.object(L.subprocess, 'run') as run:
            with self.assertRaises(AdmissionFailure): L.main()
            run.assert_not_called()


if __name__ == '__main__': unittest.main()
