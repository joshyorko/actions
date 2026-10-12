Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md
- Exact addition, after the new async cancellation admission paragraph ending “assertion.”:

Exercise both Future completion orderings. An already completed Future invokes
a newly added done callback inline; attach this callback outside
`RunsState.semaphore`, because identity cleanup acquires that non-reentrant
semaphore itself.

- Durable learning captured: immediate Future completion is a lock-order boundary, not merely an asynchronous cleanup case. Identity-safe retirement needs both pending and already-completed Future controls.
- Evidence: immutable f949 run_in_thread assigns Future then registers cleanup outside the semaphore; discard_run_runtime_info acquires it once and compares exact identity. Genuine immediate Future test and held Future lifecycle controls pass; caller audit shows generatedAPI invokes runner outside stateSemaphore. Existing create_run_runtime_info locking and scoped rejection remain byte/AST unchanged.
- Stale or ambiguous guidance removed: the new14canonical lines correctly require early registration and owner-checked cleanup. This addition makes inline completion/locking implications explicit; no new common Runner branch is inferred.
- Remaining uncertainty: actual hosted frozen integration result for this newhead pending. Local controls use real persisted Runs/state/API/Future but no genuine Action/native processes. HistoricalmacOS cause remains UNKNOWN; native/controller/lease admission stays HOLD.
Upstream disposition: none.
