"""Detached Task admission requires a live model publication."""

import json

import pytest
from actions.canvas_contract import validate_canvas_spec
from action_server_tests import test_detached_action as detached
from action_server_tests.test_generic_work_item_execution import grant
from action_server_tests import test_task_service as task_service_tests

from actions.server.deployments.foundry_values import (
    AccessDenied as DeploymentAccessDenied,
    CanvasCapabilityBinding,
    DeploymentSpecification,
    canvas_revision_digest,
)
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.foundry.sql_authorization import reference_grant_subject
from actions.server.managed_work_items.contracts import Permission
from actions.server._models import Run
from actions.server.run_outputs.detached import DetachedActions
from actions.server.run_outputs.models import (
    RunAdmission,
    RunAttempt,
    RunExecutionIntent,
    RunTaskReceipt,
)
from actions.server.run_outputs.task_service import TaskPolicy, TaskService
from actions.server.run_outputs.types import CanvasApplicationRef

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = task_service_tests.provider
postgresql_database = task_service_tests.postgresql_database
reviewed = task_service_tests.reviewed
case = task_service_tests.case
pytestmark = task_service_tests.pytestmark


class Ready:
    def require_ready(self, actor, snapshot):
        return None


def _service(c):
    owner, selected, caller = detached.setup(c)
    tasks = TaskService(
        owner,
        readiness=Ready(),
        policy=TaskPolicy("model-publication/v1", 60000, 100),
    )
    return owner, selected, caller, tasks


def _side_effect_state(db):
    return tuple(
        tuple(db.all(model))
        for model in (Run, RunAdmission, RunAttempt, RunExecutionIntent, RunTaskReceipt)
    )


def _app_only_selection(c, snapshot):
    current = c.deployments._repository.current(
        snapshot.deployment.workspace_id, snapshot.deployment.deployment_id
    )
    value = current.revision.specification.model_dump(mode="json", by_alias=True)
    raw_canvas = value["canvas_spec"]
    raw_canvas["visibility"] = ["app"]
    canvas_spec = validate_canvas_spec(raw_canvas)
    bindings = tuple(
        CanvasCapabilityBinding.model_validate(binding)
        for binding in value.get("canvas_bindings", [])
    )
    value["canvas_spec"] = canvas_spec.model_dump(mode="json", by_alias=True)
    value["canvas_bindings"] = [
        binding.model_dump(mode="json") for binding in bindings
    ]
    value["canvas_application"] = CanvasApplicationRef(
        workspace_id=snapshot.workspace_id,
        app_id=snapshot.deployment_id,
        revision_id=canvas_revision_digest(
            canvas_spec,
            bindings,
            current.revision.specification.package_revisions,
        ),
    ).model_dump(mode="json")
    value["model_published_capabilities"] = []
    return DeploymentSpecification.model_validate_json(json.dumps(value))


def _publish(c, snapshot, selection, key):
    current = c.deployments._repository.current(
        snapshot.deployment.workspace_id, snapshot.deployment.deployment_id
    )
    grant(
        c.db,
        c.actor,
        snapshot.deployment.workspace_id,
        "reference",
        reference_grant_subject(current.revision.ref),
        ["deploy"],
    )
    revision = c.deployments.publish(
        c.actor,
        snapshot.deployment.workspace_id,
        snapshot.deployment.deployment_id,
        current.revision.ref,
        selection,
        idempotency_key=key,
    )
    grant(
        c.db,
        c.actor,
        snapshot.deployment.workspace_id,
        "reference",
        reference_grant_subject(revision.ref),
        ["deploy", "execute", "read_application", *[p.value for p in Permission]],
    )
    resolved = c.deployments.resolve(
        c.actor,
        snapshot.deployment.workspace_id,
        snapshot.deployment.deployment_id,
        snapshot.capability,
        revision=revision.ref,
    )
    return resolved.snapshot


def _create(c, tasks, snapshot, key="model-task"):
    return tasks.create(
        c.actor,
        snapshot.workspace_id,
        snapshot,
        {"value": "hello"},
        key,
    )


def test_model_visible_canvas_remains_eligible_for_detached_task(case):
    c = case
    _, selected, _, tasks = _service(c)
    snapshot = selected.snapshot
    revision = c.deployments._repository.get_revision(snapshot.deployment)
    assert revision is not None
    assert "model" in revision.revision.specification.canvas_spec.visibility

    before = _side_effect_state(c.db)
    result = _create(c, tasks, snapshot)
    assert result.status == "working" and result.result is None
    after = _side_effect_state(c.db)
    assert len(after[0]) == len(before[0]) + 1
    assert len(after[1]) == len(before[1]) + 1
    assert len(after[3]) == len(before[3]) + 1
    assert len(after[4]) == len(before[4]) + 1
    assert len(after[2]) == len(before[2])


def test_app_only_canvas_task_is_denied_before_any_admission_rows(case):
    c = case
    owner, selected, _, tasks = _service(c)
    snapshot = _publish(
        c,
        selected.snapshot,
        _app_only_selection(c, selected.snapshot),
        "task-app-only-publication",
    )
    specification = c.deployments._repository.get_revision(snapshot.deployment)
    assert specification is not None
    assert "app" in specification.revision.specification.canvas_spec.visibility
    assert "model" not in specification.revision.specification.canvas_spec.visibility
    before = _side_effect_state(c.db)

    with pytest.raises(DeploymentAccessDenied):
        _create(c, tasks, snapshot, "task-app-only-denied")

    assert _side_effect_state(c.db) == before


def test_stale_model_visible_snapshot_cannot_admit_detached_task(case):
    c = case
    _, selected, _, tasks = _service(c)
    stale_snapshot = selected.snapshot
    _publish(
        c,
        stale_snapshot,
        _app_only_selection(c, stale_snapshot),
        "task-stale-publication",
    )
    before = _side_effect_state(c.db)

    with pytest.raises(DeploymentAccessDenied):
        _create(c, tasks, stale_snapshot, "task-stale-denied")

    assert _side_effect_state(c.db) == before


def test_revoked_current_model_visible_task_authority_has_no_admission(case):
    c = case
    _, selected, _, tasks = _service(c)
    snapshot = selected.snapshot
    revision = c.deployments._repository.get_revision(snapshot.deployment)
    assert revision is not None
    assert "model" in revision.revision.specification.canvas_spec.visibility
    grants = c.db.all(
        FoundryAccessGrant,
        where="subject_kind=? AND subject_id=?",
        values=("reference", reference_grant_subject(snapshot.deployment)),
    )
    assert len(grants) == 1
    with c.db.transaction():
        c.db.update_by_id(
            FoundryAccessGrant,
            grants[0].id,
            {"operations_json": '["deploy"]'},
        )
    before = _side_effect_state(c.db)

    with pytest.raises(DeploymentAccessDenied):
        _create(c, tasks, snapshot, "task-revoked-denied")

    assert _side_effect_state(c.db) == before
