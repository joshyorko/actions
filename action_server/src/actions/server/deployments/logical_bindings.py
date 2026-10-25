"""Portable named-operation requirements; never provider configuration."""
from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

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


class LogicalInputMapping(_Value):
    parameter: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    input: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")


class LogicalInvocation(_Value):
    operation: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}/v[1-9][0-9]{0,2}$")
    inputs: tuple[LogicalInputMapping, ...] = Field(max_length=32)

    @model_validator(mode="after")
    def unique_parameters(self):
        if len({item.parameter for item in self.inputs}) != len(self.inputs):
            raise ValueError("unique logical parameter mapping required")
        object.__setattr__(
            self, "inputs", tuple(sorted(self.inputs, key=lambda item: item.parameter))
        )
        return self


class LogicalBindingRequirement(_Value):
    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    kind: Literal["data", "knowledge"]
    operations: tuple[BindingOperation, ...] = Field(min_length=1, max_length=16)
    invocations: tuple[LogicalInvocation, ...] | None = Field(
        default=None, max_length=16
    )

    @model_serializer(mode="wrap")
    def preserve_legacy_bytes(self, handler):
        value = handler(self)
        if self.invocations is None:
            value.pop("invocations", None)
        return value

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
        if self.invocations is not None:
            if self.kind != "knowledge" or len(self.invocations) != len(
                self.operations
            ):
                raise ValueError("explicit Knowledge invocation coverage required")
            mappings = {item.operation: item for item in self.invocations}
            if len(mappings) != len(self.invocations) or set(mappings) != {
                op.name for op in self.operations
            }:
                raise ValueError("unique exact operation mappings required")
            for operation in self.operations:
                if {field.name for field in operation.parameters} != {
                    item.parameter for item in mappings[operation.name].inputs
                }:
                    raise ValueError("exact declared parameter mapping required")
            object.__setattr__(
                self,
                "invocations",
                tuple(sorted(self.invocations, key=lambda item: item.operation)),
            )
        return self


def validate_invocation_inputs(
    requirements: Sequence[LogicalBindingRequirement], schema: dict
) -> None:
    """Validate artifact-bound mappings against the selected Action input schema."""
    for requirement in requirements:
        if requirement.invocations is None:
            continue
        properties, required = schema.get("properties"), schema.get("required", [])
        if (
            schema.get("type") != "object"
            or not isinstance(properties, dict)
            or not isinstance(required, list)
        ):
            raise ValueError("object Action input schema required for logical mapping")
        operations = {operation.name: operation for operation in requirement.operations}
        for invocation in requirement.invocations:
            parameters = {
                field.name: field
                for field in operations[invocation.operation].parameters
            }
            for item in invocation.inputs:
                selected = properties.get(item.input)
                if (
                    item.input not in required
                    or not isinstance(selected, dict)
                    or selected.get("type") != parameters[item.parameter].kind
                ):
                    raise ValueError(
                        "logical mapping requires a required exactly typed Action input"
                    )


def mapped_parameters(
    requirement: LogicalBindingRequirement, operation: str, schema: dict, inputs: dict
) -> dict:
    """Project only declared top-level inputs; no inference, expressions or paths."""
    requirement = LogicalBindingRequirement.model_validate(requirement)
    validate_invocation_inputs((requirement,), schema)
    matches = [
        item for item in requirement.invocations or () if item.operation == operation
    ]
    if len(matches) != 1:
        raise ValueError("exact logical input mapping required")
    declared = next(item for item in requirement.operations if item.name == operation)
    kinds = {field.name: field.kind for field in declared.parameters}
    result = {}
    for item in matches[0].inputs:
        if item.input not in inputs:
            raise ValueError("mapped Action input missing")
        value, kind = inputs[item.input], kinds[item.parameter]
        allowed = {
            "string": (str,),
            "integer": (int,),
            "number": (int, float),
            "boolean": (bool,),
        }[kind]
        if (
            type(value) not in allowed
            or (type(value) is int and abs(value) > 2**53 - 1)  # noqa: E721 -- reject bool and subclasses
            or (
                type(value) is float  # noqa: E721 -- exact portable scalar
                and (not math.isfinite(value) or abs(value) > 2**53 - 1)
            )
        ):
            raise ValueError("mapped Action input type or portable bound differs")
        result[item.parameter] = value
    return result


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
