"""Typed CanvasSpec models and bounded JSON validation."""

from __future__ import annotations

import json
import re
from typing import Annotated, Literal, TypeAlias, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

SCHEMA_VERSION = "actions.canvas-spec/v1"
SCHEMA_VERSION_V2 = "actions.canvas-spec/v2"
MAX_CANVAS_SPEC_BYTES = 64 * 1024
MAX_NODE_DEPTH = 8
MAX_NODE_COUNT = 128
MAX_BINDING_COUNT = 32
_MAX_JSON_CONTAINER_DEPTH = 32

_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


class CanvasSpecValidationError(ValueError):
    """A CanvasSpec document violates the versioned authoring contract."""


class _CanvasModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        revalidate_instances="always",
        strict=True,
        validate_by_alias=True,
        validate_by_name=False,
    )


_Text = Annotated[str, Field(min_length=1, max_length=4096, strict=True)]
_ShortText = Annotated[str, Field(min_length=1, max_length=256, strict=True)]
_Identifier = Annotated[str, Field(pattern=_IDENTIFIER.pattern, strict=True)]
CanvasBindingId: TypeAlias = Annotated[
    str, Field(pattern=_IDENTIFIER.pattern, strict=True)
]
_Children = Annotated[
    tuple["CanvasNode", ...], Field(max_length=MAX_NODE_COUNT, strict=False)
]


class CanvasStack(_CanvasModel):
    type: Literal["stack"]
    id: _Identifier
    children: _Children


class CanvasText(_CanvasModel):
    type: Literal["text"]
    id: _Identifier
    text: _Text


class CanvasFormField(_CanvasModel):
    name: _Identifier
    label: _ShortText
    type: Literal["text", "integer", "boolean"]
    required: bool


class CanvasForm(_CanvasModel):
    type: Literal["form"]
    id: _Identifier
    binding_id: CanvasBindingId = Field(alias="bindingId")
    submit_label: Annotated[
        str, Field(alias="submitLabel", min_length=1, max_length=128, strict=True)
    ]
    fields: Annotated[
        tuple[CanvasFormField, ...], Field(min_length=1, max_length=32, strict=False)
    ]

    @model_validator(mode="after")
    def unique_field_names(self) -> CanvasForm:
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("form field names must be unique within a form")
        return self


class CanvasTableColumn(_CanvasModel):
    key: _Identifier
    label: _ShortText


class CanvasTable(_CanvasModel):
    type: Literal["table"]
    id: _Identifier
    binding_id: CanvasBindingId = Field(alias="bindingId")
    rows_key: Annotated[
        str, Field(alias="rowsKey", pattern=_IDENTIFIER.pattern, strict=True)
    ]
    columns: Annotated[
        tuple[CanvasTableColumn, ...], Field(min_length=1, max_length=16, strict=False)
    ]

    @model_validator(mode="after")
    def unique_column_keys(self) -> CanvasTable:
        keys = [column.key for column in self.columns]
        if len(keys) != len(set(keys)):
            raise ValueError("table column keys must be unique")
        return self


class CanvasStatus(_CanvasModel):
    type: Literal["status"]
    id: _Identifier
    binding_id: CanvasBindingId = Field(alias="bindingId")


class CanvasArtifact(_CanvasModel):
    type: Literal["artifact"]
    id: _Identifier
    binding_id: CanvasBindingId = Field(alias="bindingId")
    label: _ShortText


CanvasNode = Annotated[
    Union[
        CanvasStack, CanvasText, CanvasForm, CanvasTable, CanvasStatus, CanvasArtifact
    ],
    Field(discriminator="type"),
]

CanvasStack.model_rebuild()


class CanvasStackV2(_CanvasModel):
    type: Literal["stack"]
    id: _Identifier
    children: Annotated[
        tuple["CanvasNodeV2", ...], Field(max_length=MAX_NODE_COUNT, strict=False)
    ]


class CanvasCard(_CanvasModel):
    type: Literal["card"]
    id: _Identifier
    title: _ShortText
    children: Annotated[
        tuple["CanvasNodeV2", ...], Field(max_length=MAX_NODE_COUNT, strict=False)
    ]


class CanvasChart(_CanvasModel):
    type: Literal["chart"]
    id: _Identifier
    title: _ShortText
    binding_id: CanvasBindingId = Field(alias="bindingId")
    rows_key: _Identifier = Field(alias="rowsKey")
    chart_type: Literal["bar", "line"] = Field(alias="chartType")
    label_key: _Identifier = Field(alias="labelKey")
    value_key: _Identifier = Field(alias="valueKey")


class CanvasLog(_CanvasModel):
    type: Literal["log"]
    id: _Identifier
    title: _ShortText
    binding_id: CanvasBindingId = Field(alias="bindingId")
    rows_key: _Identifier = Field(alias="rowsKey")
    message_key: _Identifier = Field(alias="messageKey")


class CanvasInspector(_CanvasModel):
    type: Literal["inspector"]
    id: _Identifier
    title: _ShortText
    binding_id: CanvasBindingId = Field(alias="bindingId")
    value_key: _Identifier = Field(alias="valueKey")
    fields: Annotated[
        tuple[CanvasTableColumn, ...], Field(min_length=1, max_length=16, strict=False)
    ]

    @model_validator(mode="after")
    def unique_field_keys(self) -> CanvasInspector:
        keys = [field.key for field in self.fields]
        if len(keys) != len(set(keys)):
            raise ValueError("inspector field keys must be unique")
        return self


CanvasNodeV2 = Annotated[
    Union[
        CanvasStackV2,
        CanvasText,
        CanvasForm,
        CanvasTable,
        CanvasStatus,
        CanvasArtifact,
        CanvasCard,
        CanvasChart,
        CanvasLog,
        CanvasInspector,
    ],
    Field(discriminator="type"),
]
CanvasStackV2.model_rebuild()
CanvasCard.model_rebuild()
_Spec = TypeVar("_Spec", bound="_CanvasSpecBase")


class _CanvasSpecBase(_CanvasModel):
    """A frozen, declarative Canvas view with logical binding labels only."""

    model_config = ConfigDict(
        title="CanvasSpec",
        extra="forbid",
        frozen=True,
        revalidate_instances="always",
        strict=True,
        validate_by_alias=True,
        validate_by_name=False,
    )

    schema_version: str = Field(alias="schemaVersion")
    title: Annotated[str, Field(min_length=1, max_length=128, strict=True)]
    visibility: Annotated[
        tuple[Literal["model", "app"], ...], Field(max_length=2, strict=False)
    ]
    binding_ids: Annotated[
        tuple[CanvasBindingId, ...],
        Field(alias="bindingIds", max_length=MAX_BINDING_COUNT, strict=False),
    ]
    root: CanvasNode | CanvasNodeV2

    @model_validator(mode="after")
    def validate_tree_and_bindings(self: _Spec) -> _Spec:
        if len(self.visibility) != len(set(self.visibility)):
            raise ValueError("visibility values must be unique")

        binding_ids = list(self.binding_ids)
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError("binding IDs must be unique")

        node_ids: set[str] = set()
        referenced_binding_ids: set[str] = set()
        count = 0
        pending: list[tuple[CanvasNode | CanvasNodeV2, int]] = [(self.root, 1)]
        while pending:
            node, depth = pending.pop()
            if depth > MAX_NODE_DEPTH:
                raise ValueError(f"Canvas node depth exceeds maximum {MAX_NODE_DEPTH}")
            count += 1
            if count > MAX_NODE_COUNT:
                raise ValueError(f"Canvas node count exceeds maximum {MAX_NODE_COUNT}")
            if node.id in node_ids:
                raise ValueError("Canvas node IDs must be unique")
            node_ids.add(node.id)

            if isinstance(node, (CanvasStack, CanvasStackV2, CanvasCard)):
                pending.extend((child, depth + 1) for child in reversed(node.children))
            elif isinstance(node, CanvasText):
                continue
            else:
                referenced_binding_ids.add(node.binding_id)

        allowed_binding_ids = set(binding_ids)
        if referenced_binding_ids - allowed_binding_ids:
            raise ValueError("node references an undeclared logical binding ID")
        if allowed_binding_ids - referenced_binding_ids:
            raise ValueError("binding IDs must be referenced by at least one node")

        serialized = json.dumps(
            self.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        try:
            encoded_size = len(serialized.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise ValueError("CanvasSpec strings must contain valid Unicode") from exc
        if encoded_size > MAX_CANVAS_SPEC_BYTES:
            raise ValueError("CanvasSpec exceeds 64 KiB")
        return self

    @classmethod
    def from_json(cls: type[_Spec], raw: str | bytes | bytearray) -> _Spec:
        """Parse bounded JSON, reject duplicate keys, then validate the spec."""
        if isinstance(raw, str):
            try:
                encoded = raw.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise CanvasSpecValidationError(
                    "CanvasSpec must be valid UTF-8 JSON"
                ) from exc
        elif isinstance(raw, (bytes, bytearray)):
            encoded = bytes(raw)
        else:
            raise TypeError("CanvasSpec JSON must be str or bytes")

        if len(encoded) > MAX_CANVAS_SPEC_BYTES:
            raise CanvasSpecValidationError("CanvasSpec exceeds 64 KiB")

        try:
            text = encoded.decode("utf-8")
            _check_json_depth(text)
            document = json.loads(
                text,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_non_json_constant,
            )
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValueError,
            RecursionError,
        ) as exc:
            if isinstance(exc, CanvasSpecValidationError):
                raise
            raise CanvasSpecValidationError(f"invalid CanvasSpec JSON: {exc}") from exc
        return _validate_as(cls, document)

    @classmethod
    def from_python(cls: type[_Spec], values: object) -> _Spec:
        """Build from Python field names while keeping JSON validation alias-only."""
        try:
            return cls.model_validate(values, by_alias=False, by_name=True)
        except (ValidationError, TypeError, ValueError, RecursionError) as exc:
            raise CanvasSpecValidationError(
                f"invalid CanvasSpec Python values: {exc}"
            ) from exc

    def to_json(self) -> str:
        """Return canonical UTF-8 JSON bytes represented as a string."""
        return json.dumps(
            self.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )


class CanvasSpec(_CanvasSpecBase):
    """Closed v1 reader; its canonical serialization is unchanged."""

    schema_version: Literal["actions.canvas-spec/v1"] = Field(alias="schemaVersion")
    root: CanvasNode


class CanvasSpecV2(_CanvasSpecBase):
    """Explicit v2 reader adding bounded card, chart, log and inspector syntax."""

    schema_version: Literal["actions.canvas-spec/v2"] = Field(alias="schemaVersion")
    root: CanvasNodeV2


def parse_canvas_spec(raw: str | bytes | bytearray) -> CanvasSpec | CanvasSpecV2:
    """Parse bounded JSON and dispatch only an explicitly supported version."""
    # Reuse the bounded/duplicate-key parser, then narrow its result by version.
    parsed = _CanvasSpecBase.from_json(raw)
    return validate_canvas_spec(parsed.model_dump(mode="json", by_alias=True))


def validate_canvas_spec(document: object) -> CanvasSpec | CanvasSpecV2:
    """Validate either explicit version without upgrading retained documents."""
    if type(document) is not dict:  # noqa: E721 -- public JSON objects only
        raise CanvasSpecValidationError("CanvasSpec document must be an object")
    version = document.get("schemaVersion")
    if version == SCHEMA_VERSION:
        return _validate_as(CanvasSpec, document)
    if version == SCHEMA_VERSION_V2:
        return _validate_as(CanvasSpecV2, document)
    raise CanvasSpecValidationError("unsupported CanvasSpec version")


def _validate_as(cls: type[_Spec], document: object) -> _Spec:
    """Validate a public CanvasSpec document using only its JSON property names."""
    try:
        spec = cls.model_validate(document, by_alias=True, by_name=False)
    except (ValidationError, TypeError, ValueError, RecursionError) as exc:
        if isinstance(exc, CanvasSpecValidationError):
            raise
        raise CanvasSpecValidationError(f"invalid CanvasSpec: {exc}") from exc
    return spec


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_non_json_constant(value: str) -> None:
    raise ValueError(f"non-JSON numeric constant: {value}")


def _check_json_depth(text: str) -> None:
    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > _MAX_JSON_CONTAINER_DEPTH:
                raise ValueError(
                    f"JSON container depth exceeds maximum {_MAX_JSON_CONTAINER_DEPTH}"
                )
        elif character in "]}":
            depth -= 1
