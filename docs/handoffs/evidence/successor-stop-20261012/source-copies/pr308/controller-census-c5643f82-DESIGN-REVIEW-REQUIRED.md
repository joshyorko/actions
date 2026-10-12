# Provider successor controller/census design review request

Status: SOURCE DESIGN ONLY; no implementation, native, lifecycle command, or lease write authorized by this plan. Source baseline c5643f828ba0b299c0c2a99a9755d90b39b04b3c, tree5fd6b2a52a6dffb0df8df6b5d6387e94195a0e06. The existing provider reader slice has17 new controls and282 focusedPASS; controller design is not accepted.

## Exact intended source boundaries

1. action_server/scripts/verify_dakota_rcc_acceptance.py:325 run_owned_process and:592 _supervisor_main. Extend the existing dedicated Linux subreaper transport with a typed owned identity ledger and final uncapped census. Reuse _supervisor_children, Popen-owned direct-child wait, and _reap_adopted_children. Do not add another supervisor, broad process_iter dump, or standalone process killer.
2. The same file:434 _supervisor_children, :453 _reap_adopted_children, :507 _stop_supervised_processes, :475 _proc_descendants, :493 _fallback_reap_after_error. Capture and preserve owned PID/create-time identities before signals; classify final live/zombie/absent/reused/unknown states. Enumeration errors remain incomplete, never empty-success. Reused or unknown identities are not signal authority. Retain existing ECHILD observation and distinguish observed reap events from merely absent/reused processes.
3. run_owned_process's result/error transport currently discards census on ordinary failure/timeout. Attach identical typed cleanup evidence to CompletedProcess, TimeoutExpired, and ProcessTreeCleanupError while preserving original returncode/stdout/stderr and primary exception identity. Secondary observation/cleanup errors remain separately recorded fixed classes. No successful command return may hide incomplete cleanup.
4. Current two native nodes in test_source_staging_rcc_consumer.py are in-process pytest fixtures. Use one existing supervisor invocation around exactly those two serial pytest node IDs (-n0), not two new supervisors per fixture. The outer controller's ledger and terminal ECHILD are distinct from the b0a worker and c564 provider per-object evidence. A passing pytest returncode plus supervised survivor cleanup is FAIL, not promoted PASS.
5. Global deadlines require one monotonic parent origin and explicit primary, terminal cleanup, and final watchdog-reserve endpoints. The numeric native budgets require independent admission and remain unset. Pass absolute endpoints into the existing supervisor/helper operations; each phase subtracts elapsed time instead of resetting grace. The hard outer endpoint must include any escalation, Popen reaping, readers, sampler join, final census, and evidence flush. Legacy generic helper behavior/CLI must retain compatible return contracts; no implicit change to Runtime production defaults.
6. Existing _supervisor_main collects whole output files into a JSON payload. A native-only admitted output-retention transport must retain full stdout/stderr on disk with hash/size and final namespace ownership, avoiding an unbounded second in-memory copy. Validate the task-owned output root/no-follow containment before creation. This is a design decision requiring review, not an implemented claim.
7. docs/skills/repository-operations.md will describe only accepted/tested controller behavior, its scope and hold states. No session diary or native-success language.

## Bounded source controls before adoption

- More than64 owned identity rows survive transport untruncated; deterministic sorting does not drop or coalesce different creation times.
- Live/zombie/absent/reused/unknown and creation-time/enumeration/permission failures have distinct rows and conservative completeness. Empty ledger cannot imply enumeration success.
- Unknown/reused ownership never signals another identity; use injected owned-process seams for this negative control, not unrelated real processes.
- Exactly one primary deadline remains across deliberate phase delay, process waits, tree cleanup, reader/sampler joins, fallback and final evidence. Positive controls use tiny budgets and local Python children; no RCC or provider traffic.
- Popen alone consumes direct wrapper wait status; adopted-child drains preserve actual wait events and terminal ECHILD. Include detached child, short-lived zombie, and inherited output-writer controls with finally cleanup confined to created processes.
- Primary failure/timeout and raw command output remain available when census/reaping or evidence writing also fails. Validate transport schema before acceptance and retain raw bytes before decoding.
- Exact two-node dispatch and source/hash/profile binding rejected when changed. Pure dispatch controls do not enable native flags or claim actual installed/RCC execution.

## Separate dependencies and holds

Independent review of c564 is pending. Its profile is new c564v3 NOTRUN, not a mutable937 profile. Self-cgroup binding and calibrated memory admission remain external/resource holds; they do not prevent the bounded source controls above. Lease evidence is a separate design: public4148 Inspect calls reconcileLocked, which removes provisional and stale lease records. Never use it as passive evidence of natural release. A future root/digest/lease-bound no-follow raw-file observer needs schema/identity/provenance admission against actual shipped7e588 bytes. Public tag source is not byte-equivalent proof because buildinfo says vcs.modified=true; frozen7945 and unrecovered01f remain separately identified.

No workflow dispatch, publication, lease write, native launch, RCC source/default/pin modification, or infrastructure provisioning is part of this plan. Upstream disposition: none (reconciliation appears intentional, not a confirmed upstream defect).
