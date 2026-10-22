"""Private review-to-Run composition under the existing SQL authorities.

Trusted server configuration selects source and Runtime Plan. No HTTP/MCP tool,
background scheduler, adapter selection, or automatic review is installed here.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import uuid4

from actions.work_items import State
from actions.work_items._fencing import WorkItemClaim
from pydantic import BaseModel, ConfigDict, Field, model_serializer

from actions.server._models import Action, Run, RunStatus
from actions.server._rcc_runtime_adapter import (
    RCC_VERSION,
    RccProcessHandle,
    RccRuntimeDescriptor,
    build_exec_command,
    compute_source_generation,
    environment_spec_fingerprint,
    read_receipt,
    verify_rcc_version,
)
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputControlPlane,
    _canonical,
    _key,
    _now,
    _one,
    _transaction,
    _update,
)
from actions.server.run_outputs.types import (
    Actor,
    AttemptFence,
    CanvasResultScope,
    ExecutionSnapshot,
    OutputRef,
)

from .invoice_effects import SyntheticEffectPolicy, SyntheticEffectTarget
from .invoices import Invoice
from .review import InvoiceReviewService, ReviewConflict, ReviewProposal

RUNTIME_KIND = "rcc/invoice-private-output/v1"


def plan_digest(
    descriptor: RccRuntimeDescriptor,
    sdk_wheel_sha256: str,
    *,
    effect_policy: SyntheticEffectPolicy | None = None,
) -> str:
    if effect_policy is not None:
        return "sha256:" + _key(
            "actions.invoice-worker-effect-plan/v1",
            descriptor.to_json(),
            sdk_wheel_sha256,
            effect_policy.model_dump_json(),
        )
    return "sha256:" + _key(
        "actions.invoice-worker-plan/v1", descriptor.to_json(), sdk_wheel_sha256
    )


def work_item_run_key(item_id: str) -> str:
    return _key("actions.invoice-work-item-run/v1", item_id)


class ClaimValue(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )
    item_id: str
    owner_id: str
    epoch: int = Field(ge=1)

    @classmethod
    def of(cls, claim: WorkItemClaim) -> ClaimValue:
        return cls(item_id=claim.item_id, owner_id=claim.owner_id, epoch=claim.epoch)

    def as_claim(self) -> WorkItemClaim:
        return WorkItemClaim(self.item_id, self.owner_id, self.epoch)


class WorkerInput(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )
    version: Literal["actions.invoice-worker/v1"] = "actions.invoice-worker/v1"
    proposal: ReviewProposal
    initial_claim: ClaimValue
    artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_generation: str = Field(pattern=r"^[0-9a-f]{64}$")
    sdk_wheel_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    effect_policy: SyntheticEffectPolicy | None = None

    @model_serializer(mode="wrap")
    def omit_absent_effect_policy(self, handler):
        data = handler(self)
        if self.effect_policy is None:
            data.pop("effect_policy", None)
        return data


class WorkerTicket(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )
    proposal: ReviewProposal
    work_item_claim: ClaimValue
    fence: AttemptFence

    @property
    def claim(self) -> WorkItemClaim:
        return self.work_item_claim.as_claim()


@dataclass(frozen=True)
class InvoiceWorkerPlan:
    snapshot: ExecutionSnapshot
    descriptor: RccRuntimeDescriptor
    source_directory: Path
    sdk_wheel_sha256: str
    effect_policy: SyntheticEffectPolicy | None = None

    def validate(self) -> None:
        snapshot = ExecutionSnapshot.model_validate(self.snapshot)
        descriptor = self.descriptor
        if self.source_directory.is_symlink() or not self.source_directory.is_dir():
            raise AccessDenied("owned regular source directory required")
        for path in self.source_directory.rglob("*"):
            if path.is_symlink() or not (path.is_dir() or path.is_file()):
                raise AccessDenied("invoice source requires owned regular files")
        generation = compute_source_generation(self.source_directory)
        if (
            snapshot.runtime_kind != RUNTIME_KIND
            or snapshot.canvas_application is None
            or descriptor.rcc_version != RCC_VERSION
            or not descriptor.provider_context_bound
            or descriptor.source_generation != generation
            or descriptor.source_hash != generation
            or snapshot.capability.package_revision.revision_id.root
            != "sha256:" + generation
            or snapshot.runtime_plan.plan_digest.root
            != plan_digest(
                descriptor, self.sdk_wheel_sha256, effect_policy=self.effect_policy
            )
        ):
            raise AccessDenied("pinned invoice source/Runtime Plan differs")
        if (
            self.source_directory.joinpath("_invoice_task.py").read_bytes()
            != Path(__file__).with_name("_invoice_task.py").read_bytes()
        ):
            raise AccessDenied("only the fixed private-output invoice task is admitted")
        if descriptor.environment_fingerprint != environment_spec_fingerprint(
            self.source_directory / "package.yaml"
        ):
            raise AccessDenied("pinned invoice environment differs")


class InvoiceWorkerService:
    @property
    def dispatch_version(self) -> str:
        return (
            "actions.invoice-dispatch/v2"
            if self.plan.effect_policy is not None
            else "actions.invoice-dispatch/v1"
        )

    def __init__(
        self,
        reviews: InvoiceReviewService,
        plan: InvoiceWorkerPlan,
        execution_root: Path,
        rcc: Path,
        rcc_home: Path,
        *,
        effect_target: SyntheticEffectTarget | None = None,
    ):
        self.reviews, self.plan = reviews, plan
        self.effect_target = effect_target
        self.outputs, self.db = reviews.outputs, reviews.db
        self.execution_root, self.rcc, self.rcc_home = (
            execution_root.resolve(),
            rcc.resolve(),
            rcc_home.resolve(),
        )
        if plan.snapshot.canvas_application is None:
            raise AccessDenied("pinned Canvas application required")
        self.scope = CanvasResultScope(
            deployment=plan.snapshot.deployment,
            application=plan.snapshot.canvas_application,
        )

    @staticmethod
    def _result(run: Run) -> dict:
        if run.result is None:
            raise ReviewConflict("retained dispatch/publication result required")
        result = json.loads(run.result)
        if not isinstance(result, dict):
            raise ReviewConflict("retained dispatch/publication object required")
        return result

    def _approved(
        self,
        actor: Actor,
        proposal: ReviewProposal,
        item_id: str,
        *,
        open_result: bool = False,
    ):
        proposal = ReviewProposal.model_validate(proposal)
        row = self.reviews._current(
            actor, self.scope, proposal, open_result=open_result
        )
        if row.state != "approved" or row.work_item_id != item_id:
            raise ReviewConflict("approved exact-result Work Item required")
        decision = json.loads(row.decision_json)
        if decision.get("decision") != "approve":
            raise ReviewConflict("explicit approved decision required")
        reviewer = Actor(principal_id=decision["actor"])
        query_pin = _one(self.db, RunPin, proposal.binding.run_id)
        query_snapshot = self.outputs._pinned(query_pin)
        for operation in ("read", "review"):
            self.outputs._authorize(reviewer, query_snapshot, operation)
        self.outputs._authorize(actor, self.plan.snapshot, "execute")
        if self.plan.snapshot.data_binding != query_snapshot.data_binding:
            raise AccessDenied("worker source binding differs from reviewed result")
        expected = {
            "schema": "actions.invoice-review/v1",
            "review_id": row.id,
            "binding": proposal.binding.model_dump(mode="json"),
        }
        if self.reviews.queue(self.scope).load_payload(item_id) != expected:
            raise ReviewConflict("Work Item payload differs from approved result")
        return row

    def _inputs(self, proposal: ReviewProposal, claim: WorkItemClaim) -> WorkerInput:
        return WorkerInput(
            proposal=proposal,
            initial_claim=ClaimValue.of(claim),
            artifact_digest=self.plan.descriptor.artifact_digest,
            source_generation=self.plan.descriptor.source_generation,
            sdk_wheel_sha256=self.plan.sdk_wheel_sha256,
            effect_policy=self.plan.effect_policy,
        )

    def _ticket(
        self, proposal: ReviewProposal, claim: WorkItemClaim, pin: RunPin
    ) -> WorkerTicket:
        snapshot = self.outputs._pinned(pin)
        run = _one(self.db, Run, pin.run_id)
        inputs = WorkerInput.model_validate_json(run.inputs)
        expected = self._inputs(proposal, inputs.initial_claim.as_claim())
        if (
            snapshot != self.plan.snapshot
            or inputs != expected
            or inputs.initial_claim.item_id != claim.item_id
        ):
            raise AccessDenied("immutable dispatch binding differs")
        attempt = _one(self.db, RunAttempt, pin.current_attempt_id)
        if attempt.owner_id != claim.owner_id:
            raise FenceRejected("dispatch belongs to a different Attempt owner")
        fence = AttemptFence(
            run_id=pin.run_id,
            attempt_id=attempt.id,
            owner_id=attempt.owner_id,
            epoch=attempt.epoch,
        )
        if run.status in (RunStatus.PASSED, RunStatus.FAILED):
            result = self._result(run)["result"]
            if (
                result.get("work_item_claim") != ClaimValue.of(claim).model_dump()
                or result.get("publication_fence") != fence.model_dump()
            ):
                raise FenceRejected("terminal claim/Attempt differs")
            return WorkerTicket(
                proposal=proposal, work_item_claim=ClaimValue.of(claim), fence=fence
            )
        self.outputs._fence(fence)
        record = json.loads(run.result or "null")
        if (
            not isinstance(record, dict)
            or record.get("version") != self.dispatch_version
            or record.get("claim") != ClaimValue.of(claim).model_dump()
            or record.get("fence") != fence.model_dump()
        ):
            raise FenceRejected("Work Item claim is not bound to this Attempt")
        return WorkerTicket(
            proposal=proposal, work_item_claim=ClaimValue.of(claim), fence=fence
        )

    def dispatch(
        self,
        actor: Actor,
        proposal: ReviewProposal,
        claim: WorkItemClaim,
        *,
        lease_seconds: int,
    ) -> WorkerTicket:
        self.plan.validate()
        with _transaction(self.db):
            self._approved(actor, proposal, claim.item_id, open_result=True)
            queue = self.reviews.queue(self.scope)
            queue._check_format()
            key = work_item_run_key(claim.item_id)
            idem = _key(
                "actions.workspace-run-idempotency/v1",
                self.scope.application.workspace_id,
                key,
            )
            existing = self.db.all(RunPin, where="idempotency_id=?", values=[idem])
            if existing and _one(self.db, Run, existing[0].run_id).status in (
                RunStatus.PASSED,
                RunStatus.FAILED,
            ):
                return self._ticket(proposal, claim, existing[0])
            queue._require(claim)
            action = _one(self.db, Action, self.plan.snapshot.action_id)
            schema_digest = (
                "sha256:"
                + hashlib.sha256(
                    json.dumps(
                        json.loads(action.input_schema),
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest()
            )
            if schema_digest != self.plan.snapshot.capability_schema_digest:
                raise AccessDenied("worker capability schema changed")
            key = work_item_run_key(claim.item_id)
            idem = _key(
                "actions.workspace-run-idempotency/v1",
                self.scope.application.workspace_id,
                key,
            )
            existing = self.db.all(RunPin, where="idempotency_id=?", values=[idem])
            if existing:
                if existing[0].idempotency_key != key:
                    raise ReviewConflict("dispatch idempotency identity differs")
                return self._ticket(proposal, claim, existing[0])
            inputs = self._inputs(proposal, claim)
            run = self.outputs.admit(
                actor, self.plan.snapshot, inputs.model_dump(mode="json"), key
            )
            fence = self.outputs.claim(
                run.id, claim.owner_id, lease_seconds=lease_seconds
            )
            record = {
                "version": self.dispatch_version,
                "claim": ClaimValue.of(claim).model_dump(),
                "fence": fence.model_dump(),
                "launch": None,
            }
            _update(
                self.db,
                Run,
                run.id,
                {"result": json.dumps(record, sort_keys=True, separators=(",", ":"))},
            )
            return WorkerTicket(
                proposal=proposal, work_item_claim=ClaimValue.of(claim), fence=fence
            )

    def _active(self, actor: Actor, ticket: WorkerTicket) -> dict:
        ticket = WorkerTicket.model_validate(ticket)
        self._approved(actor, ticket.proposal, ticket.claim.item_id)
        queue = self.reviews.queue(self.scope)
        queue._check_format()
        queue._require(ticket.claim)
        pin = _one(self.db, RunPin, ticket.fence.run_id)
        if self._ticket(ticket.proposal, ticket.claim, pin) != ticket:
            raise FenceRejected("dispatch ticket differs from the current Attempt")
        return self._result(_one(self.db, Run, pin.run_id))

    def heartbeat(
        self, actor: Actor, ticket: WorkerTicket, *, lease_seconds: int
    ) -> None:
        with _transaction(self.db):
            self._active(actor, ticket)
            self.reviews.queue(self.scope).renew_fenced(
                ticket.claim, lease_seconds=lease_seconds
            )
            self.outputs.heartbeat(ticket.fence, lease_seconds=lease_seconds)

    def apply_effect(self, actor: Actor, ticket: WorkerTicket):
        """Explicit trusted-host invocation of a pinned owned synthetic target."""
        from .invoice_effects import InvoiceEffectController

        if self.plan.effect_policy is None:
            raise AccessDenied("pinned owned synthetic effect policy required")
        return InvoiceEffectController(self).apply(actor, ticket)

    def _directory(self, ticket: WorkerTicket, launch: dict) -> Path:
        # launch ID is generated by this host and persisted before any directory/spawn.
        launch_id = launch["id"]
        from actions.server.run_outputs.types import canonical_uuid

        canonical_uuid(launch_id)
        return (
            self.execution_root
            / ticket.fence.run_id
            / ticket.fence.attempt_id
            / launch_id
        )

    def launch(
        self,
        actor: Actor,
        ticket: WorkerTicket,
        cancelled: threading.Event,
        *,
        lease_seconds: int,
        timeout_seconds: int = 120,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, int)
            or not 1 <= timeout_seconds <= 600
        ):
            raise ValueError("bounded execution deadline required")
        self.plan.validate()
        verify_rcc_version(self.rcc)
        with _transaction(self.db):
            record = self._active(actor, ticket)
            if (
                record["launch"] is not None
                or record.get("reconciled") is not None
                or record.get("terminal_intent") is not None
            ):
                raise ReviewConflict(
                    "execution already admitted; reconcile retained evidence"
                )
            inputs = WorkerInput.model_validate_json(
                _one(self.db, Run, ticket.fence.run_id).inputs
            )
        with self.reviews.queries.export(
            actor,
            self.scope.application.workspace_id,
            ticket.proposal.binding.handle,
            canvas_scope=self.scope,
        ) as source:
            raw = source.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024 or source.read(1):
                raise ValueError("bounded invoice execution input required")
        rows = [
            Invoice.model_validate_json(line).model_dump(mode="json")
            for line in raw.splitlines()
        ]
        import actions.work_items

        sdk_module = Path(actions.work_items.__file__)
        input_data = _canonical(
            {
                "worker_input": inputs.model_dump(mode="json"),
                "claim": ClaimValue.of(ticket.claim).model_dump(),
                "fence": ticket.fence.model_dump(),
                "rows": rows,
                "sdk_module_sha256": hashlib.sha256(
                    sdk_module.read_bytes()
                ).hexdigest(),
            },
            1024 * 1024,
        ).encode()
        launch = {
            "id": str(uuid4()),
            "input_digest": hashlib.sha256(input_data).hexdigest(),
        }
        with _transaction(self.db):
            record = self._active(actor, ticket)
            if record["launch"] is not None or record.get("reconciled") is not None:
                raise ReviewConflict(
                    "execution already admitted; reconcile retained evidence"
                )
            record["launch"] = launch
            _update(
                self.db, Run, ticket.fence.run_id, {"result": _canonical(record, 65536)}
            )
        directory = self._directory(ticket, launch)
        directory.mkdir(parents=True, exist_ok=False, mode=0o700)
        snapshot = directory / "source"
        shutil.copytree(self.plan.source_directory, snapshot)
        if (
            compute_source_generation(snapshot)
            != self.plan.descriptor.source_generation
            or environment_spec_fingerprint(snapshot / "package.yaml")
            != self.plan.descriptor.environment_fingerprint
        ):
            raise AccessDenied("worker source changed during snapshot")
        (directory / "input.json").write_bytes(input_data)
        receipt_file = directory / "rcc.json"
        command = build_exec_command(
            self.rcc,
            self.plan.descriptor,
            [
                "python",
                "-I",
                "-B",
                str(snapshot / "_invoice_task.py"),
                str(directory / "input.json"),
                str(directory / "result.json"),
            ],
            receipt_file=receipt_file,
            local_trust_carrier=self.rcc_home / "artifacts/v1/trust"
            if self.plan.descriptor.provider_reference == "local"
            else None,
        )
        environment = dict(os.environ)
        for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "POETRY_ACTIVE"):
            environment.pop(key, None)
        self.rcc_home.mkdir(parents=True, exist_ok=True)
        environment.update(
            ROBOCORP_HOME=str(self.rcc_home), ACTIONS_HOME=str(self.rcc_home)
        )
        handle = None
        with (directory / "stdout.log").open("wb") as log:
            try:
                self.heartbeat(actor, ticket, lease_seconds=lease_seconds)
                process = subprocess.Popen(
                    command,
                    cwd=snapshot,
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
                handle = RccProcessHandle(process, receipt_file)
                deadline = time.monotonic() + timeout_seconds
                while process.poll() is None:
                    if cancelled.is_set():
                        self.reviews.cancel(actor, self.scope, ticket.proposal)
                        raise FenceRejected("invoice execution cancelled")
                    if time.monotonic() >= deadline:
                        raise TimeoutError("invoice RCC task deadline")
                    self.heartbeat(actor, ticket, lease_seconds=lease_seconds)
                    try:
                        process.wait(timeout=0.2)
                    except subprocess.TimeoutExpired:
                        pass
                if process.returncode != 0:
                    raise RuntimeError(
                        "invoice RCC task failed; retained evidence requires reconciliation"
                    )
            finally:
                if handle is not None and handle.process.poll() is None:
                    handle.capture_owned_processes()
                    cleanup = handle.force_kill_until(time.monotonic() + 10)
                    if not cleanup.execution_stopped:
                        raise RuntimeError("RCC process cleanup incomplete")
        self._evidence(ticket, launch)

    @staticmethod
    def _read(path: Path, limit: int) -> bytes:
        import stat

        if not stat.S_ISREG(path.lstat().st_mode):
            raise ReviewConflict("regular owned execution evidence required")
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ReviewConflict("execution evidence exceeds limit")
        return data

    def _evidence(self, ticket: WorkerTicket, launch: dict) -> dict:
        directory = self._directory(ticket, launch)
        if (
            compute_source_generation(directory / "source")
            != self.plan.descriptor.source_generation
            or environment_spec_fingerprint(directory / "source/package.yaml")
            != self.plan.descriptor.environment_fingerprint
        ):
            raise ReviewConflict("retained execution source changed")
        input_bytes = self._read(directory / "input.json", 1024 * 1024)
        if hashlib.sha256(input_bytes).hexdigest() != launch["input_digest"]:
            raise ReviewConflict("retained execution input changed")
        inputs = json.loads(input_bytes)
        if (
            inputs["fence"] != ticket.fence.model_dump()
            or inputs["claim"] != ClaimValue.of(ticket.claim).model_dump()
            or inputs["worker_input"]
            != self._inputs(
                ticket.proposal,
                WorkerInput.model_validate(
                    inputs["worker_input"]
                ).initial_claim.as_claim(),
            ).model_dump(mode="json")
        ):
            raise ReviewConflict("retained execution identity differs")
        self._read(directory / "rcc.json", 1024 * 1024)
        receipt = read_receipt(
            directory / "rcc.json", self.plan.descriptor.artifact_digest
        )
        if receipt.get("status") != "completed" or receipt.get("exitCode") != 0:
            raise ReviewConflict("completed RCC receipt required; outcome is unknown")
        task = json.loads(self._read(directory / "result.json", 1024 * 1024))
        from ._invoice_task import reconciliation_summary

        if (
            task.get("version") != "actions.invoice-task-result/v1"
            or task.get("effect_policy") != "private-result-file-only"
            or task.get("binding") != ticket.proposal.binding.model_dump(mode="json")
            or task.get("review_id") != ticket.proposal.review_id
            or task.get("fence") != ticket.fence.model_dump()
            or task.get("claim") != ClaimValue.of(ticket.claim).model_dump()
            or task.get("execution_input_digest") != launch["input_digest"]
            or task.get("sdk")
            != {
                "version": "0.5.0a1",
                "wheel_sha256": self.plan.sdk_wheel_sha256,
                "module_sha256": inputs["sdk_module_sha256"],
            }
            or task.get("invoice_count") != len(inputs["rows"])
            or task.get("total_cents")
            != sum(row["amount_cents"] for row in inputs["rows"])
            or task.get("reconciliation") != reconciliation_summary(inputs["rows"])
        ):
            raise ReviewConflict("retained task result differs from exact execution")
        return {
            "task": task,
            "rcc_receipt": receipt,
            "stdout_sha256": hashlib.sha256(
                self._read(directory / "stdout.log", 1024 * 1024)
            ).hexdigest(),
            "source_generation": self.plan.descriptor.source_generation,
            "launch": launch,
        }

    def _terminal(self, actor: Actor, ticket: WorkerTicket) -> WorkerReceipt | None:
        self._approved(actor, ticket.proposal, ticket.claim.item_id)
        run = _one(self.db, Run, ticket.fence.run_id)
        if run.status not in (RunStatus.PASSED, RunStatus.FAILED):
            return None
        disposition: Literal["completed", "dead_letter"] = (
            "dead_letter" if run.status == RunStatus.FAILED else "completed"
        )
        if disposition == "dead_letter" and (
            self.plan.effect_policy is None
            or self._result(run).get("result", {}).get("disposition") != disposition
        ):
            raise ReviewConflict("failed execution lacks a bound dead-letter receipt")
        if (
            self._ticket(ticket.proposal, ticket.claim, _one(self.db, RunPin, run.id))
            != ticket
        ):
            raise FenceRejected("terminal Attempt ticket differs")
        from .review_models import FencedWorkItem

        item = _one(self.db, FencedWorkItem, ticket.claim.item_id)
        if (
            item.state
            != (
                State.FAILED.value if disposition == "dead_letter" else State.DONE.value
            )
            or item.claim_epoch != ticket.claim.epoch
            or item.cancel_requested
        ):
            raise FenceRejected("terminal Work Item differs")
        envelope = self._result(run)
        output = OutputRef.model_validate(envelope["outputs"][0])
        return WorkerReceipt(
            run_id=run.id,
            attempt_id=ticket.fence.attempt_id,
            work_item_id=ticket.claim.item_id,
            handle=output.handle,
            disposition=disposition,
        )

    def complete(self, actor: Actor, ticket: WorkerTicket) -> WorkerReceipt:
        ticket = WorkerTicket.model_validate(ticket)
        with _transaction(self.db):
            terminal = self._terminal(actor, ticket)
            if terminal is not None:
                return terminal
            record = self._active(actor, ticket)
        if (
            self.plan.effect_policy is not None
            and record.get("terminal_intent") == "dead_letter"
        ):
            from .invoice_effects import InvoiceEffectController

            return InvoiceEffectController(self)._dead_letter(actor, ticket, record)
        evidence, executed, input_digest = self._execution_evidence(ticket, record)
        if self.plan.effect_policy is not None:
            from .invoice_effects import InvoiceEffectController

            evidence["effect_receipt"] = (
                InvoiceEffectController(self)
                .completed(ticket, record, evidence)
                .model_dump(mode="json")
            )
            evidence["effect_observations"] = record.get("effect_observations", [])
        output = self.outputs.stage(
            ticket.fence,
            [_canonical(evidence, 2 * 1024 * 1024).encode()],
            name="invoice-execution.json",
            media_type="application/json",
            retention_seconds=3600,
        )
        result = {
            "version": "actions.invoice-execution/v1",
            "review_id": ticket.proposal.review_id,
            "work_item_claim": ClaimValue.of(ticket.claim).model_dump(),
            "publication_fence": ticket.fence.model_dump(),
            "executed_fence": executed.fence.model_dump(),
            "source_generation": self.plan.descriptor.source_generation,
            "artifact_digest": self.plan.descriptor.artifact_digest,
            "execution_input_digest": input_digest,
            "reconciliations": record.get("reconciliations", []),
        }
        if self.plan.effect_policy is not None:
            result["effect_observations"] = record.get("effect_observations", [])
        with _transaction(self.db):
            self._active(actor, ticket)
            self.outputs.publish(actor, ticket.fence, [output], result)
            self.reviews.queue(self.scope).finish_fenced(
                ticket.claim,
                State.DONE,
                outputs=(
                    {
                        "run_id": ticket.fence.run_id,
                        "attempt_id": ticket.fence.attempt_id,
                        "handle": output.handle,
                    },
                ),
            )
            terminal = self._terminal(actor, ticket)
            if terminal is None:
                raise FenceRejected("publication did not reach terminal state")
            return terminal

    def _execution_evidence(
        self, ticket: WorkerTicket, record: dict
    ) -> tuple[dict, WorkerTicket, str]:
        retained = record.get("reconciled")
        if retained is not None:
            if record["launch"] is not None:
                raise ReviewConflict("conflicting execution evidence")
            executed = WorkerTicket.model_validate(retained["ticket"])
            if (
                executed.proposal != ticket.proposal
                or executed.fence.run_id != ticket.fence.run_id
                or executed.claim.item_id != ticket.claim.item_id
            ):
                raise ReviewConflict("reconciliation binding differs")
            launch = retained["launch"]
        else:
            executed, launch = ticket, record["launch"]
        if launch is None:
            raise ReviewConflict("no execution admitted")
        try:
            evidence = self._evidence(executed, launch)
        except (OSError, KeyError, ValueError) as exc:
            raise ReviewConflict(
                "execution outcome is unknown or retained evidence differs"
            ) from exc
        proof = hashlib.sha256(
            _canonical(evidence, 2 * 1024 * 1024).encode()
        ).hexdigest()
        if retained is not None and proof != retained["proof_digest"]:
            raise ReviewConflict("completed evidence changed after reconciliation")
        return evidence, executed, launch["input_digest"]

    def reconcile(
        self,
        actor: Actor,
        proposal: ReviewProposal,
        claim: WorkItemClaim,
        *,
        lease_seconds: int,
    ):
        """Explicit SQL recovery; never infer absent effects from an expired lease.

        No admitted launch proves no execution. A completed, verified journal is
        usable only for this fixed private-result-file-only task, without rerun.
        Missing/altered/incomplete evidence leaves the Run blocked.
        """
        self.plan.validate()
        if self.plan.effect_policy is not None:
            from .invoice_effects import InvoiceEffectController

            return InvoiceEffectController(self).reconcile(
                actor, proposal, claim, lease_seconds=lease_seconds
            )
        with _transaction(self.db):
            self._approved(actor, proposal, claim.item_id)
            key = work_item_run_key(claim.item_id)
            idem = _key(
                "actions.workspace-run-idempotency/v1",
                self.scope.application.workspace_id,
                key,
            )
            pins = self.db.all(RunPin, where="idempotency_id=?", values=[idem])
            if len(pins) != 1 or pins[0].idempotency_key != key:
                raise ReviewConflict("retained dispatch required")
            pin = pins[0]
            run = _one(self.db, Run, pin.run_id)
            if run.status == RunStatus.PASSED:
                return self._terminal(actor, self._ticket(proposal, claim, pin))
            self.reviews.queue(self.scope)._require(claim)
            inputs = WorkerInput.model_validate_json(run.inputs)
            if (
                self.outputs._pinned(pin) != self.plan.snapshot
                or inputs != self._inputs(proposal, inputs.initial_claim.as_claim())
                or inputs.initial_claim.item_id != claim.item_id
            ):
                raise AccessDenied("recovery source/input binding differs")
            original = run.result
            if original is None:
                raise ReviewConflict("retained dispatch evidence required")
            record = self._result(run)
            if (
                not isinstance(record, dict)
                or record.get("version") != "actions.invoice-dispatch/v1"
            ):
                raise ReviewConflict("retained dispatch evidence required")
            old = WorkerTicket(
                proposal=proposal,
                work_item_claim=ClaimValue.model_validate(record["claim"]),
                fence=AttemptFence.model_validate(record["fence"]),
            )
            attempt = _one(self.db, RunAttempt, pin.current_attempt_id)
            if (
                old.fence.run_id != run.id
                or old.fence.attempt_id != attempt.id
                or old.fence.epoch != pin.epoch
                or old.fence.owner_id != attempt.owner_id
                or old.claim.item_id != claim.item_id
            ):
                raise ReviewConflict("retained dispatch identity differs")
            if int(attempt.lease_deadline_ms) > _now(self.db):
                if old.claim != claim:
                    raise FenceRejected("current Attempt cannot be recovered")
                active = self._ticket(proposal, claim, pin)
                if record.get("reconciled") is None:
                    return active
                return self.complete(actor, active)
            expired_epoch = pin.epoch
        retained = None
        if record["launch"] is not None or record.get("reconciled") is not None:
            evidence, executed, _ = self._execution_evidence(old, record)
            proof = hashlib.sha256(
                _canonical(evidence, 2 * 1024 * 1024).encode()
            ).hexdigest()
            launch = (
                record["reconciled"]["launch"]
                if record.get("reconciled") is not None
                else record["launch"]
            )
            retained = {
                "ticket": executed.model_dump(mode="json"),
                "launch": launch,
                "proof_digest": proof,
            }
            disposition = "verified-private-result-no-reexecution"
        else:
            proof = hashlib.sha256(original.encode()).hexdigest()
            disposition = "no-admitted-launch"
        with _transaction(self.db):
            self._approved(actor, proposal, claim.item_id)
            self.reviews.queue(self.scope)._require(claim)
            latest = _one(self.db, RunPin, run.id)
            if (
                latest.epoch != expired_epoch
                or _one(self.db, Run, run.id).result != original
            ):
                raise FenceRejected("recovery raced with another owner")
            recovery = _canonical(
                {
                    "version": "actions.invoice-reconciliation/v1",
                    "disposition": disposition,
                    "epoch": expired_epoch,
                    "evidence_sha256": proof,
                    "work_item_claim": ClaimValue.of(claim).model_dump(),
                },
                1024,
            )
            RunOutputControlPlane(self.db).authorize_recovery(
                run.id, expired_epoch, receipt=recovery
            )
            fence = self.outputs.claim(
                run.id, claim.owner_id, lease_seconds=lease_seconds
            )
            next_record = {
                "version": "actions.invoice-dispatch/v1",
                "claim": ClaimValue.of(claim).model_dump(),
                "fence": fence.model_dump(),
                "launch": None,
                "reconciliations": [
                    *record.get("reconciliations", []),
                    json.loads(recovery),
                ],
            }
            if retained is not None:
                next_record["reconciled"] = retained
            _update(self.db, Run, run.id, {"result": _canonical(next_record, 65536)})
            ticket = WorkerTicket(
                proposal=proposal, work_item_claim=ClaimValue.of(claim), fence=fence
            )
        return self.complete(actor, ticket) if retained is not None else ticket


class WorkerReceipt(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )
    run_id: str
    attempt_id: str
    work_item_id: str
    handle: str
    disposition: Literal["completed", "dead_letter"] = "completed"

    @model_serializer(mode="wrap")
    def omit_legacy_completed_disposition(self, handler):
        data = handler(self)
        if self.disposition == "completed":
            data.pop("disposition", None)
        return data
