# Provenance and Observability Contract

Installed restart acceptance does not qualify coordinated restore or version
compatibility. A restore receipt must identify SQL state, sealed objects,
journals, retained source/runtime artifacts and their pins; demonstrate
authorized replay from a distinct restored root; and separately record old/new
installed compatibility. Synthetic attachment-path relocation tests establish
only that relocation contract.

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

### Publisher identity and live protection evidence

Exact repository/head, qualified complete-tree, workflow, run, manifest and
artifact checks remain necessary even for an authorized owner. A repository
name that merely resembles the expected owner/name is not the same identity;
an unqualified descendant with unchanged workflows is not qualified source.
Exercise these negatives against the existing release-button validator before
publication, without invoking its write path.

An `environment: pypi` workflow declaration proves neither required reviewers
nor branch restrictions. Read current environment protection, repository
rulesets and branch metadata separately and retain the observation time. Actor
and triggering-actor checks cannot distinguish an owner from someone using that
owner's stolen credential. Record that residual risk and the actual publisher
token scope; a secret's descriptive name does not establish its permissions.
Changing reviewer rules, branch protection, identities or credential scope needs
the applicable owner approval. Successful mocked/unit publisher tests do not
establish those live settings or authorize a publication.

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

The optional server-only `RunOutputTransport` binding installs a bounded GET
route at `/api/workspaces/{workspace_id}/outputs/{handle}` in the actual Runtime
application. Without explicit trusted configuration that route is absent. The
binding pairs the existing service with an authenticator that verifies its
credential and returns a server-owned Actor; freezing the binding does not
verify the authenticator or freeze its credential store. No CLI/environment
mapping, default principal, browser/provider-OAuth session UUID, installation
API token or caller-selected Actor ID supplies Workspace authority. When
configured, installation-key authentication remains an outer gate. The trusted
Actor authenticator and the shared resolver's current persisted read-grant
checks are mandatory with or without an installation key and occur before
provider acquisition. Present browser Origins must pass the existing trusted
origin policy; an allowed Origin or a successful preflight never grants identity
or access.

This transport streams the measured opened descriptor in chunks of at most
64 KiB and closes its resolver on completion, failure and disconnect. It serves
`application/octet-stream` as an attachment using only the opaque handle as the
filename, with `no-store` and `nosniff`; logical names/media types never enable
inline active content. Handle-bearing headers are constructed only after shared
resolution validates the canonical handle, so Unicode/control-character path
inputs cannot turn a uniform denial into a header-encoding failure. Denied, revoked, cross-Workspace, malformed and unknown
handles share an unavailable response before provider access. Storage acquisition
failure returns 503; a failure after headers aborts the stream rather than
claiming a complete artifact. Range requests return 416 explicitly and HEAD is
not implemented. This is ASGI source evidence, not socket/native/CLI acceptance
or the full #86 static-serving contract: HEAD, ETag, Last-Modified, single,
suffix, multi and invalid Range behavior, Windows descriptor/reparse parity,
shared/object providers, quotas and GC remain required. Production identity
provider configuration and actual Canvas producer/consumer execution still need
separate integration; a retrievable private-service output does not authorize
changing a template's `artifact: null` without its own end-to-end proof.

For assembled output-transport denials, count provider-open attempts before
entering the reader context; a list of successfully opened readers alone cannot
prove that storage was never touched. Take complete logical database and owned
filesystem snapshots after legitimate publication or grant changes, then compare
them across each request. Compare SQL rows rather than physical SQLite bytes:
the resolver takes idempotent writer locks even for authorized reads. HEAD 405
and Range 416 prove rejection, not method support or persisted-grant resolution.

The private filesystem provider requires Linux descriptor features and trusted
kernel procfs, borrows a verified service-owned root FD, and measures/seals actual
bounded bytes. It rejects special objects through an O_PATH pin before any
read-capable open. Its root must be separate from legacy artifact/static mounts.
It is not a hostile-tree snapshot, public HTTP Range/HEAD service or Windows
runtime implementation. Initial bounds are 256 KiB inputs, 1 MiB result envelope,
64 output records per Run (including aborted records), 64 MiB per object,
64 KiB chunks, leases up to one hour and retention up to one year. Full quotas,
GC, output-secret policy, compiler/provider admission, production actor/provider
wiring, adapters and Canvas execution integration remain separate gates; this
private slice does not accept whole #83/#86/#129/#127.

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


## Generated Package compiler preparation

The compiler can consume a trusted-host-prepared RCC cache only when the exact
staged `package.yaml` raw-byte digest matches its bounded local receipt. RCC
publish/exec replay uses `--no-build`, rechecks specification/artifact identity
and retains the actual worker compatibility check. The local cache path is
preparation evidence, never portable manifest data or admission by itself.
Trusted dependency preparation may use the existing proxy allowlist; generated
Python receives the compiler's sanitized child environment without proxy,
account or auth settings. Accurate Linux library detection requires trusted
system executable directories `/usr/sbin` and `/sbin` for `ldconfig`; retaining
that probe is different from bypassing compatibility. RCC18.19.3 exec JSON is
one top-level result object, including nested repeated artifact identities.
Generated unittest discovery uses the supplied `tests/` as its top level, so
immutable source need not acquire an invented `tests/__init__.py`. Successful
build/cache publication alone is not generated import/test or Runtime Run
execution evidence. Recompute every compiled preimage and require measured
successful phase receipts before common Package admission.

Native Package admission uses an explicit `ExecutionSnapshot.capability_authority`
value of `package-revision`. The existing common Run control plane and service
require an injected CapabilitySchemaPort for that value; absence never falls
back to a matching legacy Action row. The verified schema view must bind the
exact Action identity, Capability, Runtime Plan and input-schema byte digest.
Live native source authorization is checked alongside the existing Run grants,
including idempotent admission replay. This port is not a Package build receipt
or another Run store: the concrete adapter must still verify admitted Package
bytes and permissions. A schema-port fixture proves the boundary, not a genuine
generated backend Run.

Legacy snapshots retain their exact previous JSON encoding: the default
`legacy-action` marker is omitted. The source-codec comparison against
integration d28251090bc390b1c94a4724a0c286ea7f04ac45 verifies equal legacy wire
bytes and rejection of an explicit native marker by that older strict codec.
That focused comparison is not installed-binary upgrade/downgrade or mixed-server
acceptance. Refresh generated managed-client schemas when consuming the new
optional snapshot field; no client may infer source authority from runtime_kind,
Action names or imports.

`foundry.package_registry.FoundryPackageRegistry` joins the existing compiler,
Foundry SQL rows and private output provider. Its host-configured compiler
requires explicit trusted-developer execution admission plus live
`generate_backend` and Workspace `deploy` policy. Only the exact locally held
compiler object can cross admission; a reconstructed object or client-supplied
phase receipt grants nothing. Pending objects are a bounded local call bridge,
not durable state. After admission, every load remeasures sealed source bytes
and verifies the manifest, inventory, schemas, plan, adapter and build receipt.
Fresh-process readback uses SQL and provider objects, not that memory bridge.

Package admission serializes on the common Workspace lock. Package row,
request, audit and newly created source-reference grants commit together.
Duplicate builds preserve the first admitted bytes and never restore revoked
reference grants. The derived Run Action identity does not create a legacy
Action row. This proves Package/Run admission, not execution of a business job.
Run/Attempt execution, explicit Work Items mode and external-effect recovery
remain separately required.

The source seal is created before SQL publication. If publication fails or its
acknowledgement is uncertain, retain that owned seal until authoritative SQL
reconciliation proves it unreferenced; never delete on a timeout assumption.
Only a proven unused duplicate seal is discarded immediately. This adapter
does not qualify general orphan retention/restore or automatic retry.
`verify_invoice_queries.py --compiler-receipt <exact-prepared-receipt>` adds
genuine RCC build/import/test-to-Package admission against both owned SQL
providers. Its strict `package_compiler` selection rejects skipped cases.
That receipt is a cache precondition, not a replacement for generated-code
execution or a claim that RCC is a malicious-code sandbox.

Normal Runtime Canvas wiring passes the same facade through
`start_server` -> `_ActionRoutes` -> `McpServerSetupHelper`; constructing the
last helper only in a test host does not qualify the installed product. The
canonical frontend producer embeds `canvas.html` beside the Runtime's
`index.html`, including debug builds. Native bootstrap requires the MCP Apps
artifact marker and the existing authenticated Runtime owner key; missing
assets/auth or an unsupported private filesystem provider stay unavailable.
Never substitute the admin HTML or a fixture to make discovery look healthy.

The first authenticated native bootstrap records its nonsecret Actor/Workspace
and initial owner policy in the common SQL request/audit/grant records under
the existing installation lock. Restart reuses that receipt and never restores
deleted grants. Exact bearer verification supplies the model audience; arbitrary
audience/Workspace/principal headers and duplicate Authorization headers grant
nothing. This owner-key mapping is not a multi-user identity adapter or an app
audience grant. Generated execution profiles and app interactions still require
their real, separately admitted services.

Startup preserves Runs with common RunPin admission. The legacy blanket
restart cancellation policy applies only to unfenced process Runs. A restart
does not prove a native Attempt had no effects, and must not erase its retained
claim, launch, result or reconciliation evidence.

For an archive-based installed-consumer gate, supply read-only `GIT_DIR` and
`GIT_WORK_TREE` only to the frontend producer so its timestamp comes from the
exact archived commit. Remove those variables before Poetry builds the wheel:
Poetry otherwise detects Git through that environment but constructs a missing
archive-local `.git` path for its exclusion scan. Keep the failed attempt;
this is a build-context error, not evidence of a dependency defect. Generate
OAuth configuration only with the archived public producer and copy/measure the
pinned RCC binary through the checked-in offline-build mechanism. Never include
an existing checkout's local OAuth file.

A clean noneditable consumer must assert imported modules reside under its own
`sys.prefix`, compare Runtime wheel members to the archived producer bytes, and
launch the normal CLI from an empty owned directory with separate state roots.
An actual MCP SDK over a loopback socket can then qualify discovery, resource
read, edits, explicit activation and process restart/reconnect/rollback. A build
or ASGI transport test alone does not establish this installed route. This
protocol proof still does not qualify an official browser host, generated
business execution, authenticated ChatGPT, or offline replay of dependencies.

An official browser host can keep an MCP HTTP stream open after tools/resources
are ready. Use the discovered tool and the iframe's expected rendered content as
readiness conditions, rather than browser `networkidle`. Preserve a timed-out
attempt and verify owned-process cleanup before retrying the fixture. A screenshot
of a real AppBridge/double-iframe render qualifies only the exact installed bytes
and operations exercised; read-only rendering does not prove app-side dispatch,
approval, artifact resolution or authenticated ChatGPT acceptance.

`ReviewedGeneratedRun` is a trusted host adapter over the existing review queue
and Run/output service. It requires an already registered native Package
snapshot with the exact reviewed application/deployment pin. Its initial input
policy passes the bounded sealed UTF-8 result as the Action's `value: str`;
transport arguments cannot replace those bytes. Wider parameter mappings are
not implied. This adapter does not select a Deployment, create a grant or mount
a public execution endpoint.

Its per-dispatch output adapter rechecks the explicit decision, reviewer's live
read/review grants, current Package execution grant, exact inputs, Work Item
claim and Run fence. Renewal extends both leases; final output publication and
the Work Item terminal write share one SQL transaction. Provider sealing still
happens outside that transaction and retains the existing abort/uncertain-seal
rules. A live Run fence alone never authorizes a stale Work Item owner.

Explicit no-launch recovery requires the same exact approved item, a new live
Work Item claim and an expired Run Attempt. It uses the existing Run recovery
admission and common request/audit to retain both old and new tickets. A prior
launch marker blocks this path even if no result exists. Missing output is not
proof of no effects. Reconstructing an adapter in one interpreter is not a
fresh-process restart proof, and a fixture snapshot registration is not proof
of the full active-Deployment resolver or public app dispatch.

Dedicated RCC cases may materialize several copies of the same retained
Artifact under distinct compiler workspaces. On a small task filesystem,
prepare an explicitly owned RCC home and opt into serial view cleanup with
the `.actions-owned-compiler-fixture` marker
`actions.task-owned-compiler-fixture/v1`. The compiler verifier recognizes that
marker; the dedicated fixture checks for active executables/cwds, saves view
metadata and RCC dry-run/delete receipts, then uses pinned `rcc holotree delete`
for recognized views. It preserves Artifact/catalog/package caches, source and
build evidence. An unrecognized partial view is not removed by a fallback
filesystem deletion. Missing admission, active processes or a failed supported
cleanup remains a failed gate. Cleanup success does not establish the original
compiler failure's cause.

Runtime consumes logging through the public `actions.server_integration` exports.
The bridge preserves the owned logger objects and secret-redaction behavior.
Resolve optional child trace logging only when requested: older owned Core
without the bridge can execute ordinary actions, but a trace request must fail
with a clear upgrade requirement. Legacy fallback requires the selected Core
distribution's explicit logging dependency; failures inside an available bridge
propagate. Simulated compatibility tests do not prove retained-wheel execution.
Runtime's own viewer imports require Core 1.1.0a8 or later.

For asynchronous transport ExceptionGroups, retain bounded nested exception
classes and frame locations. Exclude arbitrary messages, locals and structured
error payloads. Outer-group-only diagnostics can conceal the failing operation.
A reviewed source correction requires a new installed candidate; keep the earlier
failed receipt unchanged. Identical Core bytes can retain their existing
same-target compiler proof without transferring trust.

Treat disappearing child metadata during shutdown as an expected enumeration
race: skip the vanished captured child without recapturing its numeric PID for
signaling, continue other owned children, and preserve unexpected metadata and
watcher errors. This narrow logging-race correction does not turn best-effort
legacy process cleanup into proof of descendant termination.

RCC wrapper and Python child working directories can differ: the wrapper uses
the source directory while the execution Python uses its holotree materialization.
A cancellation observer must bind the exact child program and arguments, source,
ancestry, process group and executable bytes; source-cwd equality alone can miss
a live execution. A failed observer before cancellation is not a cancellation
result. Prove early child termination while Runtime remains alive, with a
bounded deadline shorter than the fixture's natural completion.
