"""Deterministic, adapter-neutral runtime conformance primitives."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Tuple


def subject_fingerprint(subject: Mapping[str, Any]) -> str:
    """Return a stable digest for the protected, exact execution subject."""
    encoded = json.dumps(subject, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class AdmissionSnapshot:
    """The immutable decision shared by every admission consumer."""

    fingerprint: str
    mode: str
    outcome: str
    reason: str
    generation: str

    def __post_init__(self) -> None:
        if self.mode not in ("off", "shadow", "enforce"):
            raise ValueError("invalid admission mode")
        if self.outcome == "ready" and self.reason:
            raise ValueError("ready admission cannot have a reason")


@dataclass(frozen=True)
class RuntimePlan:
    """A selected plan; selection is explicit and has no fallback order."""

    plan_id: str
    runtime_kind: str
    adapter_contract: str
    adapter_version: str
    required_features: Tuple[str, ...] = ()


@dataclass(frozen=True)
class DeploymentRevision:
    """Immutable capability-to-plan policy used for one deployment revision."""

    revision_id: str
    capability_id: str
    plans: Tuple[RuntimePlan, ...]
    default_plan_id: Optional[str]
    allow_caller_selection: bool = False

    def select(self, plan_id: Optional[str] = None) -> RuntimePlan:
        selected = plan_id or self.default_plan_id
        if plan_id and not self.allow_caller_selection:
            raise ValueError("caller plan selection is not permitted")
        for plan in self.plans:
            if plan.plan_id == selected:
                return plan
        raise ValueError("requested runtime plan is not declared")


@dataclass(frozen=True)
class WorkerProfile:
    """Worker capabilities used to admit a selected plan."""

    worker_id: str
    runtime_kinds: Tuple[str, ...]
    features: Tuple[str, ...] = ()

    def supports(self, plan: RuntimePlan) -> bool:
        return (plan.runtime_kind in self.runtime_kinds and
                set(plan.required_features).issubset(self.features))


def admit(subject: Mapping[str, Any], mode: str, generation: str,
          plan: RuntimePlan, worker: Optional[WorkerProfile]) -> AdmissionSnapshot:
    """Compute one canonical admission result without adapter fallback."""
    if worker is None:
        outcome, reason = "no_worker", "no eligible worker"
    elif not worker.supports(plan):
        outcome, reason = "incompatible", "worker does not support selected plan"
    else:
        outcome, reason = "ready", ""
    return AdmissionSnapshot(subject_fingerprint(subject), mode, outcome,
                             reason, generation)


def assert_execution_subject(snapshot: AdmissionSnapshot,
                             subject: Mapping[str, Any]) -> None:
    """Reject execution when protected inputs no longer match admission."""
    if snapshot.fingerprint != subject_fingerprint(subject):
        raise ValueError("execution subject changed after admission")
