"""Private controlled-fixture deterministic compiler proposal contract tests."""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import os
import stat
import uuid
import zipfile

import pytest

from actions.server.deployments import source_read, source_staging
from actions.server.deployments.canonical import canonicalize_json
from actions.server.deployments.ids import CapabilityId, PackageId
from actions.server.deployments.source_manifest import SuppliedSourceEntry

pytestmark = pytest.mark.skipif(
    os.name != "posix", reason="Linux source staging fixture"
)

PACKAGE_ID = PackageId.model_validate(
    str(uuid.UUID("12345678-1234-5678-1234-567812345678"))
)
OTHER_PACKAGE_ID = PackageId.model_validate(
    str(uuid.UUID("87654321-4321-8765-4321-876543218765"))
)
CAPABILITY_ID = CapabilityId.model_validate("query")
SPEC_DIGEST = "sha256:" + "a" * 64
ARTIFACT_DIGEST = "sha256:" + "b" * 64
SOURCE_NAMES = ("action.py", "package.yaml")
PROTECTED_NAMES = ("package.yaml",)
SOURCE_CONTENTS = {
    "package.yaml": b"spec: v2\nname: controlled-fixture\n",
    "action.py": b"def query(value: str) -> str:\n    return value\n",
}


def compiler_api():
    module_name = "actions.server.deployments.package_compiler"
    assert (
        importlib.util.find_spec(module_name) is not None
    ), "controlled fixture compiler proposal API is absent"
    return importlib.import_module(module_name)


def canonical_object(value):
    return canonicalize_json(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )


def fixture_inputs(
    tmp_path, *, contents=None, options=None, input_schema=None, action_path="action.py"
):
    api = compiler_api()
    content_by_name = dict(SOURCE_CONTENTS if contents is None else contents)
    source_names = tuple(sorted(content_by_name, key=lambda path: path.encode("utf-8")))
    protected_names = ("package.yaml",)
    source_root = tmp_path / "source"
    stage_root = tmp_path / "staged"
    source_root.mkdir(parents=True)
    stage_root.mkdir(mode=0o700, parents=True)
    for name, content in content_by_name.items():
        target = source_root / name
        target.write_bytes(content)
        target.chmod(0o644)
    root_fd = os.open(source_root, os.O_RDONLY | os.O_DIRECTORY)
    stage_fd = os.open(stage_root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        source_entries = tuple(
            SuppliedSourceEntry(name, "file", content_by_name[name], 0o644)
            for name in source_names
        )
        staged = source_staging.stage_selected_files(
            root_fd,
            stage_fd,
            source_names,
            protected_input_names=protected_names,
        )
        measured = source_read.read_selected_files(
            stage_fd,
            source_names,
            protected_input_names=protected_names,
        )
        assert staged.inventory == measured.inventory
        schema = {"type": "object", "properties": {"value": {"type": "string"}}}
        input_json = canonical_object(schema if input_schema is None else input_schema)
        output_json = canonical_object({"type": "string"})
        metadata_options = canonical_object({} if options is None else options)
        action = api.SuppliedActionMetadata(
            capability_id=CAPABILITY_ID,
            source_path=action_path,
            python_name="query",
            docs="Returns the supplied value.",
            input_schema_json=input_json,
            output_schema_json=output_json,
            managed_params_schema_json=canonical_object({}),
            options_json=metadata_options,
        )
        declared_action = api.DeclaredAction(
            capability_id=CAPABILITY_ID,
            source_path=action_path,
            python_name="query",
        )
        return {
            "api": api,
            "measured": measured,
            "source_entries": source_entries,
            "source_names": source_names,
            "protected_names": protected_names,
            "declared_actions": (declared_action,),
            "supplied_actions": (action,),
            "root_fd": root_fd,
            "stage_fd": stage_fd,
            "package_id": PACKAGE_ID,
            "rcc": api.SuppliedRccIdentity(SPEC_DIGEST, ARTIFACT_DIGEST),
        }
    except BaseException:
        os.close(stage_fd)
        os.close(root_fd)
        raise


def compile_fixture(inputs, **overrides):
    values = {
        "package_id": inputs["package_id"],
        "measured": inputs["measured"],
        "declared_paths": inputs["source_names"],
        "protected_paths": inputs["protected_names"],
        "source_entries": inputs["source_entries"],
        "declared_actions": inputs["declared_actions"],
        "supplied_actions": inputs["supplied_actions"],
        "rcc": inputs["rcc"],
    }
    values.update(overrides)
    return inputs["api"].compile_controlled_fixture(**values)


def test_compile_is_byte_deterministic_over_fixture_order_and_has_fixed_zip_profile(
    tmp_path,
):
    inputs = fixture_inputs(tmp_path)
    try:
        first = compile_fixture(inputs)
        second = compile_fixture(
            inputs,
            source_entries=tuple(reversed(inputs["source_entries"])),
            declared_paths=tuple(reversed(SOURCE_NAMES)),
        )
        assert first.source_archive == second.source_archive
        assert first.capability_manifest == second.capability_manifest
        assert first.runtime_plans == second.runtime_plans
        assert first.revision_preimage == second.revision_preimage
        assert first.source_digest == second.source_digest
        assert first.capability_digest == second.capability_digest
        assert first.plan_digests == second.plan_digests
        assert first.revision_digest == second.revision_digest
        assert first.inspection_status == "not_run"
        assert first.supplied_rcc_artifact_digest == ARTIFACT_DIGEST
        assert (
            first.source_digest
            == "sha256:" + hashlib.sha256(first.source_archive).hexdigest()
        )
        capability = json.loads(first.capability_manifest)
        plan = json.loads(first.runtime_plans[0])
        revision = json.loads(first.revision_preimage)
        assert capability["domain"] == "actions-controlled-capabilities"
        assert capability["version"] == 1
        assert plan["domain"] == "actions-controlled-rcc-plan"
        assert plan["version"] == 1
        assert plan["specification_digest"] == SPEC_DIGEST
        assert revision["domain"] == "actions-controlled-package-revision"
        assert revision["version"] == 1
        assert revision["source_artifact_digest"] == first.source_digest
        assert revision["capability_manifest_digest"] == first.capability_digest
        assert revision["runtime_plan_digests"] == [str(first.plan_digests[0].root)]
        assert (
            str(first.revision_digest.root)
            == "sha256:" + hashlib.sha256(first.revision_preimage).hexdigest()
        )
        with zipfile.ZipFile(__import__("io").BytesIO(first.source_archive)) as archive:
            assert archive.namelist() == ["action.py", "package.yaml"]
            assert archive.comment == b""
            for item in archive.infolist():
                assert item.date_time == (1980, 1, 1, 0, 0, 0)
                assert item.create_system == 3
                assert item.compress_type == zipfile.ZIP_STORED
                assert item.extra == b""
                assert item.comment == b""
                assert stat.S_IFMT(item.external_attr >> 16) == stat.S_IFREG
                assert stat.S_IMODE(item.external_attr >> 16) == 0o644
                assert archive.read(item.filename) == SOURCE_CONTENTS[item.filename]
    finally:
        os.close(inputs["stage_fd"])
        os.close(inputs["root_fd"])


def test_source_metadata_specification_and_logical_package_change_separate_identities(
    tmp_path,
):
    baseline_inputs = fixture_inputs(tmp_path / "baseline")
    source_inputs = fixture_inputs(
        tmp_path / "changed-source",
        contents={
            **SOURCE_CONTENTS,
            "action.py": b"def query(value): return value + '!'\n",
        },
    )
    metadata_inputs = fixture_inputs(
        tmp_path / "changed-schema",
        input_schema={"type": "object", "properties": {"value": {"type": "integer"}}},
    )
    try:
        baseline = compile_fixture(baseline_inputs)
        source_changed = compile_fixture(source_inputs)
        metadata_changed = compile_fixture(metadata_inputs)
        assert source_changed.source_digest != baseline.source_digest
        assert source_changed.capability_digest == baseline.capability_digest
        assert source_changed.plan_digests == baseline.plan_digests
        assert source_changed.revision_digest != baseline.revision_digest
        assert metadata_changed.source_digest == baseline.source_digest
        assert metadata_changed.capability_digest != baseline.capability_digest
        assert metadata_changed.plan_digests == baseline.plan_digests
        assert metadata_changed.revision_digest != baseline.revision_digest

        spec_changed = compile_fixture(
            baseline_inputs,
            rcc=baseline_inputs["api"].SuppliedRccIdentity(
                "sha256:" + "c" * 64, ARTIFACT_DIGEST
            ),
        )
        package_changed = compile_fixture(baseline_inputs, package_id=OTHER_PACKAGE_ID)
        artifact_only_changed = compile_fixture(
            baseline_inputs,
            rcc=baseline_inputs["api"].SuppliedRccIdentity(
                SPEC_DIGEST, "sha256:" + "d" * 64
            ),
        )
        assert spec_changed.source_digest == baseline.source_digest
        assert spec_changed.capability_digest == baseline.capability_digest
        assert spec_changed.plan_digests != baseline.plan_digests
        assert spec_changed.revision_digest != baseline.revision_digest
        assert package_changed.source_digest == baseline.source_digest
        assert package_changed.capability_digest == baseline.capability_digest
        assert package_changed.plan_digests == baseline.plan_digests
        assert package_changed.revision_digest != baseline.revision_digest
        assert (
            artifact_only_changed.supplied_rcc_artifact_digest
            != baseline.supplied_rcc_artifact_digest
        )
        assert artifact_only_changed.revision_digest == baseline.revision_digest
    finally:
        for inputs in (baseline_inputs, source_inputs, metadata_inputs):
            os.close(inputs["stage_fd"])
            os.close(inputs["root_fd"])


def test_zip_envelope_preflight_counts_utf8_filename_bytes(tmp_path):
    inputs = fixture_inputs(
        tmp_path,
        contents={
            "package.yaml": b"spec: v2\nname: controlled-fixture\n",
            "é.py": b"def query(value): return value\n",
        },
        action_path="é.py",
    )
    try:
        result = compile_fixture(inputs)
        expected_size = 22
        for entry in inputs["source_entries"]:
            assert isinstance(entry.content, bytes)
            expected_size += (
                len(entry.content) + 30 + 46 + 2 * len(entry.path.encode("utf-8"))
            )
        assert len("é.py") < len("é.py".encode("utf-8"))
        assert len(result.source_archive) == expected_size
        assert (
            inputs["api"]._zip_stored_archive_size(inputs["measured"].inventory)
            == expected_size
        )
    finally:
        os.close(inputs["stage_fd"])
        os.close(inputs["root_fd"])


def test_zip_envelope_exact_limit_passes_and_one_byte_over_rejects_prebuild(
    tmp_path, monkeypatch
):
    inputs = fixture_inputs(tmp_path)
    try:
        api = inputs["api"]
        baseline = compile_fixture(inputs)
        exact_size = len(baseline.source_archive)
        monkeypatch.setattr(api, "MAX_CONTROLLED_ARCHIVE_BYTES", exact_size)
        exact = compile_fixture(inputs)
        assert exact.source_archive == baseline.source_archive

        monkeypatch.setattr(api, "MAX_CONTROLLED_ARCHIVE_BYTES", exact_size - 1)

        def unexpected_archive_build(*_args, **_kwargs):
            raise AssertionError("archive allocation started before size rejection")

        monkeypatch.setattr(api, "_make_source_archive", unexpected_archive_build)
        with pytest.raises(ValueError, match="archive exceeds its byte bound"):
            compile_fixture(inputs)
    finally:
        os.close(inputs["stage_fd"])
        os.close(inputs["root_fd"])


@pytest.mark.parametrize(
    "change,match",
    [
        ("missing_path", "complete declaration"),
        ("unlisted_path", "complete declaration"),
        ("escaped_path", "source path"),
        ("extra_directory", "entries must be files"),
        ("duplicate_path", "duplicate path"),
        ("changed_bytes", "measurement differs"),
        ("noncanonical_options", "canonical JSON"),
        ("unknown_option", "unsupported field"),
        ("bad_spec_digest", "specification digest"),
        ("wrong_entrypoint", "match"),
        ("noncanonical_schema", "canonical JSON"),
    ],
)
def test_invalid_source_or_supplied_metadata_fails_closed(tmp_path, change, match):
    inputs = fixture_inputs(tmp_path)
    try:
        overrides = {}
        if change == "missing_path":
            overrides["declared_paths"] = ("package.yaml",)
        elif change == "unlisted_path":
            overrides["declared_paths"] = (*SOURCE_NAMES, "extra.py")
        elif change == "escaped_path":
            overrides["declared_paths"] = ("../action.py", "package.yaml")
        elif change == "extra_directory":
            overrides["source_entries"] = (
                *inputs["source_entries"],
                SuppliedSourceEntry("extra", "directory"),
            )
        elif change == "duplicate_path":
            overrides["source_entries"] = (
                *inputs["source_entries"],
                inputs["source_entries"][0],
            )
        elif change == "changed_bytes":
            overrides["source_entries"] = tuple(
                SuppliedSourceEntry(
                    entry.path,
                    entry.kind,
                    b"changed" if entry.path == "action.py" else entry.content,
                    entry.mode,
                )
                for entry in inputs["source_entries"]
            )
        elif change == "noncanonical_options":
            action = inputs["supplied_actions"][0]
            overrides["supplied_actions"] = (
                inputs["api"].SuppliedActionMetadata(
                    **{
                        **action.__dict__,
                        "options_json": b'{ "is_consequential": false }',
                    }
                ),
            )
        elif change == "unknown_option":
            action = inputs["supplied_actions"][0]
            overrides["supplied_actions"] = (
                inputs["api"].SuppliedActionMetadata(
                    **{
                        **action.__dict__,
                        "options_json": canonical_object({"future_mode": True}),
                    }
                ),
            )
        elif change == "bad_spec_digest":
            overrides["rcc"] = inputs["api"].SuppliedRccIdentity("artifact-hash")
        elif change == "wrong_entrypoint":
            action = inputs["supplied_actions"][0]
            overrides["supplied_actions"] = (
                inputs["api"].SuppliedActionMetadata(
                    **{**action.__dict__, "python_name": "other"}
                ),
            )
        elif change == "noncanonical_schema":
            action = inputs["supplied_actions"][0]
            overrides["supplied_actions"] = (
                inputs["api"].SuppliedActionMetadata(
                    **{
                        **action.__dict__,
                        "input_schema_json": b'{ "type": "object" }',
                    }
                ),
            )
        with pytest.raises(ValueError, match=match):
            compile_fixture(inputs, **overrides)
    finally:
        os.close(inputs["stage_fd"])
        os.close(inputs["root_fd"])
