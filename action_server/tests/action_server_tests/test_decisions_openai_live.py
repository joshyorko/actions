"""One explicit synthetic hosted request. Never runs in ordinary offline checks."""

import os
from pathlib import Path

import pytest

from actions.server.decisions.models import DecisionInput, Option, Question
from actions.server.decisions.openai import HostedPolicy, OpenAIDecisionsProvider


@pytest.mark.integration_test
def test_one_synthetic_hosted_decision():
    if os.environ.get("DECISIONS_OPENAI_LIVE") != "1":
        pytest.skip("hosted Decisions explicitly disabled")
    key_path = os.environ.get("OPENAI_API_KEY_FILE")
    project = os.environ.get("OPENAI_PROJECT_ID")
    if not key_path or not project:
        pytest.fail("fresh key file and scoped project are required")
    provider = OpenAIDecisionsProvider(
        HostedPolicy(
            enabled=True,
            secret_ref="live-test-key",
            project_id=project,
            max_input_bytes=4096,
            max_response_bytes=16384,
        ),
        lambda _: Path(key_path).read_text().strip(),
    )
    request = DecisionInput(
        evidence='{"document_type":"invoice"}',
        policy_revision="sha256:" + "3" * 64,
        questions=(
            Question(
                name="document",
                kind="choice",
                instructions="Classify the synthetic document_type.",
                options=tuple(
                    Option(value=v) for v in ("invoice", "credit_note", "other")
                ),
            ),
        ),
    )
    result = provider.evaluate(request)
    assert result.model == "gpt-6-luna"
    assert result.request_id
    assert result.usage.input_tokens > 0
    assert result.answers[0].choice == "invoice"
