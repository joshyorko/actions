"""
The way that migrations work is the following:

We have a table with the id and name of each migration applied.

When starting up we connect to the db and see the current version.
Then, we apply each pending migration since the last version.
"""

import logging
import os.path
import typing
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Union

log = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from actions.server._database import Database

MIGRATION_ID_TO_NAME: Dict[int, str] = {
    # we'll look for a 'migration_initial' module based on this.
    1: "initial",
    # we'll look for a 'migration_add_action_enabled' module based on this.
    2: "add_action_enabled",
    # we'll look for a 'migration_add_is_consequential' module based on this.
    3: "add_is_consequential",
    # we'll look for a 'migration_add_action_managed_params' module based on this.
    4: "add_action_managed_params",
    # we'll look for a 'migration_add_action_options' module based on this.
    5: "add_action_options",
    # we'll look for a 'migration_add_session_and_indexes' module based on this.
    6: "add_session_and_indexes",
    # we'll look for a 'migration_add_code_verifier' module based on this.
    7: "add_code_verifier",
    # we'll look for a 'migration_add_request_id_to_run' module based on this.
    8: "add_request_id_to_run",
    # we'll look for a 'migration_add_robot_run_columns' module based on this.
    9: "add_robot_run_columns",
    # we'll look for a 'migration_add_schedules' module based on this.
    10: "add_schedules",
    # we'll look for a 'migration_reconcile_schema' module based on this.
    11: "reconcile_schema",
}

CURRENT_VERSION: int = max(MIGRATION_ID_TO_NAME.keys())


@dataclass
class Migration:
    id: int  # Migration id
    name: str  # Migration name


def _migrate_to(db: "Database", db_migration_version: int) -> None:
    from importlib import import_module

    name = MIGRATION_ID_TO_NAME[db_migration_version]
    mod = import_module(f"actions.server.migrations.migration_{name}")
    mod.migrate(db)


def migrate_db(
    db_path: Union[Path, str],
    to_version=CURRENT_VERSION,
    database: Optional["Database"] = None,
) -> bool:
    """
    Returns true if the migration worked properly or if the migration was not needed
    and false if the migration could not be done for some reason.

    :param database: Expected to be passed when dealing with an in-memory database.
    """
    from actions.server._database import normalize_database_url, redact_database_url

    db_path = normalize_database_url(db_path)
    is_postgresql = isinstance(db_path, str) and db_path.lower().startswith(
        "postgresql://"
    )
    if not is_postgresql:
        assert os.path.exists(
            db_path
        ), f"Unable to do migration. {redact_database_url(db_path)} does not exist."

    migration_status = db_migration_status(db_path)
    if migration_status == MigrationStatus.UP_TO_DATE:
        return True  # It's already correct

    import shutil
    import time

    path = Path(db_path) if not is_postgresql else None
    if path is not None:
        parent_dir = path.parent
        name = path.name
        log.info(
            "Preparing to migrate database at: %s",
            redact_database_url(db_path),
        )
        backup_file = parent_dir / f"{name}-pre-migration-{to_version}-{time.time()}.bak"
        log.info("Creating backup at: %s", backup_file)
        shutil.copyfile(path, backup_file)

    from actions.server._database import Database
    from actions.server._models import get_all_model_classes, get_model_db_rules

    db = database or Database(db_path)
    with db.connect():
        with db.transaction():
            if db.backend_name == "postgresql":
                db.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(?))",
                    ["actions-runtime-schema-migrations"],
                )
                if "migration" in db.list_table_names() and db.all(Migration):
                    if max(x.id for x in db.all(Migration)) >= to_version:
                        return True
            db.initialize(get_all_model_classes())
            if "migration" not in db.list_table_names():
                if db.backend_name != "postgresql":
                    raise RuntimeError(
                        f"""Error:
It seems that this version of the database ({redact_database_url(db.db_path)}) is too old.
Please erase it and recreate it from scratch."""
                    )
                db.create_tables(get_model_db_rules())
                db.insert(Migration(CURRENT_VERSION, MIGRATION_ID_TO_NAME[CURRENT_VERSION]))
                from actions.server._models import ALL_COUNTERS, Counter

                for counter in ALL_COUNTERS:
                    db.insert(Counter(counter, 0))
                db_migration_version = CURRENT_VERSION
            else:
                migrations = db.all(Migration)
                if not migrations:
                    raise RuntimeError(
                        f"""Error: 
It seems that this version of the database ({redact_database_url(db.db_path)}) is too old.
Please erase it and recreate it from scratch."""
                    )

                else:
                    db_migration_version = max(x.id for x in migrations)

            while db_migration_version < to_version:
                db_migration_version += 1
                log.info(
                    "Will migrate to version: %s (%s)",
                    db_migration_version,
                    MIGRATION_ID_TO_NAME[db_migration_version],
                )
                _migrate_to(db, db_migration_version)

    return True


class MigrationStatus(Enum):
    UP_TO_DATE = "UP_TO_DATE"
    NEEDS_MIGRATION = "NEEDS_MIGRATION"
    TOO_NEW = "TOO_NEW"


def _db_migration_status(db: "Database") -> MigrationStatus:
    if "migration" not in db.list_table_names():
        return MigrationStatus.NEEDS_MIGRATION

    db.initialize([Migration])
    migrations = db.all(Migration)
    if not migrations:
        # No migrations applied, do it now.
        return MigrationStatus.NEEDS_MIGRATION

    latest_migration_applied = max(x.id for x in migrations)

    if latest_migration_applied == CURRENT_VERSION:
        return MigrationStatus.UP_TO_DATE

    if latest_migration_applied > CURRENT_VERSION:
        return MigrationStatus.TOO_NEW

    return MigrationStatus.NEEDS_MIGRATION


def db_migration_status(db_path: Union[Path, str]) -> MigrationStatus:
    from actions.server._database import Database

    if db_path == ":memory:":
        raise RuntimeError("Migration support not available for in-memory database.")

    from actions.server._database import normalize_database_url

    db_path = normalize_database_url(db_path)
    is_postgresql = isinstance(db_path, str) and db_path.startswith("postgresql://")
    path = Path(db_path) if not is_postgresql else None
    if path is not None and not path.exists():
        raise RuntimeError(
            f"Unable to check if migration is pending because file: {db_path} does not exist."
        )

    # Ok, it already exists. Check the migration status.
    db = Database(db_path)
    with db.connect():
        log.info("Checking migration status for database backend: %s", db.backend_name)
        db.log_internal_info()
        return _db_migration_status(db)
