"""Portable current-source reproduction only; no product or public acquisition."""
import hashlib
import subprocess
from pathlib import Path
import pytest
import sys
sys.path.insert(0, "/workspace/engineering/pr305/action_server/tests")
from action_server_tests.mcp import test_canvas_runtime_admission as admission
from action_server_tests.mcp import test_mcp_apps_authoring as bridge

@pytest.mark.parametrize("member", ["actions", "actions.mcp", "actions.mcp._metadata"])
@pytest.mark.parametrize("poison", [None, "member", "version", "ownership", "prefix"])
def test_current_real_fixture_with_crlf_working_representation(tmp_path, monkeypatch, member, poison):
    repository = Path(bridge.__file__).resolve().parents[4]
    path = repository / "actions/src" / member.replace(".", "/")
    path = path.with_suffix(".py") if member.endswith("_metadata") else path / "__init__.py"
    canonical = subprocess.check_output(["git", "show", "HEAD:" + path.relative_to(repository).as_posix()], cwd=repository)
    assert hashlib.sha256(canonical).hexdigest() == bridge.PUBLISHED_CORE_MODULE_SHA256[member]
    crlf = canonical.replace(b"\n", b"\r\n")
    assert hashlib.sha256(crlf).hexdigest() != bridge.PUBLISHED_CORE_MODULE_SHA256[member]
    original = Path.read_bytes
    def working_representation(self):
        return crlf if self == path else original(self)
    monkeypatch.setattr(Path, "read_bytes", working_representation)
    assert b"\r\n" in path.read_bytes()
    admission.test_public_probe_admits_exact_sample_and_rejects_boundary_poisons(tmp_path, poison)
