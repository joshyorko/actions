"""Explicit local worker lifecycle; canonical detached Runs remain the queue."""
from __future__ import annotations

import hashlib
import json
import os
import stat
import threading
import time
import zipfile
from io import BytesIO
from pathlib import Path

from actions.server._rcc_runtime_adapter import verify_rcc_version
from actions.server.deployments.ids import WorkerProfileRevisionRef
from actions.server.deployments.package_revision_compiler import PreparedRccEnvironment
from actions.server.foundry.logical_preparation import LogicalPreparationOwner
from actions.server.foundry.rcc_execution import (
    GeneratedRccExecution,
    LogicalPreparationCleanupIncomplete,
    RccCleanupIncomplete,
)
from actions.server.foundry.robot_execution import RobotCleanupIncomplete
from actions.server.run_outputs.detached import DetachedActions, DetachedActionWorker
from actions.server.run_outputs.task_service import TaskHostUnavailable, TaskPolicy
from actions.server.run_outputs.types import Actor, ExecutionSnapshot

_POLICY_LIMIT = 16 * 1024
_POLICY_VERSION = "actions.runtime-task-policy/v1"


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate policy field")
        result[key] = value
    return result


def _nonfinite(_value):
    raise ValueError("nonfinite policy number")


def load_task_policy(path: Path) -> TaskPolicy:
    """Read an explicit private POSIX policy; never create or change files."""
    fd = None
    try:
        if (
            os.name != "posix"
            or not isinstance(path, Path)
            or not path.is_absolute()
            or ".." in path.parts
        ):
            raise ValueError("absolute private policy required")
        if any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError("symlink policy unsupported")
        original = path.stat()
        if (
            not stat.S_ISREG(original.st_mode)
            or original.st_uid != os.getuid()
            or original.st_mode & 0o077
            or original.st_nlink != 1
            or not 1 <= original.st_size <= _POLICY_LIMIT
        ):
            raise ValueError("private bounded policy required")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        before = os.fstat(fd)
        if (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_nlink,
            before.st_uid,
            before.st_size,
        ) != (
            original.st_dev,
            original.st_ino,
            original.st_mode,
            original.st_nlink,
            original.st_uid,
            original.st_size,
        ):
            raise ValueError("policy changed")
        chunks = []
        size = 0
        while size <= _POLICY_LIMIT:
            chunk = os.read(fd, min(4096, _POLICY_LIMIT + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        after, named = os.fstat(fd), path.stat()
        if (
            size != before.st_size
            or size > _POLICY_LIMIT
            or (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
            != (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            or (named.st_dev, named.st_ino) != (before.st_dev, before.st_ino)
        ):
            raise ValueError("policy changed")
        data = json.loads(
            b"".join(chunks).decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_nonfinite,
        )
        if (
            not isinstance(data, dict)
            or set(data)
            != {"schema_version", "policy_id", "ttl_ms", "poll_interval_ms"}
            or data["schema_version"] != _POLICY_VERSION
        ):
            raise ValueError("closed policy required")
        return TaskPolicy(data["policy_id"], data["ttl_ms"], data["poll_interval_ms"])
    except (OSError, ValueError, TypeError, KeyError):
        raise ValueError("Private Task policy unavailable or invalid") from None
    finally:
        if fd is not None:
            os.close(fd)


def _timeout(value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 <= value <= 60
    ):
        raise ValueError("bounded lifecycle timeout required")
    return value


class DetachedTaskHost:
    """One configured consumer; injected providers remain owned by the caller.

    A false close result forbids caller teardown of providers/DB resources. The
    caller may retry bounded joining; this host never closes those resources.
    """

    def __init__(
        self,
        authority: DetachedActions,
        *,
        actor: Actor,
        worker_id: str,
        profile: WorkerProfileRevisionRef,
        prepared: PreparedRccEnvironment,
        rcc: Path,
        execution_root: Path,
        policy: TaskPolicy,
        logical_execution=None,
        capability_runner=None,
    ):
        if not isinstance(policy, TaskPolicy) or not isinstance(
            prepared, PreparedRccEnvironment
        ):
            raise ValueError("explicit policy and prepared runtime required")
        profile = WorkerProfileRevisionRef.model_validate(profile)
        self.authority, self.actor, self.profile = (
            authority,
            Actor.model_validate(actor),
            profile,
        )
        self.prepared, self.rcc, self.execution_root, self.policy = (
            prepared,
            rcc,
            execution_root,
            policy,
        )
        self.logical_execution = logical_execution
        self.capability_runner = capability_runner
        self._preparation_cleanup: list[LogicalPreparationOwner] = []
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._startup_done = threading.Event()
        self._failed = threading.Event()
        self._cleanup_uncertain = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._worker = DetachedActionWorker(
            authority,
            self.actor,
            worker_id,
            profile,
            stop_requested=self._stop.is_set,
            logical_execution=logical_execution,
            capability_runner=capability_runner,
        )

    @property
    def failed(self) -> bool:
        return self._failed.is_set()

    def _runtime(self):
        return GeneratedRccExecution(
            self.authority.outputs.capabilities,
            self.authority.outputs,
            self.prepared,
            self.rcc,
            self.execution_root,
            **(
                {"logical_execution": self.logical_execution}
                if self.logical_execution is not None
                else {}
            ),
        )

    def start(self, timeout_seconds: float = 10) -> None:
        _timeout(timeout_seconds)
        with self._lock:
            if self._thread is not None or self._stop.is_set():
                raise TaskHostUnavailable("Task host cannot be restarted")
            self._thread = threading.Thread(
                target=self._run, name="actions-detached-worker", daemon=True
            )
            self._thread.start()
        if not self._startup_done.wait(timeout_seconds):
            self._stop.set()
            raise TaskHostUnavailable("Task host startup unavailable")
        self._check_running()

    def _check_running(self):
        if (
            not self._ready.is_set()
            or self._stop.is_set()
            or self._failed.is_set()
            or self._thread is None
            or not self._thread.is_alive()
        ):
            raise TaskHostUnavailable("Task host unavailable")

    def require_claimed_scope(self, actor, snapshot, claim) -> None:
        """Recheck host identity without database, archive or provider access."""
        self._check_running()
        if (
            actor != self.actor
            or snapshot.worker != self.profile
            or snapshot.workspace_id != str(self.profile.workspace_id.root)
            or self._worker.caller.actor != actor
            or self._worker.caller.worker_id is None
            or self._worker.caller.worker_id != claim.owner_id
            or claim.queue.deployment != snapshot.deployment
            or str(claim.queue.workspace_id.root) != snapshot.workspace_id
            or self.capability_runner is None
        ):
            raise TaskHostUnavailable("claimed Task host scope unavailable")

    def require_claimed_ready(self, actor, snapshot, claim) -> None:
        self.require_claimed_scope(actor, snapshot, claim)
        if self.authority.db.in_transaction():
            raise TaskHostUnavailable(
                "claimed readiness requires transaction-free host"
            )
        with self.authority.db.connect():
            service = self.authority.claimed_service(snapshot)
            service._current(self._worker.caller)
            name = service.policy.input_queue
            if name is None:
                raise TaskHostUnavailable("claimed input queue required")
            if claim.queue != service.queue_ref(name):
                raise TaskHostUnavailable("claimed Task queue differs")
            robot = self.capability_runner.robot_for(
                self.authority.outputs.capabilities, snapshot
            )
            if robot is None:
                raise TaskHostUnavailable("claimed Robot host unavailable")
            robot.require_ready(service)
        self.require_claimed_scope(actor, snapshot, claim)

    def require_ready(self, actor: Actor, snapshot: ExecutionSnapshot) -> None:
        self._check_running()
        if (
            actor != self.actor
            or snapshot.worker != self.profile
            or snapshot.workspace_id != str(self.profile.workspace_id.root)
            or snapshot.runtime_kind not in ("rcc", "direct")
        ):
            raise TaskHostUnavailable("Task host scope unavailable")
        with self.authority.db.connect():
            # Read-only live authorization and immutable selection. No grant,
            # common admission registration, compilation or queue mutation.
            service = self.authority._service(actor, snapshot)
            if self.capability_runner is not None:
                robot = self.capability_runner.robot_for(
                    self.authority.outputs.capabilities, snapshot
                )
                if robot is not None:
                    robot.require_ready(service)
                    self._check_running()
                    return
            compiled, _, _, _ = self._runtime()._verified_selection(snapshot)
            if (
                compiled.rcc_specification_digest
                != self.prepared.build_identity.specification_digest
                or compiled.rcc_artifact_digest
                != self.prepared.build_identity.artifact_digest
            ):
                raise TaskHostUnavailable("Task host runtime unavailable")
            with zipfile.ZipFile(BytesIO(compiled.source_archive)) as archive:
                with archive.open("package.yaml") as stream:
                    package_yaml = stream.read(32 * 1024 + 1)
            if (
                len(package_yaml) > 32 * 1024
                or "sha256:" + hashlib.sha256(package_yaml).hexdigest()
                != self.prepared.package_yaml_digest
            ):
                raise TaskHostUnavailable("Task host runtime unavailable")
        self._check_running()

    def _run(self):
        try:
            self._runtime()
            verify_rcc_version(self.rcc)
            with self.authority.db.connect():
                # Actual thread-local connection and canonical SQL scan, not a
                # readiness callback standing in for an installed consumer.
                self.authority.pending(
                    self.actor,
                    str(self.profile.workspace_id.root),
                    self.profile,
                    limit=1,
                    worker_id=self._worker.caller.worker_id,
                )
                if self._stop.is_set():
                    return
                self._ready.set()
                self._startup_done.set()
                cursor = None
                while not self._stop.is_set():
                    _, cursor = self._worker.run_once(
                        prepared=self.prepared,
                        rcc=self.rcc,
                        execution_root=self.execution_root,
                        after=cursor,
                    )
                    self._stop.wait(self.policy.poll_interval_ms / 1000)
        except LogicalPreparationCleanupIncomplete as exc:
            self._preparation_cleanup.append(exc.owner)
            self._failed.set()
        except (RccCleanupIncomplete, RobotCleanupIncomplete):
            self._cleanup_uncertain.set()
            self._failed.set()
        except Exception:
            # Includes conservative competitor/lease loss: preserve canonical
            # evidence and stop this consumer, never requeue or recover it.
            if not self._stop.is_set():
                self._failed.set()
        finally:
            self._ready.clear()
            self._startup_done.set()

    def close(self, timeout_seconds: float = 15) -> bool:
        _timeout(timeout_seconds)
        self._stop.set()
        self._ready.clear()
        with self._lock:
            thread = self._thread
        if thread is None:
            return True
        if thread is threading.current_thread():
            return False
        deadline = time.monotonic() + timeout_seconds
        thread.join(timeout_seconds)
        if thread.is_alive() or self._cleanup_uncertain.is_set():
            return False
        self._preparation_cleanup = [
            owner
            for owner in self._preparation_cleanup
            if not owner.settle(max(0, deadline - time.monotonic()))
        ]
        return not self._preparation_cleanup
