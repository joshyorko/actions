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


def supported_requirement(mapped_input="value"):
    """Executable fixture; generic mapping DTO tests above remain metadata-only."""
    fields = {
        "ingestion_handle": "string",
        "query": "string",
        "offset": "integer",
        "limit": "integer",
    }
    inputs = {
        "ingestion_handle": "corpus_handle",
        "query": mapped_input,
        "offset": "page_offset",
        "limit": "page_limit",
    }
    return LogicalBindingRequirement(
        id="documents",
        kind="knowledge",
        operations=(
            BindingOperation(
                name="documents.search/v1",
                effect="read",
                parameters=tuple(
                    BindingField(name=name, kind=kind) for name, kind in fields.items()
                ),
                result=(BindingField(name="result_json", kind="string"),),
                max_rows=10,
                max_bytes=4096,
                timeout_ms=1000,
            ),
        ),
        invocations=(
            LogicalInvocation(
                operation="documents.search/v1",
                inputs=tuple(
                    LogicalInputMapping(parameter=name, input=value)
                    for name, value in inputs.items()
                ),
            ),
        ),
    )


def compile_mapped(
    *,
    core="1.1.0a4",
    mapped_input="value",
    core_range=">=1.1.0a4,<2.0.0",
    mapped_requirement=None,
):
    from dataclasses import replace

    from contract_tests.test_package_revision_compiler import (
        _compilation_policy,
        _FakeCompilerExecutor,
        _generated_action_entries,
    )

    from actions.server.deployments.package_revision_compiler import (
        TrustedDeveloperExecutionAdmission,
        compile_generated_python_action,
    )

    req = mapped_requirement or supported_requirement(mapped_input)

    class MappedExecutor(_FakeCompilerExecutor):
        def import_action(self, *args, **kwargs):
            result = super().import_action(*args, **kwargs)
            result["actions"][0]["input_schema"] = {
                "type": "object",
                "properties": {
                    "value": {"type": "string"},
                    "corpus_handle": {"type": "string"},
                    "page_offset": {"type": "integer"},
                    "page_limit": {"type": "integer"},
                },
                "required": ["value", "corpus_handle", "page_offset", "page_limit"],
            }
            return result

    entries = _generated_action_entries(
        b"from actions import action\n\n@action\n"
        b"def generated_echo(value: str, corpus_handle: str, page_offset: int, page_limit: int) -> str:\n"
        b"    return value\n"
    )
    entries[2] = replace(
        entries[2],
        content=entries[2].content.replace(
            b"generated_echo(value='synthetic')",
            b"generated_echo(value='synthetic', corpus_handle='synthetic', page_offset=0, page_limit=20)",
        ),
    )
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
        executor=MappedExecutor(),
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
        {"parameter": "ingestion_handle", "input": "corpus_handle"},
        {"parameter": "limit", "input": "page_limit"},
        {"parameter": "offset", "input": "page_offset"},
        {"parameter": "query", "input": "value"},
    ]
    assert compile_mapped(mapped_input="missing").compiled_package is None


@pytest.mark.parametrize(
    "kwargs",
    [{"core": "1.1.0a3"}, {"core_range": ">=1.1.0a3,<2.0.0"}, {"core": "1.1.0a5"}],
)
def test_mapped_package_refuses_unsupported_or_unqualified_context_sdk(kwargs):
    assert compile_mapped(**kwargs).compiled_package is None
