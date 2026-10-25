# Isolated Robot package and lifecycle slice

## Public API for integrator wiring

`robot_package_builder.py`:

```python
build_robot_package(request: RobotPackageRequest, *,
    preparation: DirectRobotPreparation | RccRobotPreparation) -> VerifiedRobotPackage
verify_robot_package(package: VerifiedRobotPackage, *,
    preparation: DirectRobotPreparation | RccRobotPreparation) -> VerifiedRobotPackage
```

Strict authoring JSON accepts only kind=robot, logicalName, files (path/content),
suitePath, suiteName, taskName, inputSchema and runtimeKind=direct|rcc. Parse via
`RobotPackageRequest.model_validate_json`. It accepts no authority/preparation.
The immutable outcome retains SourceByteSnapshot from canonical inventory rules,
the existing deterministic source archive, exact selection strings, canonical
schema bytes, tagged plan, manifest and measured digests. DirectRobotPlan has
adapter/Robot/Python/platform identities and no RCC fields. RccRobotPlan additionally
has retained package/specification/artifact/RCC-version identities. Local paths
and credentials are not serialized. Source file modes are normalized to 0600.
Output schema is closed {suite: exact name, task: exact name, status: PASS|FAIL}.

**Verified means measured evidence, not authorized admission, task discovery,
build success or execution success.** No source library is imported. The pinned
executor still resolves exact suite/task. The host must authorize, call verifier,
retain the exact outcome through its existing admission gate, and bind resulting
canonical Package/RuntimePlan refs; never admit arbitrary client outcome objects.
No fabricated CompiledPackageRevision, RCC identity, build receipt or SQL write.

`robot_lifecycle.py`:

```python
VerifiedSelectionResolver = Callable[
    [Actor, AttemptFence, ExecutionSnapshot, object], RobotSelection]
VerifiedRobotLifecycle(outputs: RunOutputService,
    resolve_selection: VerifiedSelectionResolver, journal: RobotJournalPort, *,
    lease_seconds: int, retention_seconds: int)
RobotJournalPort.launch_intent(actor: Actor, fence: AttemptFence) -> RobotLaunchIntent | None
RobotJournalPort.record_launch_intent(actor: Actor, fence: AttemptFence,
    intent: RobotLaunchIntent) -> RobotLaunchIntent
```

Journal method names match the integrator's finalized helper contract. The wrapper
implements existing RobotLifecycle methods. Resolver must load trusted admitted
selection using canonical refs; no request-side selection authority. Wrapper
compares the entire selection and canonical input bytes to execution_context,
delegates heartbeat, checks journal identity and confirmation, bounds staging,
and delegates stage to RunOutputService. Existing intent always refuses relaunch.
No admit/publish/terminal/retry, private database helpers or duplicate journal.

The integrator-owned journal must atomically validate current admitted selection,
actor and live fence with absent-to-intent CAS. A wrapper precheck is insufficient.
Both journal methods must validate live authority; existing and uncertain intent
survive restart for reconciliation. Shared registry/bootstrap/routing and terminal
publication remain integrator-owned; installed Robot acceptance is NOT_RUN.

## Evidence and limitations

Pinned RCC18.19.3 toolkit and package-local Poetry, task-local writable caches.
Command from lane worktree after sourcing `/workspace/lane-c-state/env.sh`:

```sh
rcc task script -r developer/toolkit.yaml -- python /workspace/lane-c-state/package-command.py run pytest -p no:robocorp_log_pytest tests/contract_tests/test_robot_package_builder.py tests/contract_tests/test_robot_lifecycle.py tests/contract_tests/test_robot_execution.py -q --basetemp=/workspace/lane-c-state/robot-bridge-2 --junitxml=/workspace/lane-c-state/receipts/robot-bridge-2.xml
```

Result: **58 passed, 2 skipped**. The two existing retained-RCC adapter cases had
no opt-in preparation in this run. New builder RCC coverage validates identities
only, not actual RCC execution. New lifecycle tests use port spies including
stale-at-CAS/stale-at-stage races and uncertain-ack/no-retry; one test uses real
RunOutputService admission/heartbeat/staging/cancellation with the existing store
fixture and a clearly labeled single-threaded journal spy. No installed public
Robot bridge, durable journal implementation, fresh-process restart or atomic
journal concurrency proof is asserted. Earlier actual RCC evidence remains separate.

Initial focused run:19 passed. Failed static receipts retained locally:
robot-bridge-static-1 (E721), robot-bridge-static-final (pytest fixture F811).
Corrections are confined to allocated files. All receipts are indexed separately in package-lifecycle-receipts.json. Final scoped Ruff/isort/format checks passed; package mypy passed 581 source files. Disk remaining:23 GiB.
Independent read-only review found no blocking boundary defect; requested stale
race coverage was added. Rollback: revert these isolated commits; no schema/data
migration. Integration dependencies: canonical authorized admission, trusted
selection resolver, integrator robot_journal helper and routing/publication.

## Exact proposed canonical guide delta

For `docs/skills/repository-operations.md`:

> Robot package evidence construction is separate from admission and executable
> discovery. Preserve canonical inventory/archive/schema/plan digests, and admit
> only the authorized host's verified outcome. Direct plans must not manufacture
> RCC identities. Lifecycle prechecks do not replace the durable journal's atomic
> live-fence/selection CAS. Existing or uncertain launch intent requires
> reconciliation before relaunch; installed recovery remains a separate proof.

Learning: existing canonical inventory/archive and RunOutputService authorities
support isolated Robot adapters without duplicate persistence. Evidence: dedicated
builder/lifecycle tests and public calls above. Uncertainty: canonical admission,
actual journal integration and installed recovery await integrator wiring.
Upstream disposition: none; no external defect/report asserted.
