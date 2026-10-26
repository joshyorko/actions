# Logical expiry acknowledgement failure: provisional review

## Scope and evidence

Read-only review of the named test, its source APIs, prior repair evidence, and the current aggregate progress events. No tests were run and no source, fixtures, or services were changed.

`runtime-a52-full-corrected/progress.jsonl` records the target test's setup as passed, call as failed, and teardown as passed (events 8505–8507), but contains no assertion location or exception. The traceback in `pytest.log` is now available and is classified below.

The test is [test_logical_boundary_fixes.py](/workspace/qa327/source/action_server/tests/action_server_tests/test_logical_boundary_fixes.py:42). Its assertion path is: publish and set each output expiry to the fixed value `"1"` (lines 47–49); expect a completed metadata-only acknowledgement with no result (63–65); expect result-bearing projection and strict direct validation to refuse the expired outputs (66–79); verify the Run remains passed (80); then corrupt the digest and expiry timestamp and expect metadata-only acknowledgement to refuse both (81–93). Without the traceback, any of those expectations could be the failing point.

## Contract and likely interpretation

The implementation encodes the intended split: `TaskService._project` passes `_allow_expired_terminal=terminal and not include_result` to `validate_bound_record` ([task_service.py](/workspace/qa327/source/action_server/src/actions/server/run_outputs/task_service.py:554)); `_result` allows expired metadata only when `resolve=False` ([task_service.py](/workspace/qa327/source/action_server/src/actions/server/run_outputs/task_service.py:665)). The validator rejects that exception for nonterminal runs and still checks canonical expiry syntax, row identity, lineage, and sealed output evidence ([logical_receipts.py](/workspace/qa327/source/action_server/src/actions/server/foundry/logical_receipts.py:787), [logical_receipts.py](/workspace/qa327/source/action_server/src/actions/server/foundry/logical_receipts.py:945)). Thus, the product contract is explicit: a terminal acknowledgement may outlive result retention, but GET/result resolution and malformed or inconsistent retained metadata remain unavailable.

The fixture forces expiration by writing `expires_ms="1"`; it does not wait for a near-future deadline. A timing race in *expiry* is therefore unlikely. Before the traceback arrived, progress events alone could not distinguish a product-contract regression from test/fixture state or another assertion. The neighboring expiry-publication test and both parameterized budget-gate cases passed, which narrows scope but does not prove this case is flaky.

Prior evidence: commit `fbde9bc3947804212c930aa65c2884714eb9df2e` introduced the test and logical receipt implementation. The repository's `recovery-a36/logical-boundary-fix-evidence/README.md` records the same test passing in the 55-pass focused run and in the four-test `retention-final.xml` run, including corrupt-seal and malformed-timestamp checks. That is historical focused evidence, not a traceback or proof about this aggregate run's failing assertion.

## Terminal traceback update

The full-suite traceback identifies the first acknowledgement call (test line 63) as the failure. The test constructs `tasks` with `object.__new__(TaskService)` and assigns only `db`, `outputs`, and `policy` (lines 51–56). `_project` immediately reads `self.detached.claimed(run.id)` ([task_service.py](/workspace/qa327/source/action_server/src/actions/server/run_outputs/task_service.py:452)); the missing `detached` attribute raises `AttributeError`, which `_project` intentionally converts to `TaskUnavailable` at line 650. This happens before expiry acknowledgement validation, so the initial failure does **not** show that the product contract or expiry logic failed. It did expose an incomplete test-double initialization, but that was not the only fixture mismatch.

`TaskService.__init__` requires and stores `detached`, `readiness`, and `policy` ([task_service.py](/workspace/qa327/source/action_server/src/actions/server/run_outputs/task_service.py:131)). Follow-up focused evidence in `logical-repro.log` shows that constructing it normally with `DetachedActions(owner.deployments, g.outputs)`, a read-only readiness stub, and the same policy still fails on the first `_project` call. `logical-diagnostic-loaded.log` identifies the next failure: `DetachedActions.claimed(run.id)` raises `AccessDenied` because this logical publication unit fixture has no retained `RunExecutionIntent`. Thus normal constructor use alone is not a sufficient fix, and this helper's direct `_project` setup does not satisfy the detached lookup's fixture contract.

The QA-only isolated reproduction substitutes a claim lookup that asserts the exact run ID and returns `None` for the unclaimed run. With that fixture boundary isolated, the original expiry assertions remain unchanged and the logical-scope run is pending. This is evidence that the assertion sequence can proceed when the detached lookup represents an unclaimed task; it is not a product repair, a completed full-suite rerun, or proof of behavior for a public Task. No source edit was made.

Keep this classification scoped to the named failed test. The traceback is a missing `detached` test attribute and does not mention or establish anything about the separate a54 cancelled-read case; do not merge their outcomes or claims.

**Updated assessment:** the original failure was caused by the missing `detached` test attribute; adding a normal `DetachedActions` instance exposes a second fixture contract mismatch because no `RunExecutionIntent` exists. Classify the full-suite failure as test fixture mismatch at the detached claim lookup, not an expiry/product failure. The isolated no-claim lookup demonstrates progress past that mismatch, but the expiry assertions have not completed in the cited follow-up evidence. Product behavior for an actually retained public Task remains unverified by this failed test.

## Canonical documentation improvement proposal

- **Canonical file proposed:** `docs/skills/repository-operations.md`.
- **Exact proposed addition:** “When a JSONL test progress record reports a failed call but terminal pytest output is not yet available, record the case as failure observed with cause unresolved. Do not infer a failing assertion, product defect, or flake from phase duration or neighboring passes; obtain the traceback before classifying.”
- **Evidence:** the full-suite traceback shows the omitted `detached` field; follow-up normal-constructor reproduction and diagnostic identify the absent retained `RunExecutionIntent`; QA-only isolation with an exact-ID unclaimed lookup proceeds with the expiry assertions unchanged. Prior focused evidence records this test passing in a different run.
- **Stale guidance removed:** none; proposal only.
- **Remaining uncertainty:** the isolated scope remains pending, and no completed rerun exercises these assertions against a retained, genuinely unclaimed Task with its normal `RunExecutionIntent`. The outcome for that fuller public-Task fixture and under aggregate-suite conditions is unverified.

## Completed isolated check

The exact-ID unclaimed lookup QA copy and unchanged pending-publication control completed: 2 passed in 4.07 seconds (logical-scope-isolated.log/XML). This verifies the retained expiry assertions at unit scope after isolating the fixture’s unrelated missing Task-admission intent. Original frozen test independently reproduced failure. This does not repair or supersede the FAILED full suite and is not public Task or installed acceptance.
