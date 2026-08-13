"""
Note: this is easy while we're in a single process!

If we ever change the design to support multiple processes we'd need to have a
way to synchronize state across multiple processes.
"""
import logging
import threading
import typing
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Any, Dict, Literal, Optional

if typing.TYPE_CHECKING:
    from ._database import Database
    from ._models import Run


log = logging.getLogger(__name__)


@dataclass(slots=True)
class RunChangeEvent:
    ev: Literal["added", "changed"]
    run: "Run"
    changes: Optional[dict[str, Any]] = None


class RunRuntimeInfo:
    def __init__(self, run_id: str, ownership=None, lease=None):
        from actions.server._robo_utils.callback import Callback

        self._run_id = run_id
        self._canceled = False
        self.on_cancel = Callback()
        self._ownership = ownership
        self._lease = lease
        self._monitor_stop = threading.Event()
        if ownership is not None and lease is not None:
            threading.Thread(target=self._monitor_control, daemon=True).start()

    def _monitor_control(self):
        while not self._monitor_stop.wait(0.25):
            self._ownership.renew(self._run_id, self._lease.epoch)
            if self._ownership.control_requested(self._run_id, self._lease.epoch):
                self.cancel()
                return

    def cancel(self):
        if self._canceled:
            return
        self._canceled = True

        if not len(self.on_cancel):
            log.info(
                f"No listeners registered during run {self._run_id} cancellation (this means that it is still in the not run state)."
            )

        self.on_cancel()  # Notify all listeners that the run was canceled.

    def close(self):
        self._monitor_stop.set()

    def is_canceled(self) -> bool:
        return self._canceled


class RunsState:
    def __init__(self, db: "Database"):
        # Clients that want to register/unregister must use this semaphore
        # to avoid racing conditions.
        #
        # This is done because the expected scenario is the following:
        # 1. The client acquires this semaphore
        # 2. then notifies about existing
        # 3. then registers so that it knows about new runs in the structure
        #
        # In this case, if the client doesn't hold the semaphore himself we
        # could have a racing condition.
        #
        # We could make it an RLock, but then we'd need a wrapper to do the
        # verification on whether it's acquired, so, we use a Semaphore to
        # use the `_value` to do the needed asserts.
        self.semaphore = threading.Semaphore(1)

        # Use dict keys for uniqueness and ordering.
        self._run_listeners: Dict[Any, int] = {}

        self._db = db
        self._run_id_to_runtime_info: dict[str, RunRuntimeInfo] = {}
        from .run_ownership import RunOwnershipStore

        self.ownership = RunOwnershipStore(
            db.db_path, owner_id=f"runtime-{uuid.uuid4()}"
        )
        from ._models import Run

        with db.connect():
            for run in db.all(Run):
                self.ownership.create_run(run.id)

    def get_current_run_state(self, offset: int = 0, limit: int = 200) -> list["Run"]:
        from ._database import Database
        from ._models import Run

        assert (
            self.semaphore._value == 0
        ), "Clients getting the current run state must acquire the semaphore."
        db: Database = self._db

        with db.connect():
            return self._db.all(
                Run, offset=offset, limit=limit, order_by="numbered_id DESC"
            )

    def get_run_from_id(self, run_id: str) -> "Run":
        """
        Returns the run associated with the run id (or throws a KeyError if not found).
        """
        assert run_id, "Run id cannot be empty."
        from ._database import Database
        from ._models import Run

        assert (
            self.semaphore._value == 0
        ), "Clients getting the current run state must acquire the semaphore."
        db: Database = self._db

        with db.connect():
            return db.first(Run, "SELECT * FROM run WHERE id = ?", [run_id])

    def get_run_from_request_id(self, request_id: str) -> "Run":
        """
        Returns the run associated with the request id (or throws a KeyError if not found).
        """
        assert request_id, "Request id cannot be empty."
        from ._database import Database
        from ._models import Run

        assert (
            self.semaphore._value == 0
        ), "Clients getting the current run state must acquire the semaphore."
        db: Database = self._db

        with db.connect():
            return db.first(Run, "SELECT * FROM run WHERE request_id = ?", [request_id])

    def register(self, listener):
        assert (
            self.semaphore._value == 0
        ), "Clients registering must acquire the semaphore."
        self._run_listeners[listener] = 1

    def unregister(self, listener):
        assert (
            self.semaphore._value == 0
        ), "Clients unregistering must acquire the semaphore."
        self._run_listeners.pop(listener, None)

    def on_run_inserted(self, run: "Run"):
        # Semaphore is acquired internally in this case.
        from ._models import Run

        run_copy = Run(**asdict(run))
        self.ownership.create_run(run.id)
        with self.semaphore:
            for listener in self._run_listeners.keys():
                listener(RunChangeEvent("added", run_copy))

    def create_run_runtime_info(self, run_id: str) -> RunRuntimeInfo:
        """
        Creates the runtime info for a run and returns it.
        """
        self.ownership.create_run(run_id)
        lease = self.ownership.claim(run_id)
        runtime_info = RunRuntimeInfo(run_id, self.ownership, lease)
        assert run_id not in self._run_id_to_runtime_info
        self._run_id_to_runtime_info[run_id] = runtime_info
        return runtime_info

    def on_run_changed(self, run: "Run", changes: Dict[str, Any]):
        from actions.server._models import RunStatus

        # Semaphore is acquired internally in this case.
        from ._models import Run

        run_copy = Run(**asdict(run))
        runtime_info = self._run_id_to_runtime_info.get(run_copy.id)
        if runtime_info is not None and "status" in changes:
            self.ownership.set_status(
                run_copy.id,
                runtime_info._lease.epoch,
                "running" if changes["status"] == RunStatus.RUNNING else "finished",
            )
        with self.semaphore:
            for listener in self._run_listeners.keys():
                listener(RunChangeEvent("changed", run_copy, changes))

            if run_copy.status not in (RunStatus.RUNNING, RunStatus.NOT_RUN):
                # Finished run, remove from runtime info.
                runtime_info = self._run_id_to_runtime_info.pop(run_copy.id, None)
                if runtime_info is not None:
                    runtime_info.close()
                    self.ownership.reconcile(
                        run_copy.id, runtime_info._lease.epoch, "running"
                    )

    def cancel_run(self, run_id: str) -> bool:
        """
        Cancels a run.

        Args:
            run_id: The ID of the run to cancel.

        Returns:
            True if the run was canceled, False otherwise (if the run was not running).
        """

        with self.semaphore:
            runtime_info = self._run_id_to_runtime_info.get(run_id)
            if runtime_info is not None:
                log.info(f"Cancelling run {run_id}.")
                runtime_info.cancel()
                return True
            requested = self.ownership.request_cancel(run_id)
            log.info("Durable cancellation for %s: %s", run_id, requested)
            return requested


_runs_state: Optional[RunsState] = None


@contextmanager
def use_runs_state_ctx(db: "Database"):
    global _runs_state
    _runs_state = RunsState(db)
    try:
        yield _runs_state
    finally:
        pass
    _runs_state = None


def get_global_runs_state() -> RunsState:
    assert _runs_state
    return _runs_state
