"""Explicitly opted-in synthetic hosted Decisions smoke test."""
import json
import os
from pathlib import Path

import pytest

from actions.server.decisions.models import DecisionInput, Option, Question
from actions.server.decisions.openai import HostedPolicy, OpenAIDecisionsProvider

MODEL = "gpt-6-luna"


def test_one_synthetic_hosted_decision():
    if os.environ.get("DECISIONS_OPENAI_LIVE") != "1":
        pytest.skip("set DECISIONS_OPENAI_LIVE=1 to opt in")
    key_path = os.environ.get("OPENAI_API_KEY_FILE")
    project = os.environ.get("OPENAI_PROJECT_ID")
    if not key_path or not project or not Path(key_path).is_file():
        pytest.skip("set OPENAI_API_KEY_FILE and OPENAI_PROJECT_ID")
    secret = Path(key_path).read_text().strip()
    if not secret or "\n" in secret or "\r" in secret:
        pytest.fail("secret file must contain one non-empty key line")
    original = OpenAIDecisionsProvider.evaluate
    def evaluate(self, req):
        import requests
        post = requests.Session.post
        def scoped(session, url, **kwargs):
            kwargs.setdefault("headers", {})["OpenAI-Project"] = project
            return post(session, url, **kwargs)
        requests.Session.post = scoped
        try:
            return original(self, req)
        finally:
            requests.Session.post = post
    OpenAIDecisionsProvider.evaluate = evaluate
    try:
        req = DecisionInput(
            evidence=json.dumps({"document_type": "invoice", "total": 42}),
            policy_revision="sha256:" + "3" * 64,
            questions=(Question(name="document", kind="choice",
                instructions="Choose the matching type.",
                options=tuple(Option(value=x) for x in ("invoice", "receipt", "other"))),),
        )
        provider = OpenAIDecisionsProvider(
            HostedPolicy(enabled=True, secret_ref="live-test-key", model=MODEL,
                timeout_seconds=10, max_input_bytes=4096, max_response_bytes=16384),
            lambda _: secret,
        )
        result = provider.evaluate(req)
        assert result.answers[0].choice in {"invoice", "receipt", "other"}
    finally:
        OpenAIDecisionsProvider.evaluate = original
