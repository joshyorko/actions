import datetime
import itertools
import logging
import re
import sqlite3
import sys
import threading
from contextlib import closing, contextmanager
from pathlib import Path
from types import NoneType
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from urllib.parse import urlsplit, urlunsplit

log = logging.getLogger(__name__)

_RE_FIRST_CAP = re.compile("(.)([A-Z][a-z]+)")
_RE_ALL_CAP = re.compile("([a-z0-9])([A-Z])")


T = TypeVar("T")

_SQLToken = Tuple[str, int, int, str]
_SQL_OPERATOR_WORDS = {
    "AND",
    "OR",
    "NOT",
    "IS",
    "IN",
    "LIKE",
    "ILIKE",
    "BETWEEN",
    "THEN",
    "ELSE",
    "WHEN",
    "END",
    "FROM",
    "WHERE",
    "ORDER",
    "GROUP",
    "LIMIT",
    "OFFSET",
    "JOIN",
    "ON",
    "VALUES",
    "SET",
    "RETURNING",
    "UNION",
    "ALL",
    "DISTINCT",
    "HAVING",
    "SELECT",
    "AS",
    "NULL",
    "TRUE",
    "FALSE",
}
_LEGACY_BOOLEAN_COLUMNS = {
    "ENABLED",
    "SKIP_IF_RUNNING",
    "RETRY_ENABLED",
    "RATE_LIMIT_ENABLED",
    "NOTIFY_ON_FAILURE",
    "NOTIFY_ON_SUCCESS",
    "NOTIFICATION_SENT",
}


def _tokenize_sql(sql: str) -> List[_SQLToken]:
    """Tokenize executable SQL while leaving lexical regions opaque."""
    tokens: List[_SQLToken] = []
    i = 0
    while i < len(sql):
        if sql.startswith("--", i):
            end = sql.find("\n", i + 2)
            i = len(sql) if end < 0 else end
            continue
        if sql.startswith("/*", i):
            end = sql.find("*/", i + 2)
            i = len(sql) if end < 0 else end + 2
            continue

        char = sql[i]
        if char.isspace():
            i += 1
            continue

        start = i
        if char in "'\"":
            quote = char
            i += 1
            while i < len(sql):
                if sql[i] == "\\" and quote == "'":
                    i += 2
                elif sql[i] == quote:
                    if i + 1 < len(sql) and sql[i + 1] == quote:
                        i += 2
                    else:
                        i += 1
                        break
                else:
                    i += 1
            tokens.append(("expr", start, i, sql[start:i]))
            continue

        if char == "$":
            match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", sql[i:])
            if match:
                delimiter = match.group(0)
                end = sql.find(delimiter, i + len(delimiter))
                i = len(sql) if end < 0 else end + len(delimiter)
                tokens.append(("expr", start, i, sql[start:i]))
                continue

        if char == "\\" and i + 1 < len(sql) and sql[i + 1] == "?":
            i += 2
            tokens.append(("other", start, i, sql[start:i]))
            continue

        if char == "?":
            kind = "operator" if sql[i : i + 2] in {"?|", "?&"} else "question"
            i += 2 if kind == "operator" else 1
            tokens.append((kind, start, i, sql[start:i]))
            continue

        if char in ")]}" or char.isalnum() or char in "_$.":
            end = i + 1
            while end < len(sql) and (sql[end].isalnum() or sql[end] in "_$."):
                end += 1
            word = sql[i:end].upper()
            kind = "operator" if word in _SQL_OPERATOR_WORDS else "expr"
            tokens.append((kind, start, end, sql[start:end]))
            i = end
            continue

        kind = "expr_start" if char in "([{" else "operator"
        i += 1
        tokens.append((kind, start, i, sql[start:i]))

    return tokens


def _legacy_boolean_ddl_replacements(
    sql: str, tokens: List[_SQLToken]
) -> List[Tuple[int, int, str]]:
    replacements: List[Tuple[int, int, str]] = []
    statement_start = 0
    statement_ranges: List[Tuple[int, int]] = []
    for index, token in enumerate(tokens):
        if token[3] == ";":
            statement_ranges.append((statement_start, index))
            statement_start = index + 1
    statement_ranges.append((statement_start, len(tokens)))

    for start, end in statement_ranges:
        statement_tokens = tokens[start:end]
        words = [token[3].upper() for token in statement_tokens]
        if len(words) < 2 or words[:2] not in (["ALTER", "TABLE"], ["CREATE", "TABLE"]):
            continue
        is_alter = words[:2] == ["ALTER", "TABLE"]

        for index in range(len(statement_tokens)):
            column = words[index]
            if column in _LEGACY_BOOLEAN_COLUMNS:
                prefix = [
                    column,
                    "INTEGER",
                    "CHECK",
                    "(",
                    column,
                    "IN",
                    "(",
                    "0",
                    ",",
                    "1",
                    ")",
                    ")",
                    "NOT",
                    "NULL",
                    "DEFAULT",
                ]
                prefix_end = index + len(prefix)
                if (
                    prefix_end < len(words)
                    and words[index:prefix_end] == prefix
                    and words[prefix_end] in {"0", "1"}
                ):
                    first = statement_tokens[index]
                    last = statement_tokens[prefix_end]
                    if (
                        "--" not in sql[first[1] : last[2]]
                        and "/*" not in sql[first[1] : last[2]]
                    ):
                        default = "TRUE" if words[prefix_end] == "1" else "FALSE"
                        replacements.append(
                            (
                                first[1],
                                last[2],
                                f"{first[3]} BOOLEAN NOT NULL DEFAULT {default}",
                            )
                        )

            if is_alter and words[index : index + 4] == [
                "ADD",
                "COLUMN",
                "IS_CONSEQUENTIAL",
                "INTEGER",
            ]:
                integer_token = statement_tokens[index + 3]
                replacements.append((integer_token[1], integer_token[2], "BOOLEAN"))

            external_prefix = [
                "EXTERNAL",
                "INTEGER",
                "CHECK",
                "(",
                "EXTERNAL",
                "IN",
                "(",
                "0",
                ",",
                "1",
                ")",
                ")",
                "NOT",
                "NULL",
            ]
            external_end = index + len(external_prefix)
            if words[index:external_end] == external_prefix:
                first = statement_tokens[index]
                last = statement_tokens[external_end - 1]
                if (
                    "--" not in sql[first[1] : last[2]]
                    and "/*" not in sql[first[1] : last[2]]
                ):
                    replacements.append(
                        (
                            first[1],
                            last[2],
                            f"{first[3]} BOOLEAN NOT NULL",
                        )
                    )

    return sorted(replacements)


def _make_table_name(cls: type):
    cls_name = cls.__name__
    s1 = _RE_FIRST_CAP.sub(r"\1_\2", cls_name)
    ret = _RE_ALL_CAP.sub(r"\1_\2", s1).lower()

    # At this point something as OAuth2UserData is `o_auth2_user_data`
    return ret


# Helper functions since we must store the datetime as str.
# (no need to autoconvert all the time).


def datetime_to_str(val: datetime.datetime) -> str:
    return val.isoformat()


def str_to_datetime(val: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(val)


class DBError(Exception):
    pass


class DBRules:
    def __init__(self) -> None:
        # Fields which should have unique indexes in the format:
        # "Class.field_name"
        self.unique_indexes: Set[str] = set()

        # Fields which should have indexes in the format:
        # "Class.field_name"
        self.indexes: Set[str] = set()

        # Fields which are foreign keys in the format:
        # "Class.field_name"
        self.foreign_keys: Set[str] = set()


def redact_database_url(value: Union[Path, str]) -> Union[Path, str]:
    if not isinstance(value, str):
        return value

    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"postgresql", "postgres"}:
            return value
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return "<redacted PostgreSQL database URL>"

    if not hostname:
        return "<redacted PostgreSQL database URL>"

    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname if port is None else f"{hostname}:{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))


def normalize_database_url(value: Union[Path, str]) -> Union[Path, str]:
    if not isinstance(value, str):
        return value

    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        if value.lower().startswith(("postgresql:", "postgres:")):
            raise ValueError("Invalid PostgreSQL database URL") from exc
        raise ValueError("Invalid database URL") from exc
    scheme = parsed.scheme.lower()
    if scheme in {"postgresql", "postgres"}:
        try:
            hostname = parsed.hostname
            port = parsed.port
        except ValueError as exc:
            raise ValueError("Invalid PostgreSQL database URL") from exc

        authority = parsed.netloc.rsplit("@", 1)[-1]
        if (
            not parsed.netloc
            or not hostname
            or authority.endswith(":")
            or (port is not None and not 1 <= port <= 65535)
        ):
            raise ValueError("Invalid PostgreSQL database URL")
        if scheme == "postgres":
            return "postgresql://" + value.split("://", 1)[1]
        return value
    if parsed.scheme:
        raise ValueError("Unsupported database URL; only PostgreSQL URLs are supported")
    return value


class Database:
    """
    Some notes:

        Connections must be per-thread.

        No 2 connections should be writing at the same time (ideally, use a
        single thread for writing).

        This class makes it so that there's only one connection per thread.
    """

    verbose = 0

    def __init__(self, db_path: Optional[Union[Path, str]] = None):
        self._cls_to_type_hint: Dict[type, dict] = {}
        self._db_path: Union[Path, str]
        if not db_path:
            from ._settings import get_settings

            self._db_path = get_settings().datadir / "server.db"
        else:
            normalized = normalize_database_url(db_path)
            self._db_path = (
                normalized if self._is_postgresql_url(normalized) else Path(normalized)
            )

        self._backend_name = (
            "postgresql" if isinstance(self._db_path, str) else "sqlite"
        )

        self._table_name_to_cls: Dict[str, type] = {}
        self._tlocal = threading.local()
        self._counter = itertools.count(0)
        self._write_lock = threading.RLock()
        self._classes: List[type] = []

    @staticmethod
    def _is_postgresql_url(value: Union[Path, str]) -> bool:
        return isinstance(value, str) and value.lower().startswith(
            ("postgresql://", "postgres://")
        )

    @property
    def backend_name(self) -> str:
        return self._backend_name

    @property
    def db_path(self) -> Union[Path, str]:
        return self._db_path

    def log_internal_info(self):
        if self.backend_name == "sqlite":
            log.debug("sqlite version: %s", sqlite3.sqlite_version)
        else:
            log.debug("database backend: postgresql")

    def _get_type_hints(self, cls) -> dict:
        try:
            return self._cls_to_type_hint[cls]
        except KeyError:
            from typing import get_type_hints

            ret = get_type_hints(cls)
            self._cls_to_type_hint[cls] = ret
            return ret

    def _iter_name_and_name_cls_fields(self, cls) -> Iterator[Tuple[str, type]]:
        yield from self._get_type_hints(cls).items()

    def _iter_name_fields(self, cls) -> Iterator[str]:
        yield from self._get_type_hints(cls).keys()

    @contextmanager
    def connect(self) -> Iterator[None]:
        try:
            conn = self._tlocal.conn
        except AttributeError:
            conn = None

        if conn is not None:
            yield
            return

        if self.backend_name == "postgresql":
            try:
                import psycopg
            except ImportError as e:
                raise RuntimeError(
                    "PostgreSQL support requires the actions-runtime PostgreSQL extra."
                ) from e
            conn = psycopg.connect(cast(str, self._db_path))
        else:
            conn = sqlite3.connect(self._db_path, isolation_level=None)
            conn.execute("PRAGMA foreign_keys = ON")
        with closing(conn):
            self._tlocal.conn = conn
            try:
                yield
            finally:
                self._tlocal.conn = None

    @contextmanager
    def try_claim_schedule(self, schedule_id: str) -> Iterator[bool]:
        """Hold a PostgreSQL session lock while a due schedule is processed.

        SQLite retains its existing process-local coordination. PostgreSQL uses
        a session-level advisory lock so commits made while the schedule runs do
        not release ownership, while closing the process connection releases it
        deterministically after normal completion or process failure.
        """
        if self.backend_name != "postgresql":
            yield True
            return

        import psycopg

        claim_connection = psycopg.connect(
            cast(str, self._db_path),
            autocommit=True,
        )
        lock_key = f"actions-runtime-schedule:{schedule_id}"
        acquired = False
        try:
            with claim_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_try_advisory_lock(hashtext(%s))",
                    (lock_key,),
                )
                result = cursor.fetchone()
                acquired = bool(result and result[0])

            yield acquired
        finally:
            if acquired:
                try:
                    with claim_connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT pg_advisory_unlock(hashtext(%s))",
                            (lock_key,),
                        )
                except Exception:
                    log.debug("Unable to release PostgreSQL schedule claim", exc_info=True)
            claim_connection.close()

    def _next_savepoint_name(self):
        return f"savepoint_{next(self._counter)}"

    @contextmanager
    def cursor(self) -> Iterator[Any]:
        """
        A cursor should be requested to do queries.
        """
        try:
            conn = self._tlocal.conn
        except AttributeError:
            conn = None
        if conn is None:
            raise RuntimeError(
                "Error. Cannot create a cursor without a connection in place."
            )

        with closing(conn.cursor()) as cur:
            yield cur

    def in_transaction(self) -> bool:
        """
        Returns:
            True if we're currently in a transaction and False otherwise.
        """
        try:
            in_transaction = self._tlocal.in_transaction
        except AttributeError:
            in_transaction = self._tlocal.in_transaction = 0

        return in_transaction > 0

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """
        A transaction should be created when contents are about to be written.

        SQLite can't deal with multiple writers, so, we use a lock in Python
        which will prevent other threads from writing at the same time.

        Important: as a lock is held in python, it's important to try to minimize
        the transaction size as much as possible as a transaction in one thread
        will prevent other threads from starting a transaction.
        """

        try:
            conn = self._tlocal.conn
        except AttributeError:
            conn = None
        if conn is None:
            raise DBError(
                "Unable to create a transaction because no connection is in place."
            )

        try:
            in_transaction = self._tlocal.in_transaction
        except AttributeError:
            in_transaction = self._tlocal.in_transaction = 0

        with self._write_lock:
            # Note: the write lock is now used whenever a transaction is asked for
            # -- this is done because although on some cases sqlite can handle
            # updates in parallel in non-related fields, it doesn't do a good
            # job and can be much slower...
            #
            # i.e.
            # action_server_tests.test_database.test_database_concurrency
            # runs much slower if this lock isn't in place.
            #
            # Also, this should prevent errors where the same place is updated
            # in different places (each with its own transaction) such as:
            #
            # https://github.com/robocorp/robocorp/issues/309
            # "sqlite3.OperationalError: database is locked"

            if in_transaction:
                # Nested transactions are not supported, so, don't start a new one
                # here, but we can still use savepoints.
                self._tlocal.in_transaction += 1
                savepoint_name = self._next_savepoint_name()
                self.execute(f"savepoint {savepoint_name};")
                try:
                    yield
                except BaseException:
                    self.execute(f"rollback to savepoint {savepoint_name};")
                    raise
                finally:
                    self._tlocal.in_transaction -= 1
                return

            assert (
                self._tlocal.in_transaction == 0
            ), "Error transaction nesting logic not correct!"

            self._tlocal.in_transaction += 1
            try:
                self.execute("BEGIN")
                yield
            except BaseException:
                log.exception("Error. Rolling back database")
                conn.rollback()
                raise
            else:
                conn.commit()
            finally:
                self._tlocal.in_transaction -= 1
                assert (
                    self._tlocal.in_transaction == 0
                ), "Error transaction nesting logic not correct!"

    def where(self, instance, keys: Sequence[str]) -> tuple[str, list[Any]]:
        """
        Makes an sql which can be used in a where clause.

        Example:
            Something as:

                sql,values = db.where(some_class, keys=['id', 'age'])

                Will have as result:

                'id=? AND age=?', [id_value, age_value])
        """
        sql = ""
        values = []
        for i, key in enumerate(keys):
            if i != 0:
                sql += " AND "
            sql += f"{key} = ?"
            values.append(getattr(instance, key))
        return (sql, values)

    def where_from_dict(self, dct: dict[str, Any]) -> tuple[str, list[Any]]:
        """
        Makes an sql which can be used in a where clause.

        Example:
            Something as:

                sql,values = db.where_from_dict(some_class, keys=['id', 'age'])

                Will have as result:

                'id=? AND age=?', [id_value, age_value])
        """
        sql = ""
        values = []
        for i, (key, value) in enumerate(dct.items()):
            if i != 0:
                sql += " AND "
            sql += f"{key} = ?"
            values.append(value)
        return (sql, values)

    def delete_where(self, cls: Type, where: str, values: list[Any]):
        table_name = _make_table_name(cls)
        self.execute(f"DELETE FROM {table_name} WHERE {where}", values)

    def delete(self, instance, keys: Sequence[str]):
        """
        Deletes the given instance from the db given the keys given.
        """
        table_name = _make_table_name(instance.__class__)
        sql, values = self.where(instance, keys)

        self.execute(f"DELETE FROM {table_name} WHERE {sql}", values)

    def insert_or_update(self, instance, keys: Sequence[str] = ("id",)):
        """
        Updates database values from some instance given its id.
        """
        table_name = _make_table_name(instance.__class__)

        where, values = self.where(instance, keys)
        sql = f"SELECT * FROM {table_name} WHERE {where}"

        try:
            self.first(instance.__class__, sql, values)
        except KeyError:
            self.insert(instance)
        else:
            # Ok, instance found, update it.
            self.update_by_fields(instance, keys)

    def update(self, instance, *fields: str):
        """
        Updates database values from some instance given its id.

        Args:
            fields: The name of the fields that should be updated
                    (only the selected fields will be updated).
        """
        fields_dict: dict[str, Any] = {}
        for field in fields:
            fields_dict[field] = getattr(instance, field)
        self.update_by_id(instance.__class__, instance.id, fields_dict)

    def update_by_id(self, cls: Type, id: Any, fields: dict[str, Any]):
        """
        Updates database values from some instance given its id.
        """
        table_name = _make_table_name(cls)
        set_fields = []
        values = []
        for name, value in fields.items():
            set_fields.append(f"{name}=?")
            values.append(value)

        values.append(id)
        sql = f"UPDATE {table_name} SET {', '.join(set_fields)} WHERE id=?"
        self.execute(sql, values)

    def update_by_fields(self, instance, keys: Sequence[str]):
        """
        Updates all the database values from some instance.

        Args:
            instance: The instance with the values to be update.
            keys: The keys for which the values should be updated.
        """

        set_placeholders: list[str] = []
        set_values = []

        where_placeholders: list[str] = []
        where_values = []

        for name, _field_cls in self._iter_name_and_name_cls_fields(instance.__class__):
            if name in keys:
                where_placeholders.append(f"{name}=?")
                where_values.append(getattr(instance, name))
            else:
                set_placeholders.append(f"{name}=?")
                set_values.append(getattr(instance, name))

        table_name = _make_table_name(instance.__class__)

        sql = f"UPDATE {table_name} SET {', '.join(set_placeholders)} WHERE {' AND '.join(where_placeholders)}"
        self.execute(sql, set_values + where_values)

    def insert(
        self,
        instance,
    ) -> None:
        table_name = _make_table_name(instance.__class__)

        field_names = []
        values = []
        placeholders = []
        for name in self._iter_name_fields(instance.__class__):
            field_names.append(name)
            values.append(getattr(instance, name))
            placeholders.append("?")

        fields_str = ", ".join(field_names)
        placeholders_str = ", ".join(placeholders)

        self.execute(
            f"""
INSERT INTO {table_name}
    ({fields_str})
VALUES
    ({placeholders_str})
""",
            values,
        )

    def all(
        self,
        cls: Type[T],
        *,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        order_by: Optional[str] = None,
        where: Optional[str] = None,
        values: Optional[list] = None,
    ) -> List[T]:
        table_name = _make_table_name(cls)
        if limit is not None:
            assert isinstance(limit, int)
        if offset is not None:
            assert isinstance(offset, int)

        sql = f"SELECT * FROM {table_name}"

        if order_by:
            # Careful: users cannot provide this as it's susceptible to
            # sql injection.
            sql += f" ORDER BY {order_by}"

        if limit:
            sql += f" LIMIT {limit}"

        if offset:
            sql += f" OFFSET {offset}"

        if where:
            sql += f" WHERE {where}"

        return self.select(cls, sql, values)

    def select(self, cls: Type[T], sql: str, values: Optional[list] = None):
        with self.cursor() as cursor:
            self.execute_query(cursor, sql, values)
            return [cls(*x) for x in cursor.fetchall()]

    def first(
        self,
        cls: Type[T],
        query: Optional[str] = None,
        values: Optional[List[Any]] = None,
    ) -> T:
        """
        Note: we want to use plain sql, not a bunch of ORM to query.

        Maybe we can use the same structure as:
        https://github.com/kruxia/sqly

        to build the SQL though (but right now the query is just
        the actual SQL with placeholders and the values should be
        passed separately).

        Example:

        db.first(
                ActionPackage,
                "SELECT * FROM action_package WHERE id = ?",
                [action.action_package_id],
            )

        Raises:
            KeyError if no entries were returned in the query.
        """
        if not query:
            table_name = _make_table_name(cls)
            query = f"SELECT * FROM {table_name}"

        with self.cursor() as cursor:
            self.execute_query(cursor, query, values=values)
            one = cursor.fetchone()
            if one is None:
                raise KeyError("Query returned no entries.")
            return cls(*one)

    def list_table_names(self) -> List[str]:
        with self.cursor() as cursor:
            sql = """
SELECT
    name
FROM
    sqlite_master
WHERE
    type ='table' AND
    name NOT LIKE 'sqlite_%';
"""
            if self.backend_name == "postgresql":
                sql = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = current_schema()
  AND table_type = 'BASE TABLE';
"""
            self.execute_query(cursor, sql)
            return [x[0] for x in cursor.fetchall()]

    def list_table_and_columns(self) -> Dict[str, List[str]]:
        with self.cursor() as cursor:
            sql = """
SELECT m.name as tableName, 
       p.name as columnName
FROM sqlite_master m
left outer join pragma_table_info((m.name)) p
     on m.name <> p.name
order by tableName, columnName;
"""
            if self.backend_name == "postgresql":
                sql = """
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema = current_schema()
ORDER BY table_name, ordinal_position;
"""
            self.execute_query(cursor, sql)
            found: Dict[str, List[str]] = {}
            for table_name, column_name in cursor.fetchall():
                columns = found.get(table_name)
                if not columns:
                    columns = found[table_name] = []
                columns.append(column_name)
            return found

    def list_indexes(self) -> List[List[str]]:
        with self.cursor() as cursor:
            sql = """
SELECT 
    m.tbl_name as table_name,
    il.name as index_name,
    ii.name as column_name,
    CASE il.origin when 'pk' then 1 else 0 END as is_primary_key,
    CASE il.[unique] when 1 then 0 else 1 END as non_unique,
    il.[unique] as is_unique,
    il.partial,
    il.seq as sequence_in_index,
    ii.seqno as sequence_in_column
FROM sqlite_master AS m,
    pragma_index_list(m.name) AS il,
    pragma_index_info(il.name) AS ii
WHERE 
    m.type = 'table'
    and m.tbl_name = 'YOUR TABLENAME HERE'
GROUP BY
    m.tbl_name,
    il.name,
    ii.name,
    il.origin,
    il.partial,
    il.seq
ORDER BY index_name,il.seq,ii.seqno"""
            if self.backend_name == "postgresql":
                sql = """
SELECT tbl.relname AS table_name,
       idx.relname AS index_name,
       att.attname AS column_name,
       CASE WHEN ind.indisprimary THEN 1 ELSE 0 END AS is_primary_key,
       CASE WHEN ind.indisunique THEN 0 ELSE 1 END AS non_unique,
       CASE WHEN ind.indisunique THEN 1 ELSE 0 END AS is_unique,
       ind.indpred IS NOT NULL AS partial,
       keys.ordinality AS sequence_in_index,
       keys.ordinality AS sequence_in_column
FROM pg_index ind
JOIN pg_class tbl ON tbl.oid = ind.indrelid
JOIN pg_namespace ns ON ns.oid = tbl.relnamespace
JOIN pg_class idx ON idx.oid = ind.indexrelid
CROSS JOIN LATERAL unnest(ind.indkey) WITH ORDINALITY AS keys(attnum, ordinality)
JOIN pg_attribute att ON att.attrelid = tbl.oid AND att.attnum = keys.attnum
WHERE ns.nspname = current_schema()
ORDER BY table_name, index_name, sequence_in_index;
"""
            self.execute_query(cursor, sql)
            return [x for x in cursor.fetchall()]

    def list_whole_db(self) -> Dict[str, List[Dict[str, Any]]]:
        table_to_contents: Dict[str, List[Dict[str, Any]]] = {}
        for table, cls in self._table_name_to_cls.items():
            with self.cursor() as cursor:
                self.execute_query(cursor, f"SELECT * FROM {table}")

                cls = self._table_name_to_cls[table]
                field_names = list(self._iter_name_fields(cls))
                rows = []
                for row in cursor.fetchall():
                    rows.append(dict(itertools.zip_longest(field_names, row)))

                table_to_contents[table] = rows
        return table_to_contents

    def load_whole_db(self, contents: Dict[str, List[Dict[str, Any]]]) -> None:
        with self.transaction():
            for table, table_rows in contents.items():
                cls = self._table_name_to_cls[table]
                for row in table_rows:
                    instance = cls(**row)
                    self.insert(instance)

    def _print_sql(self, sql: str, values: Optional[list] = None):
        func_name = sys._getframe(1).f_code.co_name
        print(f"db.{func_name}('''\n{sql.strip()}\n''', {values!r})\n")

    def _raise_execute_error(self, msg):
        if self.verbose:
            print(msg, file=sys.stderr)
        raise DBError(msg)

    def _adapt_sql(self, sql: str, values: Optional[Sequence[Any]] = None) -> str:
        if self.backend_name != "postgresql":
            return sql

        tokens = _tokenize_sql(sql)

        expression_end = {"expr", "question"}
        expression_start = {"expr", "expr_start"}
        markers: set[int] = set()
        for index, (kind, position, _end, _value) in enumerate(tokens):
            if kind != "question":
                continue
            previous = tokens[index - 1][0] if index else None
            following = tokens[index + 1][0] if index + 1 < len(tokens) else None
            if previous not in expression_end or (
                following not in expression_start and following != "question"
            ):
                markers.add(position)

        changes = _legacy_boolean_ddl_replacements(sql, tokens)
        changes.extend((position, position + 1, "%s") for position in markers)
        changes.sort()

        adapted: List[str] = []
        cursor = 0
        for start, end, replacement in changes:
            if start < cursor:
                continue
            adapted.append(sql[cursor:start])
            adapted.append(replacement)
            cursor = end
        adapted.append(sql[cursor:])

        if values is not None and len(markers) != len(values):
            raise DBError(
                f"PostgreSQL query has {len(markers)} parameter placeholders; "
                f"expected {len(markers)} parameters, got {len(values)}"
            )
        return "".join(adapted)

    def execute_query(
        self, cursor: Any, sql: str, values: Optional[list] = None
    ):
        """
        Executes a query which will NOT change the database (and should return values).

        No write-lock needed.
        """
        if self.verbose:
            self._print_sql(sql, values)

        try:
            sql = self._adapt_sql(sql, values)
            if values:
                cursor.execute(sql, values)
            else:
                cursor.execute(sql)
        except DBError:
            raise
        except Exception:
            self._raise_execute_error(
                f"Error running sql query: {sql!r} with values: {values!r}"
            )

    def execute_update_returning(
        self, cursor: Any, sql: str, values: Optional[list] = None
    ):
        """
        Executes a query which will NOT change the database (and should return values).

        No write-lock needed.
        """
        if self.verbose:
            self._print_sql(sql, values)
        try:
            if not self.in_transaction():
                raise DBError(
                    "When running an sql that changes the DB, it's expected that "
                    "a transaction is in place."
                )
            with self._write_lock:
                sql = self._adapt_sql(sql, values)
                if values:
                    cursor.execute(sql, values)
                else:
                    cursor.execute(sql)
        except DBError:
            raise
        except Exception:
            self._raise_execute_error(
                f"Error running sql: {sql!r} with values: {values!r}"
            )

    def execute(self, sql: str, values: Optional[list] = None) -> None:
        """
        Executes a query which will change the database.

        Requires the write-lock to be acquired since SQLite can't deal with
        writes in multiple threads concurrently.
        """

        if self.verbose:
            self._print_sql(sql, values)
        try:
            if not self.in_transaction():
                raise DBError(
                    "When running an sql that changes the DB, it's expected that "
                    "a transaction is in place."
                )
            conn = self._tlocal.conn
            assert conn is not None
            with self._write_lock:
                sql = self._adapt_sql(sql, values)
                if values:
                    conn.execute(sql, values)
                else:
                    conn.execute(sql)
        except DBError:
            raise
        except Exception:
            self._raise_execute_error(
                f"Error running sql: {sql!r} with values: {values!r}"
            )

    def register_classes(self, classes: List[Type]) -> None:
        if self._table_name_to_cls:
            values = set(self._table_name_to_cls.values())
            if values != set(classes):
                raise RuntimeError(
                    "The classes were already registered "
                    "(and do not match the new values)."
                )
            # i.e.: they were already registered.
            return

        self._classes = classes
        for cls in classes:
            self._table_name_to_cls[_make_table_name(cls)] = cls

    def initialize(self, classes: List[Type]) -> None:
        """
        Initializes the internal structure of the tables as needed
        (but doesn't really create the db -- use 'create_tables'
        if needed).
        """
        self.register_classes(classes)

    def create_tables(self, db_rules: Optional[DBRules] = None):
        if db_rules is None:
            db_rules = DBRules()

        sqls = []
        for cls in self._classes:
            sql = self.create_table_sql(cls, db_rules)
            sqls.append(sql)

            sqls.extend(self.create_unique_indexes_sql(cls, db_rules))
            sqls.extend(self.create_non_unique_indexes_sql(cls, db_rules))

        with self.connect():
            with self.transaction():
                for sql in sqls:
                    self.execute(sql)

    def create_unique_indexes_sql(self, cls: Type, db_rules: DBRules) -> List[str]:
        table_name = _make_table_name(cls)

        columns: List[str] = []
        for name in self._iter_name_fields(cls):
            field_full_name = f"{cls.__name__}.{name}"
            if field_full_name in db_rules.unique_indexes:
                columns.append(name)

        ret: List[str] = []
        for column in columns:
            sql = f"""
CREATE UNIQUE INDEX {table_name}_{column}_index ON {table_name}({column});
"""
            ret.append(sql)
        return ret

    def create_non_unique_indexes_sql(self, cls: Type, db_rules: DBRules) -> List[str]:
        table_name = _make_table_name(cls)

        columns: List[str] = []
        for name in self._iter_name_fields(cls):
            field_full_name = f"{cls.__name__}.{name}"
            if field_full_name in db_rules.indexes:
                columns.append(name)

        ret: List[str] = []
        for column in columns:
            sql = f"""
CREATE INDEX {table_name}_{column}_non_unique_index ON {table_name}({column});
"""
            ret.append(sql)
        return ret

    def create_table_sql(self, cls: Type, db_rules: DBRules) -> str:
        table_name = _make_table_name(cls)

        fields = []
        foreign_keys = []
        for name, field_cls in self._iter_name_and_name_cls_fields(cls):
            field_full_name = f"{cls.__name__}.{name}"
            fields.append(
                self._get_field_create_sql(
                    cls, field_full_name, name, field_cls, db_rules
                )
            )

            if field_full_name in db_rules.foreign_keys:
                assert name.endswith("_id")

                foreign_table = name[:-3]
                if foreign_table not in self._table_name_to_cls:
                    raise RuntimeError(
                        f"Error: unexpected foreign reference: {foreign_table} "
                        f"(for field: {name})"
                    )
                foreign_keys.append(
                    f"FOREIGN KEY ({name}) " f"REFERENCES {foreign_table}(id)"
                )

        fields.extend(foreign_keys)
        fields_str = ",\n    ".join(fields)
        sql = f"""
CREATE TABLE IF NOT EXISTS {table_name}(
    {fields_str}
)
        """
        return sql

    def _get_field_create_sql(
        self,
        cls,
        field_full_name: str,
        name: str,
        field_cls: Type,
        db_rules: DBRules,
    ) -> str:
        primary_key = name == "id"

        if field_cls.__name__ == "Optional":
            not_none = [x for x in field_cls.__args__ if x != NoneType]
            assert len(not_none) == 1, f"Expected one not none in: {field_cls.__args__}"
            field_cls = not_none[0]
            not_null = False
        else:
            not_null = True

        if field_cls == int:
            use = "INTEGER"

        elif field_cls == str:
            use = "TEXT"

        elif field_cls == bool and not not_null:
            use = "BOOLEAN" if self.backend_name == "postgresql" else "INTEGER"

        elif field_cls == bool and not_null:
            try:
                default_value = getattr(cls, name)
                if default_value:
                    use = (
                        "BOOLEAN NOT NULL DEFAULT TRUE"
                        if self.backend_name == "postgresql"
                        else f"INTEGER CHECK({name} IN (0, 1)) NOT NULL DEFAULT 1"
                    )
                else:
                    use = (
                        "BOOLEAN NOT NULL DEFAULT FALSE"
                        if self.backend_name == "postgresql"
                        else f"INTEGER CHECK({name} IN (0, 1)) NOT NULL DEFAULT 0"
                    )
            except AttributeError:
                # No default
                use = (
                    "BOOLEAN NOT NULL"
                    if self.backend_name == "postgresql"
                    else f"INTEGER CHECK({name} IN (0, 1)) NOT NULL"
                )

        elif field_cls == datetime.datetime:
            raise RuntimeError(
                f"Datetime not supported (field: {name}). Please "
                "use str and use utility functions to convert back and forth."
            )

        elif field_cls == float:
            use = "REAL"

        else:
            raise RuntimeError(f"Unsupported type: {field_cls}")

        use = f"{name} {use}"

        if not_null and field_cls != bool:
            use = f"{use} NOT NULL"

        try:
            default_value = getattr(cls, name)
        except AttributeError:
            pass
        else:
            if field_cls == str:
                if default_value is None:
                    use = f"{use} DEFAULT NULL"
                else:
                    use = f"{use} DEFAULT {default_value!r}"

        if primary_key:
            use = f"{use} PRIMARY KEY"

        return f"{use}"
