"""Common SQL metadata only: no connection descriptors or implicit grants."""
from pydantic.dataclasses import dataclass

from actions.server._models import _db_rules


@dataclass
class FoundrySourceRevision:
    id: str
    workspace_id: str
    revision_id: str
    manifest_json: str
    _db_rules.foreign_keys.add("FoundrySourceRevision.workspace_id")
    _db_rules.indexes.add("FoundrySourceRevision.workspace_id")


@dataclass
class FoundryProviderRevision:
    id: str
    workspace_id: str
    descriptor_json: str
    foundry_source_revision_id: str
    _db_rules.foreign_keys.update(
        {
            "FoundryProviderRevision.workspace_id",
            "FoundryProviderRevision.foundry_source_revision_id",
        }
    )
    _db_rules.indexes.add("FoundryProviderRevision.workspace_id")


@dataclass
class FoundryProviderAvailability:
    id: str
    foundry_provider_revision_id: str
    generation: int
    enabled: bool
    _db_rules.foreign_keys.add(
        "FoundryProviderAvailability.foundry_provider_revision_id"
    )


MODEL_CLASSES = [
    FoundrySourceRevision,
    FoundryProviderRevision,
    FoundryProviderAvailability,
]
