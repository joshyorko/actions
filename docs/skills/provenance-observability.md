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

Portable Package Revision content is separate from its consumer-side scoped
references. The manifest may declare logical Package identity, capability and
environment requirements, Runtime Plans, and logical binding requirements;
Workspace IDs, Deployment binding references/values, credentials, provider
URLs, Worker Profiles, and host-local paths do not belong in that portable
content. A consumer-side `PackageRevisionRef` carries Workspace, logical
Package, and immutable revision identity; a `RuntimePlanRef` additionally
identifies its owning Package Revision and immutable plan digest/schema/
compatibility identity. The experimental schema and fixtures in
`docs/design/package-revision-v1-schema-draft.md` exercise only these structural
boundaries. Their example digests are not production digest calculations, and
schema validation does not prove cross-reference resolution or Run pinning.
The reference experiment has one authoritative owning package reference at
`runtimePlanRef.packageRevisionRef`; an outer duplicate is forbidden even if
it matches. Its `revisionDigest` is the complete `PackageRevisionId` called
`revision_id` in the #129 domain draft, separate from source artifact and plan
digests. Plan schema versions are positive JSON integers in both portable plan
headers and scoped references. The registry's supported versions and the
reference's match to an immutable manifest still require consumer validation.
The field mapping and regression cases are documented in the experimental
schema draft; they do not approve the paused #129 production API or identifier
syntax.

The Package Revision fixtures under `docs/design/fixtures/package-revision-v1`
have canonical UTF-8 JSON bytes with LF endings. Their scoped `.gitattributes`
rule preserves those bytes on Windows checkouts with `core.autocrlf=true`.
Verify checkout bytes as well as Git blobs; do not normalize test inputs or relax
the byte comparisons to hide checkout conversion. This is fixture preservation,
not approval of a production Package Revision digest algorithm.

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

## Private common Run-output boundary

`actions.server.run_outputs` keeps the existing `Run.status` and `Run.result`
authoritative. Migration 15 adds normalized admission pins, Attempts, outputs,
Workspace records and exact persisted grants. Trusted control-plane registration
pins Deployment, Package Revision, Capability, Runtime Plan, worker, policy,
provider and schema references and checks the actual Action/Package identity.
Registration is not compiler admission or proof of provider authenticity. Actor
IDs must come from trusted authentication; a UUID or the legacy global API key
does not grant Workspace access.

Admission rechecks execute access and immutable request/idempotency identity.
Publication uses DB time and the current owner/Attempt/epoch/live-lease/cancel
predicate, then commits terminal Run status/result and final output attachments
in one transaction. Exact terminal replay is reauthorized; changed input or
result rejects. Provider sealing precedes this commit and may leave a sealed,
non-authoritative orphan after rollback. If sealing completes but the subsequent
fence/metadata transaction fails, the service first commits the measured
ref/digest/size in an ABORTED receipt, then attempts provider discard only if
that output is unattached and no other record references the object. Cleanup
failure retains this receipt and preserves the original error. An ambiguous
abort commit never permits deletion. Published output/replay remains untouched.
A crash before the abort receipt, malformed provider response or unavailable DB
can still leave an orphan without a durable cleanup reference; no GC/retry
service is supplied here. Expired-owner recovery requires an
explicit trusted operator receipt; the service does not retry external effects
automatically or prove those effects were undone.

An `art_` handle encodes only the generated output UUID. Resolution requires the
expected Workspace, a DB-backed Run/output attachment and current persisted
Deployment read access before provider access. The handle is neither a bearer
grant nor a provider path/key. Grant revocation affects future resolutions;
an already authorized descriptor stream retains its read authority. Legacy
Run lists, details, request-ID lookup, notifications, manifest fallback,
artifact APIs and analytics exclude pinned Runs rather than infer public
Workspace authorization.

The private filesystem provider requires Linux descriptor features and trusted
kernel procfs, borrows a verified service-owned root FD, and measures/seals actual
bounded bytes. It rejects special objects through an O_PATH pin before any
read-capable open. Its root must be separate from legacy artifact/static mounts.
It is not a hostile-tree snapshot, public HTTP Range/HEAD service or Windows
runtime implementation. Initial bounds are 256 KiB inputs, 1 MiB result envelope,
64 output records per Run (including aborted records), 64 MiB per object,
64 KiB chunks, leases up to one hour and retention up to one year. Full quotas,
GC, output-secret policy, compiler/provider admission, production actor/provider
wiring, adapters and Canvas transport remain separate gates; this private slice
does not accept whole #83/#86/#129/#127.

## Verification matrix

Platform-neutral CLI checks such as `--help` and refusal to overwrite an existing
receipt must run before the Linux-only process-supervisor eligibility check; they
must not create supervisor state. The RCC acceptance CLI still fails closed on
unsupported platforms before candidate execution. Tests that prove Linux
subreaper or process-group cleanup must be explicitly Linux-only. Skipping those
process-proof tests elsewhere is not macOS or Windows cleanup acceptance, and a
mocked `CompletedProcess` does not establish descendant cleanup.

The dependency-free `devutils.runtime_conformance` module is the repository's
small executable contract for this boundary. It canonicalizes exact-subject
fingerprints, captures one immutable admission decision, selects only an
explicitly declared Deployment Runtime Plan, and rejects workers that lack the
selected runtime kind or required features. Its tests also verify changed
subjects and missing plans fail closed; adapters must build richer receipts on
top of these primitives rather than implement a second admission gate.

Contract tests must cover one collapsed and one split execution with an RCC
adapter and one non-RCC adapter; retry/Attempt linkage; RCC local/provider/
cold/warm preparation; admission off/shadow/enforce and exact-subject
reproducibility; decline/no-fallback/cancel/owner-loss/stale-fencing/
ambiguous outcomes; Work Item/workflow/interaction lineage; cross-Workspace
rejection; raw, encoded, multiline, child-output, argv, and provider
diagnostic redaction; exporter failure; bounded metrics; and auditable adapter
promotion/revocation. Equivalent logical executions must have equivalent
receipt shape, with placement-specific evidence only where applicable.
