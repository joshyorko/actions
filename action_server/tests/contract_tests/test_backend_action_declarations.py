"""Explicit per-Action declarations preserve the legacy request grammar."""
import json

import pytest

from actions.server.foundry.authoring_values import GeneratedBackend


def backend(**extra):
    return {
        "logicalName": "Two operations",
        "files": [{"path": "actions.py", "content": "# source"}],
        **extra,
    }


def parse(value):
    return GeneratedBackend.model_validate_json(json.dumps(value))


def test_explicit_actions_are_canonical_and_keep_independent_policies():
    value = parse(backend(actions=[{"actionName": "second"}, {"actionName": "first"}]))
    assert [a.action_name for a in value.actions] == ["first", "second"]
    assert value.actions[0].work_items.mode == "none"
    assert value.actions[0].logical_requirements == ()


@pytest.mark.parametrize(
    "actions",
    [
        [],
        [{"actionName": "same"}, {"actionName": "same"}],
        [{"actionName": "../escape"}],
        [{"actionName": "robot", "kind": "robot"}],
        [{"actionName": str(i)} for i in range(9)],
    ],
)
def test_invalid_action_sets_refused(actions):
    with pytest.raises(ValueError):
        parse(backend(actions=actions))


@pytest.mark.parametrize(
    "extra",
    [
        {"workItems": {"mode": "none", "allowOutputs": False}},
        {"logicalRequirements": []},
    ],
)
def test_bundle_does_not_accept_ambiguous_global_policy(extra):
    with pytest.raises(ValueError):
        parse(backend(actions=[{"actionName": "one"}], **extra))


def test_absent_actions_preserves_legacy_serialization():
    value = parse(backend())
    assert "actions" not in value.model_dump(mode="json", by_alias=True)


def test_authoring_uses_explicit_bundle_compiler_without_singleton_fallback():
    from action_server_tests.test_foundry_authoring import (
        _call,
        _caller,
        _Compiler,
        _service,
        _spec,
    )

    class BundleCompiler(_Compiler):
        def compile_trusted_source(self, *args, **kwargs):
            raise AssertionError("must not infer a singleton")

        def compile_trusted_bundle(self, entries, **kwargs):
            return super().compile_trusted_source(entries, **kwargs)

    compiler = BundleCompiler()
    service, authority, _, _, packages, selection = _service(compiler=compiler)

    def resolve(actor, workspace, capability):
        assert capability.package_revision.workspace_id == workspace
        assert capability.capability_id.root in ("action.first", "action.second")
        return capability

    packages.resolve_capability = resolve
    caller = _caller()
    created = _call(
        service, caller, "canvas_create", {"idempotencyKey": "bundle-create"}
    )
    applied = _call(
        service,
        caller,
        "canvas_apply",
        {
            "appId": created.model_result["applicationId"],
            "expectedBase": created.model_result["revisionId"],
            "spec": _spec(binding_ids=("one", "two")),
            "bindings": [
                {"bindingId": "one", "capabilityId": "action.first"},
                {"bindingId": "two", "capabilityId": "action.second"},
            ],
            "backend": backend(
                actions=[{"actionName": "second"}, {"actionName": "first"}]
            ),
            "idempotencyKey": "bundle-apply",
        },
    )
    assert applied.model_result["buildStatus"] == "passed"
    assert len(compiler.calls) == 1
    policy = compiler.calls[0][1]["policy"]
    assert [c.action_name for c in policy.capabilities] == ["first", "second"]
    assert all(
        c.policy.actions_runtime_range == ">=1.1.0a38,<2.0.0"
        for c in policy.capabilities
    )
    assert len(packages.calls) == 1
