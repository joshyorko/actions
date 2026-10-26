"""Frozen pre-provider/Task DDL, captured from the pinned installed a30 wheel."""

import json
from pathlib import Path

from actions.server._database import Database


def create_historical_schema(db: Database, version: int) -> None:
    fixture = json.loads(
        Path(__file__).with_name("foundry_historical_ddl.json").read_text()
    )
    statements = fixture["schemas"][str(version)][db.backend_name]
    for statement in statements:
        assert "state_updated_ms" not in statement
        assert "run_task_receipt" not in statement
        assert "run_execution_intent" not in statement
        db.execute(statement)


def historical_rows(db: Database, version: int) -> dict:
    """Snapshot actual historical columns without consulting future model fields."""
    import re

    fixture = json.loads(
        Path(__file__).with_name("foundry_historical_ddl.json").read_text()
    )
    result = {}
    for statement in fixture["schemas"][str(version)][db.backend_name]:
        match = re.match(r"\s*CREATE TABLE IF NOT EXISTS ([a-z_]+)\(", statement)
        if match:
            table = match.group(1)
            with db.cursor() as cursor:
                db.execute_query(cursor, f"SELECT * FROM {table}")
                result[table] = cursor.fetchall()
    return result
