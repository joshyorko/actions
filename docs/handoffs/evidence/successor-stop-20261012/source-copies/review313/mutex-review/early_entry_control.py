"""Bounded Linux mutation control; private files, no product source edits."""
import hashlib
import importlib
import importlib.util
import json
import os
import pathlib
import tempfile
import threading
from unittest.mock import patch

import pytest

root = pathlib.Path('/workspace/actions-pr313')
out = pathlib.Path('/workspace/successor-evidence/review313/mutex-review')
results = []
for lane in ('_common', '_robo_utils'):
    test_directory = 'common_tests' if lane == '_common' else 'robo_utils'
    source = root / f'action_server/tests/action_server_tests/{test_directory}/test_system_mutex.py'
    snapshot = source.read_bytes()
    spec = importlib.util.spec_from_file_location('test_review_' + lane, source)
    testmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(testmod)
    module = importlib.import_module('actions.server.' + lane + '.system_mutex')
    real_constructor = module.SystemMutex
    real_timed = module.timed_acquire_mutex
    entered = threading.Event()
    owners = []
    counter = [0]
    early = []

    def constructor(*args, **kwargs):
        result = real_constructor(*args, **kwargs)
        counter[0] += 1
        if counter[0] == 4:
            owners.append(result)
            real_release = result.release_mutex

            def blocked_release():
                if not result.disposed:
                    entered.wait(1)
                return real_release()

            result.release_mutex = blocked_release
        return result

    class EntryHandle:
        def __init__(self, handle):
            self.handle = handle

        def __enter__(self):
            early.append(not owners[0].disposed)
            entered.set()
            return self.handle.__enter__()

        def __exit__(self, *args):
            return self.handle.__exit__(*args)

    def faulty_timed(name, *args, **kwargs):
        if kwargs.get('check_reentrant') is False:
            candidate = module.SystemMutex(name, check_reentrant=False)
            assert not candidate.get_mutex_aquired(), 'Mutant needs real failed acquisition'
            pathlib.Path(tempfile.gettempdir(), name).unlink()
            return EntryHandle(real_timed(name, *args, **kwargs))
        return real_timed(name, *args, **kwargs)

    with tempfile.TemporaryDirectory(dir=out) as directory:
        monkeypatch = pytest.MonkeyPatch()
        try:
            with patch.object(module, 'SystemMutex', constructor), patch.object(module, 'timed_acquire_mutex', faulty_timed), patch.dict(os.environ, {'TMPDIR': directory}), patch.object(tempfile, 'tempdir', directory):
                testmod.test_system_mutex(monkeypatch)
            outcome = 'FALSE_PASS'
        except BaseException as error:
            outcome = type(error).__name__ + ': ' + str(error)
        finally:
            monkeypatch.undo()
            entered.set()
    results.append({'lane': lane, 'reviewed_source_sha256': hashlib.sha256(snapshot).hexdigest(), 'mutant': 'successor acquires a different inode while original owner remains held; release delayed until successor enters', 'entered_while_owner_undisposed': early, 'outcome': outcome})
receipt = {'scope': 'Linux prepared interpreter; private temporary mutex files; mutation control of test proof only, not production/native/Windows acceptance', 'results': results}
print(json.dumps(receipt, indent=2))
(out / 'early-entry-mutant-current.json').write_text(json.dumps(receipt, indent=2) + '\n')
