"""Private additive ownership contract, distinct from a capability Run Attempt.

Tokens identify a trusted queue worker; they do not authenticate a remote caller
or make external effects exactly once. Service adapters must prove this same
contract before advertising fenced support.
"""

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

from ._types import JSONType, State


class ClaimRejected(RuntimeError):
    """Claim absent, expired, superseded, or an ID-only mutation was attempted."""


class QueueStorageError(RuntimeError):
    """Service unavailable; provider diagnostics and credentials are suppressed."""


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


def payload_fingerprint(payload: JSONType) -> str:
    """Hash the current decoded payload, not the original JSON file's bytes."""
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class RetryEvidence:
    input_sha256: str
    effect: Literal["no_effect", "reconciled"]
    receipt_sha256: str
    reason: Literal["application", "infrastructure"]

    def __post_init__(self) -> None:
        for digest in (self.input_sha256, self.receipt_sha256):
            if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                raise ValueError("canonical input and receipt digests required")
        if self.effect not in ("no_effect", "reconciled") or self.reason not in (
            "application",
            "infrastructure",
        ):
            raise ValueError("Unknown effects and business failures do not authorize retry")


ReceiptVerifier = Callable[[RetryEvidence, WorkItemClaim], bool]


def verify_retry(claim: WorkItemClaim, evidence: RetryEvidence, verifier: ReceiptVerifier) -> None:
    """Trusted host verifies retained effect evidence outside the queue lock.

    This callback must resolve the receipt and authorize its exact item/epoch
    context. A digest or worker-supplied disposition alone is not proof. Queue
    release revalidates the live claim and input after this potentially slow call.
    """
    if not isinstance(claim, WorkItemClaim) or not isinstance(evidence, RetryEvidence):
        raise ClaimRejected("typed current claim and receipt evidence required")
    try:
        verified = verifier(evidence, claim)
    except Exception:
        raise ClaimRejected("Effect receipt verification unavailable") from None
    if verified is not True:
        raise ClaimRejected("Effect receipt did not authorize retry")


def retry_record(
    claim: WorkItemClaim, evidence: RetryEvidence, payload: JSONType, max_claims: int
) -> dict:
    if (
        not isinstance(max_claims, int)
        or isinstance(max_claims, bool)
        or not 1 <= max_claims <= 100
    ):
        raise ValueError("explicit claim budget of 1 through 100 required")
    if claim.epoch >= max_claims or payload_fingerprint(payload) != evidence.input_sha256:
        raise ClaimRejected("Retry budget exhausted or protected input changed")
    return {
        "schema": "actions.work-item-retry/v1",
        "item_id": claim.item_id,
        "owner_id": claim.owner_id,
        "epoch": claim.epoch,
        "input_sha256": evidence.input_sha256,
        "effect": evidence.effect,
        "receipt_sha256": evidence.receipt_sha256,
        "reason": evidence.reason,
        "max_claims": max_claims,
    }


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

    def retry_fenced(
        self,
        claim: WorkItemClaim,
        *,
        evidence: RetryEvidence,
        verify_receipt: ReceiptVerifier,
        max_claims: int,
    ) -> None: ...

    def retry_history(self, item_id: str) -> list[dict]: ...
