# #131 public Data / Knowledge integration plan (read-only)

Inspected source HEAD `62e0a02fe787e5e0f073e1ae25b0a9cb64b118be` and saved acceptance in `remaining-acceptance-reconciliation.json`. This is a design, not implemented or tested behavior. No source, root configuration, provider data, RCC/cache, remote issue or external repository was changed. Existing operator/descriptor patches remain separate and frozen.

## Finding

There is no small route-only change that completes #131. Reuse the existing immutable Deployment binding and common Run/output authorities, but join them to real generated Package requirements, explicit operator provider configuration, typed named operations, a worker-access boundary, and public authorized discovery/results. The bounded first usable flow is: operator provisions one compatible provider revision; an unchanged Package declares a logical requirement; authoring selects an authorized assignment; execution resolves the exact retained assignment; a named typed read/search publishes a sealed handle; another authorized Runtime reads/pages/exports that handle. Repeat with a second compatible provider and a new Deployment revision, preserving the same Package bytes and earlier Run pins.

That flow does not alone complete durable ingestion, split provider-service transport, arbitrary writes, all advanced Knowledge operations, or the full owner campaign. Keep those explicit release gates.

## Verified existing seams and gaps

| Evidence | Existing behavior | Missing join / consequence |
|---|---|---|
| `deployments/foundry_values.py:153,451`; `foundry_service.py:214,402,433` | BindingAssignment maps a logical requirement to an immutable ProviderProfileRevisionRef. Resolve authorizes requirement/provider, retains exact bindings in the immutable Deployment, and filters by selected capability. | Reuse this mechanism. Do not add a mutable “current provider” pointer to Run state. |
| `tests/.../test_foundry_deployments.py:1041` | A component test proves an in-flight Run retains its earlier Deployment binding while the current Deployment changes. | Uses fixture Package/authorization ports; it is not ordinary generated-Package binding qualification. |
| `deployments/package_revision_compiler.py:1201`; `foundry/package_registry.py:98,489` | Generated manifest always has empty logicalBindingRequirements; native capability declarations default to no binding requirements and get_binding_requirement returns None. | Need deterministic typed requirement declarations and registry projection from artifact-verified canonical manifest bytes. |
| `foundry/runtime_profile.py:112` | RuntimeDeploymentSelection explicitly rejects a capability with binding requirements. | Ordinary generated authoring cannot currently select these bindings. |
| `foundry/authoring.py:108,196,206` | Canvas binding targets select capabilities; they are not Data-provider binding configuration. | Do not overload UI binding labels with DSNs, SQL, local paths or provider execution instructions. |
| `run_outputs/types.py:50,103`; `foundry_service.py:366` | Snapshot has legacy invoice-specific data_binding; generated snapshot construction does not populate it. | Preserve invoice compatibility. Generic bindings can resolve through snapshot.deployment and ResolvedDeploymentExecution; avoid making every Run carry invoice schema. |
| `data_queries/invoices.py:22,160,200`; `service.py:43,81,107,154` | Named parameterized invoice reads on real DuckDB/PostgreSQL, limits/cancellation, sealed NDJSON outputs and bounded page/export through common outputs. source_version is an operator claim; DuckDB transaction label is not immutable source proof. | General typed operation/requirement catalog, source provenance, public configuration and ordinary execution join missing. |
| `foundry/bootstrap.py:253` | Ordinary Runtime constructs InvoiceQueryService(outputs, {}). | No injected data provider configuration; authenticated Canvas does not magically obtain a source query binding. |
| `data_queries/knowledge.py:81,92,536` | Operator-injected LocalCollection map, abstract authorizer, bounded lexical search, real DuckDB/PostgreSQL implementations. Source digest binds file names/bytes. | No common SQL public collection/binding authority or bootstrap wiring; production searches found no other source consumer of KnowledgeCollectionService/LocalCollection. |
| `knowledge.py:240,423` | Ingestion replaces documents by workspace+collection ID; provider records contain source_version. Open reads keep one engine snapshot. | Old collection revision is not independently retained for a newly started old-pinned Run. Public revision semantics require immutable collection versions or immutable retained source reconstitution, not just an in-process binding map. |
| `knowledge.py:560,577` | Ingest synchronously loads/publishes documents; search returns inline hits and scores. | No common Run/Attempt ingestion journal, durable task/status, fenced acknowledgement reconciliation or sealed Knowledge output handle. |
| `knowledge.py:128`; `docs/skills/repository-operations.md:4255` | File bytes are read before aggregate budget is checked. | Public ingestion must enforce bounded streaming/preallocation and protected-path validation before read, not expose the current helper directly. |
| `tests/.../test_knowledge_collections.py:32,179,280` | Injected test authorizer, persisted provider revocation across service reconstruction, real engine snapshot concurrency. | Not ordinary public SQL grants, fresh Runtime/provider processes, actual model/app traffic or Task recovery evidence. |
| `mcp/gateway_metadata.py:69` | Task method names are recognized for gateway metadata. | That is not a Run-backed Task implementation. No common task store/executor join was located in this inspected source surface. |

## Contract and implementation sequence

### 1. Declare the portable requirement and operation contract

Extend existing immutable Package generation, not the mutable Action database. A logical requirement needs a stable logical ID, kind (`data` or `knowledge`), versioned named operation contract, typed parameter/result schema digests, effect classification (read versus ingest/write), and bounded policy constraints. None may carry a provider class, binary/plugin/socket selection, DSN, file path, endpoint or credential. Provider compatibility is checked against the requirement's contract, not a display label.

Start with an explicit bounded named operation set: the preserved invoice read, one second generic records read, lexical Knowledge search, and bounded Knowledge ingestion. Keep read schemas separate from management operations. SQL text is a trusted host adapter implementation, never a model/package-supplied query. Schema aliases must use canonical bytes and be verified against the selected capability/requirement; wrong capability, schema digest, schema defaults containing secrets, overlarge schemas and unknown fields fail closed. Manifest schema evolution must preserve verification of existing zero-requirement Packages.

Files: `deployments/package_revision_compiler.py`, compiler contract tests, `foundry/package_registry.py`, `deployments/foundry_values.py` (typed requirement declaration/protocol, retaining BindingAssignment), and a new bounded `data_queries/contracts.py`. Extend the native declaration's binding_requirements and get_binding_requirement using the verified manifest. No automatic runtime-plan fallback.

### 2. Add explicit persistent operator provider revisions

Add a common-SQL provider revision repository (new model/migration under the existing DB, not another control database). The canonical nonsecret descriptor includes compatible operation/schema versions, bounds/effect policy and retained source/collection version identity. Physical connection information remains an operator-owned host configuration/secret resolver outside Package artifacts, model schema, Run payloads, receipts and logs. Public discovery must not return that private host lookup, paths or endpoint credentials.

Provide an explicit local operator configuration flow, separate from granting authority. It validates an allowlisted built-in adapter and source manifest/configuration, registers a canonical provider revision, and prints its typed reference. Changing provider policy/schema/source identity creates a new revision; do not mutate the earlier revision. Reuse the owner realm, canonical mutex, Request/Audit and CAS patterns of the separately reviewed operator patch. Do not silently install credentials, mint grants or require a proprietary service. Deployment/source permission changes remain explicit operator actions; add named Data read/manage grant scopes rather than treating Canvas-read as ingestion authority.

Files: new `data_queries/provider_registry.py`, `data_queries/provider_config.py`; common models and migration; narrowly extended explicit CLI command/parser; existing local operator helper only after its separate patch is integrated. Tests must prove no credentials in canonical descriptor/output, duplicate/conflicting registration, restart, revocation, wrong owner/workspace and provider contract mismatch. A common PostgreSQL deployment needs a separately reviewed online/admin or coordinated operator protocol; the local offline SQLite mutex must not be reused as proof of remote quiescence.

### 3. Join authoring selection to the retained Deployment

Extend the existing authoring input with an explicit map from declared logical requirement IDs to authorized provider references. This is separate from Canvas binding IDs and is resolved only after the compiler produces the actual Package revision. Extend RuntimeDeploymentSelection to construct exact BindingAssignments, validate typed compatibility, and reject missing/extra/ambiguous assignments. Expose bounded authorized provider-operation discovery so an independent model can select a reference without private fixtures. Readback includes safe logical IDs, compatible named operations and typed schemas; private connection configuration remains hidden.

Publish/update/rollback through existing FoundryDeploymentService CAS. New provider selection produces a new Deployment revision; identical Package/source/compiler bytes remain unchanged. Resolve a running operation from its retained snapshot.deployment, never current deployment or a process-global default. Explicit revocation still rechecks live grants on each execution/result read.

Files: `foundry/authoring.py`, `authoring_values.py`, `runtime_profile.py`, `deployments/foundry_service.py` and `foundry_repository.py` only if new compatibility validation requires it; safe discovery module/wrapper; existing bootstrap. Reuse current binding authorization and tests rather than duplicate it in HTTP routes. `ExecutionSnapshot.data_binding` remains the legacy invoice path; avoid an unnecessary generic Run schema migration when retained Deployment assignments already identify the binding.

### 4. Join named operations to the common Run/Attempt and worker boundary

Add a typed `BoundOperationContext` resolved by trusted server code: exact snapshot, selected requirement/provider revision, named operation/schema, live actor authority, limits and current Attempt fence. Input validation precedes any provider I/O. The implementation accepts this context, not caller-chosen provider/configuration. Stage bounded typed results with RunOutputService and publish only with the current fence. Data failures/cancellation must not produce a successful seal or silently retry uncertain effects.

A concrete missing primitive must be implemented, not hidden: generated RCC Python currently has no provider-neutral logical binding client/port. The invoice worker reads sealed input and writes a result; it does not provide this API. A reviewed host-injected worker operation port is required for actual Package code to call its declared operations. The narrow design is an attempt-scoped client that names only its declared logical requirement and operation; the trusted host resolves credentials/configuration. Any transport credential is ephemeral, bound to the exact Run/Attempt and operation allowlist, absent from durable plans/logs, and not a new user grant. The host, never Package code, chooses endpoint/transport. It must be impossible to select another actor/workspace/provider or arbitrary SQL through that port. Reuse the existing Runtime HTTP/process boundary if selected; do not create a second scheduler/database or treat a fake RCC plan as a provider adapter. Selecting/implementing this worker delegation protocol requires explicit integrator review before source work.

Files: new `data_queries/bound_operations.py`, new narrow worker-client API in `actions/src/actions/` and host route/IPC adapter, existing `foundry/rcc_execution.py` / generated execution adapter for trusted injection and cleanup, `run_outputs/service.py` only for a genuine missing typed authority seam. Preserve source-neutral plans and existing invoice service behind the same typed operation projection. Keep model-facing calls binding-based; never expose internal worker credentials or fences as model-selected authority.

Proposed typed interfaces for this join (design only):

```python
ProviderRegistry.resolve_operation(
    actor: Actor,
    resolved: ResolvedDeploymentExecution,
    requirement_id: str,
    operation_id: str,
    fence: AttemptFence,
) -> BoundOperationContext

BoundOperationExecutor.execute(
    context: BoundOperationContext,
    parameters: dict[str, JsonValue],
    cancelled: threading.Event,
) -> Iterator[TypedRecord]
```

The first method checks that the requirement belongs to the selected capability, its assignment is in the exact retained revision, provider/schema/effect compatibility matches, all grants remain live, and the Attempt belongs to that snapshot. The second receives no credential/path/endpoint supplied by the caller; it resolves a trusted host adapter and produces bounded typed rows for common output staging. Reads and ingest have distinct parameter/result DTOs. A narrow worker client may forward only declared requirement/operation IDs and schema-validated parameters; it cannot construct the trusted context.

The first independently reviewable implementation checkpoint is the real compiler/registry requirement declaration plus exact authoring selection and authorization negatives (steps 1–3). It is a prerequisite, not a completed public provider flow. The first complete public read/search checkpoint additionally requires the worker operation port, common sealed result publication and installed discovery/readback in steps 4 and 6. Full #131 additionally requires step 5 and both deployment modes. Do not relabel either prerequisite as full acceptance.

### 5. Retain Knowledge versions and make ingestion recoverable

Keep provider data in DuckDB/PostgreSQL, with shared control state only in the existing Runtime SQL authority. Version collection rows/documents by immutable collection/source revision instead of destructively replacing the sole version. Publish a new collection version atomically, preserving prior versions required by pinned Runs; operator removal/expiry needs explicit retention policy. Provider-engine mutation and common SQL publication are not a distributed transaction: use a stable operation idempotency key and a provider-visible receipt/version lookup to reconcile lost acknowledgements. Never label an uncertain ingest as absent or blindly rerun it.

Route ingest/index work through the existing canonical Run/Attempt lifecycle and a Run-backed Task/status projection. The client disconnect must not own the job lifetime. Reuse existing worker admission/claim/fencing/cancellation; do not introduce another queue or private ingestion thread scheduler. Ingest rechecks read+manage, uses streaming file budgets and retained source manifests, fences provider publication, and records verified source/schema/row-count provenance. Search stages durable NDJSON hits and exposes handles; app-scoped reads may page rows while model discovery remains bounded and handle-first. Lexical search is accurately labeled, not semantic/vector proof.

Files: `data_queries/knowledge.py`, new `data_queries/knowledge_runs.py`, existing common Run/output transport, the separately required Run-backed Task projection (#85), and provider tests. This is necessary for #131 long ingestion, not optional evidence that can be replaced by synchronous component tests.

### 6. Public result/operator flow and deployment modes

Mount authorized discovery/invoke/status/result-page/export on existing public Runtime/MCP/Canvas surfaces. Use the current model/app audience separation and exact CanvasResultScope for app rows; do not put data rows or connection metadata into default model responses. Persist metadata and output seals once; another Runtime with the same common SQL and explicitly configured compatible output/provider service must resolve them after process restart. A PostgreSQL database connection by itself is not proof of the required split provider-service contract. Qualify an allowlisted external provider-service transport with the same operation DTO and policy checks as in-process providers; deployment mode is host/operator configuration, not Package identity or caller input.

Files: bootstrap composition, typed Data/Knowledge projection module, existing run_outputs transport and Canvas adapters, optional provider-service client/server adapter. No proprietary dependency, arbitrary URL forwarding, credential fallback or mandatory vector service.

## Required executable acceptance matrix

1. **Artifact neutrality:** compile the same source twice to exact Package/requirement/schema bytes. Bind it to real DuckDB CSV, DuckDB Parquet and PostgreSQL fixtures without recompilation. Execute the actual Package path, not only a direct provider function. Retain all digests and normalized operation results.
2. **Binding lineage:** A/B revisions with identical Package; admit Run under A, publish B, execute/read A after restart, rollback current to A. Wrong requirement/provider/schema/workspace, missing plan and live grant revocation fail before provider access. No automatic fallback.
3. **Secrets:** sentinel DSN/password/token/source path absent from source archive, manifest/catalog/input schemas, Run input/output, audit/Task receipts, logs, errors and output metadata. Inject hostile aliases/defaults/unknown fields; explicitly inspect installed wire messages. Local secret/config stores remain private and outside immutable Package.
4. **Results:** large bounded read/search publishes a sealed typed artifact. Separate Runtime process/replica pages/exports it using live authorization, with digest/size/expiry/tamper/cross-app/cross-workspace negatives. Model defaults carry handle/summary, app audience gets scoped bounded rows only.
5. **Effects/recovery:** ingest with both read/manage; read-only actor denied. Duplicate request, client disconnect, worker loss before/after provider commit, lost acknowledgement, stale Attempt, cancellation during read/publish, crash after staging before common publication. Exactly one visible collection revision or explicit uncertainty requiring reconciliation; no success fabrication or implicit replay.
6. **Modes:** same named-operation contract through single-binary in-process DuckDB and independently hosted provider-service transport, including outage/timeout/cancel/auth. PostgreSQL provider-engine tests remain separate from control-plane PostgreSQL tests.
7. **Installed public flow:** fresh operator config/explicit grants, official MCP client authoring/discovery/selection/invoke/restart/reopen and browser app table/export evidence. No private SQL setup disguised as public provisioning; retained files/receipts from real installed flows.

Existing files to extend: `test_foundry_deployments.py`, compiler contract tests, `test_foundry_package_registry.py`, `test_invoice_run_outputs.py`, `test_knowledge_collections.py`, `run_outputs/test_transport.py`. Proposed focused new files: `test_data_binding_contracts.py`, `test_provider_registry.py`, `test_data_binding_authoring.py`, `test_bound_operation_execution.py`, `test_knowledge_runs.py`, `test_data_knowledge_public.py`, and installed harnesses. PostgreSQL skips are missing evidence, never substituted with SQLite.

## Exact canonical guide correction proposed

Insert after `docs/skills/repository-operations.md` “Bounded Knowledge collection provider proof”:

> These are provider-component contracts, not the ordinary public #131 Data/Knowledge product flow. Generated Package manifests currently declare no logical binding requirements, the native Package registry returns no requirement declarations, ordinary RuntimeDeploymentSelection rejects such requirements, and ordinary bootstrap supplies no data providers or Knowledge collection service. Existing Deployment BindingAssignment/ResolvedDeploymentExecution correctly retain and authorize immutable provider references, but their component fixtures do not establish generated-Package/operator/discovery integration.
>
> Knowledge ingestion/search currently use an injected authorizer and in-process binding map. Search returns inline hits; ingestion is synchronous and replaces the provider collection's sole version. It is not a common Run-backed durable ingest/Task or a retained historical collection-version contract. Opening one engine snapshot during concurrent reingestion protects that open read; it does not make a later old-pinned Run able to reopen an overwritten collection version. File preallocation/streaming bounds remain separate from post-read aggregate checks.
>
> To claim public integration, qualify explicit operator provisioning and live read/manage grants, artifact-verified logical requirements, exact Deployment assignment, actual Package execution against two compatible providers without Package mutation, sealed handle-first results across real Runtime restarts/replicas, and durable ingestion/reconciliation under client and worker loss. Source-version claims, PostgreSQL engine connectivity, metadata Task method names and injected fixture ports are not respectively retained source proof, split provider-service proof, Task execution or ordinary public setup. Advanced vector/embedding/rerank, incremental reindex/delete, rich filters and provider discovery remain explicitly tracked; a bounded lexical slice does not erase them or waive other campaign gates.

## Documentation improvement receipt

- Canonical file proposed: `docs/skills/repository-operations.md`; exact correction above. Ledger rows 576–577 should retain their current missing-integration classification until the corresponding installed gates pass.
- Durable learning: precisely separates immutable Deployment/component authority from generated Package declarations, operator provisioning, worker operation access, durable Knowledge versions and public integration.
- Evidence: cited source/tests, saved #131 acceptance, release ledger rows 576–577 and 751/777. No new tests were executed for this read-only design.
- Stale/ambiguous guidance removed: component provider passes cannot be counted as ordinary Data/Knowledge, Task, source-snapshot or split-service acceptance.
- Remaining uncertainty: exact worker delegation transport and existing canonical Task/worker protocol must be reviewed before implementation; no production credential/operator provider configuration was read. Full #131 and full owner scope remain required.

Upstream disposition: none. Located gaps are repository-owned missing integration, not evidence of a dependency defect. No external targets were authorized or mutated.
