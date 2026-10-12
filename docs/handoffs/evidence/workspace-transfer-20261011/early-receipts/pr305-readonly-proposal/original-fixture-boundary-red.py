"""Execute immutable old fixture seams only; no Runtime/browser/build is run."""
import hashlib
import json
import os
import subprocess
import tempfile
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = '71aab046754ae0e0837f223fd0ba6b8513e63a62'
raw = subprocess.check_output(['git', '-C', '/workspace/engineering/pr305', 'show', SOURCE + ':action_server/tests/action_server_tests/mcp/test_mcp_apps_authoring.py'])
source = raw.decode()
a = source.index('    playwright_executable = shutil.which("chromium")')
b = source.index('    env["CANVAS_RUNTIME_MCP_URL"]', a)
selector = textwrap.dedent(source[a:b])
with patch.dict(os.environ, {'CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH': '/reviewed/headless-shell'}, clear=False):
    namespace = {'os': os, 'shutil': SimpleNamespace(which=lambda name: '/system/chromium')}
    exec(selector, namespace)
    try:
        assert namespace['env']['CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] == '/reviewed/headless-shell'
    except AssertionError:
        print('EXPECTED RED: original actual selection seam overwrites explicit headless pin with /system/chromium')
    else:
        raise AssertionError('Old selection regression did not reproduce')
a = source.index('    candidate_core_wheel_dir = tmp_path / "candidate-core"')
b = source.index('    candidate_core_wheel = next(', a)
prepare = textwrap.dedent(source[a:b])
with tempfile.TemporaryDirectory(prefix='cv305-red-') as root:
    namespace = {'tmp_path': Path(root), 'build_temp_dir': Path(root)/'sibling', 'repository_root': Path('/reviewed/repository'), 'os': os, 'shutil': SimpleNamespace(which=lambda name: '/reviewed/uv')}
    def reject_candidate(command, **kwargs):
        assert command[1:3] == ['build', '--wheel']
        raise RuntimeError('old fixture still invokes candidate build in requested public mode')
    namespace['subprocess'] = SimpleNamespace(run=reject_candidate)
    with patch.dict(os.environ, {'ACTIONS_CANVAS_CORE_MODE': 'published'}, clear=False):
        try:
            exec(prepare, namespace)
        except RuntimeError as failure:
            print('EXPECTED RED:', failure)
        else:
            raise AssertionError('Old public/candidate boundary did not reproduce')
print(json.dumps({'source':SOURCE,'source_sha256':hashlib.sha256(raw).hexdigest(),'selector_seam_sha256':hashlib.sha256(selector.encode()).hexdigest(),'candidate_seam_sha256':hashlib.sha256(prepare.encode()).hexdigest(),'expected_failures':2,'native_browser_build_execution':False},sort_keys=True))
