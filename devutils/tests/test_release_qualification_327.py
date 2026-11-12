"""Release artifact admission negatives; no GitHub or publisher writes."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def publisher(monkeypatch):
    scripts = Path(__file__).resolve().parents[2] / "action_server" / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "release_qualification_327", scripts / "runtime_release_button.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "mutation", ["missing", "wrong-name", "duplicate", "expired", "empty", "oversize"]
)
def test_unadmitted_artifact_never_downloads(
    publisher, monkeypatch, tmp_path, mutation
):
    artifact = {"id": 9, "name": "reviewed", "expired": False, "size_in_bytes": 12}
    artifacts = [artifact]
    if mutation == "missing":
        artifacts = []
    elif mutation == "wrong-name":
        artifact["name"] = "lookalike"
    elif mutation == "duplicate":
        artifacts.append(dict(artifact))
    elif mutation == "expired":
        artifact["expired"] = True
    elif mutation == "empty":
        artifact["size_in_bytes"] = 0
    else:
        artifact["size_in_bytes"] = 2 * 1024**3 + 1

    def list_artifacts(endpoint, key):
        assert endpoint == "repos/joshyorko/actions/actions/runs/123/artifacts"
        assert key == "artifacts"
        return artifacts

    def forbidden_download(*args, **kwargs):
        pytest.fail("Rejected metadata must not start an archive download")

    monkeypatch.setattr(publisher, "pages", list_artifacts)
    monkeypatch.setattr(publisher.subprocess, "run", forbidden_download)
    with pytest.raises(publisher.ReleaseError):
        publisher.download({"id": 123}, "reviewed", tmp_path / "bundle")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("mutation", ["truncated", "command-failed"])
def test_incomplete_download_never_extracts(publisher, monkeypatch, tmp_path, mutation):
    metadata = {"id": 9, "name": "reviewed", "expired": False, "size_in_bytes": 12}
    monkeypatch.setattr(publisher, "pages", lambda *args: [metadata])

    def download(command, *, stdout, stderr):
        assert command == [
            "gh",
            "api",
            "repos/joshyorko/actions/actions/artifacts/9/zip",
        ]
        stdout.write(b"partial")
        return SimpleNamespace(returncode=1 if mutation == "command-failed" else 0)

    def forbidden_extract(*args):
        pytest.fail("Incomplete archive must not be extracted")

    monkeypatch.setattr(publisher.subprocess, "run", download)
    monkeypatch.setattr(publisher, "extract_zip", forbidden_extract)
    message = "download failed" if mutation == "command-failed" else "size mismatch"
    with pytest.raises(publisher.ReleaseError, match=message):
        publisher.download({"id": 123}, "reviewed", tmp_path / "bundle")
    assert not (tmp_path / "bundle").exists()
    assert (tmp_path / "bundle.zip").read_bytes() == b"partial"
