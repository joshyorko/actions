# Ordinary none app + model qualification and incremental join

Patch: none-model-join.patch, SHA256 4fb3f9e5f445e31cf4c4fc2bdf98207f62d97a62a476c20b01cda0235501f74f.
Dependencies in order: frozen generic-bound-app patch ab3767521b2c0f9815774f4865a826b4f00198b25214b0b793dde5b32161753c and sibling model-descriptors-aggregate.patch 4e48f2d0302e6b92c27f9ce2c26aa5cae25e1e7220c8020be419df46ff9f54ff. This is an incremental five-file patch against those dependencies; their contents are not duplicated. All ten frozen app patch file hashes remain unchanged. No shared integration edits, branches, commits, pushes, installs or external writes.

## Implemented

GenericCanvasExecution accepts ordinary none only for standalone typed input, no Work Item policy and no ClaimRef. It uses the existing StandaloneActionExecution, common Run admission/Attempt/journal/output service and configured trusted worker/RCC runner. Immutable Package registry is explicit. Model discovery obtains exact active binding/default plan/schema through the canonical repository, exposes inputMode none/inputQueue null/standaloneAllowed true, and rechecks live execution authority. Existing reviewed invocation and generic queue-policy paths remain available. No default grants, fake optional policy, artificial input item, second database or scheduler.

## Evidence

- Final ordinary-none source suite:32 passed, zero skips,66.70s (model-final.log). Real SQLite/PostgreSQL common SQL × existing DuckDB/PostgreSQL fixture providers. Covers schema-derived descriptor invocation, no new Work Item or grants, replay, Run/Attempt/fence/journal corruption, denied app audience/claims, revoked execute grants and uncertain-launch no retry.
- Existing generic model/descriptor regression plus initial none suite:93 passed,2 actual-opt-in cases deselected,167.72s (model-regression.log). This preceded the final explicit Package registry type guard and added revoked-grant/uncertain-launch cases; those final changes are covered by the32-case final suite and actual execution below.
- Final exact execution module bytes actual RCC gate:2 passed,2 redundant data-provider variants deselected,zero skips,95.10s (actual-rcc-qualified.log). SQLite and PostgreSQL each compile an ordinary echo package, run an app submission and a separate headless model invocation, assert four sealed outputs/succeeded Attempt/no added Work Items and terminal replay without relaunch. Four actual executions returned hello/headless/hello/headless. Original RCC receipts, inputs and action results are retained under real-execution-receipts/ with hashes/index. No synthetic completion runner in this gate.
- Earlier actual app-only run executed successfully but teardown errored because cleanup-evidence env was omitted; not claimed as gate pass. Corrected runs completed cleanup. Source-only initial red iteration was a malformed QueueRef test fixture, corrected before final validation.
- Source module paths/hashes, prepared receipt and binary hashes:actual-module-identity.json. Execution modules were frozen for actual-rcc-qualified. The discovery local-variable type rename is separately source-qualified; it is not exercised by that actual RCC fixture.
- Mypy two source files, changed-file Ruff and Isort passed. Patch forward application against saved dependency baselines and reverse check against scratch pass with whitespace=error. Current root cannot apply until sibling descriptor dependency introduces invocation_discovery.py.

## Exact environment and release

Prepared receipt:/workspace/actions-recovery-327/installed-a25/compiler/prepared.json. RCC18.19.3 and immutable artifact digest are recorded in actual-module-identity.json and execution receipts. Source overlays use prepared package Python; this is not installed-consumer evidence. Scratch boot.py hash dac39c8097c0d130dc1c88144e375e330d2b7650e22586592569dfa747c7b268 equals fdc38d7090c4ac470171c499e77eab636fd452e6 and includes compiler cache creation. The actual fixture explicitly pre-creates its execution root and does not exercise CLI boot.

Exclusive installed-a25/compiler/robocorp cache ownership is RELEASED:two successful recognized-view cleanup receipts, no active view processes, immutable artifacts and prepared receipt preserved (cache-release.json). Owned bounded PostgreSQL container actions327-none-model-pg was stopped after final source tests. Parent may reuse the released RCC home.

## Remaining qualification

Root must integrate dependencies and this join into Runtime composition/version/build, then test installed official MCP client/host app and model flows, real browser screenshots, process restart/reopen with stable trusted worker identity and authenticated ChatGPT owner gate. Actual tests here call the source app/model ports with synthetic authentication/data fixtures; they are not a full SDK-host/browser end-to-end proof. Actual in-flight cancellation remains unqualified; app reports request only. Required-input/consumer app forms and failed-process reconciliation remain open. No claim of READY FOR DAKOTA.

Documentation improvement:
- Canonical file proposed:docs/skills/work-items.md; exact replacements/addition in guide-delta.md.
- Durable learning:shared ordinary none authority for model/app; claim rejection; real source RCC versus installed-host qualification; mandatory unique owned cleanup evidence directory.
- Evidence:32 final source tests,93 initial regression tests,2 final actual database cases/four executions, exact identities and cleanup receipts.
- Stale/ambiguous guidance removed:pending explicit-policy-only model descriptor and none-exclusion statements.
- Remaining uncertainty:installed/browser/restart/ChatGPT, input-linked app interactions and failure reconciliation as above.

Upstream disposition:none. Findings were local fixture/typing issues; no upstream investigation or external action.
