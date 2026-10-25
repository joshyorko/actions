"""Engine-neutral immutable metadata; neither host configuration nor data access."""
from __future__ import annotations

import hashlib
from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from actions.server.deployments.canonical import canonicalize_json
from actions.server.deployments.ids import (
    ProviderProfileId,
    ProviderProfileRevisionId,
    ProviderProfileRevisionRef,
    WorkspaceId,
)
from actions.server.deployments.logical_bindings import BindingOperation, _Value


def canonical(value: _Value) -> str:
    raw = canonicalize_json(value.model_dump_json().encode())
    if len(raw) > 128 * 1024:
        raise ValueError("provider metadata exceeds bound")
    return raw.decode()


def digest(domain: str, raw: str) -> str:
    return "sha256:" + hashlib.sha256((domain + "\n" + raw).encode()).hexdigest()


class SourceObject(_Value):
    name: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    size: int = Field(ge=0, le=64 * 1024 * 1024)


class SourceColumn(_Value):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    kind: Literal["string", "integer", "number", "boolean"]
    nullable: bool = False


class _TableCodec(_Value):
    columns: tuple[SourceColumn, ...] = Field(min_length=1, max_length=32)
    max_rows: int = Field(ge=1, le=100000)
    max_decoded_bytes: int = Field(ge=1, le=64 * 1024 * 1024)
    max_field_bytes: int = Field(ge=1, le=1024 * 1024)

    @model_validator(mode="after")
    def unique_columns(self):
        # Physical column order is semantic and must not be sorted away.
        if len({column.name for column in self.columns}) != len(self.columns):
            raise ValueError("unique source columns required")
        return self


class CsvSourceCodec(_TableCodec):
    format: Literal["csv-utf8/v1"] = "csv-utf8/v1"
    encoding: Literal["utf-8"] = "utf-8"
    delimiter: Literal[","] = ","
    quote: Literal['"'] = '"'
    header: Literal[True] = True
    null_value: Literal["\\N"] = "\\N"
    extra_columns: Literal["reject"] = "reject"
    scalar_conversion: Literal["strict-v1"] = "strict-v1"


class ParquetSourceCodec(_TableCodec):
    format: Literal["parquet-flat/v1"] = "parquet-flat/v1"
    null_value: Literal["native-null"] = "native-null"
    nested_values: Literal["reject"] = "reject"
    external_metadata: Literal["reject"] = "reject"
    compression: Literal["uncompressed"] = "uncompressed"
    max_row_groups: int = Field(ge=1, le=1024)
    scalar_conversion: Literal["strict-v1"] = "strict-v1"


SourceCodec = Annotated[
    Union[CsvSourceCodec, ParquetSourceCodec], Field(discriminator="format")
]


class DecodedSourceObject(SourceObject):
    codec: SourceCodec


class SourceManifest(_Value):
    schema_version: Literal[
        "actions.logical-source/v1", "actions.logical-source/v2"
    ] = "actions.logical-source/v1"
    kind: Literal["data", "knowledge"]
    mode: Literal["sealed-files"] = "sealed-files"
    objects: tuple[Union[DecodedSourceObject, SourceObject], ...] = Field(
        min_length=1, max_length=16
    )

    @model_validator(mode="after")
    def ordered(self):
        decoded = [isinstance(obj, DecodedSourceObject) for obj in self.objects]
        if self.schema_version == "actions.logical-source/v1":
            if any(decoded):
                raise ValueError("v1 source cannot contain a decoder")
        elif not all(decoded) or self.kind != "data":
            raise ValueError("v2 data source requires every decoder")
        if len({x.name for x in self.objects}) != len(self.objects):
            raise ValueError("duplicate logical source object")
        if sum(x.size for x in self.objects) > 64 * 1024 * 1024:
            raise ValueError("retained source byte budget exceeded")
        object.__setattr__(
            self, "objects", tuple(sorted(self.objects, key=lambda x: x.name))
        )
        return self

    @property
    def revision_id(self) -> str:
        return digest(self.schema_version, canonical(self))


class ProviderDescriptor(_Value):
    schema_version: Literal[
        "actions.logical-provider/v1"
    ] = "actions.logical-provider/v1"
    workspace_id: WorkspaceId
    provider_profile_id: ProviderProfileId
    source_revision: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    kind: Literal["data", "knowledge"]
    operations: tuple[BindingOperation, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def ordered(self):
        if len({x.name for x in self.operations}) != len(self.operations):
            raise ValueError("duplicate provider operation")
        object.__setattr__(
            self, "operations", tuple(sorted(self.operations, key=lambda x: x.name))
        )
        return self

    @property
    def reference(self) -> ProviderProfileRevisionRef:
        return ProviderProfileRevisionRef(
            workspace_id=self.workspace_id,
            provider_profile_id=self.provider_profile_id,
            revision_id=ProviderProfileRevisionId(
                digest("actions.logical-provider/v1", canonical(self))
            ),
        )


def require_executable_source(source: SourceManifest) -> SourceManifest:
    """Declaration gate only; does not claim an engine or worker exists."""
    source = SourceManifest.model_validate(source)
    if source.schema_version != "actions.logical-source/v2":
        raise ValueError("source lacks an identity-bound decoder contract")
    return source
