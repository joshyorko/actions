"""Bind verified Robot bytes before SQL-only lifecycle and launch-journal checks."""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from weakref import WeakKeyDictionary

from actions.server.foundry.models import FoundryPackageRevision
from actions.server.foundry.package_registry import (
    FoundryPackageRegistry,
    RegistryRobotSelection,
)
from actions.server.foundry.provider_execution import SQLRecordPin
from actions.server.foundry.robot_execution import RobotSelection, encode_robot_inputs
from actions.server.foundry.robot_package_builder import RccRobotPlan
from actions.server.run_outputs.service import (
    FenceRejected,
    RunOutputService,
    _transaction,
)
from actions.server.run_outputs.types import Actor, AttemptFence, ExecutionSnapshot

_issued: WeakKeyDictionary = WeakKeyDictionary()


@dataclass(frozen=True, eq=False)
class PreparedRobotSelection:
    """Host-issued callback. Current deployment/Work Item checks stay host-owned.

    require_current must check current deployment and any independent Work Item
    claim using SQL only. It may not load package/provider artifacts or authorize
    arbitrary caller snapshots. This callback never owns terminal publication.
    """

    selection: RobotSelection
    source_archive: bytes
    actor: Actor
    fence: AttemptFence
    outputs: RunOutputService
    source_pin: SQLRecordPin
    require_current: Callable[[Actor, AttemptFence, ExecutionSnapshot], None]

    def __call__(
        self,
        actor: Actor,
        fence: AttemptFence,
        snapshot: ExecutionSnapshot,
        inputs: object,
    ) -> RobotSelection:
        if (
            self not in _issued
            or actor != self.actor
            or fence != self.fence
            or snapshot != self.selection.snapshot
        ):
            raise FenceRejected("unissued or different Robot selection")
        with _transaction(self.outputs.db):
            current, actual = self.outputs.execution_context(actor, fence)
            if (
                current != snapshot
                or json.dumps(
                    actual, sort_keys=True, separators=(",", ":"), allow_nan=False
                )
                != json.dumps(
                    inputs, sort_keys=True, separators=(",", ":"), allow_nan=False
                )
                or json.dumps(
                    actual, sort_keys=True, separators=(",", ":"), allow_nan=False
                ).encode()
                != self.selection.inputs
            ):
                raise FenceRejected("Robot admission changed")
            self.source_pin.recheck(self.outputs.db)
            self.require_current(actor, fence, current)
        return self.selection


def prepare_robot_selection(
    outputs: RunOutputService,
    registry: FoundryPackageRegistry,
    actor: Actor,
    fence: AttemptFence,
    *,
    require_current: Callable[[Actor, AttemptFence, ExecutionSnapshot], None],
) -> PreparedRobotSelection:
    """Provider verification occurs once, outside the caller's SQL transaction."""
    if (
        outputs.db.in_transaction()
        or registry is not outputs.capabilities
        or registry._db is not outputs.db
        or not callable(require_current)
    ):
        raise FenceRejected(
            "canonical Robot registry and transaction-free preparation required"
        )
    actor, fence = Actor.model_validate(actor), AttemptFence.model_validate(fence)
    with _transaction(outputs.db):
        snapshot, inputs = outputs.execution_context(actor, fence)
        require_current(actor, fence, snapshot)
        ref = snapshot.capability.package_revision
        pin = SQLRecordPin.capture(
            outputs.db,
            FoundryPackageRevision,
            "workspace_id=? AND package_id=? AND revision_id=?",
            (
                str(ref.workspace_id.root),
                str(ref.package_id.root),
                ref.revision_id.root,
            ),
        )
    selected = registry.selection_for(snapshot.capability, snapshot.runtime_plan)
    if not isinstance(selected, RegistryRobotSelection):
        raise FenceRejected("Robot capability selection required")
    robot = selected.robot.robot
    plan = robot.plan
    if snapshot.runtime_kind != plan.runtime_kind:
        raise FenceRejected("Robot runtime mechanism differs")
    extra = (
        {
            "rcc_specification_digest": plan.specification_digest,
            "rcc_artifact_digest": plan.artifact_digest,
            "package_yaml_digest": plan.package_yaml_digest,
        }
        if isinstance(plan, RccRobotPlan)
        else {}
    )
    selection = RobotSelection(
        snapshot,
        plan.runtime_kind,
        robot.suite_path,
        robot.suite_name,
        robot.task_name,
        robot.source_digest,
        robot.input_schema,
        robot.output_schema,
        encode_robot_inputs(inputs),
        adapter_version=plan.adapter_version,
        robot_version=plan.robot_version,
        python_version=plan.python_version,
        platform_tag=plan.platform_tag,
        **extra,
    )
    prepared = PreparedRobotSelection(
        selection, robot.source_archive, actor, fence, outputs, pin, require_current
    )
    _issued[prepared] = True
    try:
        prepared(actor, fence, snapshot, inputs)
    except BaseException:
        _issued.pop(prepared, None)
        raise
    return prepared
