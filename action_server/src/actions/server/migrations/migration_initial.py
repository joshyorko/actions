from actions.server._database import Database


def migrate(db: Database) -> None:
    from actions.server._database import redact_database_url

    raise RuntimeError(
        f"""Error: 
It seems that this version of the database ({redact_database_url(db.db_path)}) is too old.
Please erase it and recreate it from scratch."""
    )
