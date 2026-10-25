# Action Canvas integration handoff

Goal: implement the original #71 first-boot authoring vertical through the
existing Runtime, semantic View, common Package/Deployment and Run services.

Authority: Josh confirmed parallel Actions foundry implementation on October 22
at 21:59:51 UTC. The coordinator owns cloud dispatch; this lane is the sole
writer of release/327-invoice-vertical-20261020 and draft #328. This supersedes
the earlier read-only scope-choice hold. On October23 Josh also authorized a
community merge and later Runtime/PyPI publication once every agreed requirement
is verified; the parent retains final exact-source/inventory confirmation. This
lane must not merge, tag or publish ahead of that confirmation. Deployment, spending,
production, live credential/auth/tunnel changes and other-repository mutation
remain unauthorized. Every accepted lane belongs to this same #327/#328 release;
no requirement is silently parked in another release.

Protected baseline: `e2408a6e3051cdb4c44aede47618c3791807eba5`. Its invoice proof,
candidate bundle, source-specific receipts and failed/skip classifications stay
addressable. The coordinator reports all 13 workflows green at that head; this
does not qualify the new foundry or authenticated ChatGPT E1.

This handoff allocates files and integration contracts in the existing issue
graph. It is not a replacement tracker. Issue bodies and their October 9/10
amendments remain the acceptance authority.

## Exclusive ownership

| Lane | Files | Shared-file boundary |
| --- | --- | --- |
| #100 public spec | New Core semantic authoring module/tests; `docs/contracts/canvas/canvas-spec-v1.schema.json` and new schema fixtures | Existing Core exports, versions and dependency locks remain integration-owned. Historical owner review found no live owner; coordinator admitted the replacement lane. |
| #99-A renderer | New `action_server/frontend/apps/canvas-view/src/semantic-renderer/**` and colocated tests | No existing entrypoint, invoice component or shared build edits. Integration owns `McpCanvasView.tsx` and contract adaptation. |
| #130/#135 compiler | New existing-architecture compiler/manifest modules under `action_server/src/actions/server/deployments/` and new compiler tests | Reuse source_manifest/read/staging and existing Package schemas. No shared migration, legacy loader, Run or deployment-pointer edits. |
| #129 deployment | New `deployments/foundry_values.py`, `foundry_repository.py`, `foundry_service.py`; `tests/action_server_tests/test_foundry_deployments.py` | Use a borrowed Runtime Database and existing canonical refs. Supply model/DDL needs to integration. No private DB, global migration edits or Run-store replacement. |
| #71 authoring | New `foundry/authoring.py`, `authoring_values.py`; `tests/action_server_tests/test_foundry_authoring.py` | Consume spec/compiler/deployment ports. No private persistence, central MCP registration or duplicate package/queue authority. |
| #99-B/#127 boot/template | New `foundry/boot.py`, `discovery.py`, their tests and new template fixtures/files | Existing CLI and template manifest/bundle wiring remain integration-owned. External plugin-repository changes require a separate handoff. |
| Integration | Shared models/migrations/DB wiring, central MCP/server/CLI, existing Canvas lifecycle/entrypoint, Run/Work Item/output seams, versions/locks/toolkit/CI and canonical guides | Review exact worker source, import provenance and tests before convergence. No worker edits another lane or the integration branch. |

Workers return exact tested commits and proposed canonical-guide deltas. The
integration owner edits shared guides to avoid concurrent changes to the same
large file. No lane independently builds changed release artifacts under the
published Runtime1.0.4/SDK0.4.4/Core identifiers or an earlier candidate's bytes.
Integration admits provisional versions before candidate wheel verification.

## Minimal spec proposal for owner review

The #100 lane owns the canonical schema and final validation implementation.
This proposal prevents competing protocols; coordinated changes must update the
renderer/authoring fixtures before any interface is considered frozen.

```json
{
  "schemaVersion": "actions.canvas-spec/v1",
  "title": "Application title",
  "bindingIds": ["search"],
  "root": {"type": "stack", "id": "main", "children": []}
}
```

First semantic nodes:

| Type | Required data beyond `type`/`id` |
| --- | --- |
| stack | `children`: bounded nodes |
| text | `text`: bounded plain text |
| form | `bindingId`, `fields`, `submitLabel`; each field has `name`, `label`, `type` in text/integer/boolean and an explicit required flag |
| table | `bindingId`, `rowsKey`, `columns`; columns select bounded plain property keys and labels |
| status | `bindingId` |
| artifact | `bindingId`, `label` |

Proposed limits: 64 KiB serialized spec, depth 8, 128 nodes, 32 bindings, unique
node/binding IDs. Unknown required versions/features and undeclared bindings
fail. A spec contains logical binding IDs only, never provider URLs, filesystem
paths, tool names, Python, credentials or executable expressions. The server
resolves those IDs to authorized typed capabilities. Defaults and result data
must not become cached renderer HTML or implicit execution on mount.

Core serialization is not authoritative Package/Deployment identity hashing.
Runtime consumes the existing canonical JSON service for protected identities.
Renderer consumers use the accepted schema/fixtures, not a second vocabulary.
The integration-owned `src/canvas-contract/**` seam can adapt validation/types
without giving #100 and #99 overlapping frontend ownership.

## Backend integration ports

Use existing Actor, WorkspaceId, PackageRevisionRef, DeploymentRevisionRef,
RuntimePlanRef and ExecutionSnapshot values. The following semantic envelopes
are review targets, not a new portable manifest syntax.

1. Compiler input is an explicitly selected, measured staged source inventory
   plus trusted build policy. Output is immutable canonical portable manifest
   bytes, source identity, capability declarations, declared runtime plans and
   build evidence. Portable bytes contain no installation Workspace, resolved
   binding values, credentials or worker-local paths. Compiler does not insert
   deployment rows or advance activation.
2. Deployment service receives actor/Workspace, a verified compiled revision,
   logical binding resolution, expected base revision and idempotency key.
   Resolution returns the exact pinned ExecutionSnapshot for an authorized
   capability. Missing adapter or policy never selects a fallback plan.
3. Authoring create/get/apply/preview/inspect/release consume those ports. Apply
   stages UI and, when explicitly requested, generated backend bytes. Release
   requires successful validation/build and compare-and-swap activation. A
   failed stage/build leaves the accepted active revision addressable. The
   authoring lane does not own another database or scheduler.
4. Final visible Package/Deployment/app selection and common Run admission use
   the Runtime SQL authority. Immutable source/UI blobs may be staged first;
   they are inaccessible until admitted references authorize them. Do not add
   competing active pointers across a Canvas side database and the common
   Deployment store. Integration reviews the storage adapter/transaction before
   wiring the services together; the existing private invoice profile remains
   supported.
5. A long build uses existing Run/Attempt evidence and returns inspectable
   identity; no Canvas build queue or internal LLM loop. Backend generation is
   external-model authored, trusted-developer code in confined staged files.
   RCC and iframe isolation are not backend Python security sandboxes.

## MCP and renderer boundary

One Runtime exposes six fixed model-visible authoring names:
`canvas_create`, `canvas_get`, `canvas_apply`, `canvas_preview`,
`canvas_inspect`, `canvas_release`. A separate read-only `canvas_open` accepts
exactly `{}` and opens the app library/current app. It never creates, applies,
releases, queries, approves or executes. Generated operations do not grow the
model catalog.

The integration adapter owns app-only typed dispatch, manifest/state, execution
status, cancellation and artifact access. Every operation uses trusted actor
context and exact authorized app/revision/binding/Run scope. UI visibility and
possession of an app ID or artifact handle are not authorization. Additional
query/page projections require actual named-operation conformance rather than
placeholder success.

Use the same stable `ui://action-canvas/v1/canvas.html` resource with versioned,
cache-safe renderer bytes and `text/html;profile=mcp-app`. Authorized initial
state travels in complete MCP result metadata; do not refetch/execute simply
because the View opened. A pure semantic renderer receives the validated spec
and injected typed dispatch/status/artifact adapters. It does not select an
arbitrary server tool/URL or persist authoritative business state.

## Integration tasks and verification

- [ ] Record reviewed owner contracts/fixtures and exact worker heads. Keep
  parent dispatch and the existing issue graph authoritative.
- [x] Add opt-in central stable MCP/resource registration tests before implementation:
  empty user-package catalog, fixed model names, app-only caller denial,
  read-only empty-input launcher, reserved-name/resource collisions, complete
  result metadata and useful unsupported-operation failures.
  This qualifies the transport boundary with a synthetic domain port, not a
  wired first-boot service or durable authoring. Native identities are protected
  on direct registration and catalog replacement. Runtime source advances to
  provisional `1.1.0a6`; the protected invoice bundle remains `1.1.0a5`.
- [ ] Implement shared Runtime SQL/model wiring against reviewed compiler and
  deployment values. Test concurrent CAS, changed-input idempotency conflict,
  cross-Workspace/revision denial, SQL rollback and fresh-interpreter reopen.
- [ ] Join the semantic renderer to the same adapter; run real browser tests
  without intercepted backend replies. Preserve invoice rendering/review tests.
- [ ] Prove existing-capability first-boot composition, then separately prove
  externally authored Python -> common immutable Package/Deployment -> real RCC
  Run/result -> revise -> failed validation -> rollback -> restart.
- [ ] Run pinned Doctor/Bootstrap/ToolkitTest and affected package/static/real
  SQL/installed-candidate/browser gates at frozen source. Recheck imports and
  artifact/source hashes. Preserve failures, skips and platform applicability.
- [ ] Push reviewed nonforce checkpoints to the assigned integration branch;
  update the existing issues/PR with exact evidence. No community merge,
  package/image publication, deployment or live authentication change.

Review focus: malicious spec authority; stale/concurrent revisions; old Run
pinning during N+1 activation; effect-free launch/remount; crash/SQL failure
between immutable blob staging and authoritative publication. Each must have
a boundary regression before its corresponding integration is accepted.

Authenticated ChatGPT E1 remains a separate operator gate. Existing Executor
read/write remains recognized and untouched. General effects, retention/restore,
independent distribution and celld NO-GO remain visible in the release ledger.

## Candidate compiler and persistence contract

These decisions constrain the current #327/#328 release implementation. They
are provisional contracts, not implemented admission or production syntax.
The compiler and deployment lanes return tested source; integration owns shared
models, registration, migrations and final service wiring.

### Compiler manifest
1. Extend the existing `docs/design/package-revision-v1.schema.json` boundary, keeping `actions.package-revision/v1-draft` explicitly provisional. Do not rename the existing draft into an approved public format. Retain its identity/sourceArtifact/compatibility/capabilities/logicalBindingRequirements/runtimePlans split. Portable packageId is a logical key; installation PackageId UUID and Workspace/Deployment references stay outside these bytes.
2. Use Runtime's `deployments.canonical.canonicalize_json` (actions-canonical-json/v1) for protected bytes. Core CanvasSpec.to_json is serialization, not a replacement identity algorithm. Reject duplicate capability/requirement/plan IDs and dangling reciprocal capability/plan/requirement links. Sort known set-like lists (IDs/scopes/features; capabilities/requirements by id; plans by computed digest; environment requirements by kind/name/constraint); preserve ordered source/task semantics and JSON Schema arrays.
3. Candidate hash domains: plan digest = sha256(canonical JSON of ["actions.runtime-plan/v1-draft", plan object WITHOUT its own digest]); Package revision = sha256(canonical JSON of ["actions.package-revision/v1-draft", manifest WITHOUT identity.revisionDigest]). Prefix stored digests with sha256:. The complete manifest includes computed plan digests and compilerNormalizationVersion=`actions-foundry-normalizer/v1-draft`. Source artifact, plan, schema/payload and Package revision digests are distinct. Do not substitute source inventory/Git SHA/RCC Artifact for them.
4. sourceArtifact.digest/byteLength must measure the actual source ZIP required by the existing mediaType, not canonical inventory bytes. Bind the complete explicit selection and protected inputs through existing no-follow measure/stage/re-read helpers. If the current compiler snapshot only measures an inventory, preserve it as a proposal and report ZIP/admission missing. A caller can still omit selected files; staging alone does not attest selection completeness/trust or an atomic whole-tree snapshot.
5. Carry the actual measured input/output schema and adapter payload bytes/evidence alongside their digests. Initial executable acceptance is only the existing RCC contract `rcc-runtime/v1`, positive plan schemaVersion1 and exact RCC18.19.3; declarations for other runtimes do not grant fallback or dynamic admission. Portable environment requirements/specification contain no resolved provider context, credentials or local process paths. Local preparation/trust-carrier receipts remain deployment/build evidence, outside the portable manifest.
6. Compiler never inserts deployment rows, advances activation or starts a task merely by inspection. Declared source/schema facts stay distinguishable from verified build/adapter conformance. Long actual build/execution uses existing Run/Attempt evidence.

### Shared SQL persistence target
Use the borrowed Runtime Database and existing Workspace rows, not canvas.sqlite3 or another connection/store. Integration will own registered ORM rows and migration/unique-index changes. Deployment lane may implement against injected trusted row types, with local fixture row definitions in its exclusively owned test file, until the shared definitions land; do not edit shared model registration.
- FoundryPackageRevision: immutable scoped package ref + canonical manifest/source/build evidence.
- FoundryDeploymentRevision: immutable scoped deployment ref + exact protected selection/binding/profile input + verified per-capability ExecutionSnapshot map.
- FoundryDeploymentHead: Workspace/deployment key, active revision and monotonic lock_version.
- FoundryRequest: actor/Workspace/operation/idempotency-key identity, protected request fingerprint and original immutable result receipt.
- FoundryAudit: append-only actor/Workspace/deployment/request/from/to revision event.
- FoundryAccessGrant: explicit foundry operations on Workspace/subject, never inferred from a Run execute/read grant or MCP visibility. Authenticated Actor is injected by the trusted host.

Package installation and deployment selection are scoped records over portable content. Deployment revision hashing must use protected selection inputs BEFORE filling its own revision into derived ExecutionSnapshots; do not create a self-referential digest. On resolution revalidate package/plan ownership, schema/compatibility and exact profile/binding refs; missing or changed admission fails closed.

Authorization/revocation checks, immutable inserts, idempotency receipt, activation CAS and audit commit in ONE Runtime SQL transaction. CAS checks Workspace + deployment + expected active revision + lock_version, using conditional UPDATE/RETURNING, not only a Python lock. Same key/same fingerprint returns the original receipt without reactivating after later changes; changed fingerprint conflicts. Failed transaction publishes no partial head/receipt/audit. SQL bind diagnostics remain redacted as in run_outputs.service. Release/rollback never creates a Review/WorkItem/Run automatically, erases audit or rewrites existing Run pins.

### Integration-owned row interface

Repository/service code uses the borrowed initialized Runtime Database. It may
accept these trusted ORM classes by injection until integration publishes them;
tests can supply equivalent fixture-only classes. Never initialize a second
class set on an already initialized Database.

| Class | Columns (all text except `lock_version`) |
| --- | --- |
| FoundryPackageRevision | id, workspace_id, package_id, revision_id, manifest_json, source_artifact_digest, source_inventory_json, build_evidence_json |
| FoundryDeploymentRevision | id, workspace_id, deployment_id, revision_id, foundry_package_revision_id, selection_json, snapshots_json |
| FoundryDeploymentHead | id, workspace_id, deployment_id, active_revision_id, lock_version (integer) |
| FoundryRequest | id, workspace_id, principal_id, operation, idempotency_key, request_fingerprint, result_json |
| FoundryAudit | id, workspace_id, deployment_id, principal_id, operation, foundry_request_id, from_revision_id, to_revision_id, created_ms |
| FoundryAccessGrant | id, workspace_id, principal_id, subject_kind, subject_id, operations_json |

Every `workspace_id` references the existing Workspace row. Package/deployment
row IDs are scoped identities derived from complete typed references; the
revision digest alone is never a global row key. Deployment revision's
`foundry_package_revision_id` and audit's `foundry_request_id` reference their
immutable rows. `selection_json` holds protected deployment inputs;
`snapshots_json` holds derived exact per-capability snapshots. JSON is bounded,
validated and canonicalized by the service before persistence. No secret value,
raw output bytes or credential belongs in these columns.

The access-grant subject is explicit Workspace, application or deployment scope,
with current principal and named foundry operations. Run read/execute grants do
not grant install/bind/activate. Immutable requests/audit and mutable heads/grants
remain distinct records in the same SQL authority. Shared model registration,
constraints and migration tests are integration-owned; these names/columns are
a handoff contract until those tests pass, not an applied schema claim.

### PR333 consumer adaptation — one persistence authority

Decision: keep schema17's registered `Foundry*` records in the common Runtime
Database. Task01a16897-47e8-7472-82b6-668a25afa006 adapts only its reserved
`foundry_repository.py`, `foundry_service.py`, `foundry_values.py` and tests.
Do not create any `deployment*` side schema, view alias or private database.
Retain the typed #333 DeploymentSpecification/Revision and all existing semantic
assertions. The physical mapping changes; Workspace/Package/plan identities do not.

| Existing #333 operation | Accepted consumer adaptation |
| --- | --- |
| `current(workspace_id, deployment_id)` | Compute the scoped head row key; read FoundryDeploymentHead with both explicit scope columns; resolve its active revision. |
| `_insert_revision` / `_revision` | Store/read the complete canonical DeploymentRevision envelope in `selection_json`, including sequence, previous/rollback lineage and full specification. Revalidate canonical bytes, scope and computed revision digest on every read. Related package/binding/worker/policy/output-provider tables are replaced by this one protected document. |
| Package references | Validate every package against admitted FoundryPackageRevision rows in the same Workspace. The FK anchors the first package in canonical ref order for SQL integrity only; it never chooses execution or narrows the complete package set. Keep all packages and per-capability policies in the protected specification. |
| `activate` | Add a trusted Actor and authorization/preflight callback; after acquiring the shared Workspace SQL lock, recheck current grants and all references inside the publication transaction. Outer prechecks alone are insufficient for revocation races. |
| Request/replay | Use FoundryRequest keyed by Workspace/principal/operation/idempotency key and a fingerprint including deployment, expected base and complete specification. Store the original canonical revision receipt in result_json. Same request returns that receipt without changing a later head; altered input conflicts. |
| `_cas_activate` | Conditional UPDATE on FoundryDeploymentHead with Workspace, deployment, expected active_revision_id and observed lock_version; increment lock_version and require exactly one RETURNING row. Initial empty head uses explicit empty-string revision; no NULL/empty equivalence. |
| Audit | Append FoundryAudit referencing the same FoundryRequest before transaction commit. Store actor/from/to/operation lineage without secret values. |
| Resolved execution | `snapshots_json={}` explicitly means no execution snapshot admitted. Never interpret it as authorization/readiness. The resolver revalidates the protected specification and selected exact plan, then uses the existing common Run admission. Admission never selects a first/default package by storage anchor. |

Package admission is integration-owned. The repository must not manufacture a
Package row to satisfy its FK. Owner tests may seed explicit fixture-only admitted
Package rows, but must label fake compiler/execution/authorization ports as component
fixtures, preserve multi-package tests and add common migrated SQLite/real-PG proof.
Any additional columns truly needed are returned to integration before changing
shared models; do not reinstate the parallel normalized schema.

### Accepted compiler/deployment adapter seams

Consume PR331 `CompilationOutcome(compiled_package, receipt)` and its existing
`compile_generated_python_action(entries, policy, *, protected_input_names,
admission, executor, execution_root)`. Only the trusted host supplies policy,
execution root, executor and `TrustedDeveloperExecutionAdmission.TRUSTED`.
Those are not model/tool authority. Failed/not-run build/import/test phases do
not admit a Package. Verify all compiled manifest/archive/plan/schema/payload
preimages and real build/import/test evidence before storing the scoped Package.

Implement PR333's existing PackageRevisionPort as a read-only adapter over that
admitted registry: `require_revision`, `get_capability`, `get_runtime_plan`,
`get_binding_requirement`. Return exact scoped CapabilityRef/RuntimePlanRef and
binding requirements from verified compiler bytes. Keep CapabilityExecutionPort
`action_id_for` and WorkspaceAuthorizationPort separate. Never treat a caller's
CompiledPackageRevision dataclass, inventory digest or reference syntax as a grant.

### Authoring and boot injection boundary

Authoring task01a168bb-b1fa-71df-8c46-4dea107a900c owns its pure values and service
in `authoring_values.py`/`authoring.py`. Consume the public CanvasSpec validator,
PR331 compiler outcome, PR333 deployment service and injected common persistence.
Create/get/apply/preview/inspect/release must never open canvas.sqlite3 or another
store. Return a precise repository-port/value contract for integration-owned SQL
wiring; immutable source/spec staging may precede publication but grants no access.
Release uses only a successfully verified compile and expected-base activation.
Preview is nonexecuting; a build/job is distinct Run/Attempt evidence, not an
unbounded synchronous MCP call or another queue. Existing-capability composition
can omit generated Python, but cannot claim the generated-backend acceptance.

The authoring facade can implement the existing CanvasPort `schemas` and async
`call(CanvasCaller, name, arguments) -> CanvasReply` through a thin transport
adapter. Trusted caller supplies Actor/Workspace/audience. Return deliberate model
summary/data separately from app-private state. Do not repeat validation, grant
resolution or revision ownership independently in the MCP layer.

Boot task01a168bd-45be-755e-9da9-1b7a4509a039 owns only `boot.py`, `discovery.py`,
its dedicated tests and isolated example files. It receives a real CanvasPort,
a trusted authenticator and checked renderer bytes by injection and constructs
the existing CanvasMcp/McpServerSetupHelper. No fake default port may make boot
look successful. Integration owns existing CLI/MCP/template manifest wiring.

Boot must register the stable facade before user-package discovery, create only
owned apps/packages/blobs/cache/logs roots outside the immutable plugin root,
and initialize the same common SQL authority idempotently. `canvas_open({})`
only reads the app library/current state; mount/remount causes no creation,
apply/release/query/review or execution. Initialization state writes are separate
from user approval or application execution.

Discovery is bounded, atomically replaced, owner-private process metadata, not
business authority or a credential store. Include schema/instance/process-start
identity, transport/endpoints and starting/ready/failed/stopping health. Recheck
process identity rather than trusting a reused PID or partial PID file. An owned
root admits one runtime instance and idempotent attach/restart behavior. Never
attach to unrelated existing services or publish a network listener/tunnel by
default. MCP stdio stdout contains protocol only; diagnostics use stderr.
The same services serve local/stdio and explicit authenticated standalone HTTP.
No external plugin repo, live identity, credentials or tunnel change is included.


### Package-less UI and deployment source contract

The integration-owned forward schema18 makes
`FoundryDeploymentRevision.foundry_package_revision_id: Optional[str]` nullable.
It remains an actual FK for backend-bearing revisions. No synthetic Package,
third manifest or sidecar database represents an empty Canvas.
`DeploymentSpecification` now has `canvas_spec: CanvasSpec | None`,
`canvas_application: CanvasApplicationRef | None` and
`canvas_bindings: tuple[CanvasCapabilityBinding, ...]` alongside the existing
Package/plan/provider selection. UI-only selections require the view and exact
application source pin, empty Package/plan/binding sets and absent execution
profiles. Backend selections retain the existing explicit requirements.

Use `canvas_revision_digest(spec, bindings, packages)` for the immutable UI
source identity. It hashes canonical alias-key spec plus ordered exact binding
and Package references under `actions.canvas-application/v1`; it does not hash
its own Deployment revision. `CanvasCapabilityBinding` has `binding_id` and
`capability: CapabilityRef`. Every logical ID must match the spec and select a
deployed capability. The Deployment owner must match the application owner.
The common execution snapshot carries this exact application pin. These typed
values do not grant actor permission, compiler admission or automatic activation.

The SQL authoring adapter must stage full immutable Deployment revisions in
`selection_json`, keep the latest edit separate from activation, and activate
only through the one `FoundryDeploymentHead` CAS with receipt/audit. Staging is
not execution authorization. No authoring SQL adapter or joined first-boot
execution is claimed by the package-less storage/component tests alone.

### Official bridge semantic projection

The packaged Canvas view reads authored UI from the official App `toolresult`
event's `_meta["actions.canvas"]`, not from the model-visible
`structuredContent` summary. The closed app envelope carries application and
revision identity, active status, the canonical spec and exact capability/Package
bindings; a preview envelope carries only `spec` and `preview: true`. The view
validates the v1 limits and binding scope before rendering through the existing
`SemanticCanvasRenderer`. Changing the application, revision or binding scope
remounts renderer state. Existing invoice and query projections remain separate
supported envelopes on the same bridge.

This adapter currently supplies read-only semantic adapters: opening a view or
preview does not dispatch a capability, poll status or resolve an artifact. Forms
are unavailable or disabled until trusted app operations are wired. App audience
projection is enforced by the renderer; UI visibility never grants server access.
The official tool-result notification has no correlation identifier in this
adapter, so it cannot prove ordering of delayed host notifications. Do not enable
mutating adapters on an assumed notification order. Bridge component tests prove
metadata parsing, revision remount, audience filtering, no mount calls and legacy
projection preservation; they do not establish installed-host or ChatGPT proof.

Model tool discovery must expose the complete CanvasSpec schema and each
authoring operation's root description. Embedding Pydantic's standalone spec
schema unchanged under a tool's `properties.spec` breaks its root-relative
`#/$defs` references. Generate references as
`#/properties/spec/$defs/{model}` and validate the complete tool document with
a JSON Schema validator, including a recursive stack and a rejected unknown
node. Schema equality on the nested object alone does not prove usable discovery.
Authorized model results include the public authored spec for create/apply/get,
inspection and activation/rollback; concrete capability bindings and backend
source remain private. Spec data enables revision, never actor authorization.

## Local semantic projection interface

SemanticRendererAdapters may expose a pure local getProjection(bindingId) getter
returning SemanticProjectionState. This does not fetch, authorize, or accept
arbitrary dispatch metadata. A trusted adapter generation identifies each
request; ready/empty states require the current Run/Attempt, canonical JSON and
parsed data from the same authorized output under the existing restricted
RFC8785 contract (at most65536 UTF-8 bytes). Clear prior data on resubmit, error
or authorization denial and ignore stale responses. The host's changed callback
triggers rendering. The TypeScript interface alone implements no encoder,
Runtime wire contract, validation or authorization.

## Robot launch journal ownership

RobotJournal uses the existing Run.result and current Run/Attempt transaction;
its admission owner must first create the closed actions.robot-dispatch/v1
launch:null envelope. The journal acquires the Run fence before reading so two
SQLite connections cannot both pass an absent-intent check. It persists the full
versioned selection preimage, compares it with a host-derived SQL-validated
selection and canonical Run inputs, and refuses every existing launch, including
an identical replay. A lost acknowledgement leaves the intent for reconciliation,
never permission to spawn again. Work Item outputs expose the canonical ticket
claim, whose epoch is independent from the Attempt epoch; the host callback
rechecks that claim's live SQL authority. No artifact/provider/filesystem reads
belong in this callback or journal transaction. This port neither initializes nor
resets journals and does not publish, terminalize, schedule or retry execution.

Recording a Robot launch must own the outermost Database transaction. Nested
transactions are savepoints, so a returned intent inside an outer transaction
can disappear on rollback. RobotJournal rejects an existing transaction before
mutation via Database.in_transaction(); a successful record acknowledgement
therefore follows its own durable commit and subsequent validated read.
