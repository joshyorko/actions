"""Serial local SDK example, not a managed claim or approval implementation."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from actions.work_items._adapters._sqlite import SQLiteAdapter
from robot.api.deco import keyword, library

from actions.server.decisions.fixtures import SyntheticDocumentProvider
from actions.server.decisions.models import (
    DecisionInput,
    Option,
    ProviderResult,
    Question,
)
from actions.server.decisions.openai import HostedPolicy, OpenAIDecisionsProvider


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return "sha256:" + hashlib.sha256(canonical(value).encode()).hexdigest()


def configured_provider(backend):
    if backend == "synthetic":
        return SyntheticDocumentProvider()
    if backend != "openai" or os.environ.get("DECISIONS_OPENAI_LIVE") != "1":
        raise ValueError("OpenAI requires explicit live opt-in; no provider fallback")
    path = os.environ.get("OPENAI_API_KEY_FILE")
    project = os.environ.get("OPENAI_PROJECT_ID")
    if not path or not project:
        raise ValueError("fresh key file and scoped project are required")
    # Credentials stay in the trusted resolver, outside Work Item/model input.
    return OpenAIDecisionsProvider(
        HostedPolicy(
            enabled=True,
            secret_ref="robot-live-key",
            project_id=project,
            max_input_bytes=4096,
            max_response_bytes=16384,
        ),
        lambda _: Path(path).read_text().strip(),
    )


@library(scope="SUITE", auto_keywords=False)
class DecisionsDemo:
    @keyword
    def open_demo(self, state_dir, backend="synthetic"):
        self.root = Path(state_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.adapter = self._adapter()
        self.provider = configured_provider(backend)
        self.provider_id = self.provider.identity
        self.items = {}
        self.calls = 0
        self.outputs = []
        existing = self.adapter.list_items(limit=100)
        if len(existing) > 3:
            raise ValueError("use a dedicated demo state directory")
        for item in existing:
            document = item["payload"]["document_type"]
            if (
                document in self.items
                or document not in SyntheticDocumentProvider.categories
            ):
                raise ValueError("unexpected demo input")
            self.items[document] = item["id"]
        for document in SyntheticDocumentProvider.categories:
            if document not in self.items:
                self.items[document] = self.adapter.seed_input(
                    {"document_type": document}
                )

    def _adapter(self):
        return SQLiteAdapter(
            db_path=str(self.root / "workitems.sqlite"),
            queue_name="decision-demo",
            output_queue_name="decision-evidence",
            files_dir=str(self.root / "files"),
        )

    @keyword
    def get_synthetic_work_item(self, document):
        return self.items[document]

    def _request(self, payload):
        if not isinstance(payload, dict) or set(payload) != {"document_type"}:
            raise ValueError("only the synthetic document_type field is allowed")
        return DecisionInput(
            evidence=canonical(payload),
            policy_revision=digest({"policy": "review-only/v1"}),
            questions=(
                Question(
                    name="document",
                    kind="choice",
                    instructions="Classify this synthetic document by its document_type.",
                    options=tuple(
                        Option(value=v) for v in SyntheticDocumentProvider.categories
                    ),
                ),
            ),
        )

    @keyword
    def decide_work_item(self, item_id):
        item = self.adapter.get_item(item_id)
        if item["state"] != "PENDING" or item_id not in self.items.values():
            raise ValueError("exact pending demo input required")
        request = self._request(item["payload"])
        identity = digest(
            {
                "item_id": item_id,
                "payload": item["payload"],
                "request": request.model_dump(mode="json"),
                "provider": self.provider_id,
            }
        )
        outputs = self.adapter.list_items(queue_name="decision-evidence", limit=100)
        if len(outputs) > 3:
            raise ValueError("demo output bound exceeded")
        prior = [row for row in outputs if row["parent_id"] == item_id]
        if prior:
            if len(prior) != 1 or prior[0]["payload"]["input_digest"] != identity:
                raise ValueError("protected input changed; use new demo state")
            receipt = prior[0]["payload"]
            if receipt["status"] != "NEEDS_REVIEW":
                raise ValueError("evaluation uncertain; automatic retry disabled")
            result = ProviderResult.model_validate_json(json.dumps(receipt["result"]))
            result.validate_input(request)
            return receipt
        pending = {
            "schema": "actions.decision-demo/v1",
            "input_digest": identity,
            "provider": self.provider_id,
            "status": "EVALUATING",
        }
        output_id = self.adapter.create_output(item_id, pending)
        self.calls += 1
        result = self.provider.evaluate(request)
        result.validate_input(request)
        if self.adapter.load_payload(item_id) != item["payload"]:
            raise ValueError("protected input changed during inference")
        receipt = {
            **pending,
            "status": "NEEDS_REVIEW",
            "calibration": "uncalibrated",
            "policy_revision": request.policy_revision,
            "result": result.model_dump(mode="json"),
        }
        self.adapter.save_payload(output_id, receipt)
        self.outputs.append(output_id)
        return receipt

    @keyword
    def decision_should_match(self, receipt, document):
        if receipt["result"]["answers"][0]["choice"] != document:
            raise AssertionError("classification differs from synthetic input")

    @keyword
    def source_should_remain_pending(self, item_id):
        if self.adapter.get_item(item_id)["state"] != "PENDING":
            raise AssertionError("inference changed source queue state")

    @keyword
    def reopen_and_replay_without_inference(self):
        class NoInference:
            def evaluate(self, request):
                raise AssertionError("replay must not call a provider")

        self.adapter = self._adapter()
        self.provider = NoInference()
        for document, item_id in self.items.items():
            self.decision_should_match(self.decide_work_item(item_id), document)
            self.source_should_remain_pending(item_id)
        summary = {
            "schema": "actions.decision-demo-summary/v1",
            "inputs": len(self.items),
            "provider_calls_this_process": self.calls,
            "persisted_decisions": len(
                self.adapter.list_items(queue_name="decision-evidence", limit=100)
            ),
            "source_state": "PENDING",
            "provider": self.provider_id,
        }
        (self.root / "summary.json").write_text(canonical(summary) + "\n")
