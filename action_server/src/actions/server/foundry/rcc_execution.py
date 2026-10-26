"""Trusted-host RCC execution for an admitted generated Action Run.

Generated Python runs as trusted developer code through the pinned, prepared
RCC environment. This adapter bounds the process and its inputs; it is not an
operating-system security sandbox and does not admit external effects.
"""

from __future__ import annotations

import hashlib
import json
import os
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time
import zipfile
from contextlib import ExitStack
from pathlib import Path, PurePosixPath
from threading import Event
from typing import Any, Callable, cast
from uuid import uuid4

from actions.server._models import Run, RunStatus
from actions.server._rcc_runtime_adapter import (
    RCC_VERSION,
    RccRuntimeDescriptor,
    build_exec_command,
    read_receipt,
    verify_rcc_version,
)
from actions.server.deployments.package_revision_compiler import (
    MAX_COMPILER_SOURCE_FILE_BYTES,
    MAX_COMPILER_SOURCE_FILES,
    MAX_COMPILER_SOURCE_TOTAL_BYTES,
    PreparedRccEnvironment,
)
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputService,
    _advance_lifecycle,
    _canonical,
    _one,
    _transaction,
    _update,
)
from actions.server.run_outputs.types import Actor, AttemptFence, ExecutionSnapshot

_JOURNAL_VERSION = "actions.generated-rcc-dispatch/v1"
_JOURNAL_LIMIT = 64 * 1024
_INPUT_LIMIT = 256 * 1024
_RESULT_LIMIT = 512 * 1024
_RECEIPT_LIMIT = 1024 * 1024
_LOG_LIMIT = 256 * 1024
_LOG_READ_BYTES = 64 * 1024
_POST_EXIT_LOG_GRACE_SECONDS = 0.5
_OUTPUT_RETENTION_SECONDS = 3600
_LEASE_SECONDS = 30
_HEARTBEAT_SECONDS = 8
_MAX_TIMEOUT_SECONDS = 600


def _posix_fchmod() -> Callable[[int, int], None]:
    value = getattr(os, "fchmod", None)
    if not callable(value):
        raise RuntimeError("POSIX operation requires fchmod")
    return cast(Callable[[int, int], None], value)


class RccCleanupIncomplete(RuntimeError):
    """Owned process termination is unconfirmed; retain host resources."""


class LogicalPreparationCleanupIncomplete(RccCleanupIncomplete):
    """Reachable untransferred preparation may be settled by the host later."""

    def __init__(self, owner):
        super().__init__("logical preparation cleanup incomplete")
        self.owner = owner


class _OwnedProcessCapture:
    """Own an explicitly created POSIX group for trusted, nonescaping code.

    Historical descendant samples cannot prove cleanup after wrapper exit.
    Group enumeration and a post-termination rescan cover ordinary late forks.
    This is not containment for code that deliberately starts another session.
    """

    def __init__(self, process, *, owns_session=False):
        self.process = process
        self.owned = {}
        self.complete = False
        self.failed = False
        self._cleanup_result = None
        self.owns_session = owns_session and os.name == "posix"
        self.capture()

    def capture(self):
        import psutil

        self.complete = False
        if not self.owns_session:
            self.failed = True
            return
        try:
            for child in psutil.process_iter():
                try:
                    if (
                        child.pid != self.process.pid
                        and os.getpgid(child.pid) == self.process.pid
                    ):
                        self.owned[(child.pid, child.create_time())] = child
                except (ProcessLookupError, psutil.NoSuchProcess):
                    continue
            self.complete = True
        except Exception:
            self.failed = True

    def cleanup(self):
        if self._cleanup_result is not None:
            return self._cleanup_result
        from dataclasses import replace

        import psutil

        from actions.server._common.process import force_kill_process_tree_until

        deadline = time.monotonic() + 10
        while True:
            # Kill the kernel-owned group before taking the final PID snapshot.
            # Otherwise a sampled survivor could fork and exit between the
            # enumeration and status check, leaving an unobserved live child.
            if self.owns_session:
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                except OSError:
                    self.failed = True
            self.capture()
            result = force_kill_process_tree_until(
                self.process,
                list(self.owned.values()),
                deadline,
                snapshot_complete_before_call=self.complete and not self.failed,
            )
            self.capture()
            live = []
            for child in self.owned.values():
                try:
                    if child.is_running() and child.status() != psutil.STATUS_ZOMBIE:
                        live.append(child.pid)
                except psutil.NoSuchProcess:
                    continue
                except Exception:
                    self.failed = True
            if not live or time.monotonic() >= deadline:
                result = replace(
                    result,
                    live_descendant_pids=tuple(sorted(set(live))),
                    descendant_snapshot_complete=self.complete and not self.failed,
                )
                if result.execution_stopped:
                    self._cleanup_result = result
                return result


class GeneratedRccExecution:
    """Execute one pre-admitted Run under its existing AttemptFence.

    The trusted Run creator must seed ``Run.result`` with this journal before
    calling ``execute``::

        {"version":"actions.generated-rcc-dispatch/v1",
         "mode":"work-items",
         "claim":{"item_id":"<uuid>","owner_id":"<uuid>","epoch":1},
         "fence":{"run_id":"<uuid>","attempt_id":"<uuid>",
                  "owner_id":"<uuid>","epoch":1},
         "launch":null}

    The journal is replaced with a launch intent before RCC starts. Any later
    call with a launch intent fails closed and requires explicit reconciliation.
    """

    def __init__(
        self,
        registry: FoundryPackageRegistry,
        outputs: RunOutputService,
        prepared: PreparedRccEnvironment,
        rcc: Path,
        execution_root: Path,
        *,
        logical_execution=None,
    ) -> None:
        if not isinstance(prepared, PreparedRccEnvironment):
            raise TypeError("exact retained PreparedRccEnvironment required")
        if prepared.rcc_version != RCC_VERSION:
            raise ValueError("pinned RCC 18.19.3 preparation required")
        if not isinstance(rcc, Path) or not rcc.is_absolute():
            raise ValueError("absolute trusted pinned RCC executable required")
        rcc = rcc.resolve(strict=True)
        if not rcc.is_file() or not os.access(rcc, os.X_OK):
            raise ValueError("trusted pinned RCC executable is unavailable")
        if not isinstance(execution_root, Path) or not execution_root.is_absolute():
            raise ValueError("absolute execution root required")
        if execution_root.exists() and (
            execution_root.is_symlink() or not execution_root.is_dir()
        ):
            raise ValueError("regular execution root directory required")
        if prepared.robocorp_home.is_symlink() or not prepared.robocorp_home.is_dir():
            raise ValueError("exact prepared RCC home is unavailable")
        self.registry = registry
        self.outputs = outputs
        if logical_execution is not None and (
            logical_execution.db is not outputs.db
            or logical_execution.registry is not registry
        ):
            raise TypeError("shared canonical logical execution required")
        self.logical_execution = logical_execution
        self.prepared = prepared
        self.rcc = rcc
        self.execution_root = execution_root.resolve()

    def execute(
        self,
        actor,
        fence,
        *,
        cancelled,
        timeout_seconds=120,
        publication_cancelled=None,
    ):
        """Optional publication cancellation must be a trusted pure local predicate."""
        started = time.monotonic()
        state = {"owner": None, "prepared": None, "stack": ExitStack()}
        uncertain = False
        try:
            return self._execute(
                actor,
                fence,
                cancelled=cancelled,
                timeout_seconds=timeout_seconds,
                started=started,
                logical_state=state,
                publication_cancelled=publication_cancelled,
            )
        except RccCleanupIncomplete:
            uncertain = True
            raise
        finally:
            owner = state["owner"]
            if owner is not None:
                owner.stop()
                if owner.thread.is_alive() and not owner.settle(10):
                    state["stack"].close()
                    raise LogicalPreparationCleanupIncomplete(owner)
            state["stack"].close()
            if owner is not None and not uncertain:
                if state["prepared"] is not None:
                    self.logical_execution.release_preparation(owner, state["prepared"])
                else:
                    owner.settle(0)

    def _prepare_logical(
        self,
        actor,
        fence,
        cancelled,
        deadline,
        journal,
        state,
        *,
        publication_cancelled=None,
    ):
        stop = Event()
        owner = self.logical_execution.begin_preparation(
            actor, fence, cancelled=stop, deadline=deadline
        )
        state["owner"] = owner
        heartbeat_at = time.monotonic() + _HEARTBEAT_SECONDS
        while not owner.done.wait(0.05):
            self._check_deadline(deadline)
            self._check_cancel(cancelled, actor, fence)
            if time.monotonic() >= heartbeat_at:
                if self._read_journal(fence, actor=actor) != journal:
                    raise FenceRejected("logical preparation journal changed")
                self.outputs.heartbeat(fence, lease_seconds=_LEASE_SECONDS)
                heartbeat_at = time.monotonic() + _HEARTBEAT_SECONDS
        self._check_deadline(deadline)
        self._check_cancel(cancelled, actor, fence)
        prepared = owner.take_result()
        state["prepared"] = prepared
        self.logical_execution.configured.check_current()
        if prepared.actor != actor or prepared.fence != fence:
            raise FenceRejected("logical preparation scope changed")
        self.logical_execution.recheck(actor, fence, prepared)

        def publication_check():
            # Runs after SQL lock acquisition. Never call the SQL-reading
            # cancellation callback or mutate cancellation authority here.
            self._check_deadline(deadline)
            if owner.cancelled.is_set() or (
                publication_cancelled is not None and publication_cancelled()
            ):
                raise FenceRejected("generated Action publication cancelled")

        state["stack"].enter_context(
            self.outputs.bind_logical_execution(
                self.logical_execution, prepared, publication_check=publication_check
            )
        )
        return prepared

    @staticmethod
    def _publication_cancel_predicate(cancelled, explicit):
        if explicit is not None:
            return GeneratedRccExecution._cancel_predicate(explicit)
        # Detached cancellation callbacks query SQL. Only an actual local Event
        # is automatically safe inside the publication transaction.
        return cancelled.is_set if isinstance(cancelled, Event) else lambda: False

    @staticmethod
    def _check_deadline(deadline):
        if deadline is not None and time.monotonic() >= deadline:
            raise TimeoutError("generated Action total deadline")

    def _execute(
        self,
        actor: Actor,
        fence: AttemptFence,
        *,
        cancelled: Any,
        timeout_seconds: int = 120,
        started=None,
        logical_state=None,
        publication_cancelled=None,
    ) -> Run:
        """Run the one admitted Action and publish its measured JSON result.

        The host callback or event is polled during execution. In reviewed
        Work Item dispatch, the injected RunOutputService implementation also
        checks or renews the exact queue claim on heartbeat, stage and publish;
        terminal publication keeps both fences in its shared SQL transaction.
        """
        actor = Actor.model_validate(actor)
        fence = AttemptFence.model_validate(fence)
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, int)
            or not 1 <= timeout_seconds <= _MAX_TIMEOUT_SECONDS
        ):
            raise ValueError("bounded execution deadline required")
        original_cancel = self._cancel_predicate(cancelled)

        def is_cancelled():
            owner = logical_state["owner"]
            return original_cancel() or (owner is not None and owner.cancelled.is_set())

        verify_rcc_version(self.rcc)

        self.outputs.heartbeat(fence, lease_seconds=_LEASE_SECONDS)
        snapshot, inputs = self.outputs.execution_context(actor, fence)
        compiled, action, input_schema, output_schema = self._verified_selection(
            snapshot
        )
        from actions.server.foundry.logical_receipts import (
            requirement_ids,
            versions_for_selection,
        )

        requirements = requirement_ids(self.registry, snapshot)
        bound = bool(requirements)
        if bound and not callable(
            getattr(self.outputs, "bind_logical_execution", None)
        ):
            raise AccessDenied("logical domain publication required")
        deadline = started + timeout_seconds if bound else None
        self._check_deadline(deadline)
        input_bytes = _canonical(inputs, _INPUT_LIMIT).encode("utf-8")
        self._validate_json(input_bytes, input_schema, "Run inputs")

        journal = self._read_journal(fence, actor=actor)
        if journal["launch"] is not None:
            raise FenceRejected("prior RCC launch requires explicit reconciliation")
        self._check_cancel(is_cancelled, actor, fence)
        launch_id = str(uuid4())
        lineage = self._lineage(snapshot, journal["claim"], fence)
        launch = {
            "id": launch_id,
            "workItemClaim": journal["claim"],
            "lineage": lineage,
            "inputDigest": self._digest(input_bytes),
            "sourceArtifactDigest": compiled.source_artifact_digest,
            "packageRevision": snapshot.capability.package_revision.revision_id.root,
            "runtimePlanDigest": snapshot.runtime_plan.plan_digest.root,
            "rccSpecificationDigest": compiled.rcc_specification_digest,
            "rccArtifactDigest": compiled.rcc_artifact_digest,
        }
        directory = self._launch_directory(fence, launch_id)
        source = directory / "source"
        self._extract_snapshot(compiled.source_archive, source)
        package_yaml = self._read_regular(source / "package.yaml", 32 * 1024)
        if self._digest(package_yaml) != self.prepared.package_yaml_digest:
            raise AccessDenied("prepared RCC manifest differs from immutable source")
        if (
            compiled.rcc_specification_digest
            != self.prepared.build_identity.specification_digest
            or compiled.rcc_artifact_digest
            != self.prepared.build_identity.artifact_digest
        ):
            raise AccessDenied(
                "prepared RCC artifact differs from immutable Runtime Plan"
            )
        logical_summary = None
        if bound:
            from actions.server.foundry.logical_receipts import derive_summary

            self._check_deadline(deadline)
            prepared_reads = self._prepare_logical(
                actor,
                fence,
                is_cancelled,
                deadline,
                journal,
                logical_state,
                publication_cancelled=self._publication_cancel_predicate(
                    cancelled, publication_cancelled
                ),
            )
            logical_summary = derive_summary(prepared_reads).model_dump(mode="json")
            launch["logicalReads"] = logical_summary
            if (
                len(prepared_reads.context) > 256 * 1024
                or self._digest(prepared_reads.context) != prepared_reads.context_digest
            ):
                raise AccessDenied("logical context differs")
            self._write_private(
                directory / "logical-context.json", prepared_reads.context
            )
        self._check_deadline(deadline)
        self._write_private(directory / "input.json", input_bytes)
        receipt_file = directory / "rcc-receipt.json"
        result_file = directory / "action-result.json"

        with _transaction(self.outputs.db):
            # Reviewed output guards acquire Counter/Workspace before Run reads.
            # Establish the writer before inspecting a journal to avoid a
            # SQLite read-to-write upgrade racing another queue writer.
            self.outputs._fence(fence)
            current = self._read_journal(fence, actor=actor)
            if current != journal or current["launch"] is not None:
                raise FenceRejected("Work Items dispatch changed before launch")
            self.outputs._fence(fence)
            current["launch"] = launch
            _update(
                self.outputs.db,
                Run,
                fence.run_id,
                {"result": _canonical(current, _JOURNAL_LIMIT)},
            )
            _advance_lifecycle(self.outputs.db, fence.run_id)
        # A read-after-write catches lost or conflicting journal updates before
        # any generated code is started. If the commit acknowledgement is
        # uncertain, this call does not spawn and a later call remains blocked.
        if self._read_journal(fence, actor=actor) != {**journal, "launch": launch}:
            raise FenceRejected("RCC launch intent could not be confirmed")
        self.outputs.heartbeat(fence, lease_seconds=_LEASE_SECONDS)
        self._check_cancel(is_cancelled, actor, fence)

        self._check_deadline(deadline)
        helper = (
            self._bound_execution_helper(action)
            if bound
            else self._execution_helper(action)
        )
        logical_args = (
            [str(directory / "logical-context.json"), logical_summary["contextDigest"]]
            if logical_summary is not None
            else []
        )
        command = build_exec_command(
            self.rcc,
            RccRuntimeDescriptor(
                artifact_digest=compiled.rcc_artifact_digest,
                provider_reference="local",
            ),
            [
                "python",
                "-I",
                "-B",
                "-c",
                helper,
                str(source),
                str(directory / "input.json"),
                str(result_file),
                *logical_args,
            ],
            receipt_file=receipt_file,
            local_trust_carrier=self.prepared.robocorp_home / "artifacts/v1/trust",
        )
        command.insert(1, "--no-build")
        environment = self._child_environment(directory)
        ownership: _OwnedProcessCapture | None = None
        stdout_bytes = b""
        stderr_bytes = b""
        stdout_capture: dict[str, Any] = {}
        stderr_capture: dict[str, Any] = {}
        completed = False
        try:
            self._check_deadline(deadline)
            process = subprocess.Popen(
                command,
                cwd=source,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                close_fds=True,
                start_new_session=os.name == "posix",
            )
            ownership = _OwnedProcessCapture(process, owns_session=os.name == "posix")
            setattr(process, "_actions_capture_owned", ownership.capture)
            if not bound:
                deadline = time.monotonic() + timeout_seconds
            assert deadline is not None
            (
                stdout_bytes,
                stderr_bytes,
                stdout_capture,
                stderr_capture,
            ) = self._capture_process(
                process,
                actor,
                fence,
                launch,
                is_cancelled,
                deadline,
            )
            try:
                process.wait(timeout=max(0.0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                raise TimeoutError("generated Action RCC deadline") from None
            if process.returncode != 0:
                receipt_bytes, cleanup = self._confirmed_failed_receipt(
                    process, ownership, receipt_file, compiled.rcc_artifact_digest
                )
                self._verify_snapshot_unchanged(source, compiled.source_archive)
                self._check_cancel(is_cancelled, actor, fence)
                return self._publish_failed(
                    actor,
                    fence,
                    snapshot,
                    compiled,
                    journal,
                    launch,
                    receipt_bytes,
                    process.returncode,
                    cleanup,
                    stdout_bytes,
                    stderr_bytes,
                    stdout_capture,
                    stderr_capture,
                )
            receipt_bytes = self._read_regular(receipt_file, _RECEIPT_LIMIT)
            receipt = read_receipt(receipt_file, compiled.rcc_artifact_digest)
            if receipt.get("status") != "completed" or receipt.get("exitCode") != 0:
                raise RuntimeError(
                    "RCC receipt does not prove completed Action execution"
                )
            raw_result = self._read_regular(result_file, _RESULT_LIMIT)
            result_value = self._validate_json(
                raw_result, output_schema, "generated Action result"
            )
            result_bytes = _canonical(result_value, _RESULT_LIMIT).encode("utf-8")
            self._check_cancel(is_cancelled, actor, fence)
            self._assert_live_journal(actor, fence, launch)
            self.outputs.heartbeat(fence, lease_seconds=_LEASE_SECONDS)
            self._verify_snapshot_unchanged(source, compiled.source_archive)
            completed = True
        finally:
            if ownership is not None and (
                ownership.owns_session or ownership.process.poll() != 0
            ):
                cleanup = ownership.cleanup()
                if not cleanup.execution_stopped:
                    raise RccCleanupIncomplete("RCC process cleanup incomplete")

        if not completed:
            raise RuntimeError("generated Action execution did not complete")
        if bound:
            self._check_deadline(deadline)
            self.logical_execution.configured.check_current()
            self.logical_execution.recheck(actor, fence, logical_state["prepared"])
        receipt_digest = self._digest(receipt_bytes)
        execution = {
            "status": "completed",
            "resultDigest": self._digest(result_bytes),
            "receiptDigest": receipt_digest,
            "artifactDigest": compiled.rcc_artifact_digest,
            "stdout": self._capture_receipt(stdout_bytes, stdout_capture),
            "stderr": self._capture_receipt(stderr_bytes, stderr_capture),
        }
        with _transaction(self.outputs.db):
            self.outputs._fence(fence)
            current = self._read_journal(fence, actor=actor)
            if current.get("launch") != launch or current.get("execution") is not None:
                raise FenceRejected("RCC execution journal changed before publication")
            self.outputs._fence(fence)
            self.outputs.heartbeat(fence, lease_seconds=_LEASE_SECONDS)
            current["execution"] = execution
            _update(
                self.outputs.db,
                Run,
                fence.run_id,
                {"result": _canonical(current, _JOURNAL_LIMIT)},
            )
            _advance_lifecycle(self.outputs.db, fence.run_id)

        output_payloads = (
            ("generated-action-result.json", "application/json", result_bytes),
            ("rcc-receipt.json", "application/json", receipt_bytes),
            ("rcc-stdout.log", "application/octet-stream", stdout_bytes),
            ("rcc-stderr.log", "application/octet-stream", stderr_bytes),
        )
        output_refs = []
        output_receipts = []
        if bound:
            for prepared_knowledge in logical_state["prepared"].knowledge:
                pending = prepared_knowledge.ingestion
                if pending is not None:
                    self.logical_execution.recheck(
                        actor, fence, logical_state["prepared"]
                    )
                    output_refs.append(pending.output)
                    output_receipts.append(
                        {
                            "name": pending.output_name,
                            "ref": pending.output.model_dump(mode="json"),
                            "digest": pending.corpus_digest,
                            "size": pending.corpus_size,
                        }
                    )
        for name, media_type, payload in output_payloads:
            if bound:
                self._check_deadline(deadline)
                self.logical_execution.configured.check_current()
                self.logical_execution.recheck(actor, fence, logical_state["prepared"])
            self._check_cancel(is_cancelled, actor, fence)
            output_refs.append(
                self.outputs.stage(
                    fence,
                    self._chunks(payload),
                    name=name,
                    media_type=media_type,
                    retention_seconds=_OUTPUT_RETENTION_SECONDS,
                )
            )
            output_receipts.append(
                {
                    "name": name,
                    "ref": output_refs[-1].model_dump(mode="json"),
                    "digest": self._digest(payload),
                    "size": len(payload),
                }
            )
        result_receipt = {
            "version": versions_for_selection(self.registry, snapshot)[1],
            "mode": journal["mode"],
            "claim": journal["claim"],
            "lineage": lineage,
            "launch": launch,
            "publicationFence": fence.model_dump(),
            "sourceArtifactDigest": compiled.source_artifact_digest,
            "packageRevision": snapshot.capability.package_revision.revision_id.root,
            "runtimePlanDigest": snapshot.runtime_plan.plan_digest.root,
            "rccSpecificationDigest": compiled.rcc_specification_digest,
            "rccArtifactDigest": compiled.rcc_artifact_digest,
            "execution": execution,
            "outputs": output_receipts,
            "actionResult": result_value,
        }
        if bound:
            result_receipt["logicalReads"] = logical_summary
            self._check_deadline(deadline)
        self._check_cancel(is_cancelled, actor, fence)
        with _transaction(self.outputs.db):
            self._assert_live_journal(
                actor, fence, launch, completed_execution=execution
            )
            return self.outputs.publish(
                actor,
                fence,
                output_refs,
                result_receipt,
                terminal_status=RunStatus.PASSED,
            )

    def _verified_selection(
        self, snapshot: ExecutionSnapshot
    ) -> tuple[Any, dict[str, str], dict, dict]:
        if (
            getattr(snapshot, "capability_authority", "legacy-action")
            != "package-revision"
        ):
            raise AccessDenied("immutable Package capability required")
        from actions.server.foundry.execution_selection import compiled_for_snapshot

        compiled = compiled_for_snapshot(self.registry, snapshot)
        evidence = self.registry.evidence(snapshot.capability.package_revision)
        if not evidence.ready:
            raise AccessDenied(
                "successful pinned Package build/import/test evidence required"
            )
        manifest = json.loads(compiled.manifest_json)
        capability = next(
            (
                item
                for item in manifest["capabilities"]
                if item.get("id") == snapshot.capability.capability_id.root
            ),
            None,
        )
        if not isinstance(capability, dict) or capability.get("kind") != "action":
            raise AccessDenied("compiled Action capability is not executable")
        if capability.get("bindingRequirementIds"):
            from actions.server.foundry.generic_work_item_execution import (
                _GenericOutputs,
            )
            from actions.server.foundry.standalone_execution import _StandaloneOutputs

            if self.logical_execution is None or not (
                type(self.outputs) is RunOutputService
                or isinstance(self.outputs, (_GenericOutputs, _StandaloneOutputs))
            ):
                raise AccessDenied("logical execution runtime is not configured")
            declaration = self.registry.get_capability(snapshot.capability)
            if declaration is None or not declaration.binding_requirements:
                raise AccessDenied("logical requirement declaration unavailable")
            for ref in declaration.binding_requirements:
                requirement = self.registry.get_binding_requirement(ref)
                if requirement is None or requirement.contract.kind not in (
                    "data",
                    "knowledge",
                ):
                    raise AccessDenied("logical requirement runtime is unsupported")
            self.logical_execution.require_selected_adapters(snapshot)
        if (
            capability.get("mode") != "none"
            or capability.get("allowOutputs") is not False
        ):
            from actions.server.foundry.generic_work_item_execution import (
                _GenericOutputs,
            )

            generic_outputs = getattr(self, "outputs", None)
            if not isinstance(generic_outputs, _GenericOutputs):
                raise AccessDenied("compiled Action capability is not executable")
            generic_outputs.require_rcc_selection(snapshot, capability)
        if snapshot.runtime_plan.plan_digest.root not in capability.get(
            "compatiblePlanDigests", []
        ):
            raise AccessDenied("Run selected an undeclared Runtime Plan")
        schema = self.registry.schema_for(snapshot)
        if (
            schema.action_id != snapshot.action_id
            or schema.capability != snapshot.capability
            or schema.runtime_plan != snapshot.runtime_plan
            or "sha256:" + hashlib.sha256(schema.input_schema.encode()).hexdigest()
            != snapshot.capability_schema_digest
        ):
            raise AccessDenied("Action schema differs from admitted Run")
        adapter = json.loads(compiled.adapter_specification_payload)
        entrypoint = adapter.get("entrypoint")
        if (
            not isinstance(entrypoint, dict)
            or set(entrypoint) != {"module", "actionName"}
            or not all(
                isinstance(value, str) and value for value in entrypoint.values()
            )
        ):
            raise AccessDenied("verified generated Action entrypoint required")
        if capability.get("id") != "action." + entrypoint["actionName"]:
            raise AccessDenied("Action capability and entrypoint differ")
        try:
            input_schema = json.loads(compiled.input_schema_payload)
            output_schema = json.loads(compiled.output_schema_payload)
        except (TypeError, ValueError, json.JSONDecodeError):
            raise AccessDenied("verified Action schemas required") from None
        return compiled, entrypoint, input_schema, output_schema

    @staticmethod
    def _validate_json(payload: bytes, schema: dict, description: str):
        try:
            value = json.loads(payload)
            from jsonschema import validate

            validate(value, schema)
        except Exception as exc:
            raise AccessDenied(
                f"{description} does not match the admitted schema"
            ) from exc
        return value

    @staticmethod
    def _cancel_predicate(cancelled: Any) -> Callable[[], bool]:
        if callable(cancelled):
            return cancelled
        predicate = getattr(cancelled, "is_set", None)
        if callable(predicate):
            return predicate
        raise TypeError("cancellation event or zero-argument callback required")

    def _check_cancel(
        self, cancelled: Callable[[], bool], actor: Actor, fence: AttemptFence
    ) -> None:
        if cancelled():
            self.outputs.cancel(actor, fence.run_id)
            raise FenceRejected("generated Action execution cancelled")

    def _read_journal(self, fence: AttemptFence, *, actor=None) -> dict:
        with _transaction(self.outputs.db):
            run = _one(self.outputs.db, Run, fence.run_id)
            if run.result is None:
                raise FenceRejected("explicit Work Items execution journal required")
            try:
                journal = json.loads(run.result)
            except (TypeError, ValueError, json.JSONDecodeError):
                raise FenceRejected(
                    "explicit Work Items execution journal required"
                ) from None
            from actions.server.foundry.generic_work_item_execution import (
                _GenericOutputs,
            )
            from actions.server.foundry.standalone_execution import _StandaloneOutputs

            expected_version = _JOURNAL_VERSION
            snapshot = None
            if actor is not None:
                from actions.server.foundry.logical_receipts import (
                    versions_for_selection,
                )

                snapshot, _ = self.outputs.execution_context(actor, fence)
                projection = (
                    self.outputs._logical_projection()
                    if isinstance(self.outputs, (_GenericOutputs, _StandaloneOutputs))
                    else None
                )
                expected_version = versions_for_selection(
                    self.registry, snapshot, projection=projection
                )[0]
            standalone = (
                isinstance(self.outputs, (_GenericOutputs, _StandaloneOutputs))
                and self.outputs.ticket.claim is None
                and isinstance(journal, dict)
                and journal.get("mode") == "standalone"
                and journal.get("claim") is None
            )
            if (
                not isinstance(journal, dict)
                or journal.get("version") != expected_version
                or journal.get("fence") != fence.model_dump()
                or (
                    not standalone
                    and (
                        journal.get("mode") != "work-items"
                        or not isinstance(journal.get("claim"), dict)
                        or not self._valid_claim(journal["claim"], fence)
                    )
                )
            ):
                raise FenceRejected(
                    "explicit Work Items mode and current claim required"
                )
            required = {"version", "mode", "claim", "fence", "launch"}
            if set(journal) not in (required, required | {"execution"}):
                raise FenceRejected("unsupported Work Items execution journal")
            if expected_version != _JOURNAL_VERSION:
                from actions.server.foundry.logical_receipts import (
                    validate_bound_record,
                )

                validate_bound_record(
                    self.outputs.db,
                    self.registry,
                    snapshot,
                    run,
                    fence,
                    journal,
                    claim=journal["claim"],
                    terminal=False,
                    _projection=cast(Any, self.outputs)._logical_projection(),
                )
            return journal

    def _assert_live_journal(
        self,
        actor: Actor,
        fence: AttemptFence,
        launch: dict,
        *,
        completed_execution: dict | None = None,
    ) -> None:
        snapshot, _inputs = self.outputs.execution_context(actor, fence)
        journal = self._read_journal(fence, actor=actor)
        lineage = self._lineage(snapshot, journal["claim"], fence)
        if (
            journal.get("launch") != launch
            or journal.get("claim") != launch.get("workItemClaim")
            or launch.get("lineage") != lineage
            or journal.get("execution") != completed_execution
        ):
            raise FenceRejected("current RCC launch intent changed")

    @staticmethod
    def _lineage(
        snapshot: ExecutionSnapshot, claim: dict | None, fence: AttemptFence
    ) -> dict:
        """Return the exact admitted Package, Plan, Work Item, Run and Attempt."""
        package = snapshot.capability.package_revision.model_dump(mode="json")
        plan = snapshot.runtime_plan.model_dump(mode="json")
        if plan.get("package_revision") != package:
            raise AccessDenied("Runtime Plan and Package revision differ")
        return {
            "packageRevision": package,
            "runtimePlan": plan,
            "workItemClaim": claim,
            "runId": fence.run_id,
            "attemptFence": fence.model_dump(),
        }

    def _confirmed_failed_receipt(
        self, process, ownership, receipt_file, artifact_digest
    ):
        cleanup = ownership.cleanup()
        if not cleanup.execution_stopped:
            raise RccCleanupIncomplete("failed RCC child cleanup incomplete")
        receipt_bytes = self._read_regular(receipt_file, _RECEIPT_LIMIT)
        receipt = read_receipt(receipt_file, artifact_digest)
        if (
            process.returncode is None
            or process.returncode == 0
            or receipt.get("status") != "failed"
            or (
                not isinstance(receipt.get("exitCode"), int)
                or isinstance(receipt.get("exitCode"), bool)
            )
            or receipt["exitCode"] != process.returncode
        ):
            raise RuntimeError("RCC child failure lacks matching measured receipt")
        return receipt_bytes, cleanup

    def _publish_failed(
        self,
        actor,
        fence,
        snapshot,
        compiled,
        journal,
        launch,
        receipt_bytes,
        exit_code,
        cleanup,
        stdout_bytes,
        stderr_bytes,
        stdout_capture,
        stderr_capture,
    ):
        """Publish only observed child exit plus complete owned cleanup, never a result."""
        from actions.server.foundry.logical_receipts import FAILURE_V1

        binder = getattr(self.outputs, "bind_generated_failure", None)
        if not callable(binder) or not cleanup.execution_stopped:
            raise RuntimeError("failed launch requires explicit reconciliation")
        self._assert_live_journal(actor, fence, launch)
        self.outputs.heartbeat(fence, lease_seconds=_LEASE_SECONDS)
        execution = {
            "status": "failed",
            "exitCode": exit_code,
            "artifactDigest": compiled.rcc_artifact_digest,
            "receiptDigest": self._digest(receipt_bytes),
            "cleanup": {
                "wrapperReaped": cleanup.wrapper_reaped,
                "descendantSnapshotComplete": cleanup.descendant_snapshot_complete,
                "executionStopped": cleanup.execution_stopped,
            },
            "stdout": self._capture_receipt(stdout_bytes, stdout_capture),
            "stderr": self._capture_receipt(stderr_bytes, stderr_capture),
        }
        refs, records = [], []
        for name, media, payload in (
            ("rcc-receipt.json", "application/json", receipt_bytes),
            ("rcc-stdout.log", "application/octet-stream", stdout_bytes),
            ("rcc-stderr.log", "application/octet-stream", stderr_bytes),
        ):
            ref = self.outputs.stage(
                fence,
                self._chunks(payload),
                name=name,
                media_type=media,
                retention_seconds=_OUTPUT_RETENTION_SECONDS,
            )
            refs.append(ref)
            records.append(
                {
                    "name": name,
                    "ref": ref.model_dump(mode="json"),
                    "digest": self._digest(payload),
                    "size": len(payload),
                }
            )
        record = {
            "version": FAILURE_V1,
            "mode": journal["mode"],
            "claim": journal["claim"],
            "lineage": self._lineage(snapshot, journal["claim"], fence),
            "launch": launch,
            "publicationFence": fence.model_dump(),
            "sourceArtifactDigest": compiled.source_artifact_digest,
            "packageRevision": snapshot.capability.package_revision.revision_id.root,
            "runtimePlanDigest": snapshot.runtime_plan.plan_digest.root,
            "rccSpecificationDigest": compiled.rcc_specification_digest,
            "rccArtifactDigest": compiled.rcc_artifact_digest,
            "execution": execution,
            "outputs": records,
        }
        with binder(record), _transaction(self.outputs.db):
            self.outputs._fence(fence)
            self._assert_live_journal(actor, fence, launch)
            return self.outputs.publish(
                actor, fence, refs, record, terminal_status=RunStatus.FAILED
            )

    def _capture_process(
        self,
        process: subprocess.Popen,
        actor: Actor,
        fence: AttemptFence,
        launch: dict,
        cancelled: Callable[[], bool],
        deadline: float,
    ) -> tuple[bytes, bytes, dict[str, Any], dict[str, Any]]:
        """Drain both RCC pipes while retaining only bounded prefixes."""
        if process.stdout is None or process.stderr is None:
            raise RuntimeError("RCC output pipes were not created")
        selector = selectors.DefaultSelector()
        retained = {"stdout": bytearray(), "stderr": bytearray()}
        observed = {"stdout": 0, "stderr": 0}
        complete = {"stdout": False, "stderr": False}
        streams = {"stdout": process.stdout, "stderr": process.stderr}
        for name, stream in streams.items():
            selector.register(stream, selectors.EVENT_READ, name)
        heartbeat_at = time.monotonic() + _HEARTBEAT_SECONDS
        process_exit_at: float | None = None
        try:
            while selector.get_map():
                observer = getattr(process, "_actions_capture_owned", None)
                if observer is not None:
                    observer()
                now = time.monotonic()
                if now >= deadline:
                    raise TimeoutError("generated Action RCC deadline")
                if cancelled():
                    self.outputs.cancel(actor, fence.run_id)
                    raise FenceRejected("generated Action execution cancelled")
                if process.poll() is not None:
                    if process_exit_at is None:
                        process_exit_at = now
                    elif now - process_exit_at >= _POST_EXIT_LOG_GRACE_SECONDS:
                        break
                if now >= heartbeat_at:
                    self._assert_live_journal(actor, fence, launch)
                    self.outputs.heartbeat(fence, lease_seconds=_LEASE_SECONDS)
                    heartbeat_at = time.monotonic() + _HEARTBEAT_SECONDS
                for key, _mask in selector.select(timeout=0.2):
                    name = key.data
                    chunk = os.read(key.fd, _LOG_READ_BYTES)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        streams[name].close()
                        complete[name] = True
                        continue
                    observed[name] += len(chunk)
                    room = _LOG_LIMIT - len(retained[name])
                    if room > 0:
                        retained[name].extend(chunk[:room])
        finally:
            for key in list(selector.get_map().values()):
                selector.unregister(key.fileobj)
                streams[key.data].close()
            selector.close()
        values = {name: bytes(value) for name, value in retained.items()}
        receipts = {
            name: {
                "observedBytes": observed[name],
                "retainedBytes": len(values[name]),
                "discardedObservedBytes": observed[name] - len(values[name]),
                "streamComplete": complete[name],
                "truncated": observed[name] > len(values[name]) or not complete[name],
            }
            for name in retained
        }
        return (
            values["stdout"],
            values["stderr"],
            receipts["stdout"],
            receipts["stderr"],
        )

    def _capture_receipt(
        self, payload: bytes, receipt: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            **receipt,
            "digest": self._digest(payload),
            "retainedBytes": len(payload),
        }

    @staticmethod
    def _chunks(payload: bytes):
        for offset in range(0, len(payload), _LOG_READ_BYTES):
            yield payload[offset : offset + _LOG_READ_BYTES]

    @staticmethod
    def _valid_claim(claim: dict, fence: AttemptFence) -> bool:
        if set(claim) != {"item_id", "owner_id", "epoch"}:
            return False
        try:
            from actions.server.run_outputs.types import canonical_uuid

            canonical_uuid(claim["item_id"])
            canonical_uuid(claim["owner_id"])
        except (TypeError, ValueError):
            return False
        return (
            claim["owner_id"] == fence.owner_id
            and isinstance(claim["epoch"], int)
            and not isinstance(claim["epoch"], bool)
            and 1 <= claim["epoch"] <= 2_147_483_647
        )

    def _launch_directory(self, fence: AttemptFence, launch_id: str) -> Path:
        from actions.server.run_outputs.types import canonical_uuid

        canonical_uuid(launch_id)
        self._ensure_directory(self.execution_root, parents=True)
        run_root = self.execution_root / fence.run_id
        self._ensure_directory(run_root)
        attempt_root = run_root / fence.attempt_id
        self._ensure_directory(attempt_root)
        launch_root = attempt_root / launch_id
        launch_root.mkdir(mode=0o700, exist_ok=False)
        return launch_root

    @staticmethod
    def _ensure_directory(path: Path, *, parents: bool = False) -> None:
        try:
            path.mkdir(mode=0o700, parents=parents, exist_ok=False)
        except FileExistsError:
            try:
                mode = path.lstat().st_mode
            except OSError:
                raise AccessDenied("owned execution directory is unavailable") from None
            if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
                raise AccessDenied("owned regular execution directory required")

    @staticmethod
    def _extract_snapshot(source_archive: bytes, destination: Path) -> None:
        fchmod = _posix_fchmod()
        destination.mkdir(mode=0o700)
        total = 0
        count = 0
        try:
            from io import BytesIO

            with zipfile.ZipFile(BytesIO(source_archive), "r") as archive:
                infos = archive.infolist()
                if not infos or len(infos) > MAX_COMPILER_SOURCE_FILES:
                    raise ValueError("source archive entry count is invalid")
                for info in infos:
                    path = PurePosixPath(info.filename)
                    mode = info.external_attr >> 16
                    if (
                        path.is_absolute()
                        or not path.parts
                        or any(part in {"", ".", ".."} for part in path.parts)
                        or "\\" in info.filename
                        or info.is_dir()
                        or not stat.S_ISREG(mode)
                        or info.file_size > MAX_COMPILER_SOURCE_FILE_BYTES
                        or info.compress_size != info.file_size
                        or info.compress_type != zipfile.ZIP_STORED
                        or info.flag_bits & 1
                    ):
                        raise ValueError("source archive contains an invalid entry")
                    count += 1
                    total += info.file_size
                    if (
                        count > MAX_COMPILER_SOURCE_FILES
                        or total > MAX_COMPILER_SOURCE_TOTAL_BYTES
                    ):
                        raise ValueError("source archive exceeds source bounds")
                    content = archive.read(info)
                    if len(content) != info.file_size:
                        raise ValueError("source archive entry length changed")
                    target = destination.joinpath(*path.parts)
                    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                    fd = os.open(
                        target,
                        os.O_WRONLY
                        | os.O_CREAT
                        | os.O_EXCL
                        | getattr(os, "O_NOFOLLOW", 0),
                        0o600,
                    )
                    try:
                        with os.fdopen(fd, "wb", closefd=False) as stream:
                            stream.write(content)
                        fchmod(fd, stat.S_IMODE(mode))
                    finally:
                        os.close(fd)
        except (OSError, zipfile.BadZipFile, ValueError):
            shutil.rmtree(destination, ignore_errors=True)
            raise

    @staticmethod
    def _read_regular(path: Path, limit: int) -> bytes:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError("regular generated execution evidence required")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                value = stream.read(limit + 1)
            if len(value) > limit:
                raise ValueError("generated execution evidence exceeds its limit")
            return value
        finally:
            os.close(fd)

    @staticmethod
    def _write_private(path: Path, value: bytes) -> None:
        fd = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(value)
        finally:
            os.close(fd)

    def _child_environment(self, directory: Path) -> dict[str, str]:
        path_entries = os.defpath.split(os.pathsep)
        if sys.platform.startswith("linux"):
            path_entries = ["/usr/sbin", "/sbin", *path_entries]
        home = directory / "home"
        actions_home = directory / "actions-home"
        temporary = directory / "tmp"
        for path in (home, actions_home, temporary):
            path.mkdir(mode=0o700)
        return {
            "HOME": str(home),
            "PATH": os.pathsep.join(dict.fromkeys(path_entries)),
            "ROBOCORP_HOME": str(self.prepared.robocorp_home),
            "ACTIONS_HOME": str(actions_home),
            "TMPDIR": str(temporary),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "RCC_NO_BUILD": "1",
        }

    @staticmethod
    def _execution_helper(entrypoint: dict) -> str:
        # Schema bytes are bound by the immutable Package; the host validates
        # both sides too. The child only imports/calls the verified entrypoint.
        return (
            "import importlib,json,os,sys\n"
            "source,input_file,result_file=sys.argv[1:4]\n"
            "with open(input_file,'rb') as stream: inputs=json.load(stream)\n"
            "sys.path.insert(0,source)\n"
            f"module=importlib.import_module({entrypoint['module']!r})\n"
            f"action=getattr(module,{entrypoint['actionName']!r})\n"
            "value=action(**inputs)\n"
            "if hasattr(value,'model_dump'): value=value.model_dump(mode='json')\n"
            "payload=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')\n"
            f"if len(payload)>{_RESULT_LIMIT}: raise SystemExit(86)\n"
            "fd=os.open(result_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)\n"
            "with os.fdopen(fd,'wb') as stream: stream.write(payload)\n"
        )

    @staticmethod
    def _bound_execution_helper(entrypoint: dict) -> str:
        return (
            "import importlib,json,os,stat,sys\n"
            "source,input_file,result_file,context_file,context_digest=sys.argv[1:6]\n"
            "with open(input_file,'rb') as stream: inputs=json.load(stream)\n"
            "fd=os.open(context_file,os.O_RDONLY|os.O_NOFOLLOW)\n"
            "with os.fdopen(fd,'rb') as stream:\n"
            " status=os.fstat(stream.fileno())\n"
            " if not stat.S_ISREG(status.st_mode) or not 0<status.st_size<=262144: raise SystemExit(87)\n"
            " raw=stream.read(262145)\n"
            " if len(raw)!=status.st_size: raise SystemExit(87)\n"
            "from actions.data._context import install_context\n"
            "sys.path.insert(0,source)\n"
            f"module=importlib.import_module({entrypoint['module']!r})\n"
            f"action=getattr(module,{entrypoint['actionName']!r})\n"
            "with install_context(raw,expected_digest=context_digest): value=action(**inputs)\n"
            "if hasattr(value,'model_dump'): value=value.model_dump(mode='json')\n"
            "payload=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')\n"
            f"if len(payload)>{_RESULT_LIMIT}: raise SystemExit(86)\n"
            "fd=os.open(result_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)\n"
            "with os.fdopen(fd,'wb') as stream: stream.write(payload)\n"
        )

    @staticmethod
    def _digest(value: bytes) -> str:
        return "sha256:" + hashlib.sha256(value).hexdigest()

    @staticmethod
    def _verify_snapshot_unchanged(source: Path, source_archive: bytes) -> None:
        from io import BytesIO

        expected: dict[str, tuple[bytes, int]] = {}
        with zipfile.ZipFile(BytesIO(source_archive), "r") as archive:
            for info in archive.infolist():
                expected[info.filename] = (
                    archive.read(info),
                    stat.S_IMODE(info.external_attr >> 16),
                )
        observed: dict[str, tuple[bytes, int]] = {}
        for path in source.rglob("*"):
            status = path.lstat()
            if stat.S_ISLNK(status.st_mode):
                raise AccessDenied("generated Action changed its source snapshot")
            if stat.S_ISDIR(status.st_mode):
                continue
            if not stat.S_ISREG(status.st_mode):
                raise AccessDenied("generated Action changed its source snapshot")
            relative = path.relative_to(source).as_posix()
            observed[relative] = (path.read_bytes(), stat.S_IMODE(status.st_mode))
        if observed != expected:
            raise AccessDenied("generated Action changed its source snapshot")
