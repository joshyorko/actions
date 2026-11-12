"""Preview syntax/scope is not provider compatibility or execution readiness."""
import pytest
from action_server_tests.test_foundry_authoring import _call, _caller, _service, _spec
from action_server_tests.test_foundry_deployments import _refs
from action_server_tests.test_logical_binding_checkpoint import requirement

from actions.server.deployments.ids import WorkspaceId
from actions.server.foundry.authoring_values import AuthoringAccessDenied


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def preview_arguments(caller):
    provider = _refs().provider.model_copy(
        update={"workspace_id": WorkspaceId.model_validate(caller.workspace_id)}
    )
    return {
        "spec": _spec(binding_ids=("query",)),
        "bindings": [{"bindingId": "query", "capabilityId": "generated"}],
        "backend": {
            "logicalName": "Query",
            "files": [
                {"path": "package.yaml", "content": "spec: v2"},
                {"path": "main.py", "content": "pass"},
            ],
            "logicalRequirements": [requirement().model_dump(mode="json")],
        },
        "dataBindings": [
            {
                "bindingId": "query",
                "requirementId": "records",
                "provider": provider.model_dump(mode="json"),
            }
        ],
    }


def test_preview_rejects_cross_workspace_before_any_provider_or_compiler_access():
    service, authority, auth, compiler, packages, selector = _service()
    caller = _caller()
    args = preview_arguments(caller)
    args["dataBindings"][0]["provider"] = _refs().provider.model_dump(mode="json")
    with pytest.raises(AuthoringAccessDenied, match="Workspace"):
        _call(service, caller, "canvas_preview", args)
    assert not compiler.calls and not selector.calls and not packages.calls


@pytest.mark.parametrize("choices", [True, False])
def test_preview_explicitly_does_not_claim_provider_compatibility(choices):
    service, authority, auth, compiler, packages, selector = _service()
    caller = _caller()
    args = preview_arguments(caller)
    if not choices:
        args.pop("dataBindings")

    def forbidden(*args):
        raise AssertionError("preview must not inspect provider availability")

    selector.select_specification_with_bindings = forbidden
    reply = _call(service, caller, "canvas_preview", args)
    assert reply.model_result["dataBindingValidation"] == {
        "syntax": "passed",
        "compatibility": "not-checked",
        "readiness": "not-checked",
    }
    assert "not checked" in reply.summary
    assert not compiler.calls and not selector.calls and not packages.calls


def test_legacy_preview_reply_does_not_gain_binding_readiness_claims():
    service, *_ = _service()
    reply = _call(
        service, _caller(), "canvas_preview", {"spec": _spec(), "bindings": []}
    )
    assert "dataBindingValidation" not in reply.model_result
