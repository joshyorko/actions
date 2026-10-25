"""Contract tests for immutable package-revision compiler inputs."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from actions.server.deployments import canonical, source_manifest
from actions.server.deployments.package_revision_compiler import (
    PackageCompilationPolicy,
    PinnedRccPackageBuildExecutor,
    PreparedRccEnvironment,
    RccBuildIdentity,
    TrustedDeveloperExecutionAdmission,
    _extract_json_object,
    _parse_rcc_exec_result,
    compile_generated_python_action,
    load_prepared_rcc_environment,
    snapshot_source_entries,
    stage_source_snapshot,
    verify_compilation_outcome,
    verify_compiled_package_revision,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_SCHEMA = REPOSITORY_ROOT / "docs/design/package-revision-v1.schema.json"


def _entry(path: str, content: bytes) -> source_manifest.SuppliedSourceEntry:
    return source_manifest.SuppliedSourceEntry(path, "file", content, 0o644)


def _canonical_digest(value: object) -> str:
    payload = canonical.canonicalize_json(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    )
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _generated_action_entries(action_source: bytes | None = None) -> list:
    if action_source is None:
        action_source = (
            b"from actions import action\n\n"
            b"@action\n"
            b"def generated_echo(value: str) -> str:\n"
            b"    return value\n"
        )
    return [
        _entry(
            "package.yaml",
            b"name: generated-fixture\n"
            b"description: One synthetic generated Action\n"
            b"dependencies:\n"
            b"  conda-forge:\n"
            b"    - python=3.12\n"
            b"  pypi:\n"
            b"    - actions-core=1.0.2\n",
        ),
        _entry("generated_actions.py", action_source),
        _entry(
            "tests/test_generated_action.py",
            b"import unittest\n"
            b"from generated_actions import generated_echo\n\n"
            b"class GeneratedActionTest(unittest.TestCase):\n"
            b"    def test_echo(self):\n"
            b"        self.assertEqual(generated_echo(value='synthetic'), 'synthetic')\n",
        ),
    ]


class _FakeCompilerExecutor:
    rcc_version = "v18.19.3"

    def __init__(self, fail_phase: str | None = None) -> None:
        self.fail_phase = fail_phase
        self.calls: list[str] = []

    def _fail_if(self, phase: str) -> None:
        self.calls.append(phase)
        if self.fail_phase == phase:
            raise RuntimeError(f"synthetic {phase} failure at /private/worktree")

    def build_environment(
        self, package_yaml: Path, workspace: Path
    ) -> RccBuildIdentity:
        self._fail_if("build")
        return RccBuildIdentity(
            specification_digest="sha256:" + "a" * 64,
            artifact_digest="sha256:" + "b" * 64,
        )

    def import_action(
        self, build: RccBuildIdentity, package_dir: Path, workspace: Path
    ) -> dict:
        self._fail_if("import")
        return {
            "actions_spec_version": "v2",
            "actions": [
                {
                    "name": "generated_echo",
                    "file": str(package_dir / "generated_actions.py"),
                    "input_schema": {
                        "type": "object",
                        "properties": {"value": {"type": "string"}},
                        "required": ["value"],
                    },
                    "output_schema": {"type": "string"},
                }
            ],
        }

    def run_tests(
        self, build: RccBuildIdentity, package_dir: Path, workspace: Path
    ) -> None:
        self._fail_if("test")


def _compilation_policy() -> PackageCompilationPolicy:
    return PackageCompilationPolicy(
        package_id="generated-fixture",
        logical_name="Generated fixture",
        actions_runtime_range=">=1.0.3,<2.0.0",
        actions_core_range=">=1.0.2,<2.0.0",
    )


def _compile_with_fake(
    *, fail_phase: str | None = None, action_source: bytes | None = None
):
    executor = _FakeCompilerExecutor(fail_phase)
    outcome = compile_generated_python_action(
        _generated_action_entries(action_source),
        _compilation_policy(),
        protected_input_names=["package.yaml"],
        admission=TrustedDeveloperExecutionAdmission.TRUSTED,
        executor=executor,
    )
    return outcome, executor


def test_source_snapshot_digest_is_order_independent_and_idempotent() -> None:
    entries = [
        _entry("action.py", b"def generated_action():\n    return 'synthetic'\n"),
        _entry("package.yaml", b"spec-version: v2\n"),
    ]

    first = snapshot_source_entries(entries, protected_input_names=["package.yaml"])
    replay = snapshot_source_entries(
        reversed(entries), protected_input_names=["package.yaml"]
    )

    assert first.inventory.canonical_json == replay.inventory.canonical_json
    assert first.digest == replay.digest
    assert first.digest == (
        "sha256:" + hashlib.sha256(first.inventory.canonical_json).hexdigest()
    )
    assert [(file.path, file.mode, file.content) for file in first.files] == [
        ("action.py", 0o644, b"def generated_action():\n    return 'synthetic'\n"),
        ("package.yaml", 0o644, b"spec-version: v2\n"),
    ]


def test_source_snapshot_digest_changes_when_selected_bytes_change() -> None:
    first = snapshot_source_entries(
        [_entry("action.py", b"def generated_action(): return 'one'\n")],
        protected_input_names=[],
    )
    changed = snapshot_source_entries(
        [_entry("action.py", b"def generated_action(): return 'two'\n")],
        protected_input_names=[],
    )

    assert first.digest != changed.digest


@pytest.mark.parametrize(
    "path", ["../action.py", "/action.py", "nested\\action.py", "a//action.py"]
)
def test_source_snapshot_rejects_traversal_and_invalid_paths(path: str) -> None:
    with pytest.raises(ValueError):
        snapshot_source_entries(
            [_entry(path, b"def generated_action(): pass\n")],
            protected_input_names=[],
        )


def test_source_snapshot_requires_protected_inputs_to_be_selected() -> None:
    with pytest.raises(ValueError, match="protected input"):
        snapshot_source_entries(
            [_entry("action.py", b"def generated_action(): pass\n")],
            protected_input_names=["package.yaml"],
        )


def test_source_snapshot_bounds_protected_input_names() -> None:
    with pytest.raises(
        ValueError, match="protected input names exceed the entry limit"
    ):
        snapshot_source_entries(
            [_entry("action.py", b"def generated_action(): pass\n")],
            protected_input_names=["action.py"] * 33,
        )


def test_compiler_emits_schema_conformant_immutable_package_and_plan() -> None:
    outcome, _executor = _compile_with_fake()

    assert outcome.compiled_package is not None
    manifest = json.loads(outcome.compiled_package.manifest_json)
    Draft202012Validator(json.loads(PACKAGE_SCHEMA.read_text())).validate(manifest)
    assert manifest["schemaVersion"] == "actions.package-revision/v1-draft"
    assert manifest["capabilities"][0]["kind"] == "action"
    assert manifest["capabilities"][0]["id"] == "action.generated_echo"
    assert manifest["capabilities"][0]["mode"] == "none"
    assert manifest["capabilities"][0]["allowOutputs"] is False
    assert manifest["runtimePlans"][0]["runtimeKind"] == "rcc"
    assert manifest["sourceArtifact"]["mediaType"] == (
        "application/vnd.actions.package-source+zip"
    )
    compiled = outcome.compiled_package
    expected_source_artifact_digest = (
        "sha256:" + hashlib.sha256(compiled.source_archive).hexdigest()
    )
    assert compiled.source_artifact_digest == expected_source_artifact_digest
    assert manifest["sourceArtifact"]["digest"] == expected_source_artifact_digest
    assert manifest["sourceArtifact"]["byteLength"] == len(compiled.source_archive)
    assert compiled.source_inventory_digest.startswith("sha256:")
    assert (
        compiled.runtime_plan_header.plan_digest.root
        == manifest["runtimePlans"][0]["digest"]
    )
    assert b"/private/worktree" not in compiled.manifest_json
    assert (
        manifest["identity"]["compilerNormalizationVersion"]
        == "actions-foundry-normalizer/v1-draft"
    )

    runtime_plan = manifest["runtimePlans"][0]
    runtime_plan_without_digest = dict(runtime_plan)
    runtime_plan_without_digest.pop("digest")
    assert runtime_plan["digest"] == _canonical_digest(
        ["actions.runtime-plan/v1-draft", runtime_plan_without_digest]
    )
    assert json.loads(compiled.runtime_plan_payload) == runtime_plan_without_digest

    package_preimage = json.loads(compiled.manifest_json)
    package_revision_digest = package_preimage["identity"].pop("revisionDigest")
    assert package_revision_digest == _canonical_digest(
        ["actions.package-revision/v1-draft", package_preimage]
    )
    assert compiled.package_revision_id.root == package_revision_digest

    adapter_payload = json.loads(compiled.adapter_specification_payload)
    assert adapter_payload["entrypoint"] == {
        "module": "generated_actions",
        "actionName": "generated_echo",
    }
    assert runtime_plan["adapterSpecification"]["payloadDigest"] == (
        "sha256:" + hashlib.sha256(compiled.adapter_specification_payload).hexdigest()
    )
    assert json.loads(compiled.input_schema_payload)["type"] == "object"
    assert json.loads(compiled.output_schema_payload)["type"] == "string"
    assert verify_compilation_outcome(outcome) is compiled


def test_capability_execution_mode_and_output_policy_are_revision_preimage() -> None:
    outcome, _executor = _compile_with_fake()
    assert outcome.compiled_package is not None
    compiled = outcome.compiled_package
    baseline = json.loads(compiled.manifest_json)
    expected = baseline["identity"].pop("revisionDigest")
    assert expected == compiled.package_revision_id.root
    assert expected == _canonical_digest(
        ["actions.package-revision/v1-draft", baseline]
    )

    for field, replacement in (("mode", "automatic"), ("allowOutputs", True)):
        changed = json.loads(compiled.manifest_json)
        preimage = json.loads(compiled.manifest_json)
        recorded = preimage["identity"].pop("revisionDigest")
        changed["capabilities"][0][field] = replacement
        changed_preimage = json.loads(
            canonical.canonicalize_json(
                json.dumps(changed, ensure_ascii=False, separators=(",", ":")).encode()
            )
        )
        changed_digest = changed_preimage["identity"].pop("revisionDigest")
        assert recorded == expected
        assert (
            _canonical_digest(["actions.package-revision/v1-draft", changed_preimage])
            != expected
        )
        tampered = replace(
            compiled,
            manifest_json=canonical.canonicalize_json(
                json.dumps(changed, ensure_ascii=False, separators=(",", ":")).encode()
            ),
        )
        assert changed_digest == expected
        with pytest.raises(ValueError, match="integrity check failed"):
            verify_compiled_package_revision(tampered)


def test_compiled_package_verifier_rejects_source_archive_tampering() -> None:
    outcome, _executor = _compile_with_fake()
    assert outcome.compiled_package is not None

    tampered = replace(
        outcome.compiled_package,
        source_archive=outcome.compiled_package.source_archive + b"tampered",
    )
    with pytest.raises(ValueError, match="integrity check failed"):
        verify_compiled_package_revision(tampered)


def test_compiled_package_verifier_rejects_runtime_plan_payload_tampering() -> None:
    outcome, _executor = _compile_with_fake()
    assert outcome.compiled_package is not None

    tampered = replace(
        outcome.compiled_package,
        runtime_plan_payload=outcome.compiled_package.runtime_plan_payload + b" ",
    )
    with pytest.raises(ValueError, match="integrity check failed"):
        verify_compiled_package_revision(tampered)


def test_compilation_outcome_verifier_requires_all_success_phases() -> None:
    outcome, _executor = _compile_with_fake()
    assert outcome.compiled_package is not None
    incomplete = replace(
        outcome,
        receipt=replace(outcome.receipt, test_status="not-run"),
    )

    with pytest.raises(ValueError, match="all compiler phases"):
        verify_compilation_outcome(incomplete)


def test_prepared_rcc_receipt_round_trips_and_binds_exact_manifest(
    tmp_path: Path,
) -> None:
    package_yaml = _generated_action_entries()[0].content
    prepared = PreparedRccEnvironment(
        robocorp_home=tmp_path / "prepared-home",
        package_yaml_digest="sha256:" + hashlib.sha256(package_yaml).hexdigest(),
        build_identity=RccBuildIdentity(
            specification_digest="sha256:" + "a" * 64,
            artifact_digest="sha256:" + "b" * 64,
        ),
    )
    receipt_path = tmp_path / "prepared-rcc.json"
    receipt_path.write_bytes(prepared.to_receipt_bytes())

    assert load_prepared_rcc_environment(receipt_path) == prepared

    changed_yaml = tmp_path / "changed-package.yaml"
    changed_yaml.write_bytes(package_yaml + b"# changed\n")
    with pytest.raises(RuntimeError, match="manifest identity mismatch"):
        PinnedRccPackageBuildExecutor(prepared).build_environment(
            changed_yaml, tmp_path / "workspace"
        )


def test_prepared_rcc_child_environment_stays_sanitized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.invalid:8080")
    monkeypatch.setenv("RCC_ACCOUNT", "synthetic-account")
    prepared = PreparedRccEnvironment(
        robocorp_home=tmp_path / "prepared-home",
        package_yaml_digest="sha256:" + "c" * 64,
        build_identity=RccBuildIdentity(
            specification_digest="sha256:" + "a" * 64,
            artifact_digest="sha256:" + "b" * 64,
        ),
    )
    executor = PinnedRccPackageBuildExecutor(prepared)
    executor._rcc_home = prepared.robocorp_home

    child_environment = executor._child_environment(tmp_path)

    assert child_environment["RCC_NO_BUILD"] == "1"
    if sys.platform.startswith("linux"):
        child_path = child_environment["PATH"].split(os.pathsep)
        assert "/usr/sbin" in child_path
        assert "/sbin" in child_path
    assert not any("proxy" in name.casefold() for name in child_environment)
    assert not any("account" in name.casefold() for name in child_environment)


def test_compiler_outputs_are_idempotent_and_changed_source_changes_identity() -> None:
    first, _first_executor = _compile_with_fake()
    replay, _replay_executor = _compile_with_fake()
    changed, _changed_executor = _compile_with_fake(
        action_source=(
            b"from actions import action\n\n"
            b"@action\n"
            b"def generated_echo(value: str) -> str:\n"
            b"    return value + ' changed'\n"
        )
    )

    assert first.compiled_package is not None
    assert replay.compiled_package is not None
    assert changed.compiled_package is not None
    assert first.compiled_package.manifest_json == replay.compiled_package.manifest_json
    assert (
        first.compiled_package.source_archive == replay.compiled_package.source_archive
    )
    assert first.receipt.to_bytes() == replay.receipt.to_bytes()
    assert b'"sourceInventoryDigest":"sha256:' in first.receipt.to_bytes()
    assert b'"sourceArtifactDigest":"sha256:' in first.receipt.to_bytes()
    assert (
        first.compiled_package.package_revision_id
        != changed.compiled_package.package_revision_id
    )


@pytest.mark.parametrize(
    ("phase", "failure_code"),
    [
        ("build", "rcc_build_failed"),
        ("import", "action_import_failed"),
        ("test", "action_tests_failed"),
    ],
)
def test_compiler_failures_emit_deterministic_sanitized_receipts(
    phase: str, failure_code: str
) -> None:
    first, _first_executor = _compile_with_fake(fail_phase=phase)
    replay, _replay_executor = _compile_with_fake(fail_phase=phase)

    assert first.compiled_package is None
    assert first.receipt.failure_code == failure_code
    assert first.receipt.to_bytes() == replay.receipt.to_bytes()
    expected_phases = {
        "build": ("failed", "not-run", "not-run"),
        "import": ("passed", "failed", "not-run"),
        "test": ("passed", "passed", "failed"),
    }
    assert (
        first.receipt.build_status,
        first.receipt.import_status,
        first.receipt.test_status,
    ) == expected_phases[phase]
    assert b"/private/worktree" not in first.receipt.to_bytes()
    assert b"timestamp" not in first.receipt.to_bytes()


def test_compiler_requires_explicit_trusted_developer_execution_admission() -> None:
    executor = _FakeCompilerExecutor()
    outcome = compile_generated_python_action(
        _generated_action_entries(),
        _compilation_policy(),
        protected_input_names=["package.yaml"],
        admission=None,
        executor=executor,
    )

    assert outcome.compiled_package is None
    assert outcome.receipt.failure_code == "trusted_execution_not_admitted"
    assert executor.calls == []


def test_compiler_rejects_dependency_urls_before_rcc_execution() -> None:
    entries = _generated_action_entries()
    package_yaml = entries[0].content.replace(
        b"actions-core=1.0.2", b"https://example.invalid/actions-core.whl"
    )
    entries[0] = _entry("package.yaml", package_yaml)
    executor = _FakeCompilerExecutor()
    outcome = compile_generated_python_action(
        entries,
        _compilation_policy(),
        protected_input_names=["package.yaml"],
        admission=TrustedDeveloperExecutionAdmission.TRUSTED,
        executor=executor,
    )

    assert outcome.compiled_package is None
    assert outcome.receipt.failure_code == "package_input_invalid"
    assert executor.calls == []


def test_compiler_rejects_wildcard_dependency_pins_before_rcc_execution() -> None:
    entries = _generated_action_entries()
    package_yaml = entries[0].content.replace(
        b"actions-core=1.0.2", b"actions-core=1.0.*"
    )
    entries[0] = _entry("package.yaml", package_yaml)
    executor = _FakeCompilerExecutor()
    outcome = compile_generated_python_action(
        entries,
        _compilation_policy(),
        protected_input_names=["package.yaml"],
        admission=TrustedDeveloperExecutionAdmission.TRUSTED,
        executor=executor,
    )

    assert outcome.compiled_package is None
    assert outcome.receipt.failure_code == "package_input_invalid"
    assert executor.calls == []


def test_compiler_rejects_duplicate_package_yaml_keys_before_rcc_execution() -> None:
    entries = _generated_action_entries()
    entries[0] = _entry(
        "package.yaml",
        b"name: generated-fixture\n"
        b"name: overwritten-fixture\n"
        b"description: Invalid duplicate mapping key\n"
        b"dependencies: {}\n",
    )
    executor = _FakeCompilerExecutor()
    outcome = compile_generated_python_action(
        entries,
        _compilation_policy(),
        protected_input_names=["package.yaml"],
        admission=TrustedDeveloperExecutionAdmission.TRUSTED,
        executor=executor,
    )

    assert outcome.compiled_package is None
    assert outcome.receipt.failure_code == "package_input_invalid"
    assert executor.calls == []


def test_rcc_json_parser_ignores_progress_text_around_result() -> None:
    payload = {
        "specificationDigest": "sha256:" + "a" * 64,
        "artifactDigest": "sha256:" + "b" * 64,
    }
    encoded = json.dumps(payload).encode("utf-8")

    assert (
        _extract_json_object(
            b"Progress: publish started\n" + encoded + b"\nProgress: done\n",
            required_keys=("specificationDigest", "artifactDigest"),
        )
        == payload
    )


def test_rcc_exec_parser_accepts_one_result_with_nested_artifact_identity() -> None:
    payload = {
        "artifactDigest": "sha256:" + "a" * 64,
        "exitCode": 0,
        "verification": {"artifactDigest": "sha256:" + "a" * 64},
    }

    assert _parse_rcc_exec_result(json.dumps(payload).encode()) == payload


@pytest.mark.skipif(
    not os.environ.get("ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"),
    reason=(
        "set ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT to an exact-manifest "
        "trusted-host cache receipt for the pinned RCC proof"
    ),
)
def test_genuine_generated_action_rcc_build_import_and_test(tmp_path: Path) -> None:
    prepared = load_prepared_rcc_environment(
        Path(os.environ["ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"])
    )
    outcome = compile_generated_python_action(
        _generated_action_entries(),
        _compilation_policy(),
        protected_input_names=["package.yaml"],
        admission=TrustedDeveloperExecutionAdmission.TRUSTED,
        executor=PinnedRccPackageBuildExecutor(prepared),
        execution_root=tmp_path,
    )

    assert outcome.compiled_package is not None, repr(outcome.receipt)
    manifest = json.loads(outcome.compiled_package.manifest_json)
    Draft202012Validator(json.loads(PACKAGE_SCHEMA.read_text())).validate(manifest)
    assert outcome.receipt.status == "succeeded"
    assert outcome.receipt.failure_code is None
    assert verify_compilation_outcome(outcome) is outcome.compiled_package


@pytest.mark.skipif(sys.platform != "linux", reason="confined staging requires Linux")
def test_staged_source_snapshot_preserves_exact_selected_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    action_bytes = b"def generated_action():\n    return 'synthetic'\n"
    package_bytes = b"spec-version: v2\n"
    (source / "action.py").write_bytes(action_bytes)
    (source / "package.yaml").write_bytes(package_bytes)

    destination = tmp_path / "staged"
    destination.mkdir(mode=0o700)
    destination.chmod(0o700)
    source_fd = os.open(source, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    destination_fd = os.open(destination, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    try:
        snapshot = stage_source_snapshot(
            source_fd,
            destination_fd,
            [_entry("action.py", action_bytes), _entry("package.yaml", package_bytes)],
            selected_file_names=["action.py", "package.yaml"],
            protected_input_names=["package.yaml"],
        )
    finally:
        os.close(source_fd)
        os.close(destination_fd)

    assert snapshot.digest.startswith("sha256:")
    assert (destination / "action.py").read_bytes() == action_bytes
    assert (destination / "package.yaml").read_bytes() == package_bytes


@pytest.mark.skipif(sys.platform != "linux", reason="confined staging requires Linux")
def test_staged_source_snapshot_rejects_bytes_that_differ_from_the_input(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "action.py").write_bytes(b"def generated_action(): return 'actual'\n")
    destination = tmp_path / "staged"
    destination.mkdir(mode=0o700)
    destination.chmod(0o700)
    source_fd = os.open(source, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    destination_fd = os.open(destination, os.O_RDONLY | getattr(os, "O_DIRECTORY"))
    try:
        with pytest.raises(ValueError, match="staged source"):
            stage_source_snapshot(
                source_fd,
                destination_fd,
                [_entry("action.py", b"def generated_action(): return 'expected'\n")],
                selected_file_names=["action.py"],
                protected_input_names=[],
            )
    finally:
        os.close(source_fd)
        os.close(destination_fd)


@pytest.mark.parametrize(
    "mode,outputs",
    [
        ("optional", False),
        ("required-input", False),
        ("consumer", True),
        ("producer", True),
    ],
)
def test_explicit_work_item_declaration_changes_immutable_manifest(mode, outputs):
    from actions.server.deployments.foundry_values import WorkItemDeclaration

    baseline, _ = _compile_with_fake()
    outcome = compile_generated_python_action(
        _generated_action_entries(),
        replace(
            _compilation_policy(),
            work_items=WorkItemDeclaration(mode=mode, allow_outputs=outputs),
        ),
        protected_input_names=["package.yaml"],
        admission=TrustedDeveloperExecutionAdmission.TRUSTED,
        executor=_FakeCompilerExecutor(),
    )
    compiled = outcome.compiled_package
    assert compiled is not None and baseline.compiled_package is not None
    manifest = json.loads(compiled.manifest_json)
    Draft202012Validator(json.loads(PACKAGE_SCHEMA.read_text())).validate(manifest)
    assert manifest["capabilities"][0]["mode"] == mode
    assert manifest["capabilities"][0]["allowOutputs"] is outputs
    verify_compiled_package_revision(compiled)
    assert compiled.package_revision_id != baseline.compiled_package.package_revision_id
    assert (
        compiled.runtime_plan_payload == baseline.compiled_package.runtime_plan_payload
    )
    assert compiled.source_archive == baseline.compiled_package.source_archive

    # Compiling a declaration never turns the current none-only RCC port into
    # a queue worker. No execution or synthetic Work Item is admitted here.
    from types import SimpleNamespace

    from actions.server.foundry.rcc_execution import GeneratedRccExecution
    from actions.server.run_outputs.service import AccessDenied

    runner = object.__new__(GeneratedRccExecution)
    runner.registry = SimpleNamespace(
        load=lambda ref: compiled, evidence=lambda ref: SimpleNamespace(ready=True)
    )
    snapshot = SimpleNamespace(
        capability_authority="package-revision",
        capability=SimpleNamespace(
            package_revision=object(),
            capability_id=SimpleNamespace(root=manifest["capabilities"][0]["id"]),
        ),
    )
    with pytest.raises(AccessDenied, match="not executable"):
        runner._verified_selection(snapshot)


def test_default_work_item_declaration_preserves_manifest_golden():
    import hashlib

    compiled = _compile_with_fake()[0].compiled_package
    assert compiled is not None
    assert (
        hashlib.sha256(compiled.manifest_json).hexdigest()
        == "b69feea6cdb57315b9ea490bd7610371ceeeb05ec9096f101e1b50d08b3215bd"
    )


@pytest.mark.parametrize(
    "mode,outputs",
    [("none", True), ("producer", False), ("automatic", False), (None, True)],
)
def test_package_schema_rejects_contradictory_work_item_declaration(mode, outputs):
    from jsonschema.exceptions import ValidationError

    compiled = _compile_with_fake()[0].compiled_package
    manifest = json.loads(compiled.manifest_json)
    capability = manifest["capabilities"][0]
    if mode is None:
        capability.pop("mode")
    else:
        capability["mode"] = mode
    capability["allowOutputs"] = outputs
    with pytest.raises(ValidationError):
        Draft202012Validator(json.loads(PACKAGE_SCHEMA.read_text())).validate(manifest)


@pytest.mark.parametrize("mode", ["optional", "required-input", "consumer", "producer"])
def test_non_none_schema_requires_explicit_output_declaration(mode):
    from jsonschema.exceptions import ValidationError

    compiled = _compile_with_fake()[0].compiled_package
    manifest = json.loads(compiled.manifest_json)
    manifest["capabilities"][0]["mode"] = mode
    manifest["capabilities"][0].pop("allowOutputs")
    with pytest.raises(ValidationError):
        Draft202012Validator(json.loads(PACKAGE_SCHEMA.read_text())).validate(manifest)
