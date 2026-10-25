"""Private typed host configuration. Loading this DTO never resolves secrets."""
from __future__ import annotations

from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import Field, field_validator

from actions.server.deployments.ids import ProviderProfileRevisionRef
from actions.server.deployments.logical_bindings import _Value
from actions.server.deployments.provider_registry import canonical, digest


class SecretVersion(_Value):
    slot: str
    version: str

    @field_validator("slot", "version")
    @classmethod
    def uuid(cls, value: str) -> str:
        if str(UUID(value)) != value:
            raise ValueError("canonical secret identity required")
        return value


class DuckDBHost(_Value):
    adapter: Literal["duckdb.sealed-relations/v1"] = "duckdb.sealed-relations/v1"
    external_access: Literal[False] = False
    extension_loading: Literal[False] = False


class PostgreSQLHost(_Value):
    adapter: Literal[
        "postgresql.sealed-relations/v1"
    ] = "postgresql.sealed-relations/v1"
    host: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}$")
    port: int = Field(ge=1, le=65535)
    database: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")
    username: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")
    password: SecretVersion
    ca_bundle: SecretVersion | None = None
    sslmode: Literal["verify-full"] = "verify-full"
    connect_timeout_seconds: Literal[2] = 2


HostAdapter = Annotated[
    Union[DuckDBHost, PostgreSQLHost], Field(discriminator="adapter")
]


class ProviderHostConfig(_Value):
    schema_version: Literal[
        "actions.local-provider-config/v1"
    ] = "actions.local-provider-config/v1"
    provider: ProviderProfileRevisionRef
    source_revision: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    host: HostAdapter

    @property
    def config_digest(self) -> str:
        return digest("actions.local-provider-config/v1", canonical(self))
