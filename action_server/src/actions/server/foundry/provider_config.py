"""Private typed host configuration. Loading this DTO never resolves secrets."""
from __future__ import annotations

from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from actions.server.data_queries.knowledge_values import KnowledgeRevisionRef
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


class KnowledgeDuckDBHost(_Value):
    adapter: Literal["duckdb.knowledge-versions/v1"] = "duckdb.knowledge-versions/v1"
    revision: KnowledgeRevisionRef


class KnowledgePostgreSQLHost(_Value):
    adapter: Literal[
        "postgresql.knowledge-versions/v1"
    ] = "postgresql.knowledge-versions/v1"
    revision: KnowledgeRevisionRef
    host: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9.-]{0,252}$")
    port: int = Field(ge=1, le=65535)
    database: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")
    username: str = Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")
    password: SecretVersion
    ca_bundle: SecretVersion
    sslmode: Literal["verify-full"] = "verify-full"
    connect_timeout_seconds: Literal[2] = 2


HostAdapter = Annotated[
    Union[DuckDBHost, PostgreSQLHost, KnowledgeDuckDBHost, KnowledgePostgreSQLHost],
    Field(discriminator="adapter"),
]


class ProviderHostConfig(_Value):
    schema_version: Literal[
        "actions.local-provider-config/v1", "actions.local-provider-config/v2"
    ] = "actions.local-provider-config/v1"
    provider: ProviderProfileRevisionRef
    source_revision: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    host: HostAdapter

    @model_validator(mode="after")
    def versioned_host(self):
        knowledge = isinstance(
            self.host, (KnowledgeDuckDBHost, KnowledgePostgreSQLHost)
        )
        if knowledge != (self.schema_version == "actions.local-provider-config/v2"):
            raise ValueError("explicit Knowledge configuration v2 required")
        if knowledge and self.host.revision.workspace_id != self.provider.workspace_id:
            raise ValueError("Knowledge host Workspace differs")
        return self

    @property
    def config_digest(self) -> str:
        return digest(self.schema_version, canonical(self))
