"""Portable named-operation requirements; never provider configuration."""
from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from actions.server.deployments.canonical import canonicalize_json
from actions.server.deployments.ids import ProviderProfileRevisionRef
from actions.server.run_outputs.types import Actor


class _Value(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )


class BindingField(_Value):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    kind: Literal["string", "integer", "number", "boolean"]
    required: bool = True


class BindingOperation(_Value):
    name: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}/v[1-9][0-9]{0,2}$")
    effect: Literal["read", "write"]
    parameters: tuple[BindingField, ...] = Field(max_length=32)
    result: tuple[BindingField, ...] = Field(min_length=1, max_length=32)
    max_rows: int = Field(ge=1, le=100000)
    max_bytes: int = Field(ge=1, le=16 * 1024 * 1024)
    timeout_ms: int = Field(ge=1, le=30000)

    @model_validator(mode="after")
    def normalized_fields(self):
        for name in ("parameters", "result"):
            fields = getattr(self, name)
            if len({field.name for field in fields}) != len(fields):
                raise ValueError("unique typed operation fields required")
            object.__setattr__(
                self, name, tuple(sorted(fields, key=lambda field: field.name))
            )
        return self

    @property
    def contract_digest(self) -> str:
        return (
            "sha256:"
            + hashlib.sha256(
                canonicalize_json(self.model_dump_json().encode())
            ).hexdigest()
        )


class LogicalBindingRequirement(_Value):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    kind: Literal["data", "knowledge"]
    operations: tuple[BindingOperation, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def normalized_operations(self):
        if len({operation.name for operation in self.operations}) != len(
            self.operations
        ):
            raise ValueError("unique named operations required")
        object.__setattr__(
            self,
            "operations",
            tuple(sorted(self.operations, key=lambda operation: operation.name)),
        )
        return self


def normalize_requirements(
    values: Sequence[LogicalBindingRequirement],
) -> tuple[LogicalBindingRequirement, ...]:
    if len(values) > 16 or any(
        not isinstance(value, LogicalBindingRequirement) for value in values
    ):
        raise ValueError("bounded typed logical requirements required")
    result = tuple(LogicalBindingRequirement.model_validate(value) for value in values)
    if len({value.id for value in result}) != len(result):
        raise ValueError("unique logical requirement IDs required")
    return tuple(sorted(result, key=lambda value: value.id))


class ProviderCompatibilityPort(Protocol):
    """Trusted optional compatibility reader; absence never selects a default."""

    def operations(
        self,
        actor: Actor,
        provider: ProviderProfileRevisionRef,
        kind: Literal["data", "knowledge"],
    ) -> Sequence[BindingOperation]:
        ...
