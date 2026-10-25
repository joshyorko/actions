# Independent shutdown metadata review

CLEAR for source checkpoint, exact hashes:
- _server.py: 6342a86527834ed349f9602915d2dcbd19d23f9df92a5dec1c233551c5fd1650
- test_shutdown_child_metadata_327.py: d20a877ba00bc71476fc0dd2e200a14bc6b327abeed6eace1f641f9b03656690

Read-only inspection; no services, signals, tests or product edits by reviewer. These match helper hashes.json. Helper reports four actual-lifespan deterministic tests passed; root reports configured lint/typecheck PASS650files. Original RED and installed lifecycle HOLD remain preserved; source clearance is not installed cleanup acceptance.

The change bounds only child.name() metadata lookup. NoSuchProcess skips that enumerated object without invoking the numeric-PID kill helper, so vanished-child logging cannot abort cleanup of later children or initiate a new numeric-PID lookup. Unexpected metadata exceptions are logged and that child is skipped; the loop continues. This intentionally cannot prove that an uninspectable child was terminated. Existing helper invocation, process containment and descendant enumeration are unchanged.

The tests enter the real asynchronous lifespan and inject two enumerated children. Both disappearance and unexpected metadata failure leave the later child processed exactly once, with no kill attempt for the failed lookup. Crossing those cases with watcher shutdown failure proves the deferred watcher error remains observable after remaining child cleanup. They do not signal real children and make no claim about PID reuse after a successful name lookup, late forks, escaped process groups or stronger process identity fencing.

No new blanket exception swallowing covers watcher shutdown or helper invocation. The existing watcher error is still raised when no earlier active exception exists. No new blocking calls or retry loops are added. The correction is appropriately narrow for the observed metadata race.

Next gate: clean a52 checkpoint and installed lifespan regression/fixture qualification when resource admission permits. Do not promote the prior a51 lifecycle HOLD or Node process-close issue into a pass based on this patch.

Canonical documentation proposal for provenance-observability: “Best-effort shutdown diagnostics must not prevent cleanup of later enumerated children. Treat vanished-process metadata as a skip without reacquiring its PID; log other metadata failures and preserve deferred shutdown errors. Record that an inspection failure is not termination proof, and do not infer stronger PID/descendant fencing from a logging-race correction.”

Documentation improvement receipt: exact delta grounded in the narrow source guard and four actual-lifespan regression cases; root owns canonical integration. Upstream disposition: none; local diagnostic lifecycle defect, no external defect established or external issue/mutation authorized or performed.
