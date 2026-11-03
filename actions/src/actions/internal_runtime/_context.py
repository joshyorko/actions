"""Private Runtime injection hook for internal delegated child operations.

This module defines only the local client boundary. It contains no transport,
credentials, parent identity, or persistence of its own. A trusted Runtime may
install a per-invocation transport around the generated Action call.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator, Protocol

from ._models import ChildRunHandle, ChildRunStatus


class _RuntimeTransport(Protocol):
    def submit_child_run(
        self, binding_name: str, invocation_key: str, canonical_inputs: str
    ) -> ChildRunHandle:
        ...

    def child_run_status(self, handle: ChildRunHandle) -> ChildRunStatus:
        ...

    def cancel_child_run(self, handle: ChildRunHandle) -> ChildRunStatus:
        ...


_CURRENT: ContextVar[_RuntimeTransport | None] = ContextVar(
    "actions_delegated_child_transport", default=None
)


def current_transport() -> _RuntimeTransport:
    transport = _CURRENT.get()
    if transport is None:
        from . import ChildRunUnavailable

        raise ChildRunUnavailable("Runtime child Run operations are unavailable")
    return transport


@contextmanager
def install_runtime_transport(transport: _RuntimeTransport) -> Iterator[None]:
    """Install one trusted host transport for one Action invocation.

    Runtime owns the transport and its parent identity. Child Actions must not
    receive this context; nested installation in one context is rejected.
    """
    if any(
        not callable(getattr(transport, name, None))
        for name in ("submit_child_run", "child_run_status", "cancel_child_run")
    ):
        raise TypeError("complete Runtime child Run transport required")
    if _CURRENT.get() is not None:
        raise RuntimeError("nested Runtime child context is unsupported")
    token: Token[_RuntimeTransport | None] = _CURRENT.set(transport)
    try:
        yield
    finally:
        _CURRENT.reset(token)
