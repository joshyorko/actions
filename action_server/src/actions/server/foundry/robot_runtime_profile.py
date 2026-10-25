"""Explicit host-only Robot preparations; existing SQL authority remains required."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol

from pydantic import BaseModel, ConfigDict, model_validator

from actions.server.foundry.package_registry import (
    RegistryCapabilitySelection,
    RegistryRobotSelection,
)
from actions.server.foundry.robot_execution import (
    DirectRobotPreparation,
    RccRobotPreparation,
)
from actions.server.foundry.robot_runtime_runner import PinnedRobotRunner
from actions.server.run_outputs.service import AccessDenied


class RobotRuntimeProfile(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    schema_version: Literal["actions.runtime-robot-profile/v1"]
    admission: Literal["trusted-developer-execution"]
    direct_python: str | None = None
    prepared_receipt: str | None = None

    @model_validator(mode="after")
    def explicit_paths(self):
        paths = [
            p for p in (self.direct_python, self.prepared_receipt) if p is not None
        ]
        if not paths or any(not p or not Path(p).is_absolute() for p in paths):
            raise ValueError("at least one absolute trusted Robot preparation required")
        return self


def read_robot_profile(path: str | None) -> RobotRuntimeProfile | None:
    if path is None:
        return None
    source = Path(path)
    if not source.is_absolute():
        raise ValueError("absolute Robot profile path required")
    with source.open("rb") as stream:
        raw = stream.read(16385)
    if len(raw) > 16384:
        raise ValueError("Robot profile exceeds bound")

    def closed(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate Robot profile field")
            value[key] = item
        return value

    value = json.loads(raw, object_pairs_hook=closed)
    return RobotRuntimeProfile.model_validate(value)


def prepare_robot_runtimes(profile: RobotRuntimeProfile, rcc: Path):
    from actions.server.deployments.package_revision_compiler import (
        load_prepared_rcc_environment,
    )

    direct = (
        DirectRobotPreparation(Path(profile.direct_python))
        if profile.direct_python
        else None
    )
    prepared = (
        RccRobotPreparation(
            rcc, load_prepared_rcc_environment(Path(profile.prepared_receipt))
        )
        if profile.prepared_receipt
        else None
    )
    return direct, prepared


if TYPE_CHECKING:
    from actions.server._models import Run
    from actions.server.foundry.generic_work_item_execution import (
        GenericTicket,
        GenericWorkItemExecution,
    )
    from actions.server.foundry.standalone_execution import StandaloneActionExecution
    from actions.server.managed_work_items.contracts import ManagedCaller


class CapabilityRunner(Protocol):
    def execute(
        self,
        caller: ManagedCaller,
        ticket: GenericTicket,
        service: GenericWorkItemExecution | StandaloneActionExecution,
    ) -> Run:
        ...


@dataclass(frozen=True)
class RuntimeCapabilityRunner:
    """Dispatch by verified retained Package kind, never client-selected adapters."""

    python: CapabilityRunner
    direct_robot: PinnedRobotRunner | None = None
    rcc_robot: PinnedRobotRunner | None = None

    def robot_for(self, registry, snapshot):
        """Select configured Robot preparation from artifact-verified package kind."""
        selected = registry.selection_for(snapshot.capability, snapshot.runtime_plan)
        if isinstance(selected, RegistryCapabilitySelection):
            return None
        if not isinstance(selected, RegistryRobotSelection):
            raise AccessDenied("unsupported retained Package selection")
        plan = selected.robot.robot.plan
        runner = {"direct": self.direct_robot, "rcc": self.rcc_robot}.get(
            plan.runtime_kind
        )
        if runner is None:
            raise AccessDenied("retained Robot runtime is not configured")
        preparation = runner.preparation
        if plan.runtime_kind == "rcc":
            if not isinstance(preparation, RccRobotPreparation):
                raise AccessDenied("Robot preparation kind differs")
            retained = preparation.environment
            if (
                retained.build_identity.specification_digest
                != plan.specification_digest
                or retained.build_identity.artifact_digest != plan.artifact_digest
                or retained.package_yaml_digest != plan.package_yaml_digest
            ):
                raise AccessDenied("Robot prepared environment differs")
        elif not isinstance(preparation, DirectRobotPreparation):
            raise AccessDenied("Robot preparation kind differs")
        return runner

    def execute(self, caller, ticket, service):
        runner = self.robot_for(service.registry, service.snapshot)
        if runner is None:
            return self.python.execute(caller, ticket, service)
        return runner.execute(caller, ticket, service)
