"""Common authorized sealed output proof; no actual RCC execution is claimed."""

import hashlib
import json
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.run_outputs.test_service import insert_action, snapshot

from actions.server._models import Run, RunStatus, create_db
from actions.server.foundry.generic_projection import project_generated_result
from actions.server.run_outputs.models import RunOutput, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    RunOutputControlPlane,
    RunOutputService,
)
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture
def case(database_location, foundry_package_store):
    with create_db(database_location) as db:
        control = RunOutputControlPlane(db)
        snap = snapshot()
        actor = Actor(principal_id=str(uuid4()))
        insert_action(db, snap)
        control.register(snap)
        control.grant(actor, snap.deployment, {"execute", "read", "cancel"})
        outputs = RunOutputService(db, {snap.provider_key: foundry_package_store})
        c = SimpleNamespace(
            db=db,
            control=control,
            snapshot=snap,
            actor=actor,
            outputs=outputs,
            provider=foundry_package_store,
        )

        def publish(raw=b'{"rows":[{"value":3}]}', names=None, status=RunStatus.PASSED):
            run = outputs.admit(actor, snap, {"query": "alpha"}, str(uuid4()))
            fence = outputs.claim(run.id, str(uuid4()), lease_seconds=60)
            refs = []
            records = []
            for name in names or ["rcc-stdout.log", "generated-action-result.json"]:
                body = raw if name == "generated-action-result.json" else b'{"fake":99}'
                ref = outputs.stage(
                    fence,
                    [body[i : i + 32768] for i in range(0, len(body), 32768)],
                    name=name,
                    media_type="application/json"
                    if name.endswith(".json")
                    else "application/octet-stream",
                    retention_seconds=3600,
                )
                refs.append(ref)
                records.append(
                    {
                        "name": name,
                        "ref": ref.model_dump(mode="json"),
                        "digest": "sha256:" + hashlib.sha256(body).hexdigest(),
                        "size": len(body),
                    }
                )
            receipt = {
                "version": "actions.generated-rcc-execution/v1",
                "publicationFence": fence.model_dump(mode="json"),
                "outputs": records,
                "actionResult": {"fake": 123},
            }
            outputs.publish(actor, fence, refs, receipt, terminal_status=status)
            return run, fence, refs

        c.publish = publish
        yield c


def projection(c, run, fence, **kwargs):
    return project_generated_result(
        c.outputs,
        c.actor,
        snapshot=c.snapshot,
        binding_id="count",
        run_id=run.id,
        attempt_id=fence.attempt_id,
        require_current=kwargs.pop("require_current", lambda: None),
        **kwargs,
    )


def mutate(c, run, fn):
    with c.db.transaction():
        stored = c.db.first(Run, "SELECT * FROM run WHERE id=?", [run.id])
        value = json.loads(stored.result)
        fn(value)
        c.db.update_by_id(Run, run.id, {"result": json.dumps(value)})


def test_exact_named_sealed_result_not_first_or_metadata(case):
    c = case
    run, fence, refs = c.publish(b'{ "z": 2, "a": [3] }')
    value = projection(c, run, fence)
    assert value.as_dict() == {
        "bindingId": "count",
        "runId": run.id,
        "attemptId": fence.attempt_id,
        "canonicalJson": '{"a":[3],"z":2}',
        "data": {"a": [3], "z": 2},
    }
    changed = value.data
    changed["a"].append(100)
    assert value.data == {"a": [3], "z": 2}


@pytest.mark.parametrize(
    "raw",
    [
        b'{"a":1,"a":2}',
        b"NaN",
        b"9007199254740992",
        b'"\\ud800"',
        b"\xff",
        b'{"e\\u0301":1,"\\u00e9":2}',
    ],
)
def test_portability_domain(case, raw):
    c = case
    run, fence, _ = c.publish(raw)
    with pytest.raises(ValueError):
        projection(c, run, fence)


@pytest.mark.parametrize(
    "raw",
    [b'"' + b"x" * 65535 + b'"', ('"' + "\u0344" * 20000 + '"').encode()],
    ids=["raw-too-large", "canonical-too-large"],
)
def test_raw_and_canonical_size_limits(case, raw):
    c = case
    run, fence, _ = c.publish(raw)
    with pytest.raises((AccessDenied, ValueError)):
        projection(c, run, fence)


@pytest.mark.parametrize(
    "mode",
    [
        "missing",
        "ambiguous",
        "failed",
        "wrong-attempt",
        "wrong-run",
        "receipt",
        "receipt-version",
        "revoked",
        "cancel",
        "media",
        "output-attempt",
    ],
)
def test_authority_and_inventory_denials(case, mode):
    c = case
    names = (
        ["robot-output.xml"]
        if mode == "missing"
        else ["generated-action-result.json"] * 2
        if mode == "ambiguous"
        else None
    )
    run, fence, refs = c.publish(
        names=names, status=RunStatus.FAILED if mode == "failed" else RunStatus.PASSED
    )
    if mode == "wrong-attempt":
        fence = fence.model_copy(update={"attempt_id": str(uuid4())})
    if mode == "wrong-run":
        run = SimpleNamespace(id=str(uuid4()))
    if mode == "receipt":
        mutate(
            c,
            run,
            lambda v: v["result"]["outputs"][-1].update(digest="sha256:" + "f" * 64),
        )
    if mode == "receipt-version":
        mutate(
            c, run, lambda v: v["result"].update(version="actions.robot-dispatch/v1")
        )
    if mode == "revoked":
        c.control.grant(c.actor, c.snapshot.deployment, {"execute"})
    if mode == "cancel":
        with c.db.transaction():
            c.db.update_by_id(RunPin, run.id, {"cancel_requested": 1})
    if mode in {"media", "output-attempt"}:
        other_attempt = c.publish()[1].attempt_id if mode == "output-attempt" else None
        with c.db.transaction():
            c.db.update_by_id(
                RunOutput,
                refs[-1].output_id,
                {"media_type": "application/xml"}
                if mode == "media"
                else {"run_attempt_id": other_attempt},
            )
    with pytest.raises((AccessDenied, ValueError)):
        projection(c, run, fence)


def test_current_callback_and_revocation_after_read(case, monkeypatch):
    c = case
    run, fence, _ = c.publish()
    checks = []
    original = c.provider.open

    @contextmanager
    def revoke_after_read(*args):
        with original(*args) as reader:
            yield reader
        c.control.grant(c.actor, c.snapshot.deployment, {"execute"})

    monkeypatch.setattr(c.provider, "open", revoke_after_read)
    with pytest.raises(AccessDenied):
        projection(c, run, fence, require_current=lambda: checks.append(1))
    assert len(checks) == 2


def test_no_outer_transaction_and_denied_selection_before_provider(case, monkeypatch):
    c = case
    run, fence, _ = c.publish()
    monkeypatch.setattr(
        c.provider, "open", lambda *a: pytest.fail("unauthorized provider access")
    )

    def denied():
        raise AccessDenied("binding revoked")

    with pytest.raises(AccessDenied):
        projection(c, run, fence, require_current=denied)
    with c.db.transaction(), pytest.raises(AccessDenied):
        projection(c, run, fence)


def test_only_result_bytes_opened_and_bounded(case, monkeypatch):
    c = case
    run, fence, refs = c.publish()
    original = c.provider.open
    reads = []

    @contextmanager
    def observed(*args):
        with original(*args) as reader:

            class BoundedReader:
                def read(self, size=-1):
                    reads.append(size)
                    return reader.read(size)

            yield BoundedReader()

    monkeypatch.setattr(c.provider, "open", observed)
    assert projection(c, run, fence).data == {"rows": [{"value": 3}]}
    assert reads == [65537]


def test_mutated_nonresult_ref_and_boolean_envelope_denied(case):
    c = case
    run, fence, refs = c.publish()
    mutate(c, run, lambda value: value.update(version=True))
    with pytest.raises(AccessDenied):
        projection(c, run, fence)
    mutate(c, run, lambda value: value.update(version=1))
    other_run, other_fence, other_refs = c.publish()

    def wrong_ref(value):
        value["outputs"][0]["output_id"] = other_refs[0].output_id

    mutate(c, run, wrong_ref)
    with pytest.raises(AccessDenied):
        projection(c, run, fence)


@pytest.mark.parametrize(
    "field",
    [
        "sourceArtifactDigest",
        "packageRevision",
        "runtimePlanDigest",
        "launch",
        "execution",
        "claim",
        "lineage",
        "inputs",
        "attempt",
        "intent",
        "nonresult-descriptor",
    ],
)
def test_complete_terminal_preimage_pinned_across_provider_read(
    case, monkeypatch, field
):
    from actions.server.run_outputs.models import RunAttempt, RunExecutionIntent

    c = case
    run, fence, refs = c.publish()
    with c.db.transaction():
        c.db.insert(
            RunExecutionIntent(
                id=run.id,
                workspace_id=c.snapshot.workspace_id,
                actor_id=c.actor.principal_id,
                envelope_json='{"version":"fixture"}',
            )
        )
    mutate(c, run, lambda value: value["result"].update({field: "original"}))
    original = c.provider.open

    @contextmanager
    def tamper_after_read(*args):
        with original(*args) as reader:
            yield reader
        assert not c.db.in_transaction(), "post-read tamper barrier must be outside SQL"
        with c.db.transaction():
            if field == "inputs":
                c.db.update_by_id(Run, run.id, {"inputs": '{"query":"changed"}'})
            elif field == "attempt":
                c.db.update_by_id(RunAttempt, fence.attempt_id, {"heartbeat_ms": "1"})
            elif field == "intent":
                c.db.update_by_id(
                    RunExecutionIntent,
                    run.id,
                    {"envelope_json": '{"version":"changed"}'},
                )
            elif field == "nonresult-descriptor":
                c.db.update_by_id(RunOutput, refs[0].output_id, {"expires_ms": "1"})
            else:
                mutate(c, run, lambda value: value["result"].update({field: "changed"}))

    monkeypatch.setattr(c.provider, "open", tamper_after_read)
    with pytest.raises(AccessDenied):
        projection(c, run, fence)
