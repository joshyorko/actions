"""Core a8 qualification for invocation-mapped Knowledge packages."""

import json
from dataclasses import replace

import pytest
from contract_tests.test_knowledge_input_mapping import compile_mapped

from actions.server.deployments import canonical
from actions.server.deployments.package_revision_compiler import (
    verify_compilation_outcome,
)


@pytest.mark.parametrize("core", ["1.1.0a4", "1.1.0a7"])
def test_existing_qualified_knowledge_cores_still_compile_and_verify(core):
    outcome = compile_mapped(core=core)
    assert outcome.compiled_package is not None, repr(outcome.receipt)
    verify_compilation_outcome(outcome)


def test_core_a8_mapped_knowledge_compiles_with_unchanged_contract():
    outcome = compile_mapped(core="1.1.0a8")
    assert outcome.compiled_package is not None, repr(outcome.receipt)

    compiled = verify_compilation_outcome(outcome)
    manifest = json.loads(compiled.manifest_json)
    assert manifest["schemaVersion"] == "actions.package-revision/v3-invocations-draft"
    assert manifest["compatibility"] == {
        "actionsCoreRange": ">=1.1.0a4,<2.0.0",
        "actionsRuntimeRange": ">=1.1.0a39,<2.0.0",
    }
    assert {
        "kind": "python-package",
        "name": "actions-core",
        "constraint": "==1.1.0a8",
    } in manifest["runtimePlans"][0]["environmentRequirements"]
    assert manifest["logicalBindingRequirements"][0]["invocations"] == [
        {
            "operation": "documents.search/v1",
            "inputs": [
                {"parameter": "ingestion_handle", "input": "corpus_handle"},
                {"parameter": "limit", "input": "page_limit"},
                {"parameter": "offset", "input": "page_offset"},
                {"parameter": "query", "input": "value"},
            ],
        }
    ]


@pytest.mark.parametrize("core", ["1.1.0a5", "1.1.0a6", "1.1.0a999"])
def test_unqualified_knowledge_cores_remain_rejected(core):
    outcome = compile_mapped(core=core)
    assert outcome.compiled_package is None
    with pytest.raises(ValueError):
        verify_compilation_outcome(outcome)


@pytest.mark.parametrize("tamper", ["mapping", "compatibility"])
def test_core_a8_retained_verifier_rejects_changed_claim(tamper):
    outcome = compile_mapped(core="1.1.0a8")
    assert outcome.compiled_package is not None, repr(outcome.receipt)
    compiled = outcome.compiled_package
    manifest = json.loads(compiled.manifest_json)
    if tamper == "mapping":
        manifest["logicalBindingRequirements"][0]["invocations"][0]["inputs"][0][
            "input"
        ] = "value"
    else:
        manifest["compatibility"]["actionsCoreRange"] = ">=1.1.0a3,<2.0.0"
    altered = replace(
        compiled,
        manifest_json=canonical.canonicalize_json(json.dumps(manifest).encode()),
    )
    with pytest.raises(ValueError):
        verify_compilation_outcome(replace(outcome, compiled_package=altered))
