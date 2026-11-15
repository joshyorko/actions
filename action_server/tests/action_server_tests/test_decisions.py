"""Native Decisions wire contract and fail-closed evidence validation."""

import copy
import json
from uuid import uuid4

import pytest
from action_server_tests import test_invoice_review as review_fixtures
from action_server_tests import test_managed_work_items_sql_service as sql_fixtures
from pydantic import ValidationError

from actions.server.decisions.fixtures import SyntheticDocumentProvider
from actions.server.decisions.models import DecisionInput, Option, Question
from actions.server.decisions.openai import (
    HostedPolicy,
    OpenAIDecisionsProvider,
    ProviderFailure,
)
from actions.server.decisions.service import Binding, DecisionService
from actions.server.foundry.models import FoundryRequest
from actions.server.run_outputs.service import AccessDenied
from actions.server.run_outputs.types import Actor


def request(kind="choice"):
    return DecisionInput(
        evidence='{"document_type":"invoice"}',
        policy_revision="sha256:" + "a" * 64,
        questions=(
            Question(
                name="document",
                kind=kind,
                instructions="Classify document.",
                options=()
                if kind == "check"
                else tuple(
                    Option(value=v) for v in ("invoice", "credit_note", "other")
                ),
            ),
        ),
    )


def response(kind="choice"):
    answer = {
        "type": "choice",
        "name": "document",
        "choice": "invoice",
        "confidence": 0.81,
        "probabilities": [
            {"value": "invoice", "probability": 0.9},
            {"value": "credit_note", "probability": 0.05},
            {"value": "other", "probability": 0.05},
        ],
    }
    if kind == "check":
        answer = {"type": "predicate", "name": "document", "probability": 0.9}
    elif kind == "score":
        answer = {
            "type": "score",
            "name": "document",
            "score": 0.15,
            "confidence": 0.81,
            "probabilities": [
                {"value": i, "label": v, "probability": p}
                for i, v, p in [
                    (0, "invoice", 0.9),
                    (1, "credit_note", 0.05),
                    (2, "other", 0.05),
                ]
            ],
        }
    return {
        "model": "gpt-6-luna",
        "answers": [answer],
        "usage": {
            "input_tokens": 42,
            "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
            "output_tokens": 0,
            "output_tokens_details": {"reasoning_tokens": 0},
            "total_tokens": 42,
        },
    }


@pytest.mark.parametrize("kind", ["choice", "check", "score"])
def test_native_wire_mapping(kind):
    body = OpenAIDecisionsProvider.serialize(request(kind))
    assert body["model"] == "gpt-6-luna"
    assert body["input"][0]["role"] == "user"
    assert body["input"][0]["content"][0]["type"] == "input_text"
    assert body["questions"][0]["type"] == ("predicate" if kind == "check" else kind)
    result = OpenAIDecisionsProvider.parse(
        request(kind), response(kind), "request-test"
    )
    assert result.answers[0].kind == kind
    if kind != "check":
        assert result.answers[0].confidence == 0.81
        assert result.answers[0].probabilities[0].probability == 0.9
    assert result.usage.input_tokens == 42


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "nan",
        "range",
        "sum",
        "unexpected",
        "confidence",
        "model",
        "name",
        "refusal",
        "boolean",
    ],
)
def test_malformed_answers_fail_closed(mutation):
    data = response()
    answer = data["answers"][0]
    if mutation == "missing":
        answer["probabilities"].pop()
    elif mutation == "duplicate":
        answer["probabilities"][1] = copy.deepcopy(answer["probabilities"][0])
    elif mutation == "nan":
        answer["confidence"] = float("nan")
    elif mutation == "range":
        answer["confidence"] = 1.1
    elif mutation == "sum":
        answer["probabilities"][0]["probability"] = 0.1
    elif mutation == "unexpected":
        answer["choice"] = "pay-now"
    elif mutation == "confidence":
        del answer["confidence"]
    elif mutation == "model":
        data["model"] = "different-model"
    elif mutation == "name":
        answer["name"] = "different-question"
    elif mutation == "refusal":
        data["answers"] = [{"type": "refusal", "name": "document"}]
    elif mutation == "boolean":
        answer["confidence"] = True
    with pytest.raises(ProviderFailure):
        OpenAIDecisionsProvider.parse(request(), data, None)


def test_hosted_disabled_without_policy_or_secret():
    calls = []
    provider = OpenAIDecisionsProvider(
        HostedPolicy(secret_ref="decisions-key"), lambda ref: calls.append(ref)
    )
    with pytest.raises(ProviderFailure, match="egress_disabled"):
        provider.evaluate(request())
    assert calls == []


def test_input_bounded_and_question_names_unique():
    with pytest.raises(ValidationError):
        request().model_copy(update={"evidence": "x" * 8193}).model_validate(
            request().model_copy(update={"evidence": "x" * 8193})
        )
    with pytest.raises(ValidationError):
        DecisionInput(
            evidence="synthetic",
            questions=request().questions * 2,
            policy_revision="sha256:" + "a" * 64,
        )


reviewed = review_fixtures.reviewed
provider = sql_fixtures.provider


class Stub(SyntheticDocumentProvider):
    def __init__(self):
        self.calls = 0
        self.hook = lambda: None

    def evaluate(self, request):
        self.calls += 1
        self.hook()
        return super().evaluate(request)


def composed(reviewed):
    _, _, _, reviews, _, scope, _, _ = reviewed
    stub = Stub()
    binding = Binding(
        policy_revision=request().policy_revision,
        provider_revision=stub.identity,
        model=stub.model,
    )
    service = DecisionService(
        reviews, {DecisionService.scope_key(scope): (binding, stub)}
    )
    return service, stub


@pytest.mark.parametrize("document", ["invoice", "credit_note", "other"])
def test_typed_fixture_receipt_review_and_replay_without_queue_effects(
    reviewed, document
):
    db, _, _, reviews, actor, scope, handle, _ = reviewed
    service, stub = composed(reviewed)
    req = request().model_copy(
        update={"evidence": json.dumps({"document_type": document})}
    )
    receipt = service.evaluate(actor, scope, handle, req, "same-input")
    assert receipt.result.answers[0].choice == document
    assert receipt.recommendation == "NEEDS_REVIEW"
    assert receipt.calibration == "uncalibrated"
    assert reviews.queue(scope).list_items() == []
    restarted = DecisionService(reviews, service.bindings)
    assert restarted.evaluate(actor, scope, handle, req, "same-input") == receipt
    assert restarted.read(actor, scope, handle, receipt.receipt_id) == receipt
    assert restarted.evaluate(actor, scope, handle, req, "another-delivery") == receipt
    assert stub.calls == 1
    stored = db.all(FoundryRequest, where="id=?", values=[receipt.receipt_id])[0]
    assert req.evidence not in stored.result_json
    resolved = reviews.decide(actor, scope, receipt.review, "reject")
    assert resolved.state == "rejected"
    assert reviews.queue(scope).list_items() == []


def test_changed_input_policy_and_revoked_authority_fail_closed(reviewed):
    _, control, _, _, actor, scope, handle, snap = reviewed
    service, stub = composed(reviewed)
    receipt = service.evaluate(actor, scope, handle, request(), "one")
    with pytest.raises(ProviderFailure, match="changed_input"):
        service.evaluate(
            actor,
            scope,
            handle,
            request().model_copy(update={"evidence": "changed"}),
            "one",
        )
    with pytest.raises(ProviderFailure, match="policy_revision_changed"):
        service.evaluate(
            actor,
            scope,
            handle,
            request().model_copy(update={"policy_revision": "sha256:" + "b" * 64}),
            "two",
        )
    with pytest.raises(AccessDenied):
        service.read(
            Actor(principal_id=str(uuid4())), scope, handle, receipt.receipt_id
        )
    control.grant(actor, snap.deployment, {"read"})
    with pytest.raises(AccessDenied):
        service.evaluate(actor, scope, handle, request(), "one")
    assert stub.calls == 1


def test_ambiguous_provider_failure_is_not_automatically_retried(reviewed):
    _, _, _, reviews, actor, scope, handle, _ = reviewed
    service, stub = composed(reviewed)

    def fail():
        raise RuntimeError("raw secret and document must not escape")

    stub.hook = fail
    with pytest.raises(ProviderFailure, match="provider_unavailable"):
        service.evaluate(actor, scope, handle, request(), "one")
    with pytest.raises(ProviderFailure, match="provider_unavailable"):
        DecisionService(reviews, service.bindings).evaluate(
            actor, scope, handle, request(), "one"
        )
    assert stub.calls == 1
    assert reviews.queue(scope).list_items() == []


def test_revocation_during_inference_cannot_offer_review(reviewed):
    _, control, _, reviews, actor, scope, handle, snap = reviewed
    service, stub = composed(reviewed)
    stub.hook = lambda: control.grant(actor, snap.deployment, {"read"})
    with pytest.raises(AccessDenied):
        service.evaluate(actor, scope, handle, request(), "one")
    from actions.server.data_queries.review_models import InvoiceReview

    assert reviews.db.all(InvoiceReview) == []


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "authentication_failed"),
        (403, "access_denied"),
        (429, "throttled_or_credit_exhausted"),
        (500, "service_unavailable"),
        (302, "service_unavailable"),
    ],
)
def test_hosted_http_errors_do_not_leak_or_retry(monkeypatch, status, code):
    class Reply:
        status_code = status

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class Session:
        calls = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, **kwargs):
            self.calls += 1
            assert url == "https://api.openai.com/v1/decisions"
            assert kwargs["allow_redirects"] is False
            assert self.trust_env is False
            return Reply()

    session = Session()
    monkeypatch.setattr(
        "actions.server.decisions.openai.requests.Session", lambda: session
    )
    with pytest.raises(ProviderFailure, match="^" + code + "$"):
        OpenAIDecisionsProvider(
            HostedPolicy(enabled=True, secret_ref="test-only"),
            lambda _: "synthetic-secret",
        ).evaluate(request())
    assert session.calls == 1


def test_slow_stream_cannot_extend_time_budget(monkeypatch):
    clock = [0.0]

    class Reply:
        status_code = 200
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_content(self, size):
            assert size == 1
            for byte in json.dumps(response()).encode():
                clock[0] += 0.2
                yield bytes([byte])

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *args, **kwargs):
            return Reply()

    monkeypatch.setattr("actions.server.decisions.openai.requests.Session", Session)
    monkeypatch.setattr(
        "actions.server.decisions.openai.time.monotonic", lambda: clock[0]
    )
    with pytest.raises(ProviderFailure, match="time_budget_exceeded"):
        OpenAIDecisionsProvider(
            HostedPolicy(enabled=True, secret_ref="test-only", timeout_seconds=1),
            lambda _: "synthetic-secret",
        ).evaluate(request())
    assert clock[0] <= 1.2


def test_terminal_source_review_blocks_new_inference_before_provider_call(reviewed):
    _, _, _, reviews, actor, scope, handle, _ = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "reject")
    service, stub = composed(reviewed)
    with pytest.raises(ProviderFailure, match="source_review_terminal"):
        service.evaluate(actor, scope, handle, request(), "new-decision")
    assert stub.calls == 0


def test_receipt_reopens_in_fresh_python_process_without_inference(reviewed, tmp_path):
    import subprocess
    import sys

    db, _, _, reviews, actor, scope, handle, _ = reviewed
    if db.backend_name != "sqlite":
        pytest.skip("fresh-process proof uses the owned SQLite fixture")
    service, stub = composed(reviewed)
    receipt = service.evaluate(actor, scope, handle, request(), "restart")
    script = """
import json, os, sys
from actions.server._models import load_db
from actions.server.data_queries.review import InvoiceReviewService
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.decisions.fixtures import SyntheticDocumentProvider
from actions.server.decisions.models import DecisionInput
from actions.server.decisions.service import Binding, DecisionService
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.service import RunOutputService
from actions.server.run_outputs.types import Actor, CanvasResultScope
values = json.load(sys.stdin)
class NoInference(SyntheticDocumentProvider):
    def evaluate(self, request):
        raise AssertionError("restart must not infer again")
fd = os.open(values["objects"], os.O_RDONLY | os.O_DIRECTORY)
try:
    with load_db(values["database"]) as db, FilesystemOutputProvider(fd) as objects:
        scope = CanvasResultScope.model_validate_json(values["scope"])
        outputs = RunOutputService(db, {values["provider_key"]: objects})
        reviews = InvoiceReviewService(InvoiceQueryService(outputs, {}))
        provider = NoInference()
        request = DecisionInput.model_validate_json(values["request"])
        binding = Binding(policy_revision=request.policy_revision,
            provider_revision=provider.identity, model=provider.model)
        service = DecisionService(reviews,
            {DecisionService.scope_key(scope): (binding, provider)})
        actor = Actor.model_validate_json(values["actor"])
        receipt = service.evaluate(actor, scope, values["handle"], request, "restart")
        print(receipt.model_dump_json())
finally:
    os.close(fd)
"""
    values = {
        "database": str(db.db_path),
        "objects": str(tmp_path / "objects"),
        "provider_key": next(iter(reviews.outputs.providers)),
        "scope": scope.model_dump_json(),
        "actor": actor.model_dump_json(),
        "handle": handle,
        "request": request().model_dump_json(),
    }
    result = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps(values),
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == receipt.model_dump(mode="json")
    assert stub.calls == 1


def test_interrupted_evaluation_retains_timestamp_and_never_retries(reviewed):
    db, _, _, reviews, actor, scope, handle, _ = reviewed
    service, stub = composed(reviewed)

    def interrupted():
        raise SystemExit("synthetic worker exit")

    stub.hook = interrupted
    with pytest.raises(SystemExit):
        service.evaluate(actor, scope, handle, request(), "interrupted")
    pending = [row for row in db.all(FoundryRequest) if row.operation == "decisions/v1"]
    assert len(pending) == 1
    status = json.loads(pending[0].result_json)
    assert status["schema_version"] == "actions.decision-pending/v1"
    assert status["created_ms"] > 0
    with pytest.raises(ProviderFailure, match="evaluation_uncertain"):
        DecisionService(reviews, service.bindings).evaluate(
            actor, scope, handle, request(), "different-delivery"
        )
    assert stub.calls == 1


def test_receipt_read_needs_read_grant_without_execute(reviewed):
    _, control, _, _, actor, scope, handle, snap = reviewed
    service, stub = composed(reviewed)
    receipt = service.evaluate(actor, scope, handle, request(), "one")
    control.grant(actor, snap.deployment, {"read"})
    assert service.read(actor, scope, handle, receipt.receipt_id) == receipt
    with pytest.raises(AccessDenied):
        service.evaluate(actor, scope, handle, request(), "one")
    assert stub.calls == 1
