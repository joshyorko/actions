"""Common Run port boundaries; schema port fixture is not Package admission proof."""

import hashlib
import json
from uuid import uuid4

import pytest
from action_server_tests.run_outputs.test_service import insert_action, snapshot
from action_server_tests.test_foundry_deployments import _runtime_database

from actions.server._models import Run
from actions.server.run_outputs.service import (
    AccessDenied,
    RunOutputControlPlane,
    RunOutputService,
)
from actions.server.run_outputs.types import Actor, ExecutionSnapshot

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def _native():
    value = snapshot().model_dump(mode="json")
    value["capability_authority"] = "package-revision"
    value["capability_schema_digest"] = (
        "sha256:" + hashlib.sha256(b'{"type":"object"}').hexdigest()
    )
    return ExecutionSnapshot.model_validate(value)


def test_legacy_snapshot_wire_bytes_are_unchanged_and_native_is_explicit():
    legacy = snapshot()
    raw = legacy.model_dump_json()
    assert "capability_authority" not in json.loads(raw)
    assert ExecutionSnapshot.model_validate_json(raw).model_dump_json() == raw
    native = _native()
    assert (
        json.loads(native.model_dump_json())["capability_authority"]
        == "package-revision"
    )


def test_native_registration_cannot_fall_back_to_an_existing_legacy_action(
    database_location,
):
    native = _native()
    workspace = native.deployment.workspace_id
    with _runtime_database(database_location, workspace, ()) as db:
        insert_action(db, native)
        with pytest.raises(AccessDenied):
            RunOutputControlPlane(db).register(native)
        assert db.all(Run) == []


def test_same_run_authority_uses_the_trusted_package_schema_and_live_authorizer(
    database_location,
):
    from actions.server.run_outputs.types import AdmittedActionSchema

    native = _native()
    workspace = native.deployment.workspace_id
    actor = Actor(principal_id=str(uuid4()))

    class Port:
        allowed = True

        def schema_for(self, selected):
            return AdmittedActionSchema(
                selected.action_id,
                selected.capability,
                selected.runtime_plan,
                '{"type":"object"}',
                "{}",
            )

        def authorize(self, caller, selected, operation):
            if not self.allowed:
                raise AccessDenied("native source grant revoked")

    port = Port()
    with _runtime_database(database_location, workspace, ()) as db:
        control = RunOutputControlPlane(db, capabilities=port)
        control.register(native)
        control.grant(actor, native.deployment, {"execute", "read", "cancel"})
        service = RunOutputService(db, {}, capabilities=port)
        first = service.admit(actor, native, {}, "native-request")
        assert service.admit(actor, native, {}, "native-request").id == first.id
        assert len(db.all(Run)) == 1
        port.allowed = False
        with pytest.raises(AccessDenied):
            service.admit(actor, native, {}, "native-request")
        with pytest.raises(AccessDenied):
            RunOutputService(db, {}).admit(actor, native, {}, "native-request")
        assert len(db.all(Run)) == 1
