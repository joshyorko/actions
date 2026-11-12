"""Read-only optional provider injection from explicit private operator state."""
from pathlib import Path

from actions.server._database import Database
from actions.server.foundry.provider_catalog import PrivateProviderStore
from actions.server.foundry.provider_registry import SqlProviderRegistry
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.filesystem import FilesystemOutputProvider


def load_configured_provider_registry(
    db: Database, datadir: Path, blobs: FilesystemOutputProvider
) -> SqlProviderRegistry | None:
    marker = datadir / "provider-state"
    if not marker.exists() and not marker.is_symlink():
        return None
    try:
        # Do not allocate a realm or add bootstrap operations/permissions.
        from actions.server._local_authorization import _owner

        actor, workspace = _owner(db)
        with PrivateProviderStore(datadir, actor, workspace) as store:
            current = store.current()
            if current is None:
                return None  # Staged intents are never recovered on startup.
            from actions.server._local_provider_setup import verify_committed_catalog

            verify_committed_catalog(db, store, current)
            catalog, evidence = store.reconstruct(current, blobs)
            registry = SqlProviderRegistry(db, SqlFoundryAuthorization(db), evidence)
            for entry in catalog.entries:
                if registry._read(entry.descriptor.reference)[0] != entry.descriptor:
                    raise ValueError("configured provider identity differs")
            return registry
    except Exception:
        raise ValueError("explicit provider configuration unavailable") from None
