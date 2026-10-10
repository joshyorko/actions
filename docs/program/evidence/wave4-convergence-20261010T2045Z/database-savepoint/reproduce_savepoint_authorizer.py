"""Real SQLite authorizer failure at nested SAVEPOINT; no mocked Database methods."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

source_root = Path("/workspace/work/actions-mk3-db-savepoint/action_server/src")
sys.path.insert(0, str(source_root))
from actions.server._database import Database  # noqa: E402

observed_authorizer: list[tuple[int, str | None, str | None]] = []
db = Database(":memory:")
with db.connect():
    connection = db._tlocal.conn

    def authorizer(action: int, first: str | None, second: str | None, *_: str) -> int:
        observed_authorizer.append((action, first, second))
        if action == sqlite3.SQLITE_SAVEPOINT and first == "BEGIN":
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    connection.set_authorizer(authorizer)
    try:
        with db.transaction():
            with db.transaction():
                raise AssertionError("the denied SAVEPOINT must prevent body entry")
    except BaseException as error:
        print("exception_type:", type(error).__module__ + "." + type(error).__name__)
        print("exception_message:", str(error))
        context = error.__context__
        print(
            "context_type:",
            None if context is None else type(context).__module__ + "." + type(context).__name__,
        )
        print("context_message:", None if context is None else str(context))
    print("db_threadlocal_counter:", db._tlocal.in_transaction)
    print("db_in_transaction:", db.in_transaction())
    print("sqlite_in_transaction:", connection.in_transaction)
    print("authorizer_savepoint_events:", [x for x in observed_authorizer if x[0] == sqlite3.SQLITE_SAVEPOINT])

print("python:", sys.executable)
print("database_module:", Path(sys.modules["actions.server._database"].__file__).resolve())
print("sqlite:", sqlite3.sqlite_version)
