"""Explicit model-authored queue selections, never queue grants or admission."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from actions.server.deployments.foundry_values import (
    CapabilityWorkItemPolicy,
    DeploymentSpecification,
    QueueName,
)
from actions.server.foundry.authoring_values import CanvasBinding


class QueuePolicyRequest(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    binding_id: str = Field(alias="bindingId", min_length=1, max_length=64)
    input_mode: Literal["none", "optional", "required", "claim"]
    input_queue: QueueName | None = None
    output_queue: QueueName | None = None
    max_input_bytes: int = Field(default=262144, ge=1, le=262144)
    max_output_items: int = Field(default=0, ge=0, le=64)
    max_output_bytes: int = Field(default=0, ge=0, le=262144)

    @model_validator(mode="after")
    def explicit_selection(self):
        if (self.input_mode == "none") != (self.input_queue is None):
            raise ValueError("exact input queue selection required")
        if self.output_queue is None:
            if self.max_output_items or self.max_output_bytes:
                raise ValueError("output bounds require an exact queue")
        elif not self.max_output_items or not self.max_output_bytes:
            raise ValueError("output queue requires positive bounded limits")
        return self


def parse_queue_policies(
    value: object, binding_ids: Sequence[str]
) -> tuple[QueuePolicyRequest, ...]:
    if not isinstance(value, list) or len(value) > 64:
        raise ValueError("bounded explicit queue policy list required")
    requests = tuple(TypeAdapter(list[QueuePolicyRequest]).validate_python(value))
    names = [request.binding_id for request in requests]
    if len(set(names)) != len(names) or any(name not in binding_ids for name in names):
        raise ValueError("queue policy requires one exact declared binding")
    return requests


def select_queue_policies(
    selection: DeploymentSpecification,
    bindings: Sequence[CanvasBinding],
    requests: Sequence[QueuePolicyRequest],
) -> DeploymentSpecification:
    capabilities = {binding.binding_id: binding.capability for binding in bindings}
    policies = []
    for request in requests:
        values = request.model_dump(exclude={"binding_id"})
        policies.append(
            CapabilityWorkItemPolicy(
                capability=capabilities[request.binding_id], **values
            )
        )
    raw = selection.model_dump(mode="json")
    # The existing host selection remains authoritative; do not overwrite a
    # separately supplied policy or merge conflicting authoring authorities.
    if selection.work_item_policies:
        raise ValueError("host already selected Work Item policy")
    raw["work_item_policies"] = [policy.model_dump(mode="json") for policy in policies]
    import json

    return DeploymentSpecification.model_validate_json(json.dumps(raw))
