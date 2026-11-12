"""Explicitly qualified mapped Knowledge candidates; synthetic compiler only."""

import json
from dataclasses import replace

import pytest
from contract_tests.test_knowledge_input_mapping import compile_mapped

from actions.server.deployments import canonical
from actions.server.deployments.package_revision_compiler import (
    verify_compilation_outcome,
)


@pytest.mark.parametrize("core", ["1.1.0a4", "1.1.0a7"])
def test_qualified_knowledge_candidate_compiles_and_verifies(core):
    outcome = compile_mapped(core=core)
    assert outcome.compiled_package is not None, outcome.receipt
    compiled = verify_compilation_outcome(outcome)
    manifest = json.loads(compiled.manifest_json)
    assert manifest["schemaVersion"] == "actions.package-revision/v3-invocations-draft"
    assert manifest["compatibility"] == {
        "actionsCoreRange": ">=1.1.0a4,<2.0.0",
        "actionsRuntimeRange": ">=1.1.0a39,<2.0.0",
    }
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


@pytest.mark.parametrize("core", ["1.1.0a3", "1.1.0a5", "1.1.0a6", "1.1.0a999"])
def test_unqualified_knowledge_candidate_rejected(core):
    outcome = compile_mapped(core=core)
    assert outcome.compiled_package is None
    with pytest.raises(ValueError):
        verify_compilation_outcome(outcome)


@pytest.mark.parametrize("core", ["1.1.0a4", "1.1.0a7"])
def test_knowledge_candidate_rejects_mismatched_compatibility(core):
    assert (
        compile_mapped(core=core, core_range=">=1.1.0a3,<2.0.0").compiled_package
        is None
    )


@pytest.mark.parametrize("core", ["1.1.0a4", "1.1.0a7"])
@pytest.mark.parametrize("tamper", ["mapping", "compatibility"])
def test_retained_knowledge_candidate_rejects_changed_claim(core, tamper):
    outcome = compile_mapped(core=core)
    assert outcome.compiled_package is not None, outcome.receipt
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
