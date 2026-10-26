"""Bounded, reachable ownership of eager preparation threads and issued reads."""
from __future__ import annotations

import math
import threading
import time

MAX_ACTIVE_PREPARATIONS = 4


def _timeout(value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 60
    ):
        raise ValueError("bounded settlement timeout required")
    return value


class LogicalPreparationOwner:
    def __init__(self, supervisor, actor, fence, cancelled, deadline):
        self.supervisor = supervisor
        self.cancelled = cancelled
        self.done = threading.Event()
        self._lock = threading.Lock()
        self._result = None
        self._error = None
        self._transferred = False
        self._released = False
        self.thread = threading.Thread(
            target=self._run,
            args=(actor, fence, deadline),
            name="actions-logical-preparation",
            daemon=False,
        )

    def _run(self, actor, fence, deadline):
        try:
            # LogicalExecution.prepare owns this thread's Database.connect scope.
            self._result = self.supervisor.execution.prepare(
                actor, fence, cancelled=self.cancelled, deadline=deadline
            )
        except BaseException as exc:
            self._error = exc
        finally:
            self.done.set()

    def stop(self):
        self.cancelled.set()

    def take_result(self):
        if not self.done.is_set():
            raise RuntimeError("logical preparation is not complete")
        self.thread.join()
        with self._lock:
            if self._transferred or self._released or self.cancelled.is_set():
                raise RuntimeError("logical preparation ownership unavailable")
            if self._error is not None:
                raise self._error
            self._transferred = True
            return self._result

    def settle(self, timeout_seconds=0):
        timeout_seconds = _timeout(timeout_seconds)
        self.stop()
        if self.thread is threading.current_thread():
            return False
        self.thread.join(timeout_seconds)
        if self.thread.is_alive():
            return False
        with self._lock:
            if self._transferred and not self._released:
                return False
            if not self._released:
                if self._result is not None:
                    self.supervisor.execution.release(self._result)
                self._released = True
        self.supervisor._forget(self)
        return True

    def release(self, result):
        if self.thread.is_alive():
            raise RuntimeError("preparation thread still active")
        with self._lock:
            if not self._transferred or self._released or result is not self._result:
                raise RuntimeError("exact transferred preparation required")
            self.supervisor.execution.release(result)
            self._released = True
        self.supervisor._forget(self)


class LogicalPreparationSupervisor:
    def __init__(self, execution):
        self.execution = execution
        self._lock = threading.Lock()
        self._owners = set()
        self._closing = False

    def begin(self, actor, fence, *, cancelled, deadline):
        if not isinstance(cancelled, threading.Event):
            raise TypeError("owned cancellation Event required")
        if (
            isinstance(deadline, bool)
            or not isinstance(deadline, (float, int))
            or not math.isfinite(deadline)
        ):
            raise ValueError("absolute monotonic deadline required")
        with self._lock:
            if self._closing or len(self._owners) >= MAX_ACTIVE_PREPARATIONS:
                raise RuntimeError("logical preparation capacity unavailable")
            owner = LogicalPreparationOwner(self, actor, fence, cancelled, deadline)
            self._owners.add(owner)
            try:
                owner.thread.start()
            except BaseException:
                self._owners.remove(owner)
                raise
            return owner

    def _forget(self, owner):
        with self._lock:
            self._owners.discard(owner)

    def release(self, owner, prepared):
        with self._lock:
            if owner not in self._owners or owner.supervisor is not self:
                raise RuntimeError("owned logical preparation required")
        owner.release(prepared)

    def close(self, timeout_seconds=15):
        deadline = time.monotonic() + _timeout(timeout_seconds)
        with self._lock:
            self._closing = True
            owners = tuple(self._owners)
        for owner in owners:
            owner.stop()
        for owner in owners:
            owner.settle(max(0, deadline - time.monotonic()))
        with self._lock:
            return not self._owners
