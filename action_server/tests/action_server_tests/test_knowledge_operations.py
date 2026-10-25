"""Closed generated Knowledge contracts and lossless bounded JSON envelopes."""
import copy
import json

import pytest

from actions.server.data_queries.knowledge_operations import (
    encode_result,
    knowledge_contract,
)
from actions.server.deployments.logical_bindings import BindingField, BindingOperation


def operation(kind="search", **changes):
    value = dict(
        name="documents." + kind + "/v1",
        effect="write" if kind == "ingest" else "read",
        parameters=()
        if kind == "ingest"
        else tuple(
            BindingField(name=name, kind=field_type)
            for name, field_type in (
                ("ingestion_handle", "string"),
                ("query", "string"),
                ("offset", "integer"),
                ("limit", "integer"),
            )
        ),
        result=(BindingField(name="result_json", kind="string"),),
        max_rows=20,
        max_bytes=65536,
        timeout_ms=1000,
    )
    value.update(changes)
    return BindingOperation(**value)


def envelope(kind="search"):
    ref = dict(
        workspace_id="00000000-0000-4000-8000-000000000001",
        collection_id="00000000-0000-4000-8000-000000000002",
        revision_id="sha256:" + "1" * 64,
    )
    if kind == "ingest":
        return dict(
            version="actions.knowledge-ingestion-staged/v1",
            revision=ref,
            corpusHandle="art_AAAAAAAAQACAAAAAAAAAAw",
            corpusDigest="sha256:" + "2" * 64,
            status="staged",
        )
    return dict(
        version="actions.knowledge-search/v1",
        revision=ref,
        ingestionHandle="art_AAAAAAAAQACAAAAAAAAAAw",
        corpusDigest="sha256:" + "2" * 64,
        query="synthetic",
        offset=0,
        limit=20,
        total=1,
        hits=[
            dict(
                id="sha256:" + "3" * 64,
                source="document",
                ordinal=0,
                text="synthetic",
                values={"nested": {"items": [None, True, 2, 0.5, "☃"]}},
            )
        ],
    )


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


@pytest.mark.parametrize("kind", ["ingest", "search"])
def test_exact_contract_and_lossless_canonical_envelope(kind):
    op, value = operation(kind), envelope(kind)
    before = copy.deepcopy(value)
    assert knowledge_contract(op) == kind
    encoded = encode_result(op, value)
    assert set(encoded) == {"result_json"}
    assert json.loads(encoded["result_json"]) == before == value
    assert encoded["result_json"] == json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


@pytest.mark.parametrize(
    "name",
    [
        "Documents.search/v1",
        "docs.other.search/v1",
        "docs.search/v2",
        "docs.scan/v1",
        "d" * 58 + ".search/v1",
        "docs.search/v01",
    ],
)
def test_operation_names_are_closed(name):
    # model_copy exercises validation of a DTO whose normal constructor was bypassed.
    with pytest.raises(ValueError):
        knowledge_contract(operation().model_copy(update={"name": name}))


@pytest.mark.parametrize("kind", ["ingest", "search"])
def test_maximum_prefix_and_old_bytes_untouched(kind):
    op = operation(kind, name="d" * 57 + "." + kind + "/v1")
    before = op.model_dump_json()
    assert knowledge_contract(op) == kind
    encode_result(op, envelope(kind))
    assert op.model_dump_json() == before


@pytest.mark.parametrize(
    "changes",
    [
        {"effect": "write"},
        {"parameters": ()},
        {"result": (BindingField(name="text", kind="string"),)},
        {"result": (BindingField(name="result_json", kind="string", required=False),)},
        {"result": (BindingField(name="result_json", kind="integer"),)},
    ],
)
def test_wrong_effect_parameter_or_result_contract(changes):
    with pytest.raises(ValueError):
        knowledge_contract(operation(**changes))


@pytest.mark.parametrize("field", ["ingestion_handle", "query", "offset", "limit"])
def test_all_search_parameters_required_and_exact_types(field):
    op = operation()
    for mutation in ({"required": False}, {"kind": "number"}):
        fields = tuple(
            item.model_copy(update=mutation) if item.name == field else item
            for item in op.parameters
        )
        with pytest.raises(ValueError):
            knowledge_contract(op.model_copy(update={"parameters": fields}))


@pytest.mark.parametrize(
    "kind,field,value",
    [
        ("ingest", "status", "completed"),
        ("ingest", "version", "actions.knowledge-ingestion/v1"),
        ("ingest", "corpusHandle", "art_bad"),
        ("ingest", "corpusDigest", "sha256:bad"),
        ("search", "version", "actions.knowledge-search/v2"),
        ("search", "query", ""),
        ("search", "query", "\x00"),
        ("search", "offset", True),
        ("search", "limit", 0),
        ("search", "total", False),
        ("search", "total", 0),
        ("search", "hits", {}),
    ],
)
def test_closed_envelope_fields(kind, field, value):
    obj = envelope(kind)
    obj[field] = value
    with pytest.raises(ValueError):
        encode_result(operation(kind), obj)


@pytest.mark.parametrize("kind", ["ingest", "search"])
def test_missing_extra_and_foreign_reference_fields(kind):
    original = envelope(kind)
    for key in original:
        value = dict(original)
        del value[key]
        with pytest.raises(ValueError):
            encode_result(operation(kind), value)
    value = dict(original, secret="synthetic-value")
    with pytest.raises(ValueError) as error:
        encode_result(operation(kind), value)
    assert "synthetic-value" not in str(error.value)
    value = copy.deepcopy(original)
    value["revision"]["unexpected"] = "extra"
    with pytest.raises(ValueError):
        encode_result(operation(kind), value)


@pytest.mark.parametrize(
    "value",
    [
        float("inf"),
        float("nan"),
        2**53,
        float(2**53),
        -0.0,
        {str(i): i for i in range(65)},
        [0] * 10001,
    ],
)
def test_inner_portability_and_container_bounds(value):
    obj = envelope()
    obj["hits"][0]["values"] = {"value": value}
    with pytest.raises(ValueError):
        encode_result(operation(), obj)


def test_depth_cycles_and_subclasses_refused():
    obj = envelope()
    nested = {}
    for _ in range(9):
        nested = {"nested": nested}
    obj["hits"][0]["values"] = nested
    with pytest.raises(ValueError):
        encode_result(operation(), obj)
    nested["cycle"] = nested
    with pytest.raises(ValueError):
        encode_result(operation(), obj)

    class Number(int):
        pass

    obj = envelope()
    obj["hits"][0]["values"] = {"number": Number(1)}
    with pytest.raises(ValueError):
        encode_result(operation(), obj)


def test_outer_serialized_size_counts_json_escaping_and_unicode():
    obj = envelope()
    outer = encode_result(operation(), obj)
    size = len(
        json.dumps(
            outer, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    )
    assert encode_result(operation(max_bytes=size), obj) == outer
    with pytest.raises(ValueError):
        encode_result(operation(max_bytes=size - 1), obj)
    assert size > len(outer["result_json"].encode())


def test_search_row_limit_and_pagination():
    obj = envelope()
    obj["hits"].append(dict(obj["hits"][0], id="sha256:" + "4" * 64, ordinal=1))
    obj["total"] = 2
    with pytest.raises(ValueError):
        encode_result(operation(max_rows=1), obj)
    assert encode_result(operation(max_rows=2), obj)
    obj.update(hits=[], offset=3)
    assert encode_result(operation(max_rows=1), obj)
    obj.update(offset=0)
    with pytest.raises(ValueError):
        encode_result(operation(), obj)


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "not-digest"),
        ("source", "../file"),
        ("ordinal", True),
        ("ordinal", -1),
        ("text", ""),
        ("text", "nul\x00"),
        ("values", []),
        ("extra", "field"),
    ],
)
def test_hit_shape_and_identity_types(field, value):
    obj = envelope()
    obj["hits"][0][field] = value
    with pytest.raises(ValueError):
        encode_result(operation(), obj)


def test_duplicates_order_and_noncanonical_handles_rejected():
    obj = envelope()
    obj["total"] = 2
    obj["hits"].append(copy.deepcopy(obj["hits"][0]))
    with pytest.raises(ValueError):
        encode_result(operation(), obj)
    obj["hits"][1].update(id="sha256:" + "4" * 64, source="aaa")
    with pytest.raises(ValueError):
        encode_result(operation(), obj)
    obj = envelope("ingest")
    obj["corpusHandle"] = obj["corpusHandle"][:-1] + "x"
    with pytest.raises(ValueError):
        encode_result(operation("ingest"), obj)


def test_exact_boundary_depth_container_and_portable_numbers():
    obj = envelope()
    # Root0 / hits1 / document2 / values3: five nested wrappers put leaf at8.
    nested = [0] * 10000
    for _ in range(4):
        nested = {"nested": nested}
    obj["hits"][0]["values"] = nested
    assert encode_result(operation(), obj)
    obj["hits"][0]["values"] = {str(i): None for i in range(64)}
    obj["hits"][0]["values"]["0"] = 2**53 - 1
    assert encode_result(operation(), obj)


def test_ingestion_contract_does_not_accept_parameters():
    with pytest.raises(ValueError):
        knowledge_contract(
            operation(
                "ingest", parameters=(BindingField(name="source", kind="string"),)
            )
        )
