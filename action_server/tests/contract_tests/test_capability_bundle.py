"""Source-iteration bundle boundaries; synthetic executor is not RCC evidence."""
import json
from dataclasses import replace

import pytest

from actions.server.deployments.capability_bundle import (
    assemble_bundle,
    decode_bundle,
    encode_bundle,
    select_capability,
    verify_bundle,
)
from actions.server.deployments.capability_bundle_compiler import (
    BundleCompilationPolicy,
    PythonCapabilityPolicy,
    compile_generated_python_bundle,
)
from actions.server.deployments.foundry_values import WorkItemDeclaration
from actions.server.deployments.package_revision_compiler import (
    PackageCompilationPolicy,
    RccBuildIdentity,
    TrustedDeveloperExecutionAdmission,
)
from actions.server.deployments.source_manifest import SuppliedSourceEntry


def entries():
    return [
        SuppliedSourceEntry(p, "file", b, 0o644)
        for p, b in [
            (
                "package.yaml",
                b"name: fixture\ndescription: fixture\ndependencies:\n  conda-forge:\n    - python=3.12\n  pypi:\n    - actions-core=1.1.0a3\n",
            ),
            (
                "actions_impl.py",
                b"from actions import action\n@action\ndef alpha(x: str) -> str: return x\n@action\ndef beta(x: int) -> int: return x + 1\n",
            ),
            (
                "tests/test_actions.py",
                b"import unittest\nclass TestActions(unittest.TestCase):\n    def test_true(self): self.assertTrue(True)\n",
            ),
        ]
    ]


class Executor:
    rcc_version = "v18.19.3"

    def __init__(self, names=("alpha", "beta"), fail=None):
        self.names = names
        self.calls = []
        self.fail = fail

    def build_environment(self, package_yaml, workspace):
        self.calls.append("build")
        if self.fail == "build":
            raise RuntimeError("secret/path")
        return RccBuildIdentity("sha256:" + "a" * 64, "sha256:" + "b" * 64)

    def import_action(self, build, package_dir, workspace):
        self.calls.append("import")
        if self.fail == "import":
            raise RuntimeError("secret/path")
        return {
            "actions_spec_version": "v2",
            "actions": [
                {
                    "name": name,
                    "file": str(package_dir / "actions_impl.py"),
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "string" if name == "alpha" else "integer"}
                        },
                    },
                    "output_schema": {
                        "type": "string" if name == "alpha" else "integer"
                    },
                }
                for name in self.names
            ],
        }

    def run_tests(self, build, package_dir, workspace):
        self.calls.append("test")
        if self.fail == "test":
            raise RuntimeError("secret/path")


def policy():
    return BundleCompilationPolicy(
        (
            PythonCapabilityPolicy(
                "alpha",
                PackageCompilationPolicy("fixture", "Fixture", ">=1,<2", ">=1,<2"),
            ),
            PythonCapabilityPolicy(
                "beta",
                PackageCompilationPolicy(
                    "fixture",
                    "Fixture",
                    ">=1,<2",
                    ">=1,<2",
                    work_items=WorkItemDeclaration(mode="producer", allow_outputs=True),
                ),
            ),
        )
    )


def compile_bundle(executor=None):
    return compile_generated_python_bundle(
        entries(),
        policy(),
        protected_input_names=("package.yaml",),
        admission=TrustedDeveloperExecutionAdmission.TRUSTED,
        executor=executor or Executor(),
    )


def test_exact_selection_and_roundtrip():
    outcome = compile_bundle()
    bundle = outcome.bundle
    assert bundle is not None
    assert decode_bundle(encode_bundle(bundle), bundle.source_archive) == bundle
    members = verify_bundle(bundle)
    a, b = members
    selection = select_capability(
        bundle,
        bundle.package_revision_id,
        "action.beta",
        b.runtime_plan_header.plan_digest,
    )
    assert selection.compiled.input_schema_payload != a.input_schema_payload
    assert (
        json.loads(selection.compiled.manifest_json)["capabilities"][0]["mode"]
        == "producer"
    )
    assert json.loads(a.manifest_json)["capabilities"][0]["mode"] == "none"
    with pytest.raises(ValueError):
        select_capability(
            bundle,
            bundle.package_revision_id,
            "action.alpha",
            b.runtime_plan_header.plan_digest,
        )
    with pytest.raises(ValueError):
        select_capability(
            bundle,
            a.package_revision_id,
            "action.alpha",
            a.runtime_plan_header.plan_digest,
        )


@pytest.mark.parametrize(
    "names",
    [
        ("alpha",),
        ("alpha", "beta", "other"),
        ("alpha", "beta", "beta"),
        (),
        ("beta", "beta"),
    ],
)
def test_complete_declared_metadata_set(names):
    outcome = compile_bundle(Executor(names))
    assert outcome.bundle is None
    assert outcome.failure_code == "action_import_failed"


def test_order_independent():
    assert encode_bundle(compile_bundle().bundle) == encode_bundle(
        compile_bundle(Executor(("beta", "alpha"))).bundle
    )


@pytest.mark.parametrize("phase", ["build", "import", "test"])
def test_phase_fail_closed(phase):
    outcome = compile_bundle(Executor(fail=phase))
    assert outcome.bundle is None
    assert "secret" not in repr(outcome)


def test_no_execution_without_admission():
    executor = Executor()
    outcome = compile_generated_python_bundle(
        entries(), policy(), protected_input_names=(), admission=None, executor=executor
    )
    assert outcome.bundle is None
    assert executor.calls == []


def test_tamper_and_closed_codec():
    bundle = compile_bundle().bundle
    encoded = encode_bundle(bundle)
    raw = json.loads(encoded)
    raw["extra"] = True
    with pytest.raises(ValueError):
        decode_bundle(json.dumps(raw).encode(), bundle.source_archive)
    with pytest.raises(ValueError):
        decode_bundle(encoded + b" ", bundle.source_archive)
    with pytest.raises(ValueError):
        decode_bundle(encoded, bundle.source_archive + b"x")
    with pytest.raises(ValueError):
        verify_bundle(replace(bundle, manifest_json=b"{}"))
    with pytest.raises(ValueError):
        decode_bundle(b"{" + b" " * (512 * 1024) + b"}", bundle.source_archive)


def test_member_uniqueness_and_source_identity():
    bundle = compile_bundle().bundle
    members = verify_bundle(bundle)
    with pytest.raises(ValueError):
        assemble_bundle((members[0], members[0]))
    with pytest.raises(ValueError):
        assemble_bundle((members[0], replace(members[1], source_archive=b"bad")))


def test_policy_duplicates_and_bounds():
    p = policy().capabilities[0]
    for values in [(), (p, p), (p,) * 9]:
        with pytest.raises(ValueError):
            BundleCompilationPolicy(values)
    with pytest.raises(ValueError):
        PythonCapabilityPolicy("../alpha", p.policy)


def test_receipt_selection_cannot_be_reordered_or_truncated():
    from actions.server.deployments.capability_bundle_compiler import (
        verify_bundle_compilation_outcome,
    )

    outcome = compile_bundle()
    assert verify_bundle_compilation_outcome(outcome) == outcome.bundle
    for receipts in (outcome.receipts[::-1], outcome.receipts[:1]):
        with pytest.raises(ValueError):
            verify_bundle_compilation_outcome(replace(outcome, receipts=receipts))


def test_changed_inspection_is_rejected():
    class Changing(Executor):
        def import_action(self, build, package_dir, workspace):
            result = super().import_action(build, package_dir, workspace)
            if self.calls.count("import") == 2:
                result["actions"][0]["input_schema"] = {"type": "integer"}
            return result

    outcome = compile_bundle(Changing())
    assert outcome.bundle is None
    assert outcome.failure_code == "action_import_failed"


@pytest.mark.parametrize(
    "mutation",
    [
        "header_bool",
        "robot",
        "unknown_adapter",
        "schema",
        "member_duplicate",
        "mixed_scope",
        "unknown_version",
        "duplicate_key",
    ],
)
def test_adversarial_codec(mutation):
    bundle = compile_bundle().bundle
    raw = json.loads(encode_bundle(bundle))
    first = raw["members"][0]
    if mutation == "header_bool":
        first["runtime_plan_header"]["plan_schema_version"] = True
    elif mutation == "robot":
        first["manifest_json"]["capabilities"][0]["kind"] = "robot-task"
    elif mutation == "unknown_adapter":
        first["runtime_plan_header"]["runtime_kind"] = "other"
    elif mutation == "schema":
        first["input_schema_payload"] = {"type": "integer"}
    elif mutation == "member_duplicate":
        raw["members"][1] = first
    elif mutation == "mixed_scope":
        first["manifest_json"]["identity"]["packageId"] = "other"
    elif mutation == "unknown_version":
        raw["schemaVersion"] = "other"
    from actions.server.deployments.package_revision_compiler import _canonical_json

    data = _canonical_json(raw)
    if mutation == "duplicate_key":
        data = data.replace(b"{", b'{"schemaVersion":"bad",', 1)
    with pytest.raises(ValueError):
        decode_bundle(data, bundle.source_archive)


def test_build_identity_drift_is_rejected():
    class Changing(Executor):
        def build_environment(self, package_yaml, workspace):
            result = super().build_environment(package_yaml, workspace)
            return (
                result
                if self.calls.count("build") == 1
                else replace(result, artifact_digest="sha256:" + "c" * 64)
            )

    outcome = compile_bundle(Changing())
    assert outcome.bundle is None
    assert outcome.failure_code == "bundle_integrity_failed"


def test_per_capability_logical_requirements_and_policy_revision_isolation():
    from actions.server.deployments.logical_bindings import (
        BindingField,
        BindingOperation,
        LogicalBindingRequirement,
    )

    requirement = LogicalBindingRequirement(
        id="records",
        kind="data",
        operations=(
            BindingOperation(
                name="records.read/v1",
                effect="read",
                parameters=(),
                result=(BindingField(name="count", kind="integer"),),
                max_rows=1,
                max_bytes=100,
                timeout_ms=100,
            ),
        ),
    )
    original = compile_bundle().bundle
    p = policy()
    revised = replace(
        p,
        capabilities=(
            p.capabilities[0],
            replace(
                p.capabilities[1],
                policy=replace(
                    p.capabilities[1].policy, logical_requirements=(requirement,)
                ),
            ),
        ),
    )
    outcome = compile_generated_python_bundle(
        entries(),
        revised,
        protected_input_names=(),
        admission=TrustedDeveloperExecutionAdmission.TRUSTED,
        executor=Executor(),
    )
    assert outcome.bundle is not None
    before = verify_bundle(original)
    after = verify_bundle(outcome.bundle)
    assert before[0] == after[0]
    assert before[1].package_revision_id != after[1].package_revision_id
    assert original.package_revision_id != outcome.bundle.package_revision_id
    a = json.loads(after[0].manifest_json)
    b = json.loads(after[1].manifest_json)
    assert a["logicalBindingRequirements"] == []
    assert b["capabilities"][0]["bindingRequirementIds"] == ["records"]
    assert b["logicalBindingRequirements"] == [requirement.model_dump(mode="json")]


def test_metadata_source_escape_and_unsupported_contract_are_rejected(tmp_path):
    class Invalid(Executor):
        def import_action(self, build, package_dir, workspace):
            result = super().import_action(build, package_dir, workspace)
            result["actions"][1]["file"] = str(tmp_path / "outside.py")
            return result

    (tmp_path / "outside.py").write_text("")
    assert compile_bundle(Invalid()).failure_code == "action_import_failed"

    class WrongVersion(Executor):
        def import_action(self, build, package_dir, workspace):
            result = super().import_action(build, package_dir, workspace)
            result["actions_spec_version"] = "future"
            return result

    assert compile_bundle(WrongVersion()).failure_code == "action_import_failed"


def test_mixed_package_policy_rejected_before_execution():
    p = policy()
    with pytest.raises(ValueError):
        replace(
            p,
            capabilities=(
                p.capabilities[0],
                replace(
                    p.capabilities[1],
                    policy=replace(p.capabilities[1].policy, package_id="other"),
                ),
            ),
        )


def test_codec_rejects_typed_non_object_or_malformed_payloads():
    bundle = compile_bundle().bundle
    for raw in (b"[]", b"{", b"null", b'"str"', b"\xff", b'{"schemaVersion":true}'):
        with pytest.raises(ValueError):
            decode_bundle(raw, bundle.source_archive)
