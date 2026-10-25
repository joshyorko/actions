# Joined Knowledge failure: source review

No source edit or PostgreSQL workload launched by this lane.

Leading hypothesis: the reused preparation fixture gives the entire preparation-to-publication path only five seconds. `tests/action_server_tests/test_logical_execution.py:173` defaults `deadline=time.monotonic()+5`. `LogicalExecution.prepare` wraps it in `_TotalCancellation`, whose `is_set` includes monotonic deadline expiration. `KnowledgePreparation.recheck` checks that same event before and after SQL seal validation, even when preparation is complete.

The new Knowledge failure test first prepares Knowledge, invokes `publish_generated` to stage successful-path fixture outputs, then stages a second diagnostic inventory and creates two publication bindings. Its joined failing testcase took 6.898 seconds (joined-final.xml). The total includes fixture setup, so duration alone is supporting evidence, not proof that the five-second window expired. Isolation passes are consistent with this load-sensitive boundary. No obvious mutable module-global state was found in the preceding serialization tests; their helpers run in isolated subprocesses, and preceding failure-test monkeypatches use pytest cleanup.

Exact confirmation: at `LogicalExecution.recheck` exception, retain `error.__context__` type/message and each `prepared.knowledge[i].budget.cancelled` object's deadline, current monotonic time, and parent-event state. `AccessDenied: Knowledge publication cancelled or deadline exceeded` with expired deadline and unset parent confirms the hypothesis. Do not dump prepared context or secrets.

Corrective test-only probe if confirmed: pass an explicit bounded 30-second absolute deadline to `fixtures.prepare` for these SQL-publication tests, including the Data case; preserve explicit short-deadline rejection coverage separately. Do not relax production cancellation checks or reinterpret the failed joined run as passing.

Proposed canonical documentation delta: "SQL-only publication fixtures that stage multiple synthetic inventories must explicitly budget the whole preparation-to-publication interval. A completed preparation does not disable total invocation cancellation: retained Knowledge preparations recheck the same absolute deadline at publication. Keep deterministic expiry/rejection tests separate from ordinary successful publication tests, and preserve the suppressed inner exception in private diagnostic evidence when distinguishing timeout from a changed SQL seal."

Remaining uncertainty: exact inner cause of the original joined failure is not retained in its normal log. Full diagnostic replay is the integrator's pending gate.

## Deterministic expiry confirmation

The authorized `expired-publication-probe.py` uses explicit60s preparation, then patches only `logical_execution`'s module clock during final recheck to exceed that deadline. It reproduces the exact outer `LogicalReadRejected: logical publication authority unavailable` with inner `AccessDenied: Knowledge publication cancelled or deadline exceeded`. The Run remains RUNNING and all eight staged outputs remain provisional. RCC gateway test result: one passed (1.90s), retained in expired-publication-corrected.log and expired-publication.xml; structured evidence is expired-publication-result.json. First harness launch failed before tests because its tests import path was missing; expired-publication.log preserves that setup failure. No production edits or PostgreSQL workload were used.

This confirms deadline expiry can produce the joined failure signature and publication rolls back safely. It does not recover the original run's missing inner exception; diagnostic replay must distinguish expiry from another cause before declaring the original failure explained.

Upstream disposition: none.
