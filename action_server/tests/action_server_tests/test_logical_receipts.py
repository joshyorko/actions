import copy
from dataclasses import replace
from types import SimpleNamespace

import pytest
from action_server_tests.test_logical_execution import local as _local
from action_server_tests.test_logical_execution import logical as _logical
from action_server_tests.test_logical_execution import prepare
from action_server_tests.test_logical_execution import provider as _provider

from actions.server.foundry.logical_receipts import (
    LogicalOperationIdentity,
    LogicalReadSummary,
    derive_summary,
    validate_generated_version,
    validate_summary,
    validate_summary_identities,
    versions_for,
)

logical, provider, local = _logical, _provider, _local
pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    """Pure receipt checks and synthetic compilation; no RCC/cache use."""
    yield


def identity(name="records", operation="records.scan/v1"):
    return LogicalOperationIdentity(
        requirementId=name,
        operation=operation,
        sourceRevision="sha256:" + "a" * 64,
        contractDigest="sha256:" + "b" * 64,
    )


def wire():
    return {
        "version": "actions.logical-read-receipt/v1",
        "contextDigest": "sha256:" + "c" * 64,
        "operations": [
            {
                **identity().model_dump(mode="json"),
                "resultDigest": "sha256:" + "d" * 64,
                "rowCount": 1,
            }
        ],
    }


def expected():
    return LogicalReadSummary.model_validate_json(__import__("json").dumps(wire()))


def test_exact_summary_and_retained_identity_check():
    assert validate_summary(wire(), expected=expected()) == expected()
    assert (
        validate_summary_identities(
            wire(), expected_operations=(identity(),), requirement_ids=("records",)
        )
        == expected()
    )
    changed = wire()
    changed["contextDigest"] = "sha256:" + "e" * 64
    changed["operations"][0]["resultDigest"] = "sha256:" + "f" * 64
    changed["operations"][0]["rowCount"] = 2
    with pytest.raises(ValueError):
        validate_summary(changed, expected=expected())
    # Retained-reader identity validation cannot prove result/context provenance.
    assert (
        validate_summary_identities(
            changed, expected_operations=(identity(),), requirement_ids=("records",)
        )
        .operations[0]
        .row_count
        == 2
    )


@pytest.mark.parametrize("terminal", [False, True])
def test_version_selection_rejects_retags(terminal):
    old, new = versions_for(()), versions_for(("records",))
    assert old == (
        "actions.generated-rcc-dispatch/v1",
        "actions.generated-rcc-execution/v1",
    )
    assert new == (
        "actions.generated-rcc-dispatch/v2",
        "actions.generated-rcc-execution/v2",
    )
    validate_generated_version(
        {"version": new[int(terminal)]}, requirement_ids=("records",), terminal=terminal
    )
    for tag, requirements in [
        (old[int(terminal)], ("records",)),
        (new[int(terminal)], ()),
        ("unknown", ()),
    ]:
        with pytest.raises(ValueError):
            validate_generated_version(
                {"version": tag}, requirement_ids=requirements, terminal=terminal
            )


@pytest.mark.parametrize(
    "ids",
    [
        ("records", "records"),
        ("Bad",),
        ("../records",),
        ("r" * 65,),
        ["records"],
        ("r\n",),
    ],
)
def test_invalid_requirement_identity_input(ids):
    with pytest.raises(ValueError):
        versions_for(ids)


@pytest.mark.parametrize(
    "path,value",
    [
        (("version",), "unknown"),
        (("contextDigest",), "sha256:" + "C" * 64),
        (("contextDigest",), "sha256:" + "c" * 64 + "\n"),
        (("extra",), "private-token"),
        (("operations",), []),
        (("operations", 0, "extra"), "private-token"),
        (("operations", 0, "rowCount"), True),
        (("operations", 0, "rowCount"), 1.0),
        (("operations", 0, "rowCount"), -1),
        (("operations", 0, "rowCount"), 100001),
        (("operations", 0, "resultDigest"), "bad"),
        (("operations", 0, "sourceRevision"), "bad"),
        (("operations", 0, "contractDigest"), "bad"),
        (("operations", 0, "requirementId"), "bad/name"),
        (("operations", 0, "operation"), "records.select/v1"),
        (("operations", 0, "operation"), "records.scan/v2"),
    ],
)
def test_closed_summary_rejects_malformed(path, value):
    obj = wire()
    target = obj
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError) as error:
        validate_summary(obj, expected=expected())
    assert "private-token" not in str(error.value)


def test_missing_duplicate_extra_and_wrong_expected_operations():
    for mutation in ["missing", "duplicate", "extra"]:
        obj = wire()
        if mutation == "missing":
            del obj["operations"][0]["resultDigest"]
        elif mutation == "duplicate":
            obj["operations"] *= 2
        else:
            row = copy.deepcopy(obj["operations"][0])
            row["requirementId"] = "extra"
            obj["operations"].append(row)
        with pytest.raises(ValueError):
            validate_summary_identities(
                obj, expected_operations=(identity(),), requirement_ids=("records",)
            )
    for identities, requirements in [
        ((), ("records",)),
        ((identity(), identity()), ("records",)),
        ((identity("other"),), ("records",)),
        ((identity(),), ("records", "missing")),
    ]:
        with pytest.raises(ValueError):
            validate_summary_identities(
                wire(), expected_operations=identities, requirement_ids=requirements
            )
    changed = identity().model_copy(update={"source_revision": "sha256:" + "e" * 64})
    with pytest.raises(ValueError):
        validate_summary_identities(
            wire(), expected_operations=(changed,), requirement_ids=("records",)
        )


def test_duplicate_json_keys_and_noncanonical_bytes():
    import json

    raw = json.dumps(wire(), sort_keys=True, separators=(",", ":")).encode()
    assert validate_summary(raw, expected=expected()) == expected()
    for invalid in [
        raw + b"\n",
        raw.replace(b'"rowCount":1', b'"rowCount":1,"rowCount":1'),
        raw.replace(b'"rowCount":1', b'"rowCount":NaN'),
        b" " * 65537,
    ]:
        with pytest.raises(ValueError):
            validate_summary(invalid, expected=expected())


def test_expected_value_never_inferred_from_claim():
    with pytest.raises(TypeError):
        validate_summary(wire())
    with pytest.raises(TypeError):
        validate_summary_identities(wire())
    with pytest.raises(ValueError):
        validate_summary(wire(), expected=wire())
    with pytest.raises(ValueError):
        derive_summary(SimpleNamespace())


def test_real_prepared_projection_excludes_private_context(logical):
    prepared = prepare(logical)
    summary = derive_summary(prepared)
    assert summary.context_digest == prepared.context_digest
    assert summary.operations[0].row_count == 1
    assert (
        validate_summary(summary.model_dump(mode="json"), expected=summary) == summary
    )
    raw = summary.model_dump_json()
    for private in [
        prepared.context.decode(),
        prepared.actor.principal_id,
        prepared.receipts[0].config_digest,
        prepared.receipts[0].catalog_digest,
        str(prepared.receipts[0].provider.provider_profile_id.root),
    ]:
        assert private not in raw
    # Derivation is projection, not issuance verification or a publication grant.
    assert derive_summary(replace(prepared)) == summary
    with pytest.raises(ValueError):
        derive_summary(replace(prepared, context_digest="sha256:" + "0" * 64))
    logical.execution.release(prepared)


def test_operation_count_order_and_numeric_boundary():
    obj = wire()
    obj["operations"] = [
        {**obj["operations"][0], "requirementId": f"r{i:02}", "rowCount": 100000}
        for i in range(32)
    ]
    identities = tuple(identity(f"r{i:02}") for i in range(32))
    ids = tuple(f"r{i:02}" for i in range(32))
    assert (
        len(
            validate_summary_identities(
                obj, expected_operations=identities, requirement_ids=ids
            ).operations
        )
        == 32
    )
    for changed in [
        list(reversed(obj["operations"])),
        obj["operations"] + [dict(obj["operations"][0], requirementId="extra")],
    ]:
        bad = {**obj, "operations": changed}
        with pytest.raises(ValueError):
            validate_summary_identities(
                bad, expected_operations=identities, requirement_ids=ids
            )


def test_partial_version_check_is_not_an_envelope_validator():
    # This intentionally passes version-only validation. The caller must still
    # reject its missing launch/fence/receipt fields before treating it as a Run.
    assert (
        validate_generated_version(
            {"version": "actions.generated-rcc-execution/v2"},
            requirement_ids=("records",),
            terminal=True,
        )
        is None
    )
    with pytest.raises(ValueError):
        validate_generated_version(
            {"version": "actions.generated-rcc-execution/v2"},
            requirement_ids=("records",),
            terminal=1,
        )


def test_alias_collision_and_private_metadata_rejected():
    for key in [
        "context_digest",
        "provider",
        "configDigest",
        "catalogDigest",
        "context",
        "publicationFence",
    ]:
        obj = wire()
        obj[key] = "private-marker"
        with pytest.raises(ValueError) as error:
            validate_summary(obj, expected=expected())
        assert "private-marker" not in str(error.value)
    raw = wire()
    raw["operations"][0]["row_count"] = 1
    with pytest.raises(ValueError):
        validate_summary(raw, expected=expected())
