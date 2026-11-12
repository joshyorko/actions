"""Real local DuckDB scans; no installed/worker/PG execution claim."""
import json
import threading
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_generic_work_item_execution import grant

from actions.server.data_queries.sealed_duckdb import DuckDBSealedScan, _connect
from actions.server.data_queries.sealed_sources import ReadBudget, SealedReadRejected
from actions.server.deployments.logical_bindings import BindingField, BindingOperation
from actions.server.deployments.provider_registry import (
    CsvSourceCodec,
    DecodedSourceObject,
    ParquetSourceCodec,
    ProviderDescriptor,
    SourceColumn,
    SourceManifest,
)
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.foundry.provider_catalog import CatalogSeal, SourceSealRecord
from actions.server.foundry.provider_config import DuckDBHost, ProviderHostConfig
from actions.server.foundry.provider_registry import (
    RetainedSourceEvidence,
    SqlProviderRegistry,
)
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def columns():
    return (
        SourceColumn(name="record_id", kind="string"),
        SourceColumn(name="count", kind="integer"),
        SourceColumn(name="amount", kind="number"),
        SourceColumn(name="active", kind="boolean"),
        SourceColumn(name="note", kind="string", nullable=True),
    )


def codec(parquet=False, **kwargs):
    values = dict(
        columns=columns(), max_rows=100, max_decoded_bytes=65536, max_field_bytes=1024
    )
    values.update(kwargs)
    return (
        ParquetSourceCodec(**values, max_row_groups=10)
        if parquet
        else CsvSourceCodec(**values)
    )


CSV = b'record_id,count,amount,active,note\nz,2,1.5,true,\\N\na,-1,-0.0,false,"quoted, value"\n'


def parquet_bytes(tmp_path, *, compression="uncompressed", sql=None, group_size=None):
    import duckdb

    path = tmp_path / (str(uuid4()) + ".parquet")
    con = duckdb.connect(":memory:")
    try:
        if sql:
            con.execute(sql)
        else:
            con.execute(
                "create table fixture(record_id varchar,count bigint,amount double,active boolean,note varchar)"
            )
            con.execute(
                "insert into fixture values ('z',2,1.5,true,NULL),('a',-1,-0.0,false,'quoted, value')"
            )
        con.execute(
            "COPY fixture TO ? (FORMAT PARQUET, COMPRESSION "
            + compression
            + (", ROW_GROUP_SIZE " + str(group_size) if group_size else "")
            + ")",
            [str(path)],
        )
    finally:
        con.close()
    return path.read_bytes()


@pytest.fixture
def setup(tmp_path, foundry_package_store):
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    with _runtime_database(tmp_path / "runtime.db", refs.workspace, ()) as db:
        auth = SqlFoundryAuthorization(db)
        grant(
            db,
            actor,
            refs.workspace,
            "workspace",
            str(refs.workspace.root),
            ["provider.register"],
        )

        def create(
            raw=CSV,
            source_codec=None,
            *,
            max_rows=100,
            max_bytes=65536,
            timeout_ms=30000,
            name="records.scan/v1",
            effect="read",
            parameters=(),
            result=None,
        ):
            current = source_codec or codec()
            seal = foundry_package_store.stage(
                raw[i : i + 65536] for i in range(0, len(raw), 65536)
            ).receipt
            source = SourceManifest(
                schema_version="actions.logical-source/v2",
                kind="data",
                objects=(
                    DecodedSourceObject(
                        name="records",
                        digest=seal.digest,
                        size=seal.size,
                        codec=current,
                    ),
                ),
            )
            op = BindingOperation(
                name=name,
                effect=effect,
                parameters=parameters,
                result=result
                or tuple(
                    BindingField(name=c.name, kind=c.kind, required=not c.nullable)
                    for c in current.columns
                ),
                max_rows=max_rows,
                max_bytes=max_bytes,
                timeout_ms=timeout_ms,
            )
            desc = ProviderDescriptor(
                workspace_id=refs.workspace,
                provider_profile_id=_refs().provider.provider_profile_id,
                source_revision=source.revision_id,
                kind="data",
                operations=(op,),
            )
            evidence = RetainedSourceEvidence(
                foundry_package_store, {(str(refs.workspace.root), seal.digest): seal}
            )
            registry = SqlProviderRegistry(db, auth, evidence)
            ref = registry.register(actor, desc, source, idempotency_key=str(uuid4()))
            row = grant(
                db,
                actor,
                refs.workspace,
                "reference",
                reference_grant_subject(ref),
                ["provider.inspect", "data.read"],
            )
            record = SourceSealRecord(
                owner=actor,
                workspace=refs.workspace,
                source=source,
                seals=(CatalogSeal(name="records", seal=seal),),
            )
            config = ProviderHostConfig(
                provider=ref, source_revision=source.revision_id, host=DuckDBHost()
            )
            adapter = DuckDBSealedScan(
                registry, auth, foundry_package_store, config, record
            )
            return SimpleNamespace(
                adapter=adapter,
                actor=actor,
                db=db,
                grant=row,
                source=source,
                obj=source.objects[0],
                seal=seal,
                blobs=foundry_package_store,
                operation=op,
                registry=registry,
                ref=ref,
            )

        yield create


def run(g):
    return g.adapter.execute(g.actor, g.operation.name, {}, threading.Event())


def test_actual_csv_scan_order_types_and_null_omission(setup):
    g = setup()
    first, second = run(g), run(g)
    assert first == second
    assert json.loads(first.payload) == [
        {"record_id": "z", "count": 2, "amount": 1.5, "active": True},
        {
            "record_id": "a",
            "count": -1,
            "amount": -0.0,
            "active": False,
            "note": "quoted, value",
        },
    ]
    assert first.source_revision == g.source.revision_id


def test_actual_parquet_scan_matches_csv(setup, tmp_path):
    csv = run(setup())
    parquet = run(setup(parquet_bytes(tmp_path), codec(True)))
    assert parquet.payload == csv.payload


@pytest.mark.parametrize(
    "raw",
    [
        CSV.replace(b"record_id", b"RECORD_ID", 1),
        CSV.replace(b"count,amount", b"count,count", 1),
        CSV.replace(b"true", b"True"),
        CSV.replace(b",2,", b",02,"),
        CSV.replace(b"1.5", b"NaN"),
        CSV.replace(b"1.5", b"1e-999"),
        CSV.replace(b",2,", b",9007199254740992,"),
        CSV.replace(b"z,2", b"\\N,2"),
        CSV + b'"unfinished',
        b"\xff" + CSV,
        CSV.replace(b'"quoted, value"', b'"quoted"garbage'),
        CSV.replace(b"z,2", b"z,2,extra"),
    ],
)
def test_invalid_csv_is_rejected_before_materialization(setup, monkeypatch, raw):
    from actions.server.data_queries import sealed_duckdb

    g = setup(raw)
    monkeypatch.setattr(
        sealed_duckdb,
        "_connect",
        lambda **_: pytest.fail("engine materialized invalid CSV"),
    )
    with pytest.raises(SealedReadRejected):
        run(g)


@pytest.mark.parametrize("limits", [{"max_rows": 1}, {"max_bytes": 2}])
def test_output_overflow_rejects_whole_result_before_materialization(
    setup, monkeypatch, limits
):
    from actions.server.data_queries import sealed_duckdb

    g = setup(**limits)
    monkeypatch.setattr(
        sealed_duckdb,
        "_connect",
        lambda **_: pytest.fail("engine materialized overflow"),
    )
    with pytest.raises(SealedReadRejected):
        run(g)


@pytest.mark.parametrize(
    "source_codec",
    [codec(max_rows=1), codec(max_decoded_bytes=10), codec(max_field_bytes=4)],
)
def test_source_limits_before_materialization(setup, monkeypatch, source_codec):
    from actions.server.data_queries import sealed_duckdb

    g = setup(source_codec=source_codec)
    monkeypatch.setattr(
        sealed_duckdb,
        "_connect",
        lambda **_: pytest.fail("engine materialized overflow"),
    )
    with pytest.raises(SealedReadRejected):
        run(g)


@pytest.mark.parametrize(
    "change",
    [
        {"name": "records.select/v1"},
        {"name": "Records.scan/v1"},
        {"effect": "write"},
        {"parameters": (BindingField(name="minimum", kind="integer"),)},
        {"result": (BindingField(name="note", kind="string", required=True),)},
        {"result": (BindingField(name="missing", kind="string"),)},
    ],
)
def test_unsupported_or_incompatible_operation_refused(setup, change):
    if change.get("name") == "Records.scan/v1":
        with pytest.raises(ValueError):
            setup(**change)
    else:
        with pytest.raises(SealedReadRejected):
            run(setup(**change))


def test_authority_rechecked_no_implicit_read_grant(setup):
    g = setup()
    with g.db.transaction():
        g.db.update_by_id(
            FoundryAccessGrant, g.grant.id, {"operations_json": '["provider.inspect"]'}
        )
    with pytest.raises(Exception, match="authorized"):
        run(g)


def test_cancel_and_deadline_fail_closed(setup):
    g = setup()
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(SealedReadRejected, match="cancelled"):
        g.adapter.execute(g.actor, g.operation.name, {}, cancel)
    g = setup(timeout_ms=1)
    with pytest.raises(SealedReadRejected):
        run(g)


def test_connection_restrictions_are_real(tmp_path):
    conn = _connect()
    try:
        settings = dict(
            conn.execute(
                "select name,value from duckdb_settings() where name in ('enable_external_access','autoload_known_extensions','autoinstall_known_extensions','threads','temp_directory','lock_configuration')"
            ).fetchall()
        )
        assert settings == {
            "enable_external_access": "false",
            "autoload_known_extensions": "false",
            "autoinstall_known_extensions": "false",
            "threads": "1",
            "temp_directory": "",
            "lock_configuration": "true",
        }
        with pytest.raises(Exception):
            conn.execute("SET enable_external_access=true")
        target = tmp_path / "forbidden.csv"
        with pytest.raises(Exception):
            conn.execute("COPY (SELECT 1) TO ?", [str(target)])
        assert not target.exists()
        with pytest.raises(Exception):
            conn.execute("INSTALL httpfs")
        with pytest.raises(Exception):
            conn.execute("SELECT * FROM read_csv(?)", ["https://127.0.0.1:9/forbidden"])
    finally:
        conn.close()


def test_real_engine_interrupt_and_memory_limit():
    conn = _connect()
    try:
        budget = ReadBudget(20, threading.Event())
        started = time.monotonic()
        with pytest.raises(Exception):
            with budget.interruptible(conn.interrupt):
                conn.execute(
                    "SELECT sum(a.i*b.i) FROM range(1000000) a(i),range(1000000) b(i)"
                )
        assert time.monotonic() - started < 3
        with pytest.raises(Exception):
            conn.execute("SELECT list(repeat('x',1024)) FROM range(1000000)").fetchone()
    finally:
        conn.close()


def external_chunk_footer(raw):
    from actions.server.data_queries.parquet_gate import _Compact

    size = int.from_bytes(raw[-8:-4], "little")
    start = len(raw) - 8 - size
    footer = raw[start:-8]
    found = []

    class Trace(_Compact):
        def value(self, kind, depth, *, field=False):
            offset = self.offset
            result = super().value(kind, depth, field=field)
            if (
                kind == 12
                and isinstance(result, dict)
                and 2 in result
                and isinstance(result.get(3), dict)
                and result[3].get(3) == [b"record_id"]
            ):
                found.append(offset)
            return result

    Trace(footer, ReadBudget(30000, threading.Event())).value(12, 0)
    assert len(found) == 1
    offset = found[0]
    # Insert optional ColumnChunk.file_path(field1/BINARY), preserving subsequent
    # wire types and adjusting only first field2's compact delta from2 to1.
    assert footer[offset] >> 4 == 2
    path = b"../../forbidden.parquet"
    changed = (
        footer[:offset]
        + b"\x18"
        + bytes([len(path)])
        + path
        + bytes([footer[offset] - 16])
        + footer[offset + 1 :]
    )
    return raw[:start] + changed + len(changed).to_bytes(4, "little") + b"PAR1"


@pytest.mark.parametrize(
    "variant",
    [
        "external",
        "compressed",
        "nested",
        "wrong_type",
        "footer_size",
        "truncated",
        "row_limit",
        "byte_limit",
    ],
)
def test_parquet_rejects_before_any_native_read(setup, tmp_path, monkeypatch, variant):
    from actions.server.data_queries import sealed_duckdb

    raw = parquet_bytes(tmp_path)
    source_codec = codec(True)
    if variant == "external":
        raw = external_chunk_footer(raw)
    elif variant == "compressed":
        raw = parquet_bytes(tmp_path, compression="zstd")
    elif variant == "nested":
        raw = parquet_bytes(
            tmp_path, sql="create table fixture as select [1,2] as nested"
        )
    elif variant == "wrong_type":
        raw = parquet_bytes(
            tmp_path,
            sql="create table fixture as select 1::integer as record_id,2::bigint as count,1.0::double as amount,true as active,NULL::varchar as note",
        )
    elif variant == "footer_size":
        raw = raw[:-8] + (2**32 - 1).to_bytes(4, "little") + b"PAR1"
    elif variant == "truncated":
        raw = raw[:-8] + b"\xff"
    elif variant == "row_limit":
        source_codec = codec(True, max_rows=1)
    elif variant == "byte_limit":
        source_codec = codec(True, max_decoded_bytes=1)
    g = setup(raw, source_codec)
    monkeypatch.setattr(
        sealed_duckdb,
        "_connect",
        lambda **_: pytest.fail("native reader reached before gate"),
    )
    with pytest.raises(
        SealedReadRejected, match="external" if variant == "external" else None
    ):
        run(g)


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"\xff" * 100,
        b"\x1c" * 40 + b"\x00" * 40,
        b"\x19\xf5" + b"\xff" * 10,
        b"\x15\x02\x05\x02\x02\x00",
        b"\x1b\x01\x88\x00\x00\x00",
    ],
)
def test_malformed_compact_footer_is_bounded(raw):
    from actions.server.data_queries.parquet_gate import validate_footer

    with pytest.raises(SealedReadRejected):
        validate_footer(raw, 100, codec(True), ReadBudget(1000, threading.Event()))


def test_csv_quote_utf8_controls_and_parameter_injection(setup):
    raw = (
        'record_id,count,amount,active,note\r\n"é\nquoted",1,1,true,"a""b"\r\n'.encode()
    )
    value = json.loads(run(setup(raw)).payload)
    assert value[0]["record_id"] == "é\nquoted"
    assert value[0]["note"] == 'a"b'
    g = setup()
    with pytest.raises(SealedReadRejected):
        g.adapter.execute(
            g.actor, g.operation.name, {"sql": "drop table x"}, threading.Event()
        )
    with pytest.raises(SealedReadRejected):
        g.adapter.execute(g.actor, "../records.scan/v1", {}, threading.Event())


def test_output_projection_and_actual_null_failure(setup):
    op = (BindingField(name="record_id", kind="string"),)
    result = run(setup(result=op))
    assert json.loads(result.payload) == [{"record_id": "z"}, {"record_id": "a"}]
    with pytest.raises(SealedReadRejected, match="required"):
        run(setup(CSV.replace(b"z,2", b"\\N,2")))


def test_revocation_during_scan_releases_no_result(setup, monkeypatch):
    from actions.server.data_queries import sealed_duckdb

    g = setup()
    original = sealed_duckdb._connect

    def revoke(**kwargs):
        with g.db.transaction():
            g.db.update_by_id(FoundryAccessGrant, g.grant.id, {"operations_json": "[]"})
        return original(**kwargs)

    monkeypatch.setattr(sealed_duckdb, "_connect", revoke)
    with pytest.raises(SealedReadRejected):
        run(g)


def test_real_parquet_multiple_row_groups_and_source_order(
    setup, tmp_path, monkeypatch
):
    from actions.server.data_queries import sealed_duckdb

    raw = parquet_bytes(
        tmp_path,
        sql="create table fixture as select 'r'||i as record_id,i::bigint as count,i::double as amount,true as active,NULL::varchar as note from range(5000) t(i)",
        group_size=2048,
    )
    current = ParquetSourceCodec(
        columns=columns(),
        max_rows=6000,
        max_decoded_bytes=2 * 1024 * 1024,
        max_field_bytes=1024,
        max_row_groups=10,
    )
    actual = json.loads(
        run(setup(raw, current, max_rows=6000, max_bytes=1024 * 1024)).payload
    )
    assert len(actual) == 5000
    assert actual[2048]["record_id"] == "r2048"
    assert actual[-1]["record_id"] == "r4999"
    limited = current.model_copy(update={"max_row_groups": 1})
    g = setup(raw, limited, max_rows=6000, max_bytes=1024 * 1024)
    monkeypatch.setattr(
        sealed_duckdb,
        "_connect",
        lambda **_: pytest.fail("native call before group limit"),
    )
    with pytest.raises(SealedReadRejected, match="row group bound"):
        run(g)


def test_real_engine_event_cancellation():
    conn = _connect()
    cancelled = threading.Event()
    timer = threading.Timer(0.02, cancelled.set)
    try:
        timer.start()
        budget = ReadBudget(30000, cancelled)
        started = time.monotonic()
        with pytest.raises(Exception):
            with budget.interruptible(conn.interrupt):
                conn.execute(
                    "SELECT sum(a.i*b.i) FROM range(1000000) a(i),range(1000000) b(i)"
                )
        assert cancelled.is_set()
        assert time.monotonic() - started < 3
    finally:
        timer.cancel()
        timer.join()
        conn.close()


def test_parquet_field_bound_before_table_materialization(setup, tmp_path, monkeypatch):
    from actions.server.data_queries import sealed_duckdb

    g = setup(parquet_bytes(tmp_path), codec(True, max_field_bytes=4))
    original = sealed_duckdb._connect

    def parser_only(**kwargs):
        if kwargs.get("parquet") is None:
            pytest.fail("oversized field materialized")
        return original(**kwargs)

    monkeypatch.setattr(sealed_duckdb, "_connect", parser_only)
    with pytest.raises(SealedReadRejected, match="string type or bound"):
        run(g)


def test_source_seal_tamper_releases_no_private_locator(setup, tmp_path):
    g = setup()
    path = tmp_path / "package-objects" / g.seal.object_ref
    path.unlink()
    with pytest.raises(ValueError) as error:
        run(g)
    assert g.seal.object_ref not in str(error.value)


def test_empty_footer_list_with_unknown_element_type_rejected():
    from actions.server.data_queries.parquet_gate import _Compact

    with pytest.raises(SealedReadRejected, match="element encoding"):
        _Compact(b"\x0f", ReadBudget(1000, threading.Event())).value(9, 0)
