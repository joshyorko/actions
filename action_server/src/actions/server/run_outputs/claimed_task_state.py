"""Read-only cancellation evidence, never execution or output authority.

Caller must authorize Task identity/TTL and live queue plus Run read/cancel rights
before calling, and retain the SQL transaction across authorization and this read.
The live Robot receipt validator is deliberately unchanged.
"""
from __future__ import annotations

import datetime
from typing import Literal

from actions.work_items import State
from actions.work_items._adapters._sql_review import FORMAT

from actions.server._models import Run, RunStatus
from actions.server.data_queries.invoice_worker import work_item_run_key
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.foundry.generic_work_item_execution import (
    GenericInput,
    GenericWorkItemExecution,
    _digest,
)
from actions.server.foundry.robot_execution import (
    DISCRIMINATOR,
    RobotLaunchIntent,
    RobotSelection,
    encode_robot_inputs,
)
from actions.server.foundry.robot_journal import _decode, _launch
from actions.server.foundry.robot_package_builder import RccRobotPlan
from actions.server.foundry.robot_receipts import _integer, _read, _same
from actions.server.foundry.robot_retained_projection import retained_robot_projection
from actions.server.run_outputs.claimed_intent import ClaimedTaskIntent
from actions.server.run_outputs.models import RunAdmission, RunAttempt, RunPin
from actions.server.run_outputs.service import (
    MAX_INPUT_BYTES,
    MAX_RESULT_BYTES,
    FenceRejected,
    _admission,
    _canonical,
    _key,
    _one,
)
from actions.server.run_outputs.types import AttemptFence


def _milliseconds(value: str) -> int:
    if (
        not isinstance(value, str)
        or not value.isascii()
        or not value.isdecimal()
        or len(value) > 16
        or str(int(value)) != value
        or int(value) > 9_007_199_254_740_991
    ):
        raise ValueError("canonical retained timestamp required")
    return int(value)


def validate_claimed_cancellation(
    service: GenericWorkItemExecution,
    intent: ClaimedTaskIntent,
    run: Run,
    pin: RunPin,
    fence: AttemptFence | None = None,
) -> Literal["pending_cancelled", "active_unconfirmed", "active_cancelled"]:
    """Verify retained cancellation facts without acquiring any mutation right.

    No provider access, lease renewal, queue mutation, live-fence acquisition or
    terminal execution confirmation. Expired Attempt leases remain readable.
    """
    try:
        if (
            type(service) is not GenericWorkItemExecution
            or not service.db.in_transaction()
        ):
            raise ValueError("exact Generic owner and caller transaction required")
        if type(intent) is not ClaimedTaskIntent:
            raise ValueError("validated claimed Task intent required")
        db, snapshot, claim = service.db, intent.snapshot, intent.claim
        queue_name = service.policy.input_queue
        if queue_name is None:
            raise ValueError("claimed input queue required")
        current, current_pin = _one(db, Run, run.id), _one(db, RunPin, run.id)
        if (
            current != run
            or current_pin != pin
            or service.snapshot != snapshot
            or pin.id != run.id
            or pin.run_id != run.id
            or pin.workspace_id != snapshot.workspace_id
            or run.action_id != snapshot.action_id
            or not _integer(run.status, RunStatus.CANCELLED)
            or not _integer(pin.cancel_requested, 1)
            or pin.cancel_requested != 1
            or claim.queue != service.queue_ref(queue_name)
            or claim.queue.deployment != snapshot.deployment
        ):
            raise ValueError("current cancellation scope differs")
        admission = _one(db, RunAdmission, pin.run_admission_id)
        admission_id, admitted = _admission(snapshot)
        if (
            admission.id != admission_id
            or admission.snapshot_json != admitted
            or admission.workspace_id != snapshot.workspace_id
            or admission.deployment_id != snapshot.deployment_id
            or pin.request_fingerprint
            != _key("actions.run-request/v1", admitted, run.inputs)
            or pin.idempotency_key != work_item_run_key(claim.item_id)
            or pin.idempotency_id
            != _key(
                "actions.workspace-run-idempotency/v1",
                snapshot.workspace_id,
                work_item_run_key(claim.item_id),
            )
        ):
            raise ValueError("pinned claimed admission differs")
        inputs = _read(run.inputs, MAX_INPUT_BYTES)
        if (
            _canonical(inputs, MAX_INPUT_BYTES) != run.inputs
            or _digest(inputs) != intent.input_digest
        ):
            raise ValueError("claimed input digest differs")
        item = _one(db, FencedWorkItem, claim.item_id)
        envelope = GenericInput.model_validate_json(item.payload)
        stored = FoundryRepository(db).get_revision(snapshot.deployment)
        projected = retained_robot_projection(db, snapshot)
        if (
            stored is None
            or tuple(
                p
                for p in stored.revision.specification.work_item_policies
                if p.capability == snapshot.capability
            )
            != (service.policy,)
            or envelope.policy != service.policy
            or envelope.snapshot != snapshot
            or not _same(envelope.inputs, inputs)
            or envelope.input_digest != intent.input_digest
            or item.workspace_id != snapshot.workspace_id
            or item.queue_name != service.policy.input_queue
            or not _integer(item.claim_epoch, 2_147_483_647)
            or item.claim_epoch != claim.epoch
            or item.state != State.FAILED.value
            or not _integer(item.cancel_requested, 1)
            or item.cancel_requested != 1
            or item.claim_owner != ""
            or item.claim_deadline_ms != "0"
            or item.error_message != "cancelled"
            or item.format != FORMAT
            or projected.work_items.mode != "consumer"
            or projected.work_items.allow_outputs
        ):
            raise ValueError("original cancelled item evidence differs")
        service.policy.require_declaration(projected.work_items)
        updated = _milliseconds(pin.state_updated_ms)
        started = datetime.datetime.fromisoformat(run.start_time)
        if (
            started.tzinfo is None
            or started.utcoffset() != datetime.timedelta(0)
            or started.microsecond % 1000
        ):
            raise ValueError("canonical UTC admission timestamp required")
        elapsed = started - datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
        created = (
            elapsed.days * 86400000
            + elapsed.seconds * 1000
            + elapsed.microseconds // 1000
        )
        if created < 0 or updated < created:
            raise ValueError("cancellation lifecycle timestamp differs")
        if fence is None:
            if (
                run.status != RunStatus.CANCELLED
                or pin.current_attempt_id != ""
                or not _integer(pin.epoch, 2_147_483_647)
                or pin.epoch != 0
                or run.result is not None
                or db.all(RunAttempt, where="run_id=?", values=[run.id])
            ):
                raise ValueError("pending cancellation contains execution evidence")
            return "pending_cancelled"
        fence = AttemptFence.model_validate(fence)
        attempt = _one(db, RunAttempt, fence.attempt_id)
        terminal = run.status == RunStatus.CANCELLED
        if (
            run.status not in (RunStatus.RUNNING, RunStatus.CANCELLED)
            or pin.current_attempt_id != fence.attempt_id
            or pin.epoch != fence.epoch
            or run.id != fence.run_id
            or attempt.run_id != run.id
            or attempt.workspace_id != snapshot.workspace_id
            or attempt.owner_id != fence.owner_id
            or fence.owner_id != claim.owner_id
            or attempt.epoch != fence.epoch
            or attempt.state != ("cancelled" if terminal else "running")
            or not _integer(pin.epoch, 2_147_483_647)
            or not _integer(attempt.epoch, 2_147_483_647)
        ):
            raise ValueError("cancelled Attempt identity differs")
        heartbeat = _milliseconds(attempt.heartbeat_ms)
        deadline = _milliseconds(attempt.lease_deadline_ms)
        if not created <= heartbeat < deadline or updated < heartbeat:
            raise ValueError("cancelled Attempt timestamps differ")
        record = _read(run.result, MAX_RESULT_BYTES)
        expected_claim = {
            "item_id": claim.item_id,
            "owner_id": claim.owner_id,
            "epoch": claim.epoch,
        }
        if (
            not isinstance(record, dict)
            or set(record)
            != (
                {"version", "mode", "claim", "fence", "launch"}
                | ({"cancellation"} if terminal else set())
            )
            or record["version"] != DISCRIMINATOR
            or record["mode"] != "work-items"
            or not _same(record["claim"], expected_claim)
            or not _same(record["fence"], fence.model_dump(mode="json"))
        ):
            raise ValueError("closed original Robot dispatch required")
        launch = record["launch"]
        if terminal:
            confirmation = record["cancellation"]
            if (
                launch is None
                or not isinstance(confirmation, dict)
                or set(confirmation)
                != {
                    "version",
                    "confirmed_ms",
                    "execution_stopped",
                    "descendants_reaped",
                }
                or confirmation["version"] != "actions.robot-cancellation/v1"
                or confirmation["confirmed_ms"] != pin.state_updated_ms
                or confirmation["execution_stopped"] is not True
                or confirmation["descendants_reaped"] is not True
            ):
                raise ValueError("closed stopped-launch confirmation required")
        if launch is not None:
            if not isinstance(launch, dict) or set(launch) != {
                "discriminator",
                "selection_encoding",
                "selection",
                "fence",
                "launch_id",
            }:
                raise ValueError("closed original Robot launch required")
            decoded = _decode(launch["selection"])
            plan = projected.plan
            rcc = (
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
                projected.suite_path,
                projected.suite_name,
                projected.task_name,
                projected.source_digest,
                projected.input_schema,
                projected.output_schema,
                encode_robot_inputs(inputs),
                adapter_version=plan.adapter_version,
                robot_version=plan.robot_version,
                python_version=plan.python_version,
                platform_tag=plan.platform_tag,
                **rcc,
            )
            if not _same(
                _launch(RobotLaunchIntent(selection, fence, launch["launch_id"])),
                launch,
            ) or not _same(
                _launch(RobotLaunchIntent(decoded, fence, launch["launch_id"])), launch
            ):
                raise ValueError("original Robot launch selection differs")
        return "active_cancelled" if terminal else "active_unconfirmed"
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise FenceRejected("Claimed Task cancellation evidence unavailable") from exc
