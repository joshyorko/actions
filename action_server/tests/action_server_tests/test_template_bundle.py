import hashlib
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
PACKAGER = REPO / "templates/packaging/build_embedded_bundle.py"
CONFIG = REPO / "templates/packaging/templates-prod.json"
TEMPLATES = REPO / "templates"
EMBEDDED = REPO / "action_server/src/actions/server/templates"


def _run_packager(output_dir: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(PACKAGER),
            "--config",
            str(CONFIG),
            "--template-root",
            str(TEMPLATES),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
    )


def test_template_bundle_generation_is_byte_for_byte_deterministic(tmp_path):
    assert PACKAGER.is_file(), "repository-owned template packager is missing"

    first = tmp_path / "first"
    second = tmp_path / "second"
    _run_packager(first)
    _run_packager(second)

    first_files = sorted(path.relative_to(first) for path in first.rglob("*"))
    second_files = sorted(path.relative_to(second) for path in second.rglob("*"))
    assert first_files == second_files
    assert first_files
    assert all(
        (first / relative).read_bytes() == (second / relative).read_bytes()
        for relative in first_files
        if (first / relative).is_file()
    )


def test_embedded_metadata_covers_all_production_templates():
    assert (EMBEDDED / "action-templates.zip").is_file()
    metadata = yaml.safe_load((EMBEDDED / "action-templates.yaml").read_text())
    expected = {"advanced", "basic", "minimal", "workflow-producer-consumer"}
    assert {
        template["id"] for template in json.loads(CONFIG.read_text())["templates"]
    } == expected
    assert set(metadata["templates"]) == expected


def test_embedded_templates_are_available_without_network_transport(
    monkeypatch, tmp_path
):
    from actions.server import _new_project_helpers as helpers

    cache = tmp_path / "action-templates"
    monkeypatch.setattr(helpers, "_get_action_templates_dir_path", lambda: cache)

    helpers._ensure_latest_templates()

    metadata = helpers._get_local_templates_metadata()
    assert metadata is not None
    assert {template.name for template in metadata.templates} == {
        "advanced",
        "basic",
        "minimal",
        "workflow-producer-consumer",
    }
    assert (cache / "minimal.zip").is_file()

    (cache / "minimal.zip").write_bytes(b"tampered")
    helpers._ensure_latest_templates()
    with zipfile.ZipFile(cache / "minimal.zip") as archive:
        assert "package.yaml" in archive.namelist()

    embedded_metadata, embedded_bundle = helpers._embedded_assets()
    assert not helpers._cache_is_valid(
        cache,
        helpers._get_local_templates_metadata(),
        embedded_metadata,
        embedded_bundle + b"tampered",
    )


def test_symlinked_template_cache_is_reseeded_without_writing_target(
    monkeypatch, tmp_path
):
    from actions.server import _new_project_helpers as helpers

    target = tmp_path / "target"
    target.mkdir()
    cache = tmp_path / "action-templates"
    cache.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(helpers, "_get_action_templates_dir_path", lambda: cache)

    helpers._ensure_latest_templates()

    assert cache.is_dir()
    assert not cache.is_symlink()
    assert not (target / "minimal.zip").exists()
    assert (cache / "minimal.zip").is_file()


@pytest.mark.parametrize("templates", [[], None])
def test_malformed_template_metadata_is_invalid_without_raising(templates):
    from actions.server import _new_project_helpers as helpers

    metadata = yaml.safe_dump({"hash": "hash", "templates": templates})

    assert helpers._parse_templates_metadata(metadata) is None


def test_invalid_template_archive_never_writes_outside_destination(tmp_path):
    from actions.server import _new_project_helpers as helpers

    cache = tmp_path / "cache"
    cache.mkdir()
    archive = cache / "minimal.zip"
    with zipfile.ZipFile(archive, "w") as writer:
        writer.writestr("../outside.py", "print('escape')")

    destination = tmp_path / "project"
    with pytest.raises((ValueError, RuntimeError)):
        with mock.patch.object(
            helpers, "_get_action_templates_dir_path", return_value=cache
        ):
            helpers._unpack_template("minimal", destination)

    assert not (tmp_path / "outside.py").exists()


def test_duplicate_bundle_member_is_rejected(tmp_path):
    from actions.server import _new_project_helpers as helpers

    metadata, embedded_bundle = helpers._embedded_assets()
    duplicate_bundle = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(embedded_bundle)) as source, zipfile.ZipFile(
        duplicate_bundle, "w"
    ) as destination:
        for member in source.infolist():
            destination.writestr(member, source.read(member))
        with pytest.warns(UserWarning, match="Duplicate name"):
            destination.writestr("minimal.zip", source.read("minimal.zip"))

    bundle = duplicate_bundle.getvalue()
    duplicate_metadata = metadata.model_copy(
        update={"hash": hashlib.sha256(bundle).hexdigest()}
    )
    assert not helpers._install_bundle(tmp_path, duplicate_metadata, bundle)
