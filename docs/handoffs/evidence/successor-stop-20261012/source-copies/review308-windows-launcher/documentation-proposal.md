Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md
- Exact addition, after the launcher fixture paragraph ending “earlier cleanup failure whose typed diagnostic was discarded.”:

Keep original-child teardown in `finally` around descendant teardown. An
unreadable or changed descendant birth cannot authorize a signal, and a failure
in that check must still attempt original-child teardown and close its pipes.
Test this failure path separately from successful descendant cleanup.

- Durable learning captured: ownership rejection and original Popen disposal are separate responsibilities. A failed descendant identity lookup must fail closed without bypassing original-child cleanup.
- Evidence:16 exact-AST no-signal models of immutable d358 capture/finally; verified/snapshot failures and changed root rejected, reused/missing/unreadable descendants receive no kill, original Popen wait and both closes run even when descendant lookup raises PermissionError. Fresh Poetry launcher1RED→33GREEN retains strict acceptance before emergency teardown.
- Stale or ambiguous guidance removed: the new12canonical lines already remove the unsupported childPID==launcherPID assumption. This proposal makes error isolation during the new descendant teardown explicit.
- Remaining uncertainty: fresh corrected Windows CI pending; supported CPython redirector source establishes behavior but does not byte-attribute the CI executable. HistoricalmacOS cause remains UNKNOWN; native/controller/lease qualification still HOLD.
Upstream disposition: none.
