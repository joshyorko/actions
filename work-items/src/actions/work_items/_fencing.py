"""Private additive ownership contract, distinct from a capability Run Attempt.

Tokens identify a trusted queue worker; they do not authenticate a remote caller
or make external effects exactly once. Service adapters must prove this same
contract before advertising fenced support.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from ._types import JSONType, State


class ClaimRejected(RuntimeError):
    """Claim absent, expired, superseded, or an ID-only mutation was attempted."""


@dataclass(frozen=True)
class WorkItemClaim:
    item_id: str
    owner_id: str
    epoch: int

    def __post_init__(self) -> None:
        if not isinstance(self.item_id, str) or not 0 < len(self.item_id) <= 256:
            raise ValueError("bounded Work Item identity required")
        validate_owner(self.owner_id)
        if not isinstance(self.epoch, int) or isinstance(self.epoch, bool) or self.epoch < 1:
            raise ValueError("positive claim epoch required")


def validate_owner(owner_id: str) -> None:
    if not isinstance(owner_id, str) or str(UUID(owner_id)) != owner_id:
        raise ValueError("canonical worker owner UUID required")


def validate_lease(lease_seconds: int) -> None:
    if (
        not isinstance(lease_seconds, int)
        or isinstance(lease_seconds, bool)
        or not 1 <= lease_seconds <= 3600
    ):
        raise ValueError("integer lease of 1 through 3600 seconds required")


class FencedQueue(Protocol):
    def reserve_fenced(self, owner_id: str, *, lease_seconds: int) -> WorkItemClaim: ...

    def renew_fenced(self, claim: WorkItemClaim, *, lease_seconds: int) -> None: ...

    def finish_fenced(
        self,
        claim: WorkItemClaim,
        state: State,
        *,
        outputs: tuple[JSONType, ...] = (),
        message: str | None = None,
    ) -> list[str]: ...
