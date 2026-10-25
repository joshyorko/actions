# Installed Robot acceptance: blocked on canonical host contract

Inspected PR328 head `162534237f3624942a1ce8e3e4b246046d98ddb8`.
Status: **NOT_RUN** for every installed Robot case below. This is a contract
handoff, not an executable acceptance harness or installed bridge claim.
`git grep 'robot-dispatch\|RobotExecution\|RobotSelection' FETCH_HEAD -- action_server/src`
returned no matches. `foundry/generic_execution_port.py` accepts immutable generic
snapshot/claim or snapshot/inputs/idempotencyKey requests; its pinned runner calls
GeneratedRccExecution. `foundry/package_registry.py` admits compiler products,
not a client-provided RobotSelection. The isolated adapter cannot supply admission.

## Required integrator interface

Return exact installed CLI/MCP names, request/response schemas and fixture setup
commands for these operations (extend existing authorities; no parallel catalog):

1. Trusted Robot Package preparation/admission: source entries/archive, exact
   suite path/name/task, schemas, adapter/Robot/Python/platform versions and
   direct or retained RCC Runtime Plan. Return immutable Package revision,
   capability, RuntimePlanRef/digest, measured source digest and preparation
   identities. Specify public local authorization and deployment activation.
   Do not accept a runtime worker/profile/source override in invoke requests.
2. Discovery: return the canonical ExecutionSnapshot for that exact Robot
   capability and deployment. Confirm existing `capability_invoke` generic shape
   applies, or supply its actual replacement schema. Return Run/Attempt identity
   and the existing public status/cancel/readback operations.
3. Host lifecycle: bind complete RobotSelection to admitted snapshot and live
   Actor/AttemptFence. Implement check_live/heartbeat, atomic absent-only
   record_launch_intent plus readback, bounded stage_output using the existing
   run-output service. Specify the durable journal discriminator and rejection
   response for existing/uncertain launch intent. Adapter owns none of this.
4. Fault qualification seam: provide a host-owned, local test-only barrier after
   durable intent commit and before acknowledgement/process launch, and an
   observable checkpoint after process launch. Provide a sanctioned stale-fence
   transition and its expected error. No test SQL mutation or invented SDK API.
5. Artifact reads: identify existing authorized read operation and descriptor
   fields for bytes, digest, media type, Run/Attempt scope; document cancellation
   and uncertainty states and whether diagnostic staging is permitted in each.
6. Recovery: documented installed service command, same-state graceful restart
   and forced termination recovery semantics, journal inspection/status API,
   reconciliation operation and whether it requires operator approval. Never
   infer absence of side effects merely from missing success acknowledgement.

## Acceptance cases once those interfaces land

| Case | Setup/action | Required evidence |
| --- | --- | --- |
| Exact selection | Source contains Selected plus similarly normalized names and a failing unselected task; invoke pinned Selected | XML contains exactly selected task; actual Robot version, source/plan identities, succeeded Run/Attempt |
| Retained source | Admit, remove mutable producer directory, invoke in installed empty cwd | Success from retained measured archive; no checkout/PYTHONPATH fallback |
| Inputs | Typed nested/Unicode and shell-like literals through INPUT_FILE | Exact canonical bytes, typed values preserved, no shell side effects |
| Cancellation | Block a running task, cancel via existing authority | Child tree stopped; canonical cancelled state; no completion/retry fabricated |
| Stale fence | Use sanctioned ownership/epoch transition while task is live | Old epoch cannot heartbeat/stage/publish; host cleanup/reconciliation evidence |
| Uncertain intent | Stop at post-commit/pre-ack barrier, kill service, restart same state, replay same invocation | Durable intent remains; no second launch; explicit reconciliation required |
| Artifact readback | Read scoped stdout/stderr/XML and RCC receipt via authorized operation | Compare exact bytes/digests and XML media type; another scope cannot read |
| Fresh-process recovery | Stop installed process, confirm exit, start a new PID with same datadir/provider/preparation, reconnect new client | Same Run/Attempt/artifact identities and bytes; idempotent replay; no recreated fixtures |

Run both direct and RCC plans; RCC requires the exact retained preparation and
local trust carrier. Record installed wheel/source hashes, argv, process IDs,
stdout/XML and per-case PASS/FAIL/NOT_RUN receipts. Reuse ordinary installed
service setup; do not duplicate its admission, authorization, queue or scheduler.
Budget disk before running; retain failed/interrupted receipts. A stale-fence or
fault-injection case without its sanctioned interface remains NOT_RUN, not PASS.

## Canonical documentation delta proposed to integrator

Add to `docs/skills/repository-operations.md`:
“Robot adapter tests prove process execution only. Installed Robot qualification
requires canonical Package/Runtime Plan admission and host-owned lifecycle wiring.
Restart proof must start a new service process against the same durable state and
read the same scoped artifacts. A persisted launch intent with uncertain outcome
must block replay until reconciliation; it is not evidence that retry is safe.”

Learning/evidence: source inspection above separates adapter proof from absent
canonical routing. Uncertainty: public Robot admission/fault/recovery schemas are
not yet supplied. Upstream disposition: none; internal integration dependency.
Historical a38 preparation handoff is resolved by the producer's updated recipe;
no further reconstruction or historical digest substitution is proposed.
