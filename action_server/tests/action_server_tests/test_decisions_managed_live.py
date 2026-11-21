"""One separately authorized native request inside the real managed Robot vertical."""

import json
import os
from pathlib import Path

import pytest
from action_server_tests import test_decisions_work_items as fixtures
from robot.api import TestSuite as RobotSuite

from actions.server.decisions.openai import HostedPolicy, OpenAIDecisionsProvider
from actions.server.decisions.service import Binding
from actions.server.decisions.work_items import ClaimedDecisionService
from actions.server.managed_work_items.contracts import ManagedCaller

claimed = fixtures.claimed
reviewed = fixtures.reviewed
provider = fixtures.provider


@pytest.mark.integration_test
def test_one_hosted_request_through_managed_robot_review_and_restart(claimed, tmp_path):
    if os.environ.get("DECISIONS_MANAGED_LIVE") != "1":
        pytest.skip("integrated hosted acceptance needs separate owner opt-in")
    original, _, caller, command, policy, reviewed_state = claimed
    if reviewed_state[0].backend_name != "sqlite":
        pytest.skip("live request runs once on SQLite; PostgreSQL is qualified offline")
    key_path = os.environ.get("OPENAI_API_KEY_FILE")
    project = os.environ.get("OPENAI_PROJECT_ID")
    if not key_path or not project:
        pytest.fail("T3-delivered key file and scoped project required")

    class OneRequest(OpenAIDecisionsProvider):
        calls = 0
        model = "gpt-6-luna"

        def evaluate(self, request):
            if self.calls != 0:
                raise AssertionError("only one hosted request is authorized")
            self.calls += 1
            return super().evaluate(request)

    class RetainedRobotService(ClaimedDecisionService):
        latest = None

        def evaluate(self, actor, evaluation):
            self.latest = super().evaluate(actor, evaluation)
            return self.latest

    native = OneRequest(
        HostedPolicy(
            enabled=True,
            secret_ref="t3-integrated-key",
            project_id=project,
            max_input_bytes=4096,
            max_response_bytes=16384,
        ),
        lambda _: Path(key_path).read_text().strip(),
    )
    binding = Binding(
        policy_revision=command.policy_revision,
        provider_revision=native.identity,
        model=native.model,
    )
    scope_key = next(iter(original.bindings))
    service = RetainedRobotService(original.managed, {scope_key: (binding, native)})
    before = reviewed_state[3].queue(reviewed_state[5]).list_items()
    task = (
        Path(__file__).resolve().parents[3]
        / "examples/decisions_robot/tasks-managed.robot"
    )
    suite = RobotSuite.from_file_system(task)
    suite.resource.imports[0].args = (service, caller, command)
    result = suite.run(outputdir=str(tmp_path / "hosted-robot"), log=None, report=None)
    assert result.return_code == 0 and native.calls == 1
    receipt = service.latest
    assert receipt.result.model == "gpt-6-luna" and receipt.result.request_id
    assert receipt.result.answers[0].choice == "invoice"
    resolution = service.resolve(
        ManagedCaller(actor=caller.actor), receipt, command, "approve"
    )
    assert resolution.execution_authorized is False
    status = service.status(caller, receipt.receipt_id)
    assert status.resolution == resolution
    fixtures.test_receipt_survives_fresh_runtime_process_without_new_inference(
        (service, native, caller, command, policy, reviewed_state), tmp_path
    )
    assert native.calls == 1
    assert reviewed_state[3].queue(reviewed_state[5]).list_items() == before
    destination = os.environ.get("DECISIONS_LIVE_RECEIPT_FILE")
    if destination:
        Path(destination).write_text(
            json.dumps(
                {
                    "schema": "actions.decisions.managed-live-acceptance/v1",
                    "request_count": native.calls,
                    "robot_passed": True,
                    "fresh_process_replay_without_inference": True,
                    "queue_state_unchanged": True,
                    "receipt": receipt.model_dump(mode="json"),
                    "resolution": resolution.model_dump(mode="json"),
                },
                indent=2,
            )
            + "\n"
        )
