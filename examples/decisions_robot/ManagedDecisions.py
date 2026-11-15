"""Trusted host supplies live managed authority as objects, never Robot strings."""

from robot.api.deco import keyword, library


@library(scope="SUITE", auto_keywords=False)
class ManagedDecisions:
    def __init__(self, service, caller, evaluation):
        from actions.server.decisions.work_items import (
            ClaimedDecisionService,
            ClaimedEvaluation,
        )
        from actions.server.managed_work_items.contracts import ManagedCaller

        if (
            not isinstance(service, ClaimedDecisionService)
            or not isinstance(caller, ManagedCaller)
            or not isinstance(evaluation, ClaimedEvaluation)
        ):
            raise TypeError(
                "trusted host must inject managed service, caller and evaluation"
            )
        self.service, self.caller, self.evaluation = service, caller, evaluation
        self.receipt = None

    @keyword
    def evaluate_current_work_item_claim(self):
        self.receipt = self.service.evaluate(self.caller, self.evaluation)

    @keyword
    def decision_should_require_human_review(self):
        if self.receipt is None or self.receipt.recommendation != "NEEDS_REVIEW":
            raise AssertionError("review-only decision receipt required")

    @keyword
    def replay_should_reuse_exact_decision(self):
        if self.service.evaluate(self.caller, self.evaluation) != self.receipt:
            raise AssertionError("replay changed the exact decision")
