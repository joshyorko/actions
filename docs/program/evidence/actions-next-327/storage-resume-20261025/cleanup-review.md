# Held failure-lifecycle review

Verdict: HOLD confirmed by deterministic real-process counterexample; no source patch applied.

Command (repository root):

```bash
source /workspace/actions-cloud/activate.sh
rcc task script -r developer/toolkit.yaml -- python /workspace/actions-cloud/package-command.py action_server run python /workspace/recovery327/review/barrier.py > /workspace/recovery327/review/barrier.log 2>&1
```

Observed: empty snapshot marked complete; wrapper exits 3 after barrier releases late child creation; capture contains zero descendants; cleanup reports execution_stopped=true and descendant_snapshot_complete=true while late child is running. The harness killed and reaped only its own descendant. It extracts the ownership class from the held patch into memory and imports the unchanged current process helper. This is a process-boundary counterexample, not installed RCC workload acceptance.

Finding: failure.patch lines 19–39 latch an early snapshot as complete and pass it after wrapper exit; _common/process.py lines 474–493 trust that supplied snapshot when the wrapper already exited. The added cleanup test deliberately waits 0.4 seconds and asserts a descendant was sampled, excluding this interleaving.

Correction constraints:

- Do not publish terminal failure from point-in-time descendant sampling alone. Unconfirmed cleanup must retain reconciliation and block provider teardown.
- Existing robot_execution.py launch uses start_new_session=True; its _cleanup scans the owned process group after exit and repeats cleanup/rescan until no live group member remains or deadline. Reuse/review this ordinary-child approach rather than adding another weaker ownership implementation.
- Preserve process identity and wrapper Popen wait ownership; errors and deadlines fail closed. Add barriers for empty-first-snapshot, observed child plus later sibling, late grandchild during cleanup, inherited output pipes, cancellation, and group access failure.
- Process-group containment does not cover deliberate setsid/setpgid escape; existing Robot code explicitly excludes escape from its trusted-code adapter contract. If stronger arbitrary-descendant guarantees are required, platform containment is a separate prerequisite; do not claim an OS sandbox or complete hostile descendant accounting.
- A conservative immediate guard can reject cleanup proof for exited wrappers with only historical snapshots, but this alone will not qualify ordinary failure completion. More frequent polling or one extra snapshot does not close the race.

Documentation improvement (proposed, not edited):

- Canonical file: docs/skills/repository-operations.md, existing cleanup-review paragraph near line6247.
- Append: "The deterministic regression must hold a wrapper before child creation, capture an empty snapshot, release creation, and wait for wrapper exit before cleanup. Assert the late child is absent or cleanup remains uncertain; a previously successful empty sample must never establish terminal-failure eligibility. A process-group implementation must state its nonescaping trusted-code boundary and recheck the owned group after wrapper exit and termination."
- Evidence: barrier.py and barrier.log, exact held patch and unchanged process helper.
- Stale/ambiguous guidance removed: replace suggestion of a possible race with this demonstrated counterexample when integrating evidence.
- Remaining uncertainty: corrected joined lifecycle, installed failure receipts, Windows/platform containment, and real RCC acceptance are not tested by this review.

Upstream disposition: none. This is an Actions-side proof-of-cleanup defect in an unapplied patch; no external issue or repository mutation performed.

## Additional publication review

Static review of failure.patch found no additional confirmed blocker in its SQL publication/ticket path. Staging happens before SQL; binding preloads immutable projection outside transactions; issued logical preparation is rechecked by the SQL-only LogicalExecution.recheck; validator checks current Attempt, fence, launch identity and exactly three sealed diagnostics. Work Item finish is failed, carries no children, and shares the transaction. LogicalPublicationGuard.publish continues to enforce final in-memory cancellation/budget checks. This is inspection evidence, not a new passing execution test.

Integration constraints: RccProcessHandle.force_kill_until (_rcc_runtime_adapter.py near line658) also relies on historical descendant snapshot completeness. Corrected ownership must reach timeout/shutdown/provider teardown, not only the new failure-receipt branch. Existing Robot process-group cleanup is POSIX-specific; unsupported-platform and process enumeration errors must retain uncertainty. RCC v18.19.3 group inheritance for the actual env-exec route was not established by this review: run a real pinned RCC child/grandchild identity probe before treating group scans as complete. A task-script or synthetic Python process probe alone does not prove env-exec behavior.

## Actual RCC group probe: blocked before workload

The `pgid-probe.py` gateway run used the current build_exec_command, pinned RCC v18.19.3, artifact sha256:651c79e99dc9f684dceb4dea55de5b6156cb626aaba717c05897adf3173ed5d3, local compiler trust, fresh HOME/tmp and --no-build. RCC rejected execution before child/grandchild launch: `materialization does not match ready record`. Artifact verification was valid, but receipt exitCode was -1 and status failed. The wrapper was reaped; no workload identities were created. Exact invocation and receipt are retained in pgid-run; pgid-gateway.log preserves the gateway failure. No readiness/trust overrides or cache mutations were attempted. Outcome is a runtime integrity failure, not an approval denial and not a process-group pass.

Additional proposed canonical guidance: "A verified artifact digest and a successful first execution do not prove reusable materialization readiness. Preserve a repeat env-exec ready-record rejection separately from artifact verification; do not bypass the integrity check or infer child containment when execution stopped before workload launch."

## Authorized serial retry: inheritance observed

After the integrator confirmed successful real executions of the same artifact and that competing runs had stopped, exactly one serial retry ran in pgid-run-serial. It passed: wrapper3602, child3650, grandchild3651 all had PGID/SID3602. RCC exited3 and retained a matching failed/exitCode3 receipt. The ordinary grandchild remained live after wrapper exit in the same group/session, then the harness killed and reaped it. This verifies group inheritance for this pinned Linux RCC invocation and demonstrates that wrapper failure/receipt alone does not establish descendant cleanup.

Exact command:

```bash
source /workspace/actions-cloud/activate.sh
rcc task script -r developer/toolkit.yaml -- python /workspace/actions-cloud/package-command.py action_server run python /workspace/recovery327/review/pgid-probe.py pgid-run-serial > /workspace/recovery327/review/pgid-serial-gateway.log 2>&1
```

Evidence SHA256: pgid-run-serial/evidence.json = dc354e33049fa414929d16b53a4a4fa86169a42c2628e5f35a386ea79306ba45. Original failed run remains preserved. Possible overlap is a limitation, not an established cause or upstream defect. Probe used python -I; production GeneratedRccExecution uses python -I -B. This probe establishes observed process inheritance, not exact production-command acceptance, installed lifecycle completion, hostile descendant containment or Windows behavior. No further reruns performed.

Additional proposed canonical guidance: "The pinned Linux RCC env-exec wrapper and ordinary Python child/grandchild can retain one launch-owned PGID/SID after wrapper failure. A matching failed RCC receipt does not imply descendants exited: a barrier probe observed the grandchild alive after wrapper exit. Recheck and clean the owned group before terminal failure publication. Keep the original failed materialization attempt and serial retry separate, and preserve interpreter flags when progressing from a process diagnostic to production acceptance."

## Independent correction review

A second deterministic counterexample exposed a race in the initial enumeration-only correction. A wrapper SIGTERM handler created an intermediate child during cleanup; after final group enumeration, a barrier let that child fork a leaf and exit before live-status checks. Cleanup incorrectly reported stopped while the leaf remained running in the owned group. Evidence: final-rescan-race.py, final-rescan-race.log, final-rescan-gngx5emt/result.json. All diagnostic children were reaped.

The subsequent correction signals the explicitly owned POSIX group with SIGKILL before enumeration, fails closed on signal/enumeration errors, and caches successful cleanup so the failure-publication finally path cannot signal again after proof and commit. Independent behavioral probes passed:

- kill-before-handler.py/log: wrapper exit -9; cleanup stopped; SIGTERM handler never ran and created no descendant marker.
- pgid-cleanup-probe.py with pgid-run-corrected: actual pinned RCC used python -I -B and the same local artifact/trust. Wrapper4732, child4788, grandchild4789 shared PGID/SID4732. RCC exited3 with failed/exitCode3 receipt, leaving the grandchild alive. Corrected cleanup returned execution_stopped=true, descendant_snapshot_complete=true, errors=[], and the grandchild was no longer live. The harness reaped its owned processes.

Static review of current success/failure/error finally paths found no further confirmed integration blocker within the documented trusted, nonescaping POSIX-process boundary. Failure publication occurs only after cleanup proof; success cleanup completes before result publication; timeout/cancel paths use the same ownership object; repeated successful cleanup returns cached proof. Unsupported non-POSIX failure/timeout cleanup remains uncertain, while existing successful behavior is retained without claiming new containment support. Tests for the complete joined lifecycle and installed release remain the integrator's separate gate.

Exact proposed durable documentation delta: "PID enumeration followed by status checks is insufficient even with a final rescan: a sampled process can fork and exit between those steps. Before proving cleanup of a launch-owned POSIX group, stop that kernel group, then enumerate and reap; signaling or enumeration failures remain uncertain. Cache a successful proof so finally/idempotent teardown never signals the old group after terminal publication. Real RCC failure receipts can coexist with a live orphan; validate cleanup separately. This trusted nonescaping-code guarantee is not a hostile-process sandbox or cross-platform qualification."

Upstream disposition remains none: demonstrated races and correction belong to Actions; the initial RCC materialization rejection has no established upstream cause.
