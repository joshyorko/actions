# Confirmed Robot claimed-input admission gap

Production inspected read-only in isolated claimed-robot-source. Only new test source test_robot_claimed_input_bounds_327.py added. Active checkout unchanged.

Reproduction:2 SQLite characterization tests passed,2 PostgreSQL cases deselected,1 harmless assertion-rewrite warning in1.20s. A passing characterization demonstrates the defect; it is NOT desired acceptance behavior and should become pre-admission rejection assertions with the fix. Explicit isolated module-origin assertions run before SQLite. No Robot adapter, RCC or provider materialization, PostgreSQL, external mutation or production edit.

Observed for both schema-valid {'value': string} inputs:
- ASCII70000 chars: generic UTF8 JSON70013bytes, Robot compact JSON70012bytes.
- Euro12000 chars: generic UTF8 JSON36013bytes, Robot ASCII-escaped compact JSON72012bytes.

Generic policy default max_input_bytes262144 allows enqueue. Queue claim and GenericWorkItemExecution.dispatch create a new Run/Attempt. PinnedRobotRunner then prepares RobotSelection and fails with 'bounded immutable JSON bytes required' before adapter construction; persisted launch staysNone. This leaves admitted/claimed work that cannot enter execution. The existing fixture schema allows strings without maxLength; this is not a schema-invalid request.

## Smallest boundary correction (root owns)

Use existing GenericWorkItemExecution._inputs, shared by enqueue, standalone dispatch and retained-envelope revalidation. Keep its policy-specific generic byte check and schema validation. For a retained Robot package, additionally validate the exact serialized carrier consumed by RobotSelection: json.dumps(inputs, sort_keys=True, separators=(',', ':'), allow_nan=False).encode(), including current ensure_ascii=True semantics, against65536bytes.

Select Robot from existing SQL-only robot_projection_if_present(db,snapshot), or already trusted equivalent retained projection, never claimed journal tags. That helper reads validated immutable SQL metadata without provider opens. Avoid importing/executing provider code or loading source blobs inside the admission SQL transaction. Factor a pure encoder/bound helper shared with RobotSelection if root judges useful, preventing future size/escaping drift. Do not merely lower default policy to65536: the Unicode case remains oversized after Robot escaping. Do not modify default manifest or WorkItemDeclaration/policy defaults: reject impossible requests at admission while preserving historical legacy-none revision preimages and broader generated backend limits.

Regression acceptance should require rejection before new queue item/FoundryRequest/Run/Attempt rows are written, verify both Unicode and ASCII bounds, permit exact-bound inputs, preserve narrower explicit policy bounds, and prove retained Robot selection makes no provider IO under SQL. Existing queued oversized inputs must fail closed when revalidated rather than create a Run. Optional standalone Robot inputs need the same check. This read-only lane did not implement these fixes.

## Reproduction command

    source /workspace/actions-cloud/activate.sh
    rcc task script -r developer/toolkit.yaml -- python /workspace/actions-cloud/package-command.py action_server run python -I /workspace/recovery327/robot-installed/input-bounds/run-reproduction.py

Evidence reproduction.xml/log; wrapper source records isolated path/assertions. --noconftest excludes unrelated RCC bootstrap; required SQL fixture plugin is explicit, and PostgreSQL is deselected.

## Exact canonical proposal (root applies)

Target docs/skills/repository-operations.md, capability input admission:

“Validate executor-specific input limits before enqueue or Run admission, using the exact executor carrier encoding as well as the Deployment policy limit. UTF8 JSON size and ASCII-escaped JSON size differ; a Unicode payload under64KiB can exceed Robot's64KiB carrier. Select executor kind from validated retained SQL metadata without provider IO inside admission transactions. Preserve immutable package/default policy identity; do not repair an execution-bound mismatch by changing historical manifests. Test rejection leaves no new queue, request, Run or Attempt records.”

Documentation-improvement receipt: two observed post-admission failures with byte sizes above support this delta. Remaining work is root's production correction and acceptance/installed qualification; no safe rejection claim made yet.

Upstream disposition:none. Confirmed owned Actions admission/executor integration gap, no upstream defect or external report. External reporting draft-only/no authorized target.

## Pre-admission acceptance RED

At root request, characterization source was preserved as characterization-test.py and new test source converted to desired behavior. The isolated pre-patch run produced4 failures (DID NOT RAISE) and2 passes,6 PostgreSQL cases deselected in1.84s. admission-red.xml/log preserve this result. Oversized ASCII/Unicode must fail both enqueue and optional standalone dispatch without adding FencedWorkItem, FoundryRequest, Run or RunAttempt rows. Exact65536-byte ASCII carriers successfully enqueue/claim or standalone-admit and independently prepare RobotSelection; these boundary cases passed even before the fix. No adapter executes in this gate.

Root was notified RED ready before production correction. Root owns pure exact-encoder reuse and SQL-only Robot kind selection; no production change made by this lane. Existing exact canonical guide proposal remains applicable, now backed by failing pre-admission acceptance and passing exact-boundary tests. Upstream disposition remains none.

## Root correction GREEN and non-Robot regression

After root's pure encode_robot_inputs/shared-caller/Generic._inputs correction, isolated bounds plus existing generic_work_item_execution selection completed25 passed,3 skipped,27 deselected in6.95s (admission-green.xml/log). All6 bounds cases pass: oversized ASCII/Unicode enqueue and optional no-claim dispatch reject without new queue/request/Run/Attempt rows; exact65536-byte payloads admit and independently prepare in both paths. Existing generated/non-Robot generic cases pass. Three skips are explicit genuine-RCC opt-in tests (ACTIONS_GENERIC_REAL_RCC absent);27 PostgreSQL cases deselected. No RCC/PG execution occurred.

Static authorized5 files: robot_execution.py, robot_execution_selection.py, robot_receipts.py, generic_work_item_execution.py, robot_work_item_authority.py. Ruff format/isort/lint all exit0; isolated mypy0 errors in5 target files (1279 resolved modules). Only formatter/import-order edits by this lane, no semantic change. static/source-sha256.json fingerprints exact final bytes; static/results.json/tool logs record gates. Mypy verbose evidence confirms all5 target paths isolated and contains no active Runtime/Core/Work Items source paths. Frozen tests/active checkout untouched except own acceptance test in isolated source.

Standalone service (distinct from Generic optional no-claim dispatch) is a separate root/cleanup-lane correction; this result does not claim its pending gate. No new production permission/grant or package revision change is part of this lane.

Canonical guide proposal above now has red-to-green evidence. Additional exact sentence for the same section: “Use one pure encoder for admission and execution carriers; retain byte-equivalence tests for non-ASCII expansion and exact-size accepted payloads, and separately qualify Generic optional no-claim dispatch versus the standalone service.”

Upstream disposition remains none; owned integration fix, no external report or mutation.
