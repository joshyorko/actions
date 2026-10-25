# Isolated Robot adapter slice

Approved exclusive production path: `action_server/src/actions/server/foundry/robot_execution.py`.
Contract tests: `action_server/tests/contract_tests/test_robot_execution.py`.
Base source remains da928b69; the existing branch also contains test/evidence-only
commits75fe3ca7,3814b858,012a71c5. No shared registry/schema/SQL/routing/auth/version
or canonical-guide edits. This slice follows the integrator-approved lifecycle port.

## Implemented boundary

`RobotExecution(execution_root, preparation).execute(actor, fence, *, selection,
source_archive, lifecycle, cancelled, timeout_seconds)` executes trusted retained
Robot source. Frozen values bind the existing ExecutionSnapshot, exact suite path,
suite/task name, source archive digest, canonical input/output schema bytes,
input bytes, adapter1/Robot7.4.2/Python3.12/Linux-x86_64 contract, and direct/RCC
plan discrimination. Direct preparation supplies a trusted interpreter. RCC
preparation requires the existing PreparedRccEnvironment and exact artifact,
specification and package.yaml identities. It cannot fall back to direct execution.

The host port must implement:

- `check_live(actor,fence,selection) -> ExecutionSnapshot`: authorize actor and
  exact live Attempt/WorkItem fences, and bind **all** selection/schema/source/plan
  fields to canonical retained admission; returning the supplied snapshot alone
  is not a production implementation.
- `heartbeat(actor,fence,selection)`: renew only that current admitted execution.
- `launch_intent(actor,fence)` and `record_launch_intent(actor,fence,intent)`:
  the latter atomically CASes absent to exact intent under live authority, rejects
  every existing launch, and returns the committed intent. Read-after-write must
  match before spawning. Lost acknowledgement is not permission to launch/retry.
- `stage_output(actor,fence,*,name,media_type,content) -> OutputRef`: bounded staging
  with current authority, never publication. Returned scope must match the Run
  and Workspace. Partial staged outputs on later failure remain uncommitted.

`actions.robot-dispatch/v1` appears only in adapter DTOs/tests, not a persisted
journal schema or new registry. The adapter does not admit/claim/terminalize Runs,
write SQL, reserve queues, retry, or publish. The integrator owns persistence,
registry projection, host wiring, terminal publication and reconciliation.

Inputs are delivered through an owned JSON file exposed to the Robot task as
`${INPUT_FILE}`. The output schema currently describes the typed execution summary
`{suite,task,status}`, not business JSON or a fabricated Action result. Staged
outputs are `robot-output.xml` (application/xml), bounded stdout/stderr, and the
verified actual RCC receipt for RCC plans. Arbitrary business artifact projection
is not implemented in this slice. The exact task object is selected from Robot's
model before execution; CLI wildcard/normalized matching is not used. Actual XML
must contain exactly that leaf suite/task, version, PASS/FAIL and matching exit
status. RCC receipt exitCode must be an integer (not bool) and match completion.
Retained source inventory bytes/modes are rechecked before staging.

Execution checks cancellation, deadline and live authority while draining both
pipes and heartbeating. Both logs retain at most256KiB with observed/truncated
counts. XML/receipt reads are bounded1MiB, nonblocking, regular single-link files;
links/FIFOs are not trusted evidence. Process cleanup begins immediately after
launch, includes initialization failures, and uses existing process-tree cleanup
plus a Linux process-group sweep to catch ordinary orphaned children. Normal
process-disappearance races do not invalidate completion. Unknown cleanup prevents
staging and retains the directory. Zombie descendants are reported separately by
the existing cleanup value; execution_stopped does not claim they were reaped.

This is Linux x86_64 trusted-developer execution, not an OS sandbox or protection
against deliberately escaping sessions/filesystem mutation by the same OS user.
Unsupported host/platform/version refuses. Workload-created disk use is not an OS
quota; the adapter bounds its diagnostics/reads/staging. Host-owned execution
directories are retained on success and failure for explicit cleanup/reconciliation.

## Verification and honest boundaries

- Final combined Robot gate: **216 passed,1 skipped**,38.51s;217 cases in attached
  `adapter-tests.xml`. Includes32 adapter cases and6 first-slice genuine execution
  cases, actual Robot/RCC success/failure, literal inputs, exact task selection,
  changed source, cancellation/timeout, stale fence, uncertain launch/replay,
  truncation, orphan child cleanup, FIFO refusal and selector/exit races.
- Only the host lifecycle port is a test spy. No fake process/RCC/queue/database
  stands in for the actual execution. Cleanup-failure, XML-corruption and race
  cases deliberately instrument those specific failure boundaries.
- One existing regression case remains skipped: `test_pinned_rcc_executes_selected_task_with_declared_inputs`, requiring its separate ACTIONS_ROBOT_INPUT_RCC opt-in.
  It is not counted as passing; new RCC cases executed with their own opt-ins.
- Full configured package typecheck: **PASS**,577 source files, after final source
  changes. Scoped Ruff/format/isort and whitespace checks pass.
- Full configured package lint: **FAIL**, untouched
  `tests/contract_tests/test_knowledge_input_mapping.py` import sorting. Initial
  own test import sorting was corrected; the shared file remains integrator-owned.
- Full package test attempt: **INTERRUPTED** at the180s budget, exit124, at roughly
  1% with no final pytest count/JUnit file. Do not infer aggregate success. Stdout
  and exit receipt retained. RCC's three reported migrated PIDs were inspected:
  all were zombies parented to PID1, none executing. No kill/reap success invented.
- Independent source review found and then cleared FIFO reads, selector cleanup,
  orphan group handling, exit race and cross-platform test issues. Final source
  inventory recheck was added afterward and exercised by the final combined gate.

Raw receipts remain `/workspace/lane-c-state/receipts/adapter-*`; each rerun uses
its own basetemp and XML so no prior failure/skip/interruption is overwritten.
`adapter-receipts.json` inventories their SHA256/size and exact source file hashes.
Initial red import failure is retained. Intermediate failures include access-time
comparison in evidence reads, missing ldconfig in sanitized RCC PATH, an honest
10s cold-materialization timeout (RCC acceptance now requests60s within unchanged
production1..600s bounds), and initial focused mypy/import-format errors. These are
not relabeled passes. Corrected RCC PATH follows existing `/usr/sbin:/sbin` plus
os.defpath so host library detection works without inheriting ambient secrets.

Pinned preparation used Josh RCC18.19.3 and a fresh local artifact:
`sha256:fa8cef1a89d69e62f50172110e19531cf72b5048251ed59ee2b70695000c19a6`;
specification `sha256:208901b02626fb7f3d846f491848f2fcf8b3a4a031b642e754c152a51e426dc0`.
Exact synthetic manifest is adjacent. This Robot artifact is unrelated to the
missing historical a38 consumer artifact23094fc and must never substitute for it.
Disk: about23GiB free after this gate; optional pytest tracing disabled.

## Reproduction

Use Doctor -> Bootstrap -> ToolkitTest and package-local Poetry through the
existing RCC task-script gateway. Prepare the adjacent Robot manifest with actual
`rcc env publish --environment ... --provider local --json` in an owned writable
ROBOCORP_HOME; serialize actual returned identities with
PreparedRccEnvironment.to_receipt_bytes. Put prepared.json next to package.yaml.
No hand-generated RCC result or local path in the portable manifest.

From the prepared toolchain in `action_server/`:

```sh
ACTIONS_ROBOT_PREPARED_RCC_RECEIPT=/owned/compiler/prepared.json ACTIONS_RUNTIME_RCC_BINARY=/verified/rcc-18.19.3 ACTIONS_ROBOT_REAL_RCC=1 ROBOTS_HOME=/owned/robots-home poetry run pytest -p no:robocorp_log_pytest tests/contract_tests/test_robot_execution.py tests/action_server_tests/test_robot_real_execution.py tests/action_server_tests/test_robot_artifacts.py tests/action_server_tests/test_robot_run_artifacts.py tests/action_server_tests/test_robot_run_inputs.py tests/action_server_tests/test_api_robots.py -q --basetemp=/owned/fresh-tests --junitxml=/owned/receipts/robot.xml
poetry run invoke typecheck
poetry run invoke lint
```

Actual local outer dispatch is the same `rcc task script -r developer/toolkit.yaml
-- python /workspace/lane-c-state/package-command.py ...` wrapper from first-slice.md.
The full package attempt used `timeout --signal=INT --kill-after=15s 180s` around
that gateway with `poetry run pytest tests -q`, optional tracing disabled and its
own basetemp/XML target. Preserve interruption evidence; do not treat missing XML
as zero failures.

## Integration, rollback and remaining work

Cherry-pick this incremental adapter commit after the earlier first slice; it
adds only the approved two production/test paths and lane evidence. No migration
or dependency change. Rollback is revert of this isolated commit; it never
registers itself or changes ordinary startup. Apply the canonical guide delta
below separately. Canonical Package/Deployment admission, host lifecycle port,
output schema/projection and installed worker routing remain integration tasks.
No installed Robot bridge, managed Robot completion/retry, Task, independent
worker restart, durable host reconciliation, or exactly-once effects claim.

## Exact canonical-guide delta

Append after the Robot runner qualification paragraph in
`docs/skills/repository-operations.md`:

> `foundry.robot_execution.RobotExecution` is an isolated trusted-host adapter,
> currently qualified only for Linux x86_64, Robot7.4.2 and Python3.12. It selects
> an exact task model from retained source and stages real XML/logs through an
> injected host port. The host must bind the complete plan/schema/source selection
> to live canonical fences and atomically record/re-read launch intent; an existing
> or uncertain launch requires reconciliation. Direct and retained-RCC preparation
> never substitute for each other. This adapter does not admit, terminalize, retry
> or publish Runs, and is not yet ordinary installed Robot wiring. Nonblocking
> regular-file evidence reads and cleanup guarded immediately after Popen avoid
> FIFO and setup-failure hangs. Linux group cleanup covers ordinary orphaned
> descendants; deliberate session escape is outside the trusted-code contract.
> Unknown cleanup retains resources and blocks staging. Retain XML/stdout plus
> failed, skipped and interrupted gate receipts; a timed-out full suite is not a
> passing gate. Canonical host, registry and installed qualification remain separate.

Documentation learning is backed by code, final genuine execution tests and
independent review. No existing guide claim is removed or silently upgraded.
Remaining uncertainty: canonical integration, other platforms and complete package
gate. Upstream disposition: none; no confirmed dependency defect or external report.

Pre-delivery PR328 re-fetch: `f5a019183da69a5017aa69db4ce2a6f8dc3ae276`.
Existing Actor/AttemptFence/ExecutionSnapshot/OutputRef, RCC command/receipt and
process-cleanup helpers are unchanged from this lane's base. Shared compiler and
generated RCC execution gained Knowledge integration; the source-extraction helper
used here is unchanged. This is inspection, not qualification of the combined head.
The integrator must run combined-source acceptance after cherry-pick. Full-suite
interruption and remaining package lint failure logs are attached verbatim.
