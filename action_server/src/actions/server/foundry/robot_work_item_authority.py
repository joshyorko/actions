"""Host-issued Robot authority snapshot; verify artifacts before SQL callbacks."""
from __future__ import annotations

from dataclasses import dataclass
from weakref import WeakKeyDictionary

from actions.server.foundry.models import FoundryPackageRevision
from actions.server.foundry.package_registry import (
    FoundryPackageRegistry,
    RegistryRobotSelection,
)
from actions.server.foundry.provider_execution import SQLRecordPin
from actions.server.run_outputs.service import AccessDenied, _transaction

_issued: WeakKeyDictionary = WeakKeyDictionary()


@dataclass(frozen=True, eq=False)
class RobotWorkItemAuthority:
    snapshot: object
    declaration: object
    deployment: object
    input_schema: str
    source_pin: SQLRecordPin

    def recheck(self, owner, caller, ticket):
        identity = _issued.get(self)
        if (
            identity is None
            or identity[0] is not owner
            or identity[1] != caller
            or identity[2] != ticket
            or self.snapshot != owner.snapshot
        ):
            raise AccessDenied("issued exact Robot Work Item authority required")
        self.source_pin.recheck(owner.db)


def prepare_robot_work_item_authority(owner, caller, ticket):
    """Prepare artifact-backed authority for subsequent SQL-only bound checks."""
    from actions.server.foundry.generic_work_item_execution import (
        GenericWorkItemExecution,
    )

    if (
        type(owner) is not GenericWorkItemExecution
        or owner.db.in_transaction()
        or not isinstance(owner.registry, FoundryPackageRegistry)
        or owner.registry is not owner.base.capabilities
        or owner.registry is not owner.deployments._packages
        or owner.registry._db is not owner.db
    ):
        raise AccessDenied(
            "canonical transaction-free Robot authority preparation required"
        )
    snapshot = owner.snapshot
    owner.base._authorize(caller.actor, snapshot, "execute")
    ref = snapshot.capability.package_revision
    with _transaction(owner.db):
        pin = SQLRecordPin.capture(
            owner.db,
            FoundryPackageRevision,
            "workspace_id=? AND package_id=? AND revision_id=?",
            (
                str(ref.workspace_id.root),
                str(ref.package_id.root),
                ref.revision_id.root,
            ),
        )
    # Artifact-backed selection and declaration are verified outside SQL. The
    # pre-read metadata pin closes changes across these separate provider reads.
    selection = owner.registry.selection_for(snapshot.capability, snapshot.runtime_plan)
    declaration = owner.registry.get_capability(snapshot.capability)
    schema = owner.registry.schema_for(snapshot)
    work_items = owner._current(caller)
    deployment = owner.deployments._repository.get_revision(snapshot.deployment)
    if (
        not isinstance(selection, RegistryRobotSelection)
        or selection.capability != snapshot.capability
        or selection.runtime_plan != snapshot.runtime_plan
        or declaration is None
        or declaration.binding_requirements
        or declaration.work_items != selection.robot.robot.work_items
        or work_items != declaration.work_items
        or work_items.mode not in ("optional", "required-input", "consumer")
        or work_items.allow_outputs
        or deployment is None
        or schema.input_schema.encode() != selection.robot.robot.input_schema
    ):
        raise AccessDenied("exact supported Robot Work Item declaration required")
    authority = RobotWorkItemAuthority(
        snapshot, declaration, deployment, schema.input_schema, pin
    )
    with _transaction(owner.db):
        pin.recheck(owner.db)
    _issued[authority] = (owner, caller, ticket)
    return authority
