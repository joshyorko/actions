"""Typed host policy for one-level internal Action-to-Robot delegation.

This module defines immutable policy values only. It performs no persistence,
authorization, model publication, admission, or Runtime transport work. A host
must resolve current immutable snapshots and recheck delegation and execute
authority at every operation before using a selected target.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from actions.server.foundry.package_registry import (
    RegistryCapabilitySelection,
    RegistryRobotSelection,
)
from actions.server.run_outputs.types import ExecutionSnapshot

MAX_INTERNAL_CHILD_RUNS = 16
MAX_INTERNAL_DELEGATION_BINDINGS = 32
_BINDING_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z", re.ASCII)


class DetachPolicy(str, Enum):
    """Explicit parent-exit behavior required for every delegation policy."""

    CANCEL_ON_PARENT_EXIT = "cancel-on-parent-exit"
    ALLOW_AUTHORIZED_DETACH = "allow-authorized-detach"


@dataclass(frozen=True)
class ActionParentSnapshot:
    """An exact generated Action selection, not a Robot or model audience."""

    snapshot: ExecutionSnapshot
    selection: RegistryCapabilitySelection

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, ExecutionSnapshot):
            raise ValueError("exact Action execution snapshot required")
        if not isinstance(self.selection, RegistryCapabilitySelection):
            raise ValueError("generated Action capability selection required")
        if (
            self.snapshot.capability_authority != "package-revision"
            or self.snapshot.runtime_kind != "rcc"
            or self.selection.package_revision
            != self.snapshot.capability.package_revision
            or self.selection.capability != self.snapshot.capability
            or self.selection.runtime_plan != self.snapshot.runtime_plan
        ):
            raise ValueError("Action capability selection differs from snapshot")

    @property
    def capability(self):
        return self.snapshot.capability


@dataclass(frozen=True)
class RobotTargetSnapshot:
    """An exact Robot selection paired with its Deployment execution snapshot."""

    snapshot: ExecutionSnapshot
    selection: RegistryRobotSelection

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, ExecutionSnapshot):
            raise ValueError("exact Robot execution snapshot required")
        if not isinstance(self.selection, RegistryRobotSelection):
            raise ValueError("canonical Robot selection required")
        if (
            self.snapshot.capability_authority != "package-revision"
            or self.selection.package_revision
            != self.snapshot.capability.package_revision
            or self.selection.capability != self.snapshot.capability
            or self.selection.runtime_plan != self.snapshot.runtime_plan
        ):
            raise ValueError("Robot capability selection differs from snapshot")
        robot = getattr(self.selection.robot, "robot", None)
        plan = getattr(robot, "plan", None)
        runtime_kind = getattr(plan, "runtime_kind", None)
        if runtime_kind != "rcc" or self.snapshot.runtime_kind != "rcc":
            raise ValueError("RCC Robot target required")


@dataclass(frozen=True)
class InternalDelegationBinding:
    """One Action-supplied name mapped to one fixed Robot target."""

    name: str
    target: RobotTargetSnapshot

    def __post_init__(self) -> None:
        if (
            type(self.name) is not str  # noqa: E721 - require an exact primitive
            or len(self.name.encode("utf-8", errors="surrogatepass")) > 128
            or _BINDING_NAME.fullmatch(self.name) is None
        ):
            raise ValueError("invalid internal delegation binding name")
        if not isinstance(self.target, RobotTargetSnapshot):
            raise ValueError("exact Robot child target required")


@dataclass(frozen=True)
class InternalDelegationPolicy:
    """Immutable local policy for one parent Action's bounded Robot children.

    The policy has no audience, app binding, model-publication field, caller
    target override, or recursive child-policy field. It is data for a trusted
    host integration and grants no authority by itself.
    """

    parent: ActionParentSnapshot
    bindings: tuple[InternalDelegationBinding, ...]
    max_child_runs: int
    detach_policy: DetachPolicy

    def __post_init__(self) -> None:
        if not isinstance(self.parent, ActionParentSnapshot):
            raise ValueError("exact generated Action parent required")
        if type(self.bindings) is not tuple or not self.bindings:  # noqa: E721
            raise ValueError("nonempty immutable delegation bindings required")
        if len(self.bindings) > MAX_INTERNAL_DELEGATION_BINDINGS:
            raise ValueError("internal delegation binding bound exceeded")
        if (
            type(self.max_child_runs) is not int  # noqa: E721 - reject booleans
            or not 1 <= self.max_child_runs <= MAX_INTERNAL_CHILD_RUNS
        ):
            raise ValueError("internal child count outside bound")
        if not isinstance(self.detach_policy, DetachPolicy):
            raise ValueError("explicit internal detach policy required")

        names = [binding.name for binding in self.bindings]
        if len(names) != len(set(names)):
            raise ValueError("duplicate internal delegation binding")
        targets = [
            (
                binding.target.snapshot.deployment,
                binding.target.snapshot.capability,
                binding.target.snapshot.runtime_plan,
            )
            for binding in self.bindings
        ]
        if len(targets) != len(set(targets)):
            raise ValueError("duplicate internal Robot target")
        parent_snapshot = self.parent.snapshot
        for binding in self.bindings:
            target = binding.target.snapshot
            if target.workspace_id != parent_snapshot.workspace_id:
                raise ValueError("internal Robot target Workspace differs from parent")
            if target == parent_snapshot:
                raise ValueError("parent snapshot cannot be a child target")

        object.__setattr__(
            self, "bindings", tuple(sorted(self.bindings, key=lambda item: item.name))
        )

    def target_for(self, binding_name: str) -> RobotTargetSnapshot:
        """Return only the exact policy-selected target for a known binding."""
        if type(binding_name) is not str:  # noqa: E721 - require an exact primitive
            raise KeyError("internal delegation binding unavailable")
        for binding in self.bindings:
            if binding.name == binding_name:
                return binding.target
        raise KeyError("internal delegation binding unavailable")
