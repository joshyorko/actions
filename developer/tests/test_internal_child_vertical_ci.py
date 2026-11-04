"""Exercise installed-vertical RCC admission without downloads or host mutation."""

import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("status", [0, 124])
def test_supervised_rcc_retains_diagnostics_before_reporting_result(tmp_path, status):
    path = Path(__file__).with_name("prepare_internal_child_real_vertical_rcc.py")
    spec = importlib.util.spec_from_file_location("vertical_preparation", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    home, temporary = tmp_path / "robocorp-home", tmp_path / "tmp"
    home.mkdir()
    temporary.mkdir()

    def supervised(*args, **kwargs):
        return status, b"owned RCC stdout", b"owned RCC stderr"

    def run():
        return module._run_supervised(
            supervised,
            ["rcc", "env", "acquire"],
            {"ROBOCORP_HOME": str(home), "TMPDIR": str(temporary)},
            "acquire",
            120,
            10803773440,
        )

    if status:
        with pytest.raises(RuntimeError, match="status 124"):
            run()
    else:
        assert run() == b"owned RCC stdout"
    assert (tmp_path / "rcc-acquire.stdout.log").read_bytes() == b"owned RCC stdout"
    assert (tmp_path / "rcc-acquire.stderr.log").read_bytes() == b"owned RCC stderr"


@pytest.mark.skipif(sys.platform != "linux", reason="Linux installed vertical shell")
@pytest.mark.parametrize(
    "existing",
    ["absent", "matching", "different", "symlink", "directory", "not-executable"],
)
def test_vertical_preserves_and_verifies_existing_rcc(tmp_path, existing):
    root = Path(__file__).parents[2]
    script = (root / "developer/tests/run_internal_child_vertical_ci.sh").read_text()
    admission = script.split('runtime_rcc="$repo_root/', 1)[1]
    admission = (
        'runtime_rcc="$repo_root/'
        + admission.split('\ncd "$repo_root/action_server"', 1)[0]
    )
    source = tmp_path / "pinned-rcc"
    source.write_bytes(b"exact pinned executable fixture")
    source.chmod(0o700)
    target = tmp_path / "action_server/src/actions/server/bin/rcc-18.19.3"
    target.parent.mkdir(parents=True)
    if existing == "symlink":
        target.symlink_to(source)
    elif existing == "directory":
        target.mkdir()
    elif existing != "absent":
        target.write_bytes(
            b"wrong bytes" if existing == "different" else source.read_bytes()
        )
        target.chmod(0o600 if existing == "not-executable" else 0o700)
    before = target.lstat() if existing != "absent" else None
    environment = os.environ.copy()
    environment.update(
        repo_root=str(tmp_path),
        rcc=str(source),
        rcc_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    )
    result = subprocess.run(
        ["bash", "-e", "-u", "-o", "pipefail", "-c", admission],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert (result.returncode == 0) == (
        existing in {"absent", "matching"}
    ), result.stderr
    if before is not None:
        after = target.lstat()
        assert (after.st_ino, after.st_mode, after.st_mtime_ns, after.st_ctime_ns) == (
            before.st_ino,
            before.st_mode,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
    if existing in {"absent", "matching"}:
        assert target.read_bytes() == source.read_bytes()
