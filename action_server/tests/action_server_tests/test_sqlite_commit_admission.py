"""Independent admission regression; use candidate Runtime source via PYTHONPATH."""

import pytest

from actions.server._database import Database


class CommitFailure(RuntimeError):
    pass


class FailingCommitConnection:
    """Fail before SQLite durability while keeping the same connection alive."""

    def __init__(self, connection):
        self.connection = connection
        self.failure = CommitFailure("injected nondurable SQLite commit failure")
        self.rollback_calls = 0
        self.commit_calls = 0
        self.rollback_failure = None

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def commit(self):
        self.commit_calls += 1
        raise self.failure

    def rollback(self):
        self.rollback_calls += 1
        if self.rollback_failure is not None:
            raise self.rollback_failure
        return self.connection.rollback()


def test_nondurable_commit_failure_rolls_back_same_connection(tmp_path):
    db = Database(tmp_path / "state.db")
    with db.connect():
        connection = db._tlocal.conn
        with db.transaction():
            db.execute("CREATE TABLE generation (value TEXT NOT NULL)")
            db.execute("INSERT INTO generation VALUES ('last-good')")
        proxy = FailingCommitConnection(connection)
        db._tlocal.conn = proxy
        try:
            with pytest.raises(CommitFailure) as caught:
                with db.transaction():
                    db.execute("UPDATE generation SET value = 'candidate'")
            assert caught.value is proxy.failure
            # Inspect before closing/reconnecting: close would hide this defect.
            observed = {
                "rows": connection.execute("SELECT value FROM generation").fetchall(),
                "sqlite_in_transaction": connection.in_transaction,
                "database_in_transaction": db.in_transaction(),
                "rollback_calls": proxy.rollback_calls,
                "commit_calls": proxy.commit_calls,
            }
            print("SAME_CONNECTION_STATE", observed)
            assert observed == {
                "rows": [("last-good",)],
                "sqlite_in_transaction": False,
                "database_in_transaction": False,
                "rollback_calls": 1,
                "commit_calls": 1,
            }
            # The connection must be usable for a subsequent admission.
            db._tlocal.conn = connection
            with db.transaction():
                db.execute("UPDATE generation SET value = 'recovered'")
            assert connection.execute("SELECT value FROM generation").fetchone() == (
                "recovered",
            )
        finally:
            db._tlocal.conn = connection
            connection.rollback()


def test_batch_commit_failure_rolls_back_staging_without_publication(
    tmp_path, monkeypatch
):
    from actions.server import _actions_import, _api_action_routes, _models
    from actions.server._models import Action, ActionPackage, get_model_db_rules

    db = Database(tmp_path / "catalog.db")
    db.initialize([ActionPackage, Action])
    old_snapshot = tmp_path / "last-good-source"
    candidate_snapshot = tmp_path / "candidate-source"
    old_snapshot.mkdir()
    candidate_snapshot.mkdir()
    (old_snapshot / "action.py").write_text("last-good", encoding="utf-8")
    (candidate_snapshot / "action.py").write_text("candidate", encoding="utf-8")
    old_package = ActionPackage("package-id", "package", str(old_snapshot), "old", "{}")
    old_action = Action(
        "action-id", "package-id", "do_it", "last-good", "action.py", 1, "{}", "{}"
    )
    new_package = ActionPackage(
        "candidate-id", "package", str(candidate_snapshot), "new", "{}"
    )
    new_action = Action(
        "candidate-action",
        "candidate-id",
        "do_it",
        "candidate",
        "action.py",
        1,
        "{}",
        "{}",
    )
    events = []
    public_generation = {"value": "last-good"}
    pool_generation = {"value": "last-good"}

    def collect(**kwargs):
        assert not db.in_transaction(), "slow collection must precede admission"
        kwargs["_prepared"].append((new_package, [new_action]))

        def cleanup():
            import shutil

            events.append("candidate-cleanup")
            shutil.rmtree(candidate_snapshot)

        kwargs["_candidate_cleanup"].append(cleanup)

    def prepare_generation():
        assert db.in_transaction()
        assert db.all(Action)[0].docs == "candidate"
        events.append("prepare")
        pool_generation["value"] = "candidate"

        def publish():
            events.append("publish")
            public_generation["value"] = "candidate"

        def rollback():
            events.append("rollback")
            pool_generation["value"] = "last-good"

        return publish, rollback

    monkeypatch.setattr(_models, "get_db", lambda: db)
    monkeypatch.setattr(_actions_import, "import_action_package", collect)
    # Exercise the real batch/database writes; route construction is a separate gate.
    monkeypatch.setattr(
        _api_action_routes._ActionRoutes, "prepare_actions", lambda self: None
    )
    with db.connect():
        db.create_tables(get_model_db_rules())
        with db.transaction():
            db.insert(old_package)
            db.insert(old_action)
        connection = db._tlocal.conn
        proxy = FailingCommitConnection(connection)
        db._tlocal.conn = proxy
        try:
            with pytest.raises(CommitFailure) as caught:
                _actions_import.import_action_packages(
                    datadir=tmp_path,
                    action_package_dirs=[str(tmp_path / "input")],
                    disable_not_imported=True,
                    skip_lint=True,
                    whitelist="",
                    after_import=prepare_generation,
                )
            assert caught.value is proxy.failure
            assert events == ["prepare", "rollback", "candidate-cleanup"]
            assert public_generation["value"] == "last-good"
            assert pool_generation["value"] == "last-good"
            assert (old_snapshot / "action.py").read_text(
                encoding="utf-8"
            ) == "last-good"
            assert not candidate_snapshot.exists()
            observed = {
                "directory": db.all(ActionPackage)[0].directory,
                "docs": db.all(Action)[0].docs,
                "sqlite_in_transaction": connection.in_transaction,
                "database_in_transaction": db.in_transaction(),
                "rollback_calls": proxy.rollback_calls,
            }
            print("BATCH_SAME_CONNECTION_STATE", observed, "EVENTS", events)
            assert observed == {
                "directory": str(old_snapshot),
                "docs": "last-good",
                "sqlite_in_transaction": False,
                "database_in_transaction": False,
                "rollback_calls": 1,
            }
        finally:
            db._tlocal.conn = connection
            connection.rollback()


def test_rollback_failure_preserves_original_commit_error(tmp_path):
    db = Database(tmp_path / "rollback-failure.db")
    with db.connect():
        connection = db._tlocal.conn
        with db.transaction():
            db.execute("CREATE TABLE generation (value TEXT NOT NULL)")
            db.execute("INSERT INTO generation VALUES ('last-good')")
        proxy = FailingCommitConnection(connection)
        proxy.rollback_failure = RuntimeError("injected SQLite rollback failure")
        db._tlocal.conn = proxy
        try:
            with pytest.raises(CommitFailure) as caught:
                with db.transaction():
                    db.execute("UPDATE generation SET value = 'candidate'")
            assert caught.value is proxy.failure
            assert proxy.rollback_calls == 1
            assert not db.in_transaction()
        finally:
            # A failed driver rollback cannot promise clean SQLite state.
            db._tlocal.conn = connection
            connection.rollback()
