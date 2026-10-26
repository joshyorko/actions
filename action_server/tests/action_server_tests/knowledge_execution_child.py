"""Private fixture reconstruction for independent-process retained search proof."""
import json
import os
import sys
import threading
from pathlib import Path

from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.data_queries import knowledge_execution
from actions.server.data_queries.knowledge_execution import (
    KnowledgeExecution,
    KnowledgeExecutionBinding,
    KnowledgeSearch,
)
from actions.server.data_queries.knowledge_values import KnowledgeRevisionRef
from actions.server.data_queries.knowledge_versions import (
    DuckDBKnowledgeVersions,
    PostgreSQLKnowledgeVersions,
)
from actions.server.deployments.ids import ProviderProfileRevisionRef
from actions.server.deployments.provider_registry import SourceManifest
from actions.server.foundry.knowledge_authority import KnowledgeRevisionAuthority
from actions.server.foundry.provider_registry import (
    RetainedSourceEvidence,
    SqlProviderRegistry,
)
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.service import RunOutputService
from actions.server.run_outputs.types import (
    Actor,
    AttemptFence,
    ExecutionSnapshot,
    SealReceipt,
)


def main():
    config = json.loads(Path(sys.argv[1]).read_text())
    snapshots = [
        ExecutionSnapshot.model_validate_json(json.dumps(v))
        for v in config["snapshots"]
    ]
    revision = KnowledgeRevisionRef.model_validate_json(json.dumps(config["revision"]))
    provider_ref = ProviderProfileRevisionRef.model_validate_json(
        json.dumps(config["provider"])
    )
    source = SourceManifest.model_validate_json(json.dumps(config["source"]))
    seals = {
        k: SealReceipt.model_validate_json(json.dumps(v))
        for k, v in config["seals"].items()
    }
    if config["postgres"]:
        import psycopg

        versions = PostgreSQLKnowledgeVersions(
            lambda: psycopg.connect(config["store_location"])
        )
    else:
        import duckdb

        versions = DuckDBKnowledgeVersions(
            lambda: duckdb.connect(config["store_location"])
        )
    fd = os.open(config["blobs"], os.O_RDONLY | os.O_DIRECTORY)
    try:
        with FilesystemOutputProvider(fd) as blobs:
            db = Database(config["database"])
            with db.connect():
                db.initialize(get_all_model_classes())
                auth = SqlFoundryAuthorization(db)
                providers = SqlProviderRegistry(
                    db,
                    auth,
                    RetainedSourceEvidence(
                        blobs,
                        {
                            (str(revision.workspace_id.root), k): v
                            for k, v in seals.items()
                        },
                    ),
                )
                outputs = RunOutputService(
                    db, {s.provider_key: blobs for s in snapshots}
                )
                bindings = tuple(
                    KnowledgeExecutionBinding(
                        s,
                        revision,
                        provider_ref,
                        source,
                        blobs,
                        seals,
                        versions,
                        operation,
                    )
                    for s, operation in zip(snapshots, ["ingest", "search"])
                )
                service = KnowledgeExecution(
                    outputs, KnowledgeRevisionAuthority(db, providers), bindings
                )
                result = service.search_for_execution(
                    Actor.model_validate(config["actor"]),
                    AttemptFence.model_validate(config["fence"]),
                    KnowledgeSearch.model_validate(config["inputs"]),
                    threading.Event(),
                )
                print(
                    json.dumps(
                        {"source": knowledge_execution.__file__, "result": result}
                    )
                )
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
