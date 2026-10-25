"""Strict retained standalone Robot metadata reads; caller owns live authorization.

No provider or registry reader is invoked. SQL metadata integrity is not a claim
that source/output bytes have been read, nor permission to execute or read them.
"""
from __future__ import annotations

import json
import re
from dataclasses import fields

from actions.server._common.process import ProcessTreeCleanupResult
from actions.server._models import Run, RunStatus
from actions.server.foundry.robot_execution import (
    DISCRIMINATOR,
    RobotLaunchIntent,
    RobotSelection,
)
from actions.server.foundry.robot_journal import _closed_pairs, _decode, _launch
from actions.server.foundry.robot_package_builder import RccRobotPlan
from actions.server.foundry.robot_retained_projection import retained_robot_projection
from actions.server.run_outputs.models import RunAdmission, RunAttempt, RunOutput
from actions.server.run_outputs.service import (
    MAX_INPUT_BYTES,
    MAX_RESULT_BYTES,
    FenceRejected,
    _admission,
    _canonical,
    _key,
    _lock_run,
    _now,
    _one,
    _transaction,
)
from actions.server.run_outputs.types import (
    AttemptFence,
    ExecutionSnapshot,
    OutputRef,
    SealReceipt,
)


def _encoded(value):
    # Unlike Python equality (and numeric-normalizing JCS), this distinguishes
    # true, 1, and 1.0 at every nested scalar boundary.
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _same(left, right):
    return _encoded(left) == _encoded(right)


def _read(raw, limit):
    if not isinstance(raw, str) or len(raw.encode()) > limit:
        raise ValueError("bounded retained Robot JSON required")
    return json.loads(
        raw,
        object_pairs_hook=_closed_pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")),
    )


def _integer(value, maximum=9_007_199_254_740_991):
    return (
        isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= maximum
    )


def robot_output_names(record):
    """Names after strict validation only; this helper grants no read authority."""
    try:
        kind = record["launch"]["selection"]["plan_kind"]
    except (KeyError, TypeError):
        raise FenceRejected("Robot output plan missing") from None
    if kind not in ("direct", "rcc"):
        raise FenceRejected("Robot output plan unsupported")
    names = {"robot-stdout.log", "robot-stderr.log", "robot-output.xml"}
    if kind == "rcc":
        names.add("rcc-receipt.json")
    return names


def validate_robot_record(
    db,
    registry,
    snapshot,
    run,
    fence,
    record,
    *,
    claim,
    terminal,
    outputs=None,
    _allow_expired_terminal=False,
):
    """Pure SQL retained integrity check; safe inside the caller's transaction.

    The caller must authenticate/authorize first. The private expiry exception is
    terminal metadata acknowledgement only, never output resolution permission.
    ``registry`` stays in the shared port signature but is deliberately not read.
    """
    from actions.server.foundry.robot_runtime_runner import TERMINAL_VERSION

    try:
        if (
            claim is not None
            or not isinstance(terminal, bool)
            or not isinstance(_allow_expired_terminal, bool)
            or (_allow_expired_terminal and not terminal)
        ):
            raise ValueError("standalone Robot mode and explicit read scope required")
        snapshot = ExecutionSnapshot.model_validate(snapshot)
        fence = AttemptFence.model_validate(fence)
        outer = _read(run.result, MAX_RESULT_BYTES)
        if terminal:
            if (
                not isinstance(outer, dict)
                or set(outer) != {"version", "result", "outputs"}
                or not _integer(outer["version"], 1)
                or outer["version"] != 1
                or not _same(outer["outputs"], outputs)
            ):
                raise ValueError("closed Robot terminal envelope required")
            retained = outer["result"]
        else:
            if outputs is not None:
                raise ValueError("dispatch cannot attach terminal outputs")
            retained = outer
        if not isinstance(record, dict) or not _same(retained, record):
            raise ValueError("Robot record differs from retained carrier")
        expected = (
            {"version", "mode", "claim", "fence", "launch"}
            if not terminal
            else {
                "version",
                "mode",
                "claim",
                "launch",
                "publicationFence",
                "packageRevision",
                "runtimePlanDigest",
                "sourceArtifactDigest",
                "status",
                "returnCode",
                "cleanup",
                "outputs",
                "actionResult",
            }
        )
        fence_key = "publicationFence" if terminal else "fence"
        if (
            set(record) != expected
            or record["version"] != (TERMINAL_VERSION if terminal else DISCRIMINATOR)
            or record["mode"] != "standalone"
            or record["claim"] is not None
            or not _same(record[fence_key], fence.model_dump(mode="json"))
        ):
            raise ValueError("closed standalone Robot record required")
        # The existing Run/workspace lock serializes authoritative Run/Attempt,
        # package and output writers. Nested use retains the caller's boundary.
        with _transaction(db):
            pin = _lock_run(db, fence.run_id)
            current = _one(db, Run, fence.run_id)
            attempt = _one(db, RunAttempt, fence.attempt_id)
            if (
                run.id != fence.run_id
                or current.id != run.id
                or current.inputs != run.inputs
                or current.result != run.result
                or current.action_id != snapshot.action_id
                or current.status != run.status
                or not _integer(run.status, RunStatus.CANCELLED)
                or pin.id != run.id
                or pin.run_id != run.id
                or pin.workspace_id != snapshot.workspace_id
                or pin.current_attempt_id != fence.attempt_id
                or pin.epoch != fence.epoch
                or attempt.run_id != run.id
                or attempt.workspace_id != snapshot.workspace_id
                or attempt.owner_id != fence.owner_id
                or attempt.epoch != fence.epoch
            ):
                raise ValueError("Robot current Run/Attempt scope differs")
            expected_states = {
                RunStatus.RUNNING: "running",
                RunStatus.PASSED: "succeeded",
                RunStatus.FAILED: "failed",
                RunStatus.CANCELLED: "cancelled",
            }
            if (
                attempt.state != expected_states.get(run.status)
                or terminal != (run.status in (RunStatus.PASSED, RunStatus.FAILED))
                or (terminal and pin.cancel_requested != 0)
            ):
                raise ValueError("Robot Run/Attempt lifecycle differs")
            admission = _one(db, RunAdmission, pin.run_admission_id)
            admission_id, admitted = _admission(snapshot)
            if (
                admission.id != admission_id
                or admission.snapshot_json != admitted
                or admission.workspace_id != snapshot.workspace_id
                or admission.deployment_id != snapshot.deployment_id
                or pin.request_fingerprint
                != _key("actions.run-request/v1", admitted, run.inputs)
            ):
                raise ValueError("Robot pinned admission differs")
            inputs = _read(run.inputs, MAX_INPUT_BYTES)
            if _canonical(inputs, MAX_INPUT_BYTES) != run.inputs:
                raise ValueError("Robot inputs changed from canonical admission")
            projected = retained_robot_projection(db, snapshot)
            launch = record["launch"]
            if launch is None:
                if terminal:
                    raise ValueError("terminal Robot launch missing")
                return
            if not isinstance(launch, dict) or set(launch) != {
                "discriminator",
                "selection_encoding",
                "selection",
                "fence",
                "launch_id",
            }:
                raise ValueError("closed Robot launch required")
            selection = _decode(launch["selection"])
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
            expected_selection = RobotSelection(
                snapshot,
                plan.runtime_kind,
                projected.suite_path,
                projected.suite_name,
                projected.task_name,
                projected.source_digest,
                projected.input_schema,
                projected.output_schema,
                _encoded(inputs).encode(),
                adapter_version=plan.adapter_version,
                robot_version=plan.robot_version,
                python_version=plan.python_version,
                platform_tag=plan.platform_tag,
                **rcc,
            )
            expected_intent = RobotLaunchIntent(
                expected_selection, fence, launch["launch_id"]
            )
            if not _same(_launch(expected_intent), launch) or not _same(
                _launch(RobotLaunchIntent(selection, fence, launch["launch_id"])),
                launch,
            ):
                raise ValueError("Robot launch differs from immutable selection")
            if not terminal:
                return
            _terminal(
                db,
                snapshot,
                run,
                fence,
                record,
                outputs,
                projected,
                _allow_expired_terminal,
            )
    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        UnicodeError,
        RecursionError,
        OverflowError,
    ):
        raise FenceRejected("retained Robot record unavailable or differs") from None


def _terminal(db, snapshot, run, fence, record, outputs, projected, allow_expired):
    status = "PASS" if run.status == RunStatus.PASSED else "FAIL"
    if (
        record["status"] != status
        or not _integer(record["returnCode"], 1)
        or record["returnCode"] != (0 if status == "PASS" else 1)
        or not _same(
            record["packageRevision"],
            snapshot.capability.package_revision.model_dump(mode="json"),
        )
        or record["runtimePlanDigest"] != snapshot.runtime_plan.plan_digest.root
        or record["sourceArtifactDigest"] != projected.source_digest
        or not _same(
            record["actionResult"],
            {
                "suite": projected.suite_name,
                "task": projected.task_name,
                "status": status,
            },
        )
    ):
        raise ValueError("Robot terminal outcome differs")
    cleanup = record["cleanup"]
    if (
        not isinstance(cleanup, dict)
        or set(cleanup) != {field.name for field in fields(ProcessTreeCleanupResult)}
        or cleanup["wrapper_reaped"] is not True
        or cleanup["descendant_snapshot_complete"] is not True
        or cleanup["live_descendant_pids"] != []
        or cleanup["errors"] != []
        or not isinstance(cleanup["zombie_descendant_pids"], list)
        or any(
            not _integer(pid, 2_147_483_647) or pid == 0
            for pid in cleanup["zombie_descendant_pids"]
        )
        or len(set(cleanup["zombie_descendant_pids"]))
        != len(cleanup["zombie_descendant_pids"])
    ):
        raise ValueError("Robot process cleanup not proven")
    entries = record["outputs"]
    names = robot_output_names(record)
    if not isinstance(entries, list) or len(entries) != len(names):
        raise ValueError("closed Robot output inventory required")
    refs = []
    seen = set()
    ids = set()
    now = _now(db)
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
            "name",
            "ref",
            "digest",
            "size",
            "observedBytes",
            "truncated",
        }:
            raise ValueError("closed Robot output descriptor required")
        name = entry["name"]
        if not isinstance(name, str) or name not in names or name in seen:
            raise ValueError("unique Robot output name required")
        seen.add(name)
        ref = OutputRef.model_validate(entry["ref"])
        if (
            not _same(ref.model_dump(mode="json"), entry["ref"])
            or ref.output_id in ids
            or ref.run_id != run.id
            or ref.workspace_id != snapshot.workspace_id
        ):
            raise ValueError("unique exact Robot output reference required")
        ids.add(ref.output_id)
        row = _one(db, RunOutput, ref.output_id)
        media = (
            "application/xml"
            if name == "robot-output.xml"
            else "application/json"
            if name == "rcc-receipt.json"
            else "application/octet-stream"
        )
        limit = (
            1024 * 1024
            if name in {"robot-output.xml", "rcc-receipt.json"}
            else 256 * 1024
        )
        if (
            not _integer(entry["size"], limit)
            or not _integer(entry["observedBytes"])
            or entry["observedBytes"] < entry["size"]
            or not isinstance(entry["truncated"], bool)
            or entry["truncated"] != (entry["observedBytes"] > entry["size"])
            or (name in {"robot-output.xml", "rcc-receipt.json"} and entry["truncated"])
        ):
            raise ValueError("bounded Robot output counts required")
        seal = SealReceipt(object_ref=row.object_ref, digest=row.digest, size=row.size)
        if (
            row.workspace_id != snapshot.workspace_id
            or row.run_id != run.id
            or row.run_attempt_id != fence.attempt_id
            or row.epoch != fence.epoch
            or row.provider_key != snapshot.provider_key
            or row.name != name
            or row.media_type != media
            or row.state != "final"
            or seal.digest != entry["digest"]
            or seal.size != entry["size"]
            or not isinstance(row.expires_ms, str)
            or not re.fullmatch(r"0|[1-9][0-9]{0,15}", row.expires_ms)
            or (not allow_expired and int(row.expires_ms) <= now)
        ):
            raise ValueError("Robot output seal/scope/retention differs")
        refs.append(ref.model_dump(mode="json"))
    final = db.select(
        RunOutput,
        "SELECT * FROM run_output WHERE run_id=? AND state='final' LIMIT 5",
        [run.id],
    )
    if (
        {row.id for row in final} != ids
        or len(final) != len(ids)
        or not _same(outputs, refs)
    ):
        raise ValueError("Robot final output inventory differs")
