import asyncio
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from actions.data import scan
from actions.data._context import install_context


def payload(rows=None, *, requirement="records", operation="records.scan/v1"):
    return canonical(
        {
            "version": "actions.logical-read-context/v1",
            "lookups": [
                {
                    "requirementId": requirement,
                    "operation": operation,
                    "rows": rows
                    if rows is not None
                    else [
                        {"label": "sample", "amount": 0.0, "count": 2, "active": True}
                    ],
                }
            ],
        }
    )


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode()


def install(raw):
    return install_context(
        raw, expected_digest="sha256:" + hashlib.sha256(raw).hexdigest()
    )


def test_bound_lookup_is_fresh_and_finally_reset():
    with pytest.raises(ValueError):
        scan("records", "records.scan/v1")
    raw = payload([{"name": "before"}])
    with install(raw):
        rows = scan("records", "records.scan/v1")
        rows[0]["name"] = "changed"
        rows.append({"injected": "row"})
        assert scan("records", "records.scan/v1") == [{"name": "before"}]
    with pytest.raises(ValueError):
        scan("records", "records.scan/v1")


def test_nested_context_and_exception_reset():
    with install(payload([{"value": "outer"}])):
        with pytest.raises(RuntimeError):
            with install(payload([{"value": "inner"}])):
                assert scan("records", "records.scan/v1") == [{"value": "inner"}]
                raise RuntimeError("test")
        assert scan("records", "records.scan/v1") == [{"value": "outer"}]
        with pytest.raises(ValueError):
            with install(b"{}"):
                pass
        assert scan("records", "records.scan/v1") == [{"value": "outer"}]


def test_async_and_thread_context_isolation():
    async def task(value):
        with install(payload([{"value": value}])):
            await asyncio.sleep(0)
            return scan("records", "records.scan/v1")

    async def run():
        return await asyncio.gather(task("one"), task("two"))

    assert asyncio.run(run()) == [[{"value": "one"}], [{"value": "two"}]]

    def thread(value):
        with pytest.raises(ValueError):
            scan("records", "records.scan/v1")
        with install(payload([{"value": value}])):
            return scan("records", "records.scan/v1")

    with install(payload([{"value": "parent"}])), ThreadPoolExecutor(
        max_workers=2
    ) as executor:
        assert list(executor.map(thread, ["left", "right"])) == [
            [{"value": "left"}],
            [{"value": "right"}],
        ]
        assert scan("records", "records.scan/v1") == [{"value": "parent"}]


@pytest.mark.parametrize(
    "value", [None, [], {}, [1], 2**53, -(2**53), float(2**53), -0.0]
)
def test_invalid_or_noncanonical_scalar_rejected(value):
    raw = payload([{"value": value}])
    with pytest.raises(ValueError):
        with install(raw):
            pass


@pytest.mark.parametrize(
    "raw",
    [
        b'{"version":"actions.logical-read-context/v1","version":"actions.logical-read-context/v1","lookups":[]}',
        b'{"lookups":[],"version":"wrong"}',
        b'{"lookups":[],"version":"actions.logical-read-context/v1","private":"synthetic-token"}',
        b'{"lookups":null,"version":"actions.logical-read-context/v1"}',
        b"\xef\xbb\xbf{}",
        b"{}\n",
        b"\xff",
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b'{"x":1e999}',
        b'{"x":' + b"9" * 10000 + b"}",
        b"[" * 1000 + b"]" * 1000,
    ],
)
def test_malformed_payload_is_sanitized(raw):
    with pytest.raises(ValueError) as error:
        with install(raw):
            pass
    assert "synthetic-token" not in str(error.value)
    assert len(str(error.value)) < 100


@pytest.mark.parametrize(
    "field,value",
    [
        ("requirementId", "../records"),
        ("requirementId", "Records"),
        ("requirementId", "r" * 65),
        ("operation", "records.select/v1"),
        ("operation", "records.scan/v2"),
        ("operation", "records.scan/v01"),
        ("operation", "records.other.scan/v1"),
        ("operation", "r" * 60 + ".scan/v1"),
        ("rows", {}),
        ("rows", [{"Bad": 1}]),
        ("rows", [{"a-b": 1}]),
        ("rows", [{"a": 1}, {"a": True}]),
        ("rows", [{"a": 1.0}, {"a": 1}]),
    ],
)
def test_closed_lookup_and_flat_typed_rows(field, value):
    obj = json.loads(payload())
    obj["lookups"][0][field] = value
    with pytest.raises(ValueError):
        with install(canonical(obj)):
            pass


def test_duplicate_or_extra_lookup_fields_rejected():
    obj = json.loads(payload())
    obj["lookups"] *= 2
    with pytest.raises(ValueError):
        with install(canonical(obj)):
            pass
    obj = json.loads(payload())
    obj["lookups"][0]["provider"] = "forbidden"
    with pytest.raises(ValueError):
        with install(canonical(obj)):
            pass


def test_portable_values_names_optional_fields_and_long_string():
    name = "r" * 59
    requirement = "q" * 64
    rows = [
        {"s": "\x00☃" + ("z" * 100000), "n": (2**53) - 1, "x": -1.5, "b": False},
        {},
    ]
    with install(payload(rows, requirement=requirement, operation=name + ".scan/v1")):
        assert scan(requirement, name + ".scan/v1") == rows
    with install(payload([], requirement="row-items", operation="row-items.scan/v1")):
        assert scan("row-items", "row-items.scan/v1") == []


def test_unknown_lookup_or_parameter_denied():
    with install(payload()):
        with pytest.raises(ValueError):
            scan("other", "records.scan/v1")
        with pytest.raises(ValueError):
            scan("records", "other.scan/v1")
        with pytest.raises(ValueError):
            scan(None, "records.scan/v1")
        with pytest.raises(TypeError):
            scan("records", "records.scan/v1", {})


def test_digest_and_byte_limit():
    raw = payload()
    with pytest.raises(ValueError):
        with install_context(raw, expected_digest="sha256:" + "0" * 64):
            pass
    for value in [bytearray(raw), raw.decode()]:
        with pytest.raises(ValueError):
            with install_context(
                value, expected_digest="sha256:" + hashlib.sha256(raw).hexdigest()
            ):
                pass
    with pytest.raises(ValueError):
        with install(payload([{"text": "a" * (256 * 1024)}])):
            pass


def test_operation_count_bound_and_empty_context():
    obj = {
        "version": "actions.logical-read-context/v1",
        "lookups": [
            {"requirementId": "r" + str(i), "operation": "records.scan/v1", "rows": []}
            for i in range(33)
        ],
    }
    with pytest.raises(ValueError):
        with install(canonical(obj)):
            pass
    obj["lookups"] = obj["lookups"][:32]
    with install(canonical(obj)):
        assert scan("r31", "records.scan/v1") == []
    with install(
        canonical({"version": "actions.logical-read-context/v1", "lookups": []})
    ):
        with pytest.raises(ValueError):
            scan("records", "records.scan/v1")


def test_import_does_not_discover_environment_or_file_context():
    import subprocess
    import sys

    code = """
import actions
from unittest.mock import patch
with patch("os.getenv", side_effect=AssertionError("environment lookup")), patch("builtins.open", side_effect=AssertionError("file lookup")):
    from actions.data import scan
    try:
        scan("records", "records.scan/v1")
    except ValueError:
        pass
    else:
        raise AssertionError("unexpected context")
"""
    subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True
    )


def test_manager_construction_does_not_validate_until_entered():
    manager = install_context(b"bad", expected_digest="bad")
    with install(payload([{"value": "outer"}])):
        assert scan("records", "records.scan/v1") == [{"value": "outer"}]
        with pytest.raises(ValueError):
            with manager:
                pass
        assert scan("records", "records.scan/v1") == [{"value": "outer"}]
