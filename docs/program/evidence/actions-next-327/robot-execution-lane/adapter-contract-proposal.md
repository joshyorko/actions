# Robot execution adapter boundary (proposal, not implementation)

Source inspected: `da928b69e0558917c3e88af9297ddfd3bec818e8`.

The first test slice adds genuine Robot Framework 7.4.2 processes, literal input
checks, real XML/status checks, failure diagnostics, and artifact retention after
source removal. Its RCC variant invokes the existing legacy Robot API and real
Josh RCC 18.19.3. It does not create immutable Robot Packages or qualify canonical
RunPin/RunAttempt execution. Reopening a SQLite connection is not an independent
worker restart or uncertain-effect reconciliation test.

## Concrete next slice, pending integrator contract

Proposed isolated implementation: `action_server/src/actions/server/foundry/robot_execution.py`.
Proposed independent tests: `action_server/tests/contract_tests/test_robot_execution.py`.
These paths are proposals only; no production module is included in this slice.

The adapter needs a registry-selected typed Robot capability and exact immutable
Runtime Plan, retained source bytes, the existing actor/snapshot/AttemptFence,
trusted host runner preparation, bounded execution root, and cancellation input.
It must return existing staged output references and execution evidence through
RunOutputService; it must not admit Runs, create tables, choose a different plan,
reserve arbitrary Work Items, install dependencies, or publish unfenced results.

Integrator prerequisite: version-dispatched portable Robot Package/plan admission
and exact capability/schema projection in the existing registry. The current
`deployments/package_revision_compiler.py` verifier requires kind `action`,
`runtimeKind=rcc`, and its RCC contract. The multi-Action bundle can select exact
legacy compilations; that alone does not make a Robot compilation admissible.
`foundry/execution_profiles.py` also requires the RCC kind. Do not fabricate RCC
fields for a direct runner or weaken the legacy verifier. Integrator owns those
shared value/registry/profile changes, artifact identities and journal contract.

A direct plan must pin trusted adapter version, Robot version, Python/platform
compatibility, exact suite/task identity and schemas, with no host paths or
RCC-only preparation fields. An RCC Robot plan must use actual retained RCC
preparation, not infer compatibility from a developer toolchain. Robot task
selection needs exact execution-result verification because CLI name matching
is not a capability identity. Package-controlled libraries execute code: inspect
in a bounded child only after trusted-developer admission, never in the registry
coordinator. No claim of an OS security sandbox.

Reuse existing pre-launch journal, live lease/epoch checks, heartbeat, bounded
stdout/stderr, process cleanup and explicit uncertain-launch reconciliation.
The integrator must decide the common journal discriminator before implementation;
copying GeneratedRccExecution into a second scheduler is not an acceptable shortcut.
Work Items retain SDK0.5.0a2 `SQLReviewQueue.reserve_item_fenced(item_id, owner_id,
lease_seconds=...)` and separate WorkItem/Attempt fences. No SDK database writes
or replacement queue. Retry/dead-letter, cancellation, recovery, and output
publication remain the existing authority's decisions. Do not claim exactly-once
external effects.

Required future acceptance: execute both plans from retained source with original
mutable directory absent; distinct capabilities and schemas; reject unknown
adapter/plan and changed retained bytes; competing/stale fences; cancellation;
crash after launch intent; explicit reconciliation without blind rerun; durable
stdout/XML/failure artifacts; independent process restart. Existing direct and
legacy API cases do not satisfy these gates.

## Exact canonical guide delta for the integrator

Append immediately after the paragraph beginning “The pinned development Robot
Framework runner can be qualified” in `docs/skills/repository-operations.md`:

> `test_robot_real_execution.py` separates genuine development Robot execution
> from opt-in legacy Robot API/RCC execution. Both inspect Robot 7.4.2 XML for the
> exact selected task and status, preserve failure diagnostics, and verify retained
> payloads after removing the mutable source. The direct cases use real subprocesses
> and the production artifact collector; the RCC cases use the real pinned binary
> and reopen the legacy Run database. These cases do not qualify immutable Robot
> Package admission, canonical RunAttempt leases, independent worker restart, Task
> protocol, or uncertain-effect recovery. Run RCC cases only with
> `ACTIONS_ROBOT_REAL_RCC=1`, an absolute `ACTIONS_RUNTIME_RCC_BINARY` pointing to
> Josh RCC18.19.3, and an owned writable `ROBOTS_HOME`; otherwise they are explicitly
> skipped. Disable optional HTML reports/tracing while retaining stdout and XML.

Evidence: named test assertions plus the first-slice receipt. This replaces no
existing claim; it makes the established direct-runner boundary executable.
Uncertainty: immutable Robot plan and common worker integration remain pending.
Upstream disposition: none; no confirmed upstream defect and no external report.

Additional exact guide sentence from independent review:

> Robot fixtures comparing exact UTF-8 bytes must encode explicitly and use
> `Create Binary File`; `OperatingSystem.Create File` converts LF to CRLF on
> Windows. Stream child stdout to the retained receipt while execution runs so
> a timeout does not discard the captured diagnostics.

Evidence: installed locked Robot7.4.2 OperatingSystem implementation and the
reviewed test fixture. Windows execution remains unverified.

## Installed Action handoff checked

PR328 was re-fetched at `5b16289da3d0f45f3d2534a4abf29fb1e3a9463e`.
Its diff from this test slice's base is documentation/evidence only.
Read `recovery-a38/managed-installed-consumer/{README.md,qualify.py,receipt.json}`.
That handoff proves real installed a38 generated Action execution, managed complete
and SAME-datadir completion replay, against its recorded f332a828 source/wheel.
It does not qualify Robot or retry, and this lane does not repeat that setup.

Precise ordinary bridge: authoring currently compiles generated Action backend
files; `capability_invoke(mode='generic', snapshot=..., claim=...)` then executes
that exact admitted Action and managed `items.complete` verifies its canonical
terminal outputs. The Robot addition belongs before registry admission and at
trusted worker adapter selection, not in `items.complete` and not via the legacy
`/api/robots/run` path. Completion's four-output Action inventory also needs
integrator-owned versioned projection for Robot XML/artifacts; do not rename
Robot XML to an Action JSON result to satisfy it. The handoff's ordinary bootstrap
has no retry `worker_for`; Robot tests must not inject one to claim product retry.
