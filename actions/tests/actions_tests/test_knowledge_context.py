"""Prepared result selection only: no provider, file or network authority."""
import asyncio
import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from actions.data import scan
from actions.data._context import install_context


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode()


def parameters(**changes):
    return dict(
        ingestion_handle="art_" + "a" * 22,
        query="Synthetic",
        offset=0,
        limit=20,
        **changes,
    )


def context():
    return dict(
        version="actions.logical-context/v2",
        lookups=[
            dict(
                requirementId="data",
                operation="records.scan/v1",
                kind="data",
                parameters={},
                result=[{"value": 1}],
            ),
            dict(
                requirementId="write",
                operation="docs.ingest/v1",
                kind="knowledge",
                parameters={},
                result={"state": "staged", "revision": "synthetic"},
            ),
            dict(
                requirementId="read",
                operation="docs.search/v1",
                kind="knowledge",
                parameters=parameters(),
                result={
                    "hits": [
                        {"text": "Synthetic", "values": {"count": 1, "optional": None}}
                    ],
                    "total": 1,
                },
            ),
        ],
    )


def install(value):
    raw = canonical(value)
    return install_context(
        raw, expected_digest="sha256:" + hashlib.sha256(raw).hexdigest()
    )


def search(**kwargs):
    from actions.knowledge import search

    args = parameters()
    args.update(kwargs)
    return search("read", "docs.search/v1", **args)


def test_mixed_context_fresh_deep_copies_and_default_normalization():
    from actions.knowledge import ingest
    from actions.knowledge import search as lookup

    value = context()
    with install(value):
        assert scan("data", "records.scan/v1") == [{"value": 1}]
        prepared = ingest("write", "docs.ingest/v1")
        assert prepared == value["lookups"][1]["result"]
        prepared["state"] = "fabricated"
        result = lookup(
            "read",
            "docs.search/v1",
            ingestion_handle=parameters()["ingestion_handle"],
            query="Synthetic",
        )
        result["hits"][0]["values"]["count"] = 5
        assert search() == value["lookups"][2]["result"]
        assert ingest("write", "docs.ingest/v1")["state"] == "staged"
    with pytest.raises(ValueError):
        search()


@pytest.mark.parametrize(
    "change",
    [
        {"query": "other"},
        {"ingestion_handle": "other"},
        {"offset": 1},
        {"limit": 19},
        {"offset": False},
        {"limit": 20.0},
        {"offset": -1},
        {"limit": 0},
        {"query": None},
        {"query": ["Synthetic"]},
        {"offset": 2**53},
    ],
)
def test_exact_prepared_parameters_no_query_authority(change):
    with install(context()), pytest.raises(ValueError):
        search(**change)


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "data"),
        ("kind", "other"),
        ("operation", "docs.scan/v1"),
        ("operation", "docs.search/v2"),
        ("operation", "docs.other.search/v1"),
        ("requirementId", "../private"),
        ("result", []),
        ("parameters", {"query": "Synthetic"}),
    ],
)
def test_closed_knowledge_lookup(field, value):
    obj = context()
    obj["lookups"][2][field] = value
    with pytest.raises(ValueError), install(obj):
        pass


@pytest.mark.parametrize(
    "change",
    [
        {"provider": "private"},
        {"parameters": {"query": "unexpected"}},
        {"result": [{"nested": {"x": 1}}]},
    ],
)
def test_data_v2_uses_existing_flat_contract(change):
    obj = context()
    obj["lookups"][0].update(change)
    with pytest.raises(ValueError), install(obj):
        pass


def test_ingest_empty_parameters_and_strict_namespace():
    from actions.knowledge import ingest
    from actions.knowledge import search as lookup

    with install(context()):
        for fn, args, kwargs in (
            (scan, ("write", "docs.ingest/v1"), {}),
            (ingest, ("read", "docs.search/v1"), {}),
            (ingest, ("data", "records.scan/v1"), {}),
            (lookup, ("write", "docs.ingest/v1"), parameters()),
            (ingest, ("other", "docs.ingest/v1"), {}),
        ):
            with pytest.raises(ValueError):
                fn(*args, **kwargs)
    obj = context()
    obj["lookups"][1]["parameters"] = {"source": "not-authority"}
    with pytest.raises(ValueError), install(obj):
        pass


@pytest.mark.parametrize(
    "result",
    [
        {"x": 2**53},
        {"x": float(2**53)},
        {"x": -0.0},
        {str(i): i for i in range(65)},
        {"x": [0] * 10001},
    ],
)
def test_result_numeric_and_container_limits(result):
    obj = context()
    obj["lookups"][2]["result"] = result
    with pytest.raises(ValueError), install(obj):
        pass


def test_depth_and_byte_limits_and_duplicate_keys():
    obj = context()
    result = {"value": 1}
    for _ in range(9):
        result = {"nested": result}
    obj["lookups"][2]["result"] = result
    with pytest.raises(ValueError), install(obj):
        pass
    obj["lookups"][2]["result"] = {"text": "x" * (256 * 1024)}
    with pytest.raises(ValueError), install(obj):
        pass
    raw = canonical(context()).replace(b'"total":1', b'"total":1,"total":2')
    with pytest.raises(ValueError), install_context(
        raw, expected_digest="sha256:" + hashlib.sha256(raw).hexdigest()
    ):
        pass
    obj = context()
    obj["lookups"].append(copy.deepcopy(obj["lookups"][2]))
    with pytest.raises(ValueError), install(obj):
        pass


def test_nested_exception_async_and_thread_isolation():
    async def task(label):
        obj = context()
        obj["lookups"][2]["result"] = {"label": label}
        with install(obj):
            await asyncio.sleep(0)
            return search()

    async def gather():
        return await asyncio.gather(task("one"), task("two"))

    with install(context()):
        with pytest.raises(RuntimeError):
            with install(dict(version="actions.logical-context/v2", lookups=[])):
                raise RuntimeError("synthetic")
        assert search()["total"] == 1
        assert asyncio.run(gather()) == [{"label": "one"}, {"label": "two"}]

        def thread(_):
            with pytest.raises(ValueError):
                search()
            with install(context()):
                return search()["total"]

        with ThreadPoolExecutor(max_workers=2) as pool:
            assert list(pool.map(thread, [1, 2])) == [1, 1]


def test_v1_cannot_supply_knowledge():
    with install(
        dict(version="actions.logical-read-context/v1", lookups=[])
    ), pytest.raises(ValueError):
        search()


def test_import_and_lookup_do_not_read_external_authority():
    import os
    import subprocess
    import sys
    from pathlib import Path

    import actions.data._context as module

    root = Path(module.__file__).resolve().parents[2]
    code = """
import actions
from unittest.mock import patch
with patch("os.getenv", side_effect=AssertionError("environment lookup")), patch("builtins.open", side_effect=AssertionError("file lookup")), patch("socket.create_connection", side_effect=AssertionError("network lookup")):
    from actions.knowledge import search, ingest
    for function, args, kwargs in [(ingest, ("docs", "docs.ingest/v1"), {}), (search, ("docs", "docs.search/v1"), {"ingestion_handle": "synthetic", "query": "test"})]:
        try:
            function(*args, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("unexpected context")
"""
    env = dict(
        os.environ,
        PYTHONPATH=str(root) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    )
    subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
    )


def test_maximum_depth_and_container_boundaries_are_usable():
    obj = context()
    nested = 1
    for _ in range(8):
        nested = {"nested": nested}
    obj["lookups"][2]["result"] = nested
    with install(obj):
        assert search() == nested
    obj["lookups"][2]["result"] = {
        str(i): [0] * 10000 if i == 0 else None for i in range(64)
    }
    with install(obj):
        assert len(search()["0"]) == 10000


def test_context_isolation_from_original_values_and_scalar_subclasses():
    class Text(str):
        pass

    class Number(int):
        pass

    obj = context()
    with install(obj):
        obj["lookups"][2]["result"]["hits"].clear()
        assert len(search()["hits"]) == 1
        for change in (
            {"query": Text("Synthetic")},
            {"limit": Number(20)},
            {"query": "\ud800"},
        ):
            with pytest.raises(ValueError) as error:
                search(**change)
            assert len(str(error.value)) < 100


def test_v2_operation_count_and_closed_envelope():
    obj = context()
    obj["lookups"] = [
        dict(
            requirementId="r" + str(i),
            operation="docs.ingest/v1",
            kind="knowledge",
            parameters={},
            result={},
        )
        for i in range(32)
    ]
    with install(obj):
        from actions.knowledge import ingest

        assert ingest("r31", "docs.ingest/v1") == {}
    obj["lookups"].append(dict(obj["lookups"][-1], requirementId="r32"))
    with pytest.raises(ValueError), install(obj):
        pass
    obj = context()
    obj["private"] = "not-a-context-field"
    with pytest.raises(ValueError), install(obj):
        pass
