# Provenance and Observability Contract

This guide is the repository contract for capability/execution provenance. It
does not define agent or LLM tracing, and it does not make telemetry a source
of execution authority.

## Version and identity

The contract version is `actions.runtime.evidence/v1`. Every request, Run, and
Attempt carries that version and a Workspace scope. Durable correlation uses
stable generated IDs and immutable fingerprints, never a PID, path, MCP
session, provider URL, mutable tag, container task ID, or cache-service
session.

The canonical chain is:

```text
Workspace -> DeploymentRevision -> PackageRevision -> Capability
  -> RuntimePlan -> AdmissionSnapshot -> Request -> Run
  -> Attempt(epoch) -> Worker/Placement -> Preparation/ExecutionReceipt
  -> ProviderOperation/Effect -> Artifact/Result -> WorkItem/Workflow/Interaction
```

Each durable identity records its owner, Workspace scope, sensitivity,
cardinality class, retention class, and serialization version. A child record
references its parent; it does not reconstruct identity from mutable state.
Retries create a new Attempt under the same Run and retain the selected
Runtime Plan. A parent/child Run, workflow fan-out/fan-in, Work Item, and
interaction link uses an explicit typed link with its source and destination
Workspace checks.

## Admission and execution receipt

Run creation stores one immutable `AdmissionSnapshot` containing the schema
version, exact-subject fingerprint, relevant object/policy/binding
generations, `off|shadow|enforce` mode, canonical outcome and reason codes,
unknown/partial state, static requirements, dynamic observations, and
revalidation result. Later global state cannot be used to infer the decision.

The terminal Run/Attempt receipt is a compact durable record containing Run,
Attempt and epoch; Workspace/Deployment/Package/Capability/Runtime Plan
references; adapter contract, version and features; the AdmissionSnapshot;
binding/policy/Worker Profile; worker/placement/process receipt; preparation
and provider phases; timing and terminal outcome; retry/cancel/decline/lease
loss/fencing/ambiguous reasons; effect idempotency receipts; output,
artifact, Work Item, workflow, and interaction links; no-fallback assertion;
and redaction/truncation indicators. A receipt is evidence, not permission to
replay an effect or switch adapters.

Adapter runtime evidence is namespaced beneath the Runtime Plan and Attempt:

* RCC: Environment Specification, Artifact, source/provider/build choice,
  publish/acquire, verify/materialize, process-owned lease, `env exec`,
  release, and `cache serve` provider request class.
* uv/Python/Robot Framework: their own project/lock/interpreter/venv,
  suite/runner, environment, preparation, and validation identities.

`cache serve` is provider evidence only and never worker scheduling or Run
authority. Non-RCC adapters must not emit RCC fields.

## OpenTelemetry

Use stable names under the `actions.runtime` namespace for gateway request and
MCP method/name/client; resolution; admission computation/revalidation;
package fetch/verify/compile/import; adapter negotiation/preparation; Run
queue/claim/Attempt lifecycle; worker selection/decline/backpressure/drain;
process/container/session lifecycle; typed provider operations; publication;
Work Item/review; workflow/interaction links; retry/reconciliation/lease
loss/fencing/ambiguous effect; and update/rollback/promotion/revocation/GC.

Propagate versioned context across queues and processes independently of MCP
sessions. Use span links for retries and fan-out/fan-in where there is no
single synchronous parent. Collapsed local mode emits the same IDs and event
shape as distributed mode; placement details are namespaced evidence.

Never put secrets, credentials, auth headers, raw inputs/outputs, source,
tables, prompts, local paths, or unbounded logs in span attributes. IDs,
digests, exact fingerprints, provider references, and high-cardinality
capability names belong in receipts/logs/audit, not metric labels.

Metrics use bounded dimensions only: operation/adapter kind, outcome/reason
class, admission mode, preparation/cache class, provider class, placement
class, and coarse size/latency buckets. Run IDs, digests, and exact names are
not metric dimensions.

## Audit, logs, and failure policy

Audit records are append-oriented durable decisions, not exported spans. They
include actor/auth source, Workspace, exact object generations/fingerprints,
safe before/after references, timestamp/source, correlation, and outcome.
Record consequential configuration, trust/promotion/revocation, deployment,
admission, authorization, Run, override, worker ownership, effect, Work Item,
artifact access/deletion/hold, and provider-reference administration events.

The implementation must declare whether mandatory audit persistence failure
blocks the consequential operation. Exporter or collector failure must never
corrupt authoritative Run state. Structured logs carry trace/Run/Attempt IDs,
ordered stream/cursor identity, live-versus-durable status, bounded size/rate,
and truncation markers. Register redaction before adapter or user output;
sanitize diagnostics and reject secret argv/env/provider URL leakage.

## Privacy and support export

All telemetry, audit, artifact, and provider access is Workspace-scoped and
deny-by-default for secrets, tokens, cookies, private source, data rows, raw
payloads, and local paths. Caller baggage is neither authorization nor durable
identity. Debug mode cannot weaken redaction, and exporter scope changes are
audited. Trusted Runtime Plan, admission, and worker fields are produced by
the control plane, not package code or adapters.

A support bundle is a sanitized, authorized machine-readable export of runtime
and adapter versions/features, identity/fingerprint references, configuration
and provider references without credentials, schema/migration versions,
worker readiness, cache/provider health, correlated failures/evidence/logs,
disk/GC state, and a redaction manifest. It rejects archive traversal,
absolute paths, symlinks, duplicate names, and oversized members.

## Verification matrix

Contract tests must cover one collapsed and one split execution with an RCC
adapter and one non-RCC adapter; retry/Attempt linkage; RCC local/provider/
cold/warm preparation; admission off/shadow/enforce and exact-subject
reproducibility; decline/no-fallback/cancel/owner-loss/stale-fencing/
ambiguous outcomes; Work Item/workflow/interaction lineage; cross-Workspace
rejection; raw, encoded, multiline, child-output, argv, and provider
diagnostic redaction; exporter failure; bounded metrics; and auditable adapter
promotion/revocation. Equivalent logical executions must have equivalent
receipt shape, with placement-specific evidence only where applicable.
