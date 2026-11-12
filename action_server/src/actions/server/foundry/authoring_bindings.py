"""Explicit logical-provider selections, distinct from Canvas UI bindings."""
from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from actions.server.deployments.ids import ProviderProfileRevisionRef


class DataBindingChoice(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    binding_id: str = Field(alias="bindingId", pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    requirement_id: str = Field(
        alias="requirementId", pattern=r"^[a-z][a-z0-9_-]{0,63}$"
    )
    provider: ProviderProfileRevisionRef


def parse_data_bindings(
    value: object, binding_ids: Sequence[str]
) -> tuple[DataBindingChoice, ...]:
    if not isinstance(value, list) or len(value) > 64:
        raise ValueError("bounded explicit data binding choices required")
    choices = tuple(TypeAdapter(list[DataBindingChoice]).validate_python(value))
    keys = [(choice.binding_id, choice.requirement_id) for choice in choices]
    if len(keys) != len(set(keys)) or any(
        choice.binding_id not in binding_ids for choice in choices
    ):
        raise ValueError("one exact declared binding/requirement choice required")
    return choices


def public_schema(model: type[BaseModel]) -> dict:
    """Inline this bounded acyclic DTO so nested tool schemas have no broken refs."""
    schema = model.model_json_schema()
    definitions = schema.pop("$defs", {})

    def expand(value):
        if isinstance(value, list):
            return [expand(item) for item in value]
        if isinstance(value, dict):
            if "$ref" in value:
                key = value["$ref"].removeprefix("#/$defs/")
                return expand(definitions[key])
            return {key: expand(item) for key, item in value.items()}
        return value

    return expand(schema)
