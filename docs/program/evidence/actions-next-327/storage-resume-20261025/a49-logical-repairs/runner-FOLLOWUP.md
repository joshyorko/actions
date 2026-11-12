# Incomplete cleanup retains logical preparation

Root's SQLite run: three original cases PASS, added cleanup case FAIL. Original receipt remains `/workspace/recovery327/a49-runner-sqlite.xml` and `.log`.

Production contract is explicit: GeneratedRccExecution.execute catches RccCleanupIncomplete, marks termination uncertain, and intentionally skips release_preparation. LogicalPreparationOwner.settle refuses transferred/unreleased results; LogicalExecution.close returns false while any preparation remains issued. The initial test's unconditional release/close expectation was incorrect. Do not relax that guard.

`followup.patch` against root's currently applied test captures actual preparation owner/result through existing method wrappers. The cleanup case asserts exactly that preparation remains issued, its preparation thread is stopped, close(0) returns false, and the resource remains held afterward. Existing RUNNING/reconciliation and no-extra-spawn assertions stay intact. Test teardown confirms its entirely synthetic Process.wait(0)==0, explicitly changes only the fake owner's simulated termination confirmation, checks successful fake cleanup, and calls the existing exact owner/result release_preparation API. No direct registry clearing, production cancellation bypass, real process signaling or provider release under unconfirmed state occurs.

Validation: static AST/compile PASS; follow-up tests NOT RUN by this lane. Root should rerun the same four SQLite cases, then configured provider cases serially. No services started. The initial test failure remains evidence of the corrected fixture assumption, not a product cleanup failure.

Canonical documentation improvement (replace initial proposal's unconditional release language): “Synthetic lifecycle tests must distinguish confirmed termination from uncertain cleanup. On RccCleanupIncomplete, assert the exact transferred logical preparation remains held and close returns false, preventing provider teardown. Only after the owning process controller confirms termination may the exact owner/result release API run. Test teardown may explicitly resolve a synthetic owner; this is not evidence of real subprocess cleanup.”

Upstream disposition: none. Owned test expectation correction, no external mutation.
