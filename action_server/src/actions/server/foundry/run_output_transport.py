"""Adapt an existing host-managed identity to canonical Run output transport."""
from __future__ import annotations

from fastapi import Request

from actions.server.managed_work_items.api import Authenticate as ManagedAuthenticate
from actions.server.managed_work_items.contracts import ManagedCaller
from actions.server.run_outputs.service import RunOutputService
from actions.server.run_outputs.transport import RunOutputTransport
from actions.server.run_outputs.types import Actor


def create_run_output_transport(
    outputs: RunOutputService, authenticate: ManagedAuthenticate
) -> RunOutputTransport:
    """Reuse the host's verified identity without minting output authority.

    The host supplies its ordinary managed authenticator, not an AppSession
    resolver. No headers, cookies, principal IDs or audience hints are interpreted
    here. Authentication failures propagate to the existing transport's unavailable
    response. Live Run/Package grants, Workspace, seals and retention remain the
    existing output service's responsibility. This factory installs no route.
    """
    if not callable(authenticate):
        raise TypeError("existing host managed authenticator required")

    async def current(request: Request) -> Actor | None:
        caller = await authenticate(request)
        if not isinstance(caller, ManagedCaller):
            return None
        return caller.actor

    return RunOutputTransport(outputs, current)
