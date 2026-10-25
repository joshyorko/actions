"""Mapped compilation and retained verification enforce executable contracts."""
import json
from dataclasses import replace

import pytest
from contract_tests.test_knowledge_input_mapping import (
    compile_mapped,
    requirement,
    supported_requirement,
)
from contract_tests.test_package_revision_compiler import _canonical_digest

from actions.server.deployments import canonical, ids
from actions.server.deployments.logical_bindings import LogicalBindingRequirement
from actions.server.deployments.package_revision_compiler import (
    verify_compiled_package_revision,
)


def invalid_requirement(case):
    raw = supported_requirement().model_dump(mode="json")
    op = raw["operations"][0]
    if case == "effect":
        op["effect"] = "write"
    elif case == "missing-parameter":
        op["parameters"] = [
            field for field in op["parameters"] if field["name"] != "query"
        ]
        raw["invocations"][0]["inputs"] = [
            field
            for field in raw["invocations"][0]["inputs"]
            if field["parameter"] != "query"
        ]
    elif case == "result":
        op["result"] = [{"name": "text", "kind": "string", "required": True}]
    else:
        op["result"][0]["required"] = False
    return LogicalBindingRequirement.model_validate_json(json.dumps(raw))


@pytest.mark.parametrize(
    "case", ["effect", "missing-parameter", "result", "optional-result"]
)
def test_build_refuses_mapped_but_unsupported_operation(case):
    result = compile_mapped(mapped_requirement=invalid_requirement(case))
    assert result.compiled_package is None
    assert result.receipt.status == "failed"


@pytest.mark.parametrize(
    "case", ["effect", "missing-parameter", "result", "optional-result"]
)
def test_retained_verifier_rejects_even_correctly_rehashed_unsupported_contract(case):
    compiled = compile_mapped().compiled_package
    assert compiled is not None
    value = json.loads(compiled.manifest_json)
    value["logicalBindingRequirements"] = [
        invalid_requirement(case).model_dump(mode="json")
    ]
    value["identity"].pop("revisionDigest")
    digest = _canonical_digest([value["schemaVersion"], value])
    value["identity"]["revisionDigest"] = digest
    forged = replace(
        compiled,
        package_revision_id=ids.PackageRevisionId(digest),
        manifest_json=canonical.canonicalize_json(json.dumps(value).encode()),
    )
    with pytest.raises(ValueError, match="integrity check failed"):
        verify_compiled_package_revision(forged)


def test_unmapped_legacy_knowledge_metadata_does_not_enter_new_validator():
    raw = requirement().model_dump(mode="json")
    raw.pop("invocations")
    legacy = LogicalBindingRequirement.model_validate_json(json.dumps(raw))
    result = compile_mapped(
        mapped_requirement=legacy, core="1.1.0a3", core_range=">=1.1.0a3,<2.0.0"
    )
    assert result.compiled_package is not None, result.receipt
    value = json.loads(result.compiled_package.manifest_json)
    assert value["schemaVersion"] == "actions.package-revision/v2-bindings-draft"
    assert "invocations" not in value["logicalBindingRequirements"][0]
    verify_compiled_package_revision(result.compiled_package)


def test_supported_empty_ingestion_mapping_compiles_under_v3_floor():
    raw = supported_requirement().model_dump(mode="json")
    raw["operations"][0].update(
        name="documents.ingest/v1", effect="write", parameters=[]
    )
    raw["invocations"][0] = {"operation": "documents.ingest/v1", "inputs": []}
    req = LogicalBindingRequirement.model_validate_json(json.dumps(raw))
    result = compile_mapped(mapped_requirement=req)
    assert result.compiled_package is not None, result.receipt
    verify_compiled_package_revision(result.compiled_package)
    value = json.loads(result.compiled_package.manifest_json)
    assert value["schemaVersion"] == "actions.package-revision/v3-invocations-draft"
    assert value["compatibility"] == {
        "actionsCoreRange": ">=1.1.0a4,<2.0.0",
        "actionsRuntimeRange": ">=1.1.0a39,<2.0.0",
    }
