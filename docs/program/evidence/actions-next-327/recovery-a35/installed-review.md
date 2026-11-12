# Installed a34 Task harness review

Read-only review of `ordinary-task-a34/qualify.py`, SHA256 `5fed7942c2433193ff8295499ca97e8e77f90061cdcf22297c7e0028361d457b`. No harness execution, RCC access, Runtime mutation, or root edits. Compared current `run_outputs/task_host.py`, `task_service.py`, `mcp/task_wire.py`, `task_adapter.py`, `foundry/bootstrap.py`, and `test_task_adapter.py` official SDK HTTP test.

## Corrections before treating PASS as qualification

1. **Shutdown can silently pass after forced kill** (`stop`, lines 83 onward; final PASS before final stop). The helper records any stopped process as successful, including SIGKILL fallback. This bypasses the host's bounded join/provider-retention evidence. Record `forced_kill`, return code and elapsed shutdown; on the normal completed/restart path require graceful exit (normally zero) and no forced kill. Always clean up on failures, but classify cleanup separately and do not overwrite the primary exception. Move final PASS assignment after successful final graceful shutdown (set `running=None` then write receipt). Preserve a failed receipt if shutdown times out rather than emitting PASS after kill. This is a harness false-positive risk, not an observed product failure.

2. **Persisted identity proof is only aggregate counts** (lines 232–241). Global +1 Run/+1 Attempt is useful but does not verify that returned Task identifies those rows. After terminal get, assert `current.result.structuredContent.version == 'actions.detached-invocation-result/v1'` (the checked current RESULT_CONTRACT), `runId == task_id`, state `completed`, one nonempty attemptId and four unique output handles. Read the synthetic SQLite rows by this exact task_id: one Run, one RunExecutionIntent, one RunTaskReceipt, one RunPin/current Attempt and one matching RunAttempt; capture workspace/snapshot digests and terminal status/fence only, not raw journals or secrets. Compare exact IDs/fences after restart and replay, in addition to existing global counts. The current service validates sealed terminal evidence, so this strengthens installed integration evidence rather than compensating for a known service bug.

3. **Task capability negotiation is not asserted** (`connect`). Retain `discovered = await session.discover()` and assert Task extension present on configured compile/execute/restart servers and absent on initial unconfigured server; use an explicit expected-task-enabled argument rather than unconditional presence. Record installed `mcp`, `mcp-types`, `actions-core` versions and module origins alongside Runtime. `NamedTaskRequest.name_param='taskId'` matches the already-tested current SDK route seam; keep it. Capture only relevant method/protocol/name headers, never Authorization, if proving exact current header negotiation.

4. **Acknowledgment timing is diagnostic only** (lines 218–224). The harness stores ack_seconds but asserts no bound or wall-clock relation to execution completion. The initial working response plus later terminal get proves a nonterminal acknowledgment, but alone cannot prove a specific response-time SLA. Keep this precise scope; optionally capture exact Run status immediately on acknowledgment and a monotonic completion observation. Do not impose a fragile `<3 seconds` assertion that includes network/session discovery and cold preparation. Add `result not in created` and `resultType == 'task'` on both creation replays. Preserve original createdAt and ttlMs on replay; do not require lastUpdatedAt equality while worker transitions are occurring.

5. **Terminal output content is not independently checked.** Current TaskService get resolves and validates all sealed output references, so 'authorized result' is supported. However, no harness assertion reads the actual generated result `slow`; describe this as genuine sealed RCC completion unless the harness additionally reads the exact authorized output through an existing public output path and asserts its value. Do not claim a model artifact-read flow from internal SQLite/filesystem evidence. Record four scoped handles without copying source/journal material. Existing `reopened == current` correctly proves stable completed projection under unchanged policy and grants; retain it.

6. **Polling budget and failure receipt.** The 120-second completion deadline is a test budget, not protocol TTL or product failure classification. Cold RCC may exceed it; on timeout preserve bounded latest Task state/process state and mark TIMEOUT, without retrying or starting another Run. The current finally writes status RUNNING on exceptions; explicitly write FAIL plus bounded exception type/stage (no credentials) while preserving the original exception. Do not treat timeout as a successful cleanup/recovery qualification.

## Checked compatible behavior

- Explicit mode detached/snapshot/inputs/idempotencyKey matches the closed invocation schema; no request-supplied worker or TTL.
- Policy schema and 50ms poll/600000ms TTL satisfy strict TaskPolicy bounds; file is absolute and chmod0600. The owned parent directories must remain free of symlinks for the strict loader.
- Task-enabled startup before compile is valid: host initial readiness probes SQL and RCC; exact compiled snapshot eligibility is checked at Task creation, not startup.
- Public offline source/exact-deployment authorization stays separate from SQL fixture writes. No Run/admission is seeded by this harness.
- Ordinary server readiness occurs after ASGI lifespan starts the configured host; Task create independently checks worker readiness.
- Current wire uses flat task creation with resultType task, and get resultType complete with nested original result. Terminal creation replay intentionally has no result. Existing assertions match this.
- Terminal reconnect/restart should not advance lifecycle clocks; full equality is appropriate here with unchanged configured poll policy.

## Exact constant clarification

The checked current `RESULT_CONTRACT` is `actions.detached-invocation-result/v1` (`run_outputs/task_service.py:45`). Pin this literal with the source SHA in the harness receipt.

## Canonical guide improvement proposal

Target `docs/skills/repository-operations.md`, in installed-consumer qualification guidance, insert:

> Installed detached Task qualification must distinguish nonterminal acknowledgment, reconnect replay, sealed completion, process restart, and graceful worker shutdown. Verify the returned Task ID against the exact persisted Run/Attempt/intent/receipt identities; aggregate row counts alone are insufficient. Assert current extension negotiation using the actual installed MCP SDK versions and preserve immutable creation time/TTL across replay. Terminal get re-resolves sealed output inventory; claiming an application result value or a public artifact-read flow additionally requires reading that value through its authorized interface. A force-killed server is cleanup evidence, not successful graceful shutdown. Set PASS only after normal shutdown succeeds; preserve timeout/failure receipts without re-admitting or recovering an uncertain Run.

Evidence: current TaskHost lifecycle/cleanup latch, TaskService identity and sealed-output validation, current Task wire creation/get projection, and the harness assertions reviewed above. No new runtime result is claimed by this review. This is a durable exact proposed delta for the sole integrator; canonical source remains untouched.

Upstream disposition: none. Findings concern this Actions-owned qualification harness; no confirmed dependency defect and no external mutation.

Full scope remains open beyond this harness: Robot, consumer/producer Task modes, interactions, legacy compatibility, effect-safe explicit recovery, and owner ChatGPT gate. This review does not claim those pass.
