"""Strict retained identity for a claimed Robot Task; no execution authority."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from actions.server.managed_work_items.contracts import ClaimRef
from actions.server.run_outputs.service import _canonical
from actions.server.run_outputs.types import ExecutionSnapshot

CLAIMED_INTENT_VERSION: Literal[
    "actions.detached-claimed-robot/v1"
] = "actions.detached-claimed-robot/v1"


class ClaimedTaskIntent(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    version: Literal["actions.detached-claimed-robot/v1"] = CLAIMED_INTENT_VERSION
    snapshot: ExecutionSnapshot
    claim: ClaimRef
    input_digest: str = Field(alias="inputDigest", pattern=r"^sha256:[0-9a-f]{64}$")

    @classmethod
    def create(cls, snapshot: ExecutionSnapshot, claim: ClaimRef, inputs: object):
        if claim.queue.deployment != snapshot.deployment:
            raise ValueError("claimed Task queue Deployment differs")
        digest = (
            "sha256:" + hashlib.sha256(_canonical(inputs, 262144).encode()).hexdigest()
        )
        return cls(snapshot=snapshot, claim=claim, inputDigest=digest)

    def canonical(self) -> str:
        return _canonical(self.model_dump(mode="json", by_alias=True), 131072)


def claimed_intent(raw: str) -> ClaimedTaskIntent | None:
    """Select only the explicit version; consumers still verify all pinned records."""
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get("version") != CLAIMED_INTENT_VERSION:
        return None
    intent = ClaimedTaskIntent.model_validate_json(raw)
    if (
        intent.canonical() != raw
        or intent.claim.queue.deployment != intent.snapshot.deployment
    ):
        raise ValueError("noncanonical claimed Task intent")
    return intent
