from pathlib import Path
import os,json,hashlib,subprocess,difflib
O=Path(__file__).parent;R=Path('/workspace/engineering/pr308')
def write(n,b):
 p=O/n;raw=b.encode() if isinstance(b,str) else b;fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as s:s.write(raw)
 return p
old=(R/'action_server/src/actions/server/_rcc_runtime_adapter.py').read_text();target='        compatibility = verify_rcc_compatibility(rcc_location, runner=runner)\n';assert old.count(target)==1
new=old.replace(target,'        compatibility = verify_rcc_compatibility(\n            rcc_location, runner=None if runner is _subprocess_runner else runner\n        )\n');write('original_rcc_runtime_adapter.py',old);write('proposed_rcc_runtime_adapter.py',new)
tests='''import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "selector", ["released-18.19.5-linux-amd64", "candidate-727-18.19.6-linux-amd64"]
)
@pytest.mark.parametrize("entrypoint", ["verify_rcc_version", "get_rcc_location"])
def test_isolated_default_version_routes_use_ten_second_probe(
    tmp_path, monkeypatch, selector, entrypoint
):
    from actions.server import _rcc_runtime_adapter as adapter

    policy = adapter.approved_rcc_test_policy(selector)
    binary = tmp_path / "service-free-version-probe"
    binary.write_bytes(b"fake: no native binary is executed")
    binary.chmod(0o700)
    monkeypatch.setenv("ACTIONS_RUNTIME_RCC_TEST_COMPATIBILITY", selector)
    monkeypatch.setenv("ACTIONS_RUNTIME_RCC_BINARY", str(binary))
    monkeypatch.setenv("ACTIONS_RUNTIME_RCC_TIMEOUT", "900")
    events = []
    monkeypatch.setattr(adapter, "_rcc_platform", lambda: "linux-amd64")
    monkeypatch.setattr(
        adapter,
        "_binary_sha256",
        lambda path: events.append(("hash", path)) or policy.binary_sha256,
    )

    def completed(argv, **kwargs):
        events.append(("probe", argv, kwargs["timeout"]))
        return subprocess.CompletedProcess(argv, 0, policy.version + "\\n", "")

    monkeypatch.setattr(adapter.subprocess, "run", completed)
    if entrypoint == "get_rcc_location":
        assert adapter.get_rcc_location() == binary
    else:
        assert adapter.verify_rcc_version(binary) == policy.version
    assert events == [("hash", binary), ("probe", [str(binary), "--version"], 10)]
    assert adapter.RCC_VERSION == "v18.19.3"


def test_legacy_default_version_route_keeps_general_command_budget(monkeypatch):
    from actions.server import _rcc_runtime_adapter as adapter

    monkeypatch.delenv("ACTIONS_RUNTIME_RCC_TEST_COMPATIBILITY", raising=False)
    monkeypatch.setenv("ACTIONS_RUNTIME_RCC_TIMEOUT", "900")
    calls = []

    def completed(argv, **kwargs):
        calls.append((argv, kwargs["timeout"]))
        return subprocess.CompletedProcess(argv, 0, "v18.19.3\\n", "")

    monkeypatch.setattr(adapter.subprocess, "run", completed)
    assert adapter.verify_rcc_version(Path("/service-free/rcc")) == "v18.19.3"
    assert calls == [(["/service-free/rcc", "--version"], 900)]


def test_isolated_explicit_injected_version_runner_is_preserved(monkeypatch):
    from actions.server import _rcc_runtime_adapter as adapter

    selector = "released-18.19.5-linux-amd64"
    policy = adapter.approved_rcc_test_policy(selector)
    monkeypatch.setenv("ACTIONS_RUNTIME_RCC_TEST_COMPATIBILITY", selector)
    monkeypatch.setattr(adapter, "_rcc_platform", lambda: "linux-amd64")
    monkeypatch.setattr(adapter, "_binary_sha256", lambda path: policy.binary_sha256)
    monkeypatch.setattr(
        adapter.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("Injected runner must not spawn"),
    )
    calls = []

    def runner(*argv):
        calls.append(argv)
        return 0, policy.version, ""

    assert adapter.verify_rcc_version(Path("/service-free/rcc"), runner) == policy.version
    assert calls == [("/service-free/rcc", "--version")]


def test_isolated_default_version_timeout_uses_fixed_error(monkeypatch):
    from actions.server import _rcc_runtime_adapter as adapter

    policy = adapter.approved_rcc_test_policy("released-18.19.5-linux-amd64")
    monkeypatch.setenv(
        "ACTIONS_RUNTIME_RCC_TEST_COMPATIBILITY", "released-18.19.5-linux-amd64"
    )
    monkeypatch.setattr(adapter, "_rcc_platform", lambda: "linux-amd64")
    monkeypatch.setattr(adapter, "_binary_sha256", lambda path: policy.binary_sha256)
    calls = []

    def timed_out(argv, **kwargs):
        calls.append(kwargs["timeout"])
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"], output="secret-probe")

    monkeypatch.setattr(adapter.subprocess, "run", timed_out)
    with pytest.raises(adapter.RccRuntimeError) as error:
        adapter.verify_rcc_version(Path("/service-free/rcc"))
    assert calls == [10]
    assert str(error.value) == "RCC compatibility failed: unable to verify selected version"
    assert error.value.__cause__ is None
'''
write('test_isolated_default_version_probe_regressions.py',tests)
originaltest=(R/'action_server/tests/action_server_tests/test_rcc_runtime_adapter.py').read_text();assert tests.startswith('import subprocess\nfrom pathlib import Path\n\nimport pytest\n\n');append=tests.split('import pytest\n',1)[1];write('proposed_test_rcc_runtime_adapter.py',originaltest+'\n'+append)
write('adapter-and-seven-regressions.patch',''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/action_server/src/actions/server/_rcc_runtime_adapter.py',tofile='b/action_server/src/actions/server/_rcc_runtime_adapter.py'))+''.join(difflib.unified_diff(originaltest.splitlines(keepends=True),(originaltest+'\n'+append).splitlines(keepends=True),fromfile='a/action_server/tests/action_server_tests/test_rcc_runtime_adapter.py',tofile='b/action_server/tests/action_server_tests/test_rcc_runtime_adapter.py')))
print('PRIVATE_PATCH_PREPARED_NO_PRODUCT_SOURCE_CHANGE_OR_NATIVE')
