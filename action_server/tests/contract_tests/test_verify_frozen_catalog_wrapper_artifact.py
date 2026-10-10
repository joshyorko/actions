import hashlib
import importlib.util
import json
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

SCRIPT = (
    Path(__file__).parents[2] / "scripts" / "verify_frozen_catalog_wrapper_artifact.py"
)
SPEC = importlib.util.spec_from_file_location(
    "verify_frozen_catalog_wrapper_artifact", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)
REPOSITORY_ROOT = Path(__file__).parents[3]


def _write_archive(
    path: Path,
    *,
    data: bytes = b"wrapper executable fixture",
    name: str = "action-server",
    mode: int = stat.S_IFREG | 0o755,
    extra_member: bool = False,
) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        member = zipfile.ZipInfo(name)
        member.create_system = 3
        member.external_attr = mode << 16
        archive.writestr(member, data)
        if extra_member:
            archive.writestr("unexpected", b"extra")


def _pin_fixture(monkeypatch, archive: Path, data: bytes) -> None:
    member = zipfile.ZipFile(archive).infolist()[0]
    monkeypatch.setattr(VERIFIER, "EXPECTED_ARCHIVE_SIZE", archive.stat().st_size)
    monkeypatch.setattr(
        VERIFIER,
        "EXPECTED_ARCHIVE_SHA256",
        hashlib.sha256(archive.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(VERIFIER, "EXPECTED_BINARY_SIZE", len(data))
    monkeypatch.setattr(
        VERIFIER, "EXPECTED_BINARY_COMPRESSED_SIZE", member.compress_size
    )
    monkeypatch.setattr(
        VERIFIER, "EXPECTED_BINARY_SHA256", hashlib.sha256(data).hexdigest()
    )


def _write_source_fixture(root: Path, monkeypatch) -> None:
    for relative_path in VERIFIER.WRAPPER_SOURCE_FILES:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"fixture:{relative_path}\n", encoding="utf-8")
    monkeypatch.setattr(
        VERIFIER,
        "EXPECTED_WRAPPER_SOURCE_SHA256",
        VERIFIER._wrapper_source_sha256(root),
    )


def test_wrapper_verifier_extracts_one_exact_executable_member(tmp_path, monkeypatch):
    archive = tmp_path / "wrapper.zip"
    data = b"wrapper executable fixture"
    _write_archive(archive, data=data)
    _pin_fixture(monkeypatch, archive, data)
    source_root = tmp_path / "source"
    _write_source_fixture(source_root, monkeypatch)
    destination = tmp_path / "unpacked"
    output = tmp_path / "receipt.json"

    target = VERIFIER.verify(archive, destination, output, source_root)

    assert target == destination / "action-server"
    assert target.read_bytes() == data
    assert stat.S_IMODE(target.stat().st_mode) == 0o755
    record = json.loads(output.read_text(encoding="utf-8"))
    assert record["archive_and_member_verified"] is True
    assert record["binary_sha256"] == hashlib.sha256(data).hexdigest()
    assert record["frozen_binary_sha256"] == VERIFIER.EXPECTED_FROZEN_BINARY_SHA256
    assert (
        record["wrapper_source_sha256_checked"]
        == VERIFIER.EXPECTED_WRAPPER_SOURCE_SHA256
    )


def test_generated_wrapper_workflow_invokes_verifier_from_repository_root():
    workflow_path = (
        REPOSITORY_ROOT
        / ".github/workflows/actions_runtime_frozen_catalog_rollback.yml"
    )
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    wrapper_job = workflow["jobs"]["go_wrapper"]
    verifier_step = next(
        step for step in wrapper_job["steps"] if step.get("id") == "wrapper_artifact"
    )
    run_script = verifier_step["run"]
    relative_script = "action_server/scripts/verify_frozen_catalog_wrapper_artifact.py"

    assert 'cd "$GITHUB_WORKSPACE"' in run_script
    assert f"python {relative_script}" in run_script
    assert "--source-root action_server" in run_script
    verifier_script = REPOSITORY_ROOT / relative_script
    assert verifier_script.is_file()
    result = subprocess.run(
        [sys.executable, str(verifier_script), "--help"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--source-root SOURCE_ROOT" in result.stdout


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"name": "../action-server"}, "member identity is invalid"),
        (
            {"name": "action-server", "mode": stat.S_IFLNK | 0o777},
            "member identity is invalid",
        ),
        (
            {"name": "action-server", "mode": stat.S_IFREG | 0o700},
            "member identity is invalid",
        ),
        ({"name": "action-server", "extra_member": True}, "exactly one member"),
    ],
)
def test_wrapper_verifier_rejects_unsafe_or_unexpected_zip_members(
    tmp_path, monkeypatch, kwargs, match
):
    archive = tmp_path / "wrapper.zip"
    data = b"wrapper executable fixture"
    _write_archive(archive, data=data, **kwargs)
    _pin_fixture(monkeypatch, archive, data)
    source_root = tmp_path / "source"
    _write_source_fixture(source_root, monkeypatch)

    with pytest.raises(ValueError, match=match):
        VERIFIER.verify(
            archive, tmp_path / "unpacked", tmp_path / "receipt.json", source_root
        )


def test_wrapper_verifier_rejects_wrong_binary_digest(tmp_path, monkeypatch):
    archive = tmp_path / "wrapper.zip"
    data = b"wrapper executable fixture"
    _write_archive(archive, data=data)
    _pin_fixture(monkeypatch, archive, data)
    source_root = tmp_path / "source"
    _write_source_fixture(source_root, monkeypatch)
    monkeypatch.setattr(VERIFIER, "EXPECTED_BINARY_SHA256", "0" * 64)

    with pytest.raises(ValueError, match="bytes do not match candidate"):
        VERIFIER.verify(
            archive, tmp_path / "unpacked", tmp_path / "receipt.json", source_root
        )


def test_wrapper_verifier_rejects_existing_destination(tmp_path, monkeypatch):
    archive = tmp_path / "wrapper.zip"
    data = b"wrapper executable fixture"
    _write_archive(archive, data=data)
    _pin_fixture(monkeypatch, archive, data)
    source_root = tmp_path / "source"
    _write_source_fixture(source_root, monkeypatch)
    destination = tmp_path / "unpacked"
    destination.mkdir()

    with pytest.raises(ValueError, match="destination already exists"):
        VERIFIER.verify(archive, destination, tmp_path / "receipt.json", source_root)


def test_wrapper_verifier_rejects_changed_wrapper_source_before_extraction(
    tmp_path, monkeypatch
):
    archive = tmp_path / "wrapper.zip"
    data = b"wrapper executable fixture"
    _write_archive(archive, data=data)
    _pin_fixture(monkeypatch, archive, data)
    source_root = tmp_path / "source"
    _write_source_fixture(source_root, monkeypatch)
    (source_root / "go-wrapper/main.go").write_text("changed\n", encoding="utf-8")
    destination = tmp_path / "unpacked"

    with pytest.raises(ValueError, match="source digest does not match"):
        VERIFIER.verify(archive, destination, tmp_path / "receipt.json", source_root)
    assert not destination.exists()
