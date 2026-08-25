from devutils.runtime_conformance import (
    DeploymentRevision,
    WorkerProfile,
    admit,
    assert_execution_subject,
    subject_fingerprint,
)
from devutils.runtime_conformance import RuntimePlan


def test_exact_subject_is_order_independent_and_detects_changes():
    subject = {"package": "p1", "capability": "c1", "policy_generation": 3}
    assert subject_fingerprint(subject) == subject_fingerprint(
        {"policy_generation": 3, "capability": "c1", "package": "p1"}
    )
    snapshot = admit(subject, "enforce", "g3", _plan(), _worker())
    assert_execution_subject(snapshot, dict(reversed(list(subject.items()))))

    changed = dict(subject, policy_generation=4)
    try:
        assert_execution_subject(snapshot, changed)
    except ValueError as exc:
        assert str(exc) == "execution subject changed after admission"
    else:
        raise AssertionError("changed subject was accepted")


def test_admission_is_canonical_and_does_not_fallback():
    snapshot = admit({"capability": "c1"}, "shadow", "g1", _plan(), None)
    assert (snapshot.outcome, snapshot.reason, snapshot.mode) == (
        "no_worker", "no eligible worker", "shadow"
    )

    revision = DeploymentRevision("d2", "c1", (_plan(),), "missing")
    try:
        revision.select()
    except ValueError as exc:
        assert str(exc) == "requested runtime plan is not declared"
    else:
        raise AssertionError("undeclared plan was selected")


def _plan():
    return RuntimePlan("r1", "test", "adapter.v1", "1", ("exec",))


def _worker():
    return WorkerProfile("w1", ("test",), ("exec",))
