# Generated failure lifecycle review — HOLD

Reviewed immutable failure.patch SHA256
6f3d7cae2e905aaf3485e10661d384fc16c6675b3d78fb9f81de01b154eb88b3
at /workspace/generated-failure-evidence/failure-delivery/failure.patch.
Applies after the separately reviewed serialization patch already integrated by root.
Read-only static review and retained receipt inspection. No tests, PG containers,
RCC jobs, builds or cleanup started in this review. Patch is UNAPPROVED for integration.

## Potential blocking cleanup race

rcc_execution.py adds _OwnedProcessCapture. Its capture method marks complete=True
after any successful point-in-time descendant snapshot, including an empty snapshot
immediately after Popen. That bit remains true after the wrapper exits. A wrapper can
fork a long-lived child after the last observed snapshot, then exit before the next
capture (the pipe loop polls with a 0.2-second selector wait). The next capture sees
poll()!=None and returns without invalidating completeness. cleanup passes the old
observed list with snapshot_complete_before_call=True to the common helper.

The common force_kill_process_tree_until does not take another descendant snapshot
when the wrapper has exited; it only terminates/checks observed descendants. With
an empty or stale list it can return wrapper_reaped=True, no observed live children,
no errors and descendant_snapshot_complete=True, hence execution_stopped=True,
while an unseen reparented child remains live. _confirmed_failed_receipt then permits
failed publication when the RCC receipt matches. This is stronger than the proof
actually obtained and conflicts with the requested no-false-cleanup boundary.

This is a source-derived counterexample, NOT an executed regression result. Existing
seven local-process cases prove observed descendant cleanup and first-snapshot-after-
exit refusal, but do not cover a child forked after the last successful snapshot.

Fresh-owner bounded reproducer proposal: wrapper initially waits on a release barrier;
construct capture and confirm an empty snapshot; release wrapper to fork a child with
stdio redirected away from inherited pipes, record its PID, then exit nonzero; wait
wrapper; invoke cleanup/failed-receipt validation with a synthetic matching receipt;
check whether it reports stopped while the child remains alive. The reproducer must
own and terminate its child in finally. Do not weaken reconciliation until reliable
process ownership/termination proof covers this case. No implementation redesign or
new security contract was approved in this review.

Parent storage handoff explicitly stops reproduction/testing in this container.
Suggested reproducer was sent to the implementation helper and then explicitly
cancelled before starting on our lane. Fresh owner must reproduce and resolve before
integration; root will retain the patch as UNAPPROVED WIP.

## Other reviewed boundaries

- Closed actions.generated-rcc-failure/v1 binds source, Package/Plan, RCC identity,
  launch, actual inputs, lineage, Attempt fence and independent Work Item claim.
- Exact diagnostic inventory is three sealed objects (RCC receipt/stdout/stderr).
  No actionResult/resultDigest, generated result file, Work Item children or
  Knowledge/domain publication is allowed by the closed failure branch.
- Immutable registry selection and metadata pins are prepared outside the SQL
  transaction; wrappers recheck live actor/current selection/fence and logical
  authority before base publication. Work Item FAILED completion shares the
  Run/output transaction, with no children. No separate scheduler or DB is added.
- Failed Task readers have an explicit discriminant, revalidate the closed retained
  receipt and output descriptors, and resolve authorized diagnostic handles. They
  do not assume completed status or a generated result digest for failed records.
- Missing binding remains FenceRejected/reconciliation; missing/mismatched RCC
  receipt, timeout and explicitly uncertain cleanup do not use this publication path.
- Receipt bytes are read once for retention and again by existing read_receipt(path)
  for validation. This follows the current private-file approach; no independent
  exploit was established here. Do not treat the cleanup race as resolved merely
  because the file is private; an unseen surviving child invalidates that premise.

No additional blocker found in the bounded SQL/receipt/Task source review. This does
not override the cleanup HOLD or qualify actual installed execution.

## Evidence and limits

Producer receipt records 102 earlier focused SQLite/PostgreSQL passes, three
Data/Knowledge SQL-only passes, seven local-process cleanup cases, and config checks.
Prior baseline146 selected:144 passed/2 failed exception-compatibility assertions;
correction retained final SQLite focused3 passed/7 skipped (125 deselected). Newer
final PG rerun was interrupted by parent storage instruction; it remains pending.
Original failing/skipped/interrupted receipts are retained in the delivery. These
counts were inspected, not independently rerun. Actual RCC/installed acceptance,
Robot hooks and final PG correction qualification remain open.

## Exact canonical guide delta

Target docs/skills/provenance-observability.md, near process cleanup / generated failure
receipts; propose this verified clarification instead of claiming the patch complete:

“ProcessTreeCleanupResult.execution_stopped describes the observed wrapper and captured
descendants. A successful earlier descendant snapshot is not proof that a wrapper
cannot later fork an unseen child before exiting. When a failure publication requires
complete owned-process termination, preserve reconciliation until the ownership
mechanism excludes that interval or independently proves termination. Regression
coverage must include fork-after-last-snapshot followed by wrapper exit, not only
wrapper-exited-before-first-snapshot. A matching RCC receipt and nonzero wrapper exit
alone cannot strengthen incomplete descendant evidence.”

Documentation improvement:
- Canonical file proposed: docs/skills/provenance-observability.md.
- Durable learning: point-in-time observed process state is weaker than complete
  lifetime ownership; failure publication must not conflate them.
- Evidence: reviewed _OwnedProcessCapture state transitions and existing common
  force_kill_process_tree_until implementation; unexecuted counterexample labeled.
- Stale/ambiguous guidance: withhold proposed claim that all cleanup boundaries are
  established; distinguish existing seven cases from the missing race coverage.
- Remaining uncertainty: barrier reproduction and appropriate supported ownership fix.

Upstream disposition: none. Local patch review concern, no external mutation target.

Lane process status: this review launched no long-lived workloads; all read-only
commands completed. Earlier lane-owned PostgreSQL test containers were stopped in
finally before the prior registry delivery. No cleanup or mutation is pending here.
