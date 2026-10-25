"""Portable explicit Knowledge input mappings, never ambient request discovery."""
import json

import pytest

from actions.server.deployments.logical_bindings import (
    BindingField,
    BindingOperation,
    LogicalBindingRequirement,
    LogicalInputMapping,
    LogicalInvocation,
    mapped_parameters,
    validate_invocation_inputs,
)


def requirement():
    return LogicalBindingRequirement(
        id="documents",
        kind="knowledge",
        operations=(
            BindingOperation(
                name="documents.search/v1",
                effect="read",
                parameters=(BindingField(name="query", kind="string"),),
                result=(BindingField(name="text", kind="string"),),
                max_rows=10,
                max_bytes=4096,
                timeout_ms=1000,
            ),
        ),
        invocations=(
            LogicalInvocation(
                operation="documents.search/v1",
                inputs=(LogicalInputMapping(parameter="query", input="question"),),
            ),
        ),
    )


SCHEMA = {
    "type": "object",
    "properties": {"question": {"type": "string"}},
    "required": ["question"],
}


def test_exact_explicit_mapping_does_not_discover_ambient_keys():
    req = requirement()
    validate_invocation_inputs((req,), SCHEMA)
    assert mapped_parameters(
        req, "documents.search/v1", SCHEMA, {"question": "owned", "query": "foreign"}
    ) == {"query": "owned"}
    with pytest.raises(ValueError):
        mapped_parameters(req, "documents.search/v1", SCHEMA, {"query": "foreign"})
    with pytest.raises(ValueError):
        mapped_parameters(req, "documents.search/v1", SCHEMA, {"question": True})


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "object", "properties": {}, "required": []},
        {
            "type": "object",
            "properties": {"question": {"type": "integer"}},
            "required": ["question"],
        },
        {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": [],
        },
    ],
)
def test_mapping_requires_existing_required_exactly_typed_input(schema):
    with pytest.raises(ValueError):
        validate_invocation_inputs((requirement(),), schema)


def test_old_requirement_bytes_omit_new_declaration():
    value = requirement().model_dump(mode="json")
    value.pop("invocations")
    old = LogicalBindingRequirement.model_validate_json(json.dumps(value))
    assert old.model_dump(mode="json") == value
    assert "invocations" not in old.model_dump_json()


def test_operation_coverage_is_exact_and_unique():
    value = requirement().model_dump(mode="json")
    for invocations in (
        [],
        value["invocations"] * 2,
        [{"operation": "other.search/v1", "inputs": []}],
        [{"operation": "documents.search/v1", "inputs": []}],
    ):
        with pytest.raises(ValueError):
            LogicalBindingRequirement.model_validate_json(
                json.dumps(dict(value, invocations=invocations))
            )
    with pytest.raises(ValueError):
        LogicalBindingRequirement.model_validate_json(
            json.dumps(dict(value, kind="data"))
        )


def compile_mapped(
    *, core="1.1.0a4", mapped_input="value", core_range=">=1.1.0a4,<2.0.0"
):
    from dataclasses import replace
    from contract_tests.test_package_revision_compiler import (
        _FakeCompilerExecutor,
        _compilation_policy,
        _generated_action_entries,
    )
    from actions.server.deployments.package_revision_compiler import (
        compile_generated_python_action,
        TrustedDeveloperExecutionAdmission,
    )

    req = requirement()
    req = req.model_copy(
        update={
            "invocations": (
                LogicalInvocation(
                    operation="documents.search/v1",
                    inputs=(
                        LogicalInputMapping(parameter="query", input=mapped_input),
                    ),
                ),
            )
        }
    )
    entries = _generated_action_entries()
    entries[0] = replace(
        entries[0],
        content=entries[0].content.replace(
            b"actions-core=1.0.2", ("actions-core=" + core).encode()
        ),
    )
    return compile_generated_python_action(
        entries,
        replace(
            _compilation_policy(),
            logical_requirements=(req,),
            actions_runtime_range=">=1.1.0a39,<2.0.0",
            actions_core_range=core_range,
        ),
        protected_input_names=["package.yaml"],
        admission=TrustedDeveloperExecutionAdmission.TRUSTED,
        executor=_FakeCompilerExecutor(),
    )


def test_mapped_package_has_new_identity_domain_and_verified_input_mapping():
    from actions.server.deployments.package_revision_compiler import (
        verify_compilation_outcome,
    )

    result = compile_mapped()
    assert result.compiled_package is not None, result.receipt
    verify_compilation_outcome(result)
    manifest = json.loads(result.compiled_package.manifest_json)
    assert manifest["schemaVersion"] == "actions.package-revision/v3-invocations-draft"
    assert manifest["logicalBindingRequirements"][0]["invocations"][0]["inputs"] == [
        {"parameter": "query", "input": "value"}
    ]
    assert compile_mapped(mapped_input="missing").compiled_package is None


@pytest.mark.parametrize(
    "kwargs",
    [{"core": "1.1.0a3"}, {"core_range": ">=1.1.0a3,<2.0.0"}, {"core": "1.1.0a5"}],
)
def test_mapped_package_refuses_unsupported_or_unqualified_context_sdk(kwargs):
    assert compile_mapped(**kwargs).compiled_package is None
