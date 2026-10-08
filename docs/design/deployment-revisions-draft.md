> Paused draft, October 8, 2026. Not approved, implemented, or ready to merge. Published only to preserve existing work for adversarial review.

Open review points: this packet is an unapproved design proposal. Its earlier schema sketch omitted concrete composite-FK column tuples, the same-Deployment FK for `deployment_revision_request.parent_revision_id`, and backend-specific cyclic-pointer creation details; the schema contract below now specifies them. None of these requirements has been implemented or proven by the repository.

# Actions Deployment and Revision Contract

**Design-only #129 contract. This document is not implementation, source verification, issue closure, or #82 acceptance.**

- Repository: `joshyorko/actions`
- Original inspected source: `8bdce09944c9e370917a8222243cd1a239ea7060`; the review packet verified its relevant code remained unchanged at `848e0bbc`. This branch updates design text only; verify implementation evidence again at any later target-branch head.
- Live issue state checked 2026-10-08: #129 is open (body last updated 2026-09-07) with no comments. #82, #130, #135, #136, and #148 are also open. Relevant live comments: #82 comment `5373995960` separates optional Work Items, Robot Task kind, adapter kind, and placement; #130 comments `5335430196` and `5374010203` sequence #134 → #135 → #136 → #129 and keep package authoring separate from compiled contract; #135 comment `5374000307` extends compilation for Robot Tasks. #129 has no comments. The full bodies/comments are upstream acceptance authority; the ledger is an accounting snapshot, not a substitute.
- Scope: settle the minimum local-first object identities, immutable revision model, resolution boundary, and downstream handoff. This is not #130's compiler, #135's package compiler, #136's registry/cache, #143's adapter/preflight implementation, or #83's Run/Attempt store.
- Non-goals: no source edits in the source checkout, no multi-tenant control plane, no generic scheduler, no new service/process decomposition, no adapter implementation, no claim #129/#130/#135/#83 is complete.

### Decision boundaries

- #129 fixes Workspace-scoped identity/references, immutable Deployment Revisions, publication/replay/CAS behavior, the Current-versus-Retained selector, static resolution snapshot, and lifecycle semantics.
- #130 owns Package manifest, Capability and logical binding requirement syntax, Runtime Plan payload and projection schemas. #129 carries full references and a minimal generic Runtime Plan header; it does not invent those payload schemas.
- This design can name opaque Package Revision/Runtime Plan references before those producers are complete, but package-backed binding/index/repository implementation follows the live #130 ordering: #134 contract, #135 compiler, #136 package provider, then #129 Deployment binding/resolution. Do not treat #129 design readiness as permission to invent the missing compiler/provider schemas.
- #143 owns complete adapter descriptors and dynamic admission modes, outcomes, evidence and freshness after the remaining #134 lifecycle proof. A minimal versioned `AdmissionSnapshot` envelope is pinned to the exact `ResolutionDigest` here; its dynamic contents are not.
- #83 owns Run/Attempt persistence and the transaction that commits an admitted Run pin. The transaction boundary and its required pointer/state rechecks are part of the handoff contract below.
- #84 remains a source-schema gate: its current PostgreSQL/SQLite implementation receipt exists, while current package/frozen gates remain open. #134 blocks #143 adapter-contract freeze, not generic #129 IDs or CAS. #140 owns mixed-version rollout enforcement.

## Decision summary

Use a Workspace-scoped relational control-plane model with immutable content/revision records and one mutable pointer per logical Deployment. Keep Package/Capability/Runtime Plan identity separate from Deployment binding/projection/Worker Profile policy. Resolve one selected plan into a typed immutable execution snapshot before calling the #83 Run service. Pin every full reference and revision in that snapshot. Deployment updates use compare-and-swap on the current revision pointer; rollback publishes a new revision whose config matches an older revision. Neither operation mutates a Run or its retries.

Keep the #129 Run/deployment model adapter-neutral without speculating about adapter payload variants. A generic plan reference carries a full `RuntimePlanRef`, `runtime_kind`, plan digest/schema version, opaque `ContractId`, supported adapter-version range, required feature IDs, and a selected-plan compatibility digest. The pinned immutable Package Revision is authoritative for the namespaced plan payload; #129 does not duplicate it in the snapshot. #130 owns the manifest; #143 owns complete adapter descriptors, payloads, admission and lifecycle after its #134 proof boundary. Generic IDs, references, revision storage and CAS do not wait on #134. The current RCC identifier `rcc-runtime/v1` remains opaque and is never parsed as a semantic version.

The simple installation synthesizes one stable default Workspace, SQLite-backed state, an explicit local Worker Profile, local files, the bundled RCC adapter where present, and the existing local process worker. The default workspace is stored in the database and never inferred from a directory, port, Runtime PID, Kubernetes object, or provider account. All control-plane references carry Workspace scope; same-workspace checks and composite scoped keys/FKs reject cross-Workspace references. No role requires a new service.

## Grounding and evidence

### Live issue requirements

- [Issue #129](https://github.com/joshyorko/actions/issues/129) requires Workspace, Package/Package Revision, Capability, generic Runtime Plan selection, Deployment/Deployment Revision, bindings, projection, Worker Profile, deterministic Run pinning, update/rollback, single-Workspace local behavior, and safe multi-Workspace references. It explicitly says exact table/API names require approved design and declares no hard dependency header. It corrected its initial RCC-shaped assumption: generic Runtime Plans come from #130/#143, with RCC identities preserved only inside an RCC plan.
- [Issue #130](https://github.com/joshyorko/actions/issues/130) owns Package v3. Its current body distinguishes source/capability artifacts from RCC Environment Artifacts and Run outputs, asks for explicit typed plans/projections, and rejects credentials, provider URLs, local paths, worker state, and package-selected executable plugins as portable identity. Its comments `5335430196` and `5374010203` sequence #134 → #135 → #136 → Deployment binding and extend the manifest for #143/#144 without forcing Robot Tasks into `@action` or an arbitrary environment bag.
- [Issue #143](https://github.com/joshyorko/actions/issues/143) owns generic adapter descriptors, requirements, preflight, admission modes and second-adapter conformance. Its full adapter-neutral freeze remains behind its #134 proof boundary; that is not a blocker for #129 generic identities, revision storage or CAS. This packet defines no adapter methods or fallback ordering.
- [Umbrella #82](https://github.com/joshyorko/actions/issues/82) requires the same local and split semantics, real RCC as first adapter, a genuinely different second adapter, pinning, worker/profile identity, no fallback/simulation, and a retained single-binary experience. Comment `5373995960` states Work Items are optional context and Robot Task, adapter kind, and placement are distinct axes; it orders Robot Task support over common Package/Run infrastructure rather than a parallel subsystem.
- [Issue #83](https://github.com/joshyorko/actions/issues/83) owns durable Run/Attempt authority and must persist the resolved Deployment Revision, Package Revision, capability/schema, selected plan, binding/policy, and Worker Profile. This packet defines that input type but does not create Run state.

### Repository evidence at the inspected subject

- `actions-convergence/AGENTS.md`, `.agents/skills/actions-repository/SKILL.md`, `docs/skills/README.md`, and `docs/skills/repository-operations.md` were read. Canonical docs guidance is evidence-only; this design is not implemented behavior.
- `action_server/src/actions/server/_models.py` has path-backed `ActionPackage` (`directory`, `conda_hash`, `env_json`), `Action`, and legacy `Run` (`action_id`, Robot path/task/environment hash, old status integers). It has no Workspace, Package Revision, Runtime Plan, Deployment Revision, binding, or Worker Profile model.
- `action_server/src/actions/server/_api_action_package.py` builds list responses by reading `package.yaml` from the mutable package directory. `_actions_run.py` creates and updates the legacy Run record; `_api_run.py` exposes legacy Run read/cancel/artifact routes. This makes an additive migration and explicit bridge safer than silently reinterpreting old records.
- The current path-backed flow is split across `_ActionRoutes.register_actions()` (loads ActionPackage/Action DB rows to register HTTP/MCP behavior), `_api_action_package.list_action_packages()` (reads current package metadata from disk), and `_actions_run._create_run()` (persists a legacy Action ID Run and binds artifact storage/cache state). The new domain owns static resolution and the Run service; HTTP/MCP/CLI handlers become thin callers instead of adding independent package parsers.
- `action_server/src/actions/server/_database.py` is a compact SQLite/PostgreSQL facade with thread-local connections, transactions, and dataclass-backed row models. The migration registry in `action_server/src/actions/server/migrations/__init__.py` is currently immutable IDs 1–12. New tables should be added by a numbered migration after that registry, not by rewriting an applied migration.
- A relevant migration trap: `Database.initialize()` only registers model classes, but `create_db()` and the fresh-PostgreSQL branch of `migrate_db()` directly create all registered model tables and stamp the current migration version. A new default Workspace/bootstrap placed only in a numbered upgrade migration would be skipped on those fresh-database paths. Invoke one idempotent schema/bootstrap helper from the upgrade migration and both fresh-schema paths; keep their SQLite/PostgreSQL DDL and scoped constraints identical.
- `action_server/src/actions/server/_rcc_runtime_adapter.py` currently has `RccRuntimeDescriptor`, canonical JSON, RCC artifact digest validation, and local process evidence. It is deliberately RCC-specific and provisional. Preserve `rcc-runtime/v1` as an opaque `ContractId`; do not parse it as a semantic version or copy its RCC fields into generic identity.
- `actions-release-audit/foundations-ledger.json` and `full-graph-ledger.json` are aligned to subject `8bdce099…`. They record #129 as design-ready, #130 blocked on #129, #135 blocked on #130/#134, and #83 blocked on current #84 acceptance plus #129. They also correct old draft-only claims: PR #109 (database/#84) and PR #197 (RCC/#134) are merged. The accepted real RCC Action execution receipt is PR #197 comment `5572191068` at merged head `1a556431`; relevant adapter/pool/import/test paths are unchanged through `8bdce099`. That proves the cited real Action execution only, not all #134 lifecycle/distribution acceptance. PR #109's merged PostgreSQL/SQLite test receipt is comment `5571681251`; current clean-install/frozen gates remain open. Do not reuse stale draft comments as current state.

## Contract types and ownership

Use Pydantic v2 frozen models for boundary/domain values and a typed `DeploymentRepository` at the persistence edge. Public JSON enters as raw UTF-8 bytes and is parsed with a duplicate-preserving parser before Pydantic runs. Reject duplicate property names before normalization, invalid UTF-8, lone surrogates, and non-finite numbers; then NFC-normalize keys/strings and reject duplicate keys created by normalization. Pydantic receives the validated tree with strict coercion and `extra='forbid'`. IDs use runtime-validated semantic parsers/`Annotated` validators; Python `NewType` alone is not runtime validation. TypeScript clients treat server-issued IDs/digests as opaque. If a JavaScript path ever computes an identity, it must pass the same byte-and-digest golden vectors as Python before it can author or validate it.

### Workspace and scoped references

```text
WorkspaceId = UUID
PackageId = UUID scoped by WorkspaceId
DeploymentId = UUID scoped by WorkspaceId
ProviderProfileId = UUID scoped by WorkspaceId
WorkerProfileId = UUID scoped by WorkspaceId
PolicyId = UUID scoped by WorkspaceId
PolicyRevisionId = sha256:<64 lowercase hex> scoped by WorkspaceId
PackageRevisionId = sha256:<64 lowercase hex>
DeploymentRevisionId = sha256:<64 lowercase hex> scoped by DeploymentId
ProviderProfileRevisionId = sha256:<64 lowercase hex> scoped by ProviderProfileId
WorkerProfileRevisionId = sha256:<64 lowercase hex> scoped by WorkerProfileId
RuntimePlanDigest = sha256:<64 lowercase hex>
CatalogRevisionId = sha256:<64 lowercase hex>
CapabilityId = non-empty NFC stable package-local key
BindingRequirementId = non-empty NFC stable package-local key
WorkerRequirementId = non-empty NFC stable package-local key
FeatureId = non-empty NFC namespaced adapter feature key
ExposureProjectionId = sha256:<64 lowercase hex>
RuntimeKind = validated opaque registered identifier (e.g. "rcc"); not an enum of speculative adapters
ContractId = exact opaque ASCII token (preserve "rcc-runtime/v1"; never parse as a version)
AdapterVersion = PEP 440 Version parsed by the `packaging` grammar
AdapterVersionRange = PEP 440 SpecifierSet parsed by the same `packaging` grammar
PlanSchemaVersion = positive integer accepted by the Package/RuntimePlan schema registry
CompatibilityIdentityDigest = sha256:<64 lowercase hex>
WorkspacePolicyRevisionRef = { workspace_id: WorkspaceId, policy_id: PolicyId, revision_id: PolicyRevisionId }

WorkspaceRef<T> = { workspace_id: WorkspaceId, id: T }
PackageRevisionRef = { workspace_id, package_id, revision_id: PackageRevisionId }
DeploymentRevisionRef = { workspace_id, deployment_id, revision_id: DeploymentRevisionId }
ProviderProfileRevisionRef = { workspace_id, provider_profile_id, revision_id: ProviderProfileRevisionId }
WorkerProfileRevisionRef = { workspace_id, worker_profile_id, revision_id: WorkerProfileRevisionId }
CapabilityRef = { package_revision: PackageRevisionRef, capability_id: CapabilityId }
RuntimePlanRef = { package_revision: PackageRevisionRef, plan_digest: RuntimePlanDigest }
BindingRequirementRef = { package_revision: PackageRevisionRef, requirement_id: BindingRequirementId }

RevisionSelector = Current | Retained(DeploymentRevisionRef)
PlanChoice = UseDeclaredDefault | Explicit(RuntimePlanRef)
```

The IDs/digests are references, not capabilities. Authorization and scope checks happen on every read/write. SQLite and PostgreSQL both enforce same-Workspace composite foreign keys for every row-backed reference; no backend may silently omit a scoped constraint. The repository also checks each parsed reference in the same transaction; corrupted/legacy mismatches fail closed. References to items embedded only in immutable Package Revision JSON are validated against that canonical manifest on publish and every resolution. Public APIs return `404 not_found` for an out-of-scope reference so they do not disclose another Workspace's existence; internal diagnostics use a sanitized `workspace_mismatch` code.

Workspace owns the trust/policy/provider/adapter/worker/audit namespace. It is not an SaaS tenant or a Kubernetes namespace. The first local installation has one default Workspace, with its generated UUID stored once as installation metadata. The local API/CLI may omit the Workspace ID only through a `DefaultWorkspaceContext`; all domain calls still require it. If multiple Workspaces are later enabled, ambiguous unscoped requests fail rather than selecting the first record. No new authorization service is part of this packet; the existing single-owner local mode maps its authenticated local caller to the default Workspace. Cross-Workspace denial is nevertheless a hard repository invariant.

### Package, capability and plan identities (#130/#135 produce; #129 consumes)

`Package` is a stable logical identity scoped to its Workspace. `PackageRevision` is immutable. `CapabilityRef` is `{ package_revision: PackageRevisionRef, capability_id: CapabilityId }`; `CapabilityId` is package-scoped, stable across MCP names, selected adapter, and placement. #130/#135 own its authoring/derivation rules; #129 only requires that the compiler produce it and never substitutes a model-visible name as its identity.

```text
PackageRevision = frozen {
  package_id: PackageId,
  logical_package_name: NFC display name at compile time,
  revision_id: PackageRevisionId,
  package_schema_version: int,
  compiler_normalization_version: str,
  source_artifact_digest: Sha256,
  capability_manifest_digest: Sha256,
  capabilities: tuple[CapabilityDescriptor, ...],
  runtime_plans: tuple[RuntimePlanRecord, ...],  # opaque payload; #130/#143 own its schema
  logical_binding_requirements: tuple[BindingRequirement, ...],
  provenance_ref: Optional[ProvenanceRef]  # sidecar/reference, not digest input
}

CapabilityDescriptor = frozen {
  id: CapabilityId,
  kind: Action | RobotTask | Workflow | DevTask | Resource | ResourceTemplate | Prompt | App,
  schema_digest: Sha256,
  input_schema: canonical JSON,
  output_schema: canonical JSON,
  compatible_plan_digests: sorted tuple[RuntimePlanDigest, ...],  # sole compatibility authority
  binding_requirement_ids: sorted tuple[BindingRequirementId, ...],
  worker_requirement_ids: sorted tuple[WorkerRequirementId, ...],
  effect/cancellation/timeout/work-item declarations: typed #130/#143 values
}

RuntimePlanRecord = frozen {
  header: RuntimePlanHeader,  # #129 pinning/compatibility fields
  payload: versioned canonical object validated by its owning #130/#143 schema
}

RuntimePlanHeader = frozen {
  plan_digest: RuntimePlanDigest,
  runtime_kind: RuntimeKind,
  plan_schema_version: PlanSchemaVersion,
  contract_id: ContractId,
  adapter_version_range: AdapterVersionRange,
  required_features: sorted tuple[FeatureId, ...],
  compatibility_identity_digest: CompatibilityIdentityDigest
}
```

This is the minimum #129 header/reference, not a closed list of adapter variants. #130 owns the immutable Package manifest syntax and complete plan payload; #143 owns adapter descriptors, the full namespaced payload schemas and feature semantics after the #134 proof boundary. `RuntimePlanDigest` hashes the versioned complete immutable plan payload produced by #130. `CompatibilityIdentityDigest` hashes only the selected plan's versioned generic compatibility header so #83 can pin and compare it without copying the adapter payload. The reverse relation from a plan to supported capabilities is derived from the capability-owned `compatible_plan_digests`; it is not stored as a second authority. A plan is immutable Package Revision content, never an executable plugin or Deployment-created object. No plan list order implies preference. Package source cannot install or select privileged adapter binaries, provider URLs, sockets, images, mounts or host grants.

### Canonicalization and digest identity

The service is the sole identity authority. Only the Python server computes `PackageRevisionId`, `RuntimePlanDigest`, `DeploymentRevisionId`, provider/profile/policy revision IDs, `ResolutionDigest`, and `CatalogRevisionId`; clients parse and return those values as opaque IDs. The current API and UI do not compute these hashes. If any JavaScript path is later required to compute one, it must pass the same committed byte-and-digest golden vectors as Python before use.

`actions-canonical-json/v1` is a domain normalization layered before RFC 8785 JCS, not behavior specified by RFC 8785 itself. The serializer is Python package [`rfc8785`](https://pypi.org/project/rfc8785/0.1.4/) version `0.1.4`, locked exactly in the owning package; `rfc8785.dumps()` supplies the JCS UTF-8 bytes. The service must not switch implementations or versions in place: changing the canonicalizer or serializer implementation requires a new canonicalizer version and new digests. The NFC pre-pass, raw-byte parser, schema checks, and input restrictions below remain this system's behavior, not package behavior.

1. Decode raw request bytes as strict UTF-8. Parse with a duplicate-preserving object-pairs parser. Reject every duplicate raw property name, even if values match; then normalize keys and string values to NFC and reject any duplicate key created by normalization. Reject invalid UTF-8, lone surrogates/non-scalar Unicode, NaN, Infinity, unknown schema fields, unknown canonicalizer versions, and unknown required schema/plan/feature versions. Pydantic validation runs only after these raw-byte checks.
2. Normalize domain JSON strings/keys to NFC, then pass the resulting I-JSON-compatible tree to `rfc8785.dumps()`. RFC 8785 preserves string code points; the NFC pre-pass is this system's explicit, versioned domain rule.
3. Numeric values use finite IEEE-754 binary64/JCS semantics. Accept exact JSON integers only in `[-9007199254740991, 9007199254740991]`; reject larger exact integers, non-finite conversions, and non-zero decimals that underflow to zero. Fractional/exponent values are interpreted as their finite binary64 value and then JCS-canonicalized. Exact larger integers/decimals must be represented as canonical decimal strings or scaled integers in a versioned schema, never silently rounded.
4. Each set-valued array is named in its owning schema and sorted by its stable key before JCS (`compatible_plan_digests`, required feature IDs, binding requirement refs, allowed plan refs, profile refs, projection IDs, and projected catalog entries). All other arrays preserve schema-defined order; no global array sorting.
5. Every identity preimage contains a distinct `domain` tag, the canonicalizer version, and the authoritative schema/normalization version. A version change creates new digests; no stored hash is reinterpreted. Golden fixtures cover raw duplicate keys; post-NFC key collisions; invalid Unicode; `-0` and `1.0`; `1e-6`, `1e-7`, and `1e21`; exact safe-integer limits and their rejected next values; decimal overflow/underflow; map ordering; domain separation; and each identity digest.

`ContractId` and versions are different fields. `ContractId` is an exact opaque ASCII token, preserved byte-for-byte and never passed to a semantic-version parser; `rcc-runtime/v1` remains the current example. Adapter implementation versions/ranges use one grammar: Python PEP 440, parsed with `packaging.version.Version` / `packaging.specifiers.SpecifierSet` (for example, `==18.19.3` or `>=18.19.3,<19`). RCC's current `v18.19.3` is normalized by that parser to `18.19.3`; it does not change the opaque `ContractId`. The range describes compatible adapter implementation versions, not the meaning of the contract ID. The `RuntimePlanHeader` includes both. Unknown contract IDs, required features, plan schemas, or unsupported versions fail closed.

Use separate, domain-tagged hashes:

1. `SourceArtifactDigest = sha256(JCS_v1({domain: "actions.source-artifact/v1", canonicalizer_version, entries}))`. Each entry is `{relative_posix_path, file_kind, normalized_mode, byte_length, content_sha256}`. Exclude source checkout path, mtime/ctime, owner IDs, archive timestamp, and local environment files. Normalize relative paths to NFC and `/`; reject absolute paths, `..`, case-fold collisions, special files, and symlinks for the first trusted v2 compiler vertical. Re-stat/hash after snapshot and fail if the source changed while being captured. This filesystem walk and its security tests belong to #135; #129 only fixes the digest contract.
2. `CapabilityManifestDigest = sha256(JCS_v1({domain: "actions.capabilities/v1", canonicalizer_version, capability_schema_version, sorted capabilities, sorted logical binding requirements}))`; capability schema arrays preserve their declared semantics.
3. `RuntimePlanDigest = sha256(JCS_v1({domain: "actions.runtime-plan/v1", canonicalizer_version, plan_schema_version, runtime_kind, contract_id, adapter_version_range, required_features, normalized complete plan payload}))`. #130 owns the payload schema; #129 consumes the digest/header.
4. `PackageRevisionId` (the canonical Package Revision identity) is `sha256(JCS_v1({domain: "actions.package-revision/v1", canonicalizer_version, package_schema_version, package_id, logical_package_name, compiler_normalization_version, source_artifact_digest, capability_manifest_digest, sorted runtime_plan_digests, compatibility_metadata}))`. Package ID is included so identical source under two logical packages cannot alias; Workspace ID, source URL, local path, Deployment, bindings, selected plan, provider configuration, worker, and signature/provenance timestamp are excluded. The logical package name is immutable manifest metadata, not a database key; renaming it creates a new revision.
5. `DeploymentRevisionId`, `ProviderProfileRevisionId`, `WorkerProfileRevisionId`, and `PolicyRevisionId` use distinct domain tags plus canonicalizer/schema versions over `{object_id, normalized immutable payload, previous_revision_id, change_kind}`. Sequence, creation time, actor display name, and mutable pointers are not hash input. The parent/change kind make a rollback a new revision even when config matches an earlier revision. A signing/SBOM/provenance attestation is a sidecar over a digest, not an identity mutation.
6. `ResolutionDigest` uses its own domain tag and schema version over the immutable Run pin without its digest field. `CatalogRevisionId` uses the catalog domain/schema version and sorted external surface. Runtime identity values are computed by the Python service; a TypeScript producer is not allowed without the same cross-language golden vectors.

A Package Revision remains portable across test/production Deployments because Workspace binding, selected plan, provider profile, and Worker Profile are outside its digest. Worker paths, host clock, provider URLs/tokens, and Runtime processes are never digest inputs.

### Workspace provider references and logical bindings

`BindingRequirement` lives in the immutable Package Revision and declares a stable logical key, provider kind, minimum capability/scopes, and whether it is required. It never contains a production value. `BindingRequirementRef = { package_revision_ref, requirement_id }` prevents same-name bindings in two packages from colliding. A `BindingReference` is `{requirement_ref, provider_profile_revision_ref, granted_scope}` and lives in a Deployment Revision; one requirement has at most one mapping. `RuntimeProviderGrant` is a tagged union: `PackageSourceGrant {purpose: "package-source", provider_profile_revision_ref, granted_capabilities}` or `AdapterArtifactGrant {purpose: "runtime-artifact" | "environment-content", runtime_kind, provider_profile_revision_ref, granted_capabilities}`. `runtime_kind` is present only for the adapter-owned artifact variant; the references stay generic and contain no RCC object protocol.

A provider-profile revision is only an identity/config-reference envelope: `{workspace_id, provider_profile_id, revision_id, provider_kind, config_generation_id, endpoint_locator_ref?, credential_locator_ref?, capability_set_digest, target_identity_digest?}`. Endpoint and credential locators resolve in owner-local configuration/secret storage; provider URLs, tokens and secret values are never copied into Package, Runtime Plan, Deployment, Run pin, catalog, logs, or provenance. Where an adapter can compute a secretless target identity fingerprint, it binds that fingerprint into the provider-profile revision without serializing the URL. Each Runtime verifies its local mapping against the pinned profile/config generation; a missing or generation-mismatched mapping is unavailable and cannot be silently rebound. Prefer versioned external secret/profile locators so a retry resolves the same authorization generation. If a provider only offers mutable `latest`, its configuration generation must change and new Runs require a new Deployment revision; old Runs remain pinned and block if that old generation is no longer satisfiable. Missing/mismatched local configuration produces `runtime_auth_required` or `runtime_unavailable`; it never edits the shared Deployment or invents a fallback.

### Worker Profile (#90/#138 consume)

`WorkerProfile` is a Workspace-scoped stable ID with immutable `WorkerProfileRevision` values. A revision holds declared eligibility requirements, not a PodSpec or worker registration:

```text
WorkerProfileRevision = frozen {
  id: WorkerProfileRevisionId,
  allowed_runtime_kinds: sorted set[RuntimeKind],
  plan_compatibility_requirements: versioned values defined by #143,
  required_features: sorted set[FeatureId],
  platform/architecture/ABI: typed constraints,
  placement_classes: {local_process, container, independent_worker, ...},
  resource_class: {cpu_millis, memory_bytes, concurrency},
  network/provider grants: scoped references,
  trust_domain/isolation/dedication requirements,
  cache/locality hints: optimization only
}
```

A worker's actual identity and dynamic eligibility are selected/leased by #90/#138 at Attempt time; no worker ID, local path, cache path, or process ID is embedded in a Package/Deployment identity. The synthesized `local/default` profile describes actual local adapter/process-pool capabilities and is versioned like any other profile. #143 supplies the typed compatibility requirement values after its proof boundary. If a selected plan's requirements are absent, admission fails closed under the #143 contract; #129 defines no adapter-specific outcome.

### Deployment and immutable Deployment Revision (#129 owns)

`Deployment` is a stable Workspace-scoped identity with a mutable `current_revision_id` and operational state (`active`, `paused`, or `retired`). It does not contain source trees, secret values, or current environment paths. Its current sequence is read from the referenced immutable Deployment Revision, not stored as a second mutable pointer value.

`active -> paused` blocks new Run admissions without changing the current revision or existing Run pins. `paused -> active` reuses that revision but re-runs live authorization/admission on each new Run. `active|paused -> retired` is a terminal tombstone transition: it blocks new Run admissions and publish/rollback, preserves Deployment Revisions and Run history as readable, and performs no physical deletion or GC. Retirement does not rewrite/cancel already admitted Runs; retry/Attempt eligibility is still checked against the exact pinned snapshot by #83/#143 and may never resolve a replacement plan. Pause or retirement does not grant permission to redirect retries or stop an already-running Attempt; #83 owns cancellation/reconciliation. An execution-policy change (allowed plan, binding, Worker Profile, limits, projection) is always a new Deployment Revision. Access authorization is re-evaluated at each privileged operation and Run/Attempt boundary; a revocable ACL decision is not frozen as a permission grant just because its reference was captured in a Run audit record.

```text
DeploymentRevision = frozen {
  id: DeploymentRevisionId,
  deployment_id: DeploymentId,
  sequence: int,                  # display/ordering, not content identity
  previous_revision_id: Optional[DeploymentRevisionId],
  rollback_of: Optional[DeploymentRevisionId],
  packages: tuple[PackageRevisionRef, ...],
  capabilities: tuple[CapabilityDeploymentPolicy, ...],
  binding_references: tuple[BindingReference, ...],
  runtime_provider_grants: tuple[RuntimeProviderGrant, ...],
  worker_profile_refs: tuple[WorkerProfileRevisionRef, ...],
  policy_revision_ref: WorkspacePolicyRevisionRef,
  execution_limits: typed quota/timeout/effect/cancellation values,
  projections: tuple[ExposureProjection, ...],
  compatibility_metadata: typed,  # never an executable migration
}

CapabilityDeploymentPolicy = frozen {
  capability_ref: CapabilityRef,
  runtime_selection: RuntimeSelection,
  worker_profile_ref: WorkerProfileRevisionRef,
  binding_requirements: sorted tuple[BindingRequirementRef, ...],
  exposure_projection_ids: sorted tuple[ExposureProjectionId, ...],
  policy/limit overrides: bounded typed values
}

RuntimeSelection = discriminated union on `mode`:
  { mode: "locked", plan_ref: RuntimePlanRef }
  { mode: "default-among-allowed", default_plan_ref: RuntimePlanRef,
    allowed_plan_refs: sorted tuple[RuntimePlanRef, ...] }
  { mode: "caller-may-choose", allowed_plan_refs: sorted tuple[RuntimePlanRef, ...] }
```

For local v1, a Deployment may contain one Package Revision; the representation is a tuple so #130's package-bundle/catalog case does not require a later semantic rewrite. Every `RuntimePlanRef` must name a Package Revision present in the same Deployment Revision and a digest declared by that Package Revision. A default must be in both the capability's compatible-plan set and the sorted allowed-plan refs. `CallerMayChoose` is not a fallback list: a caller must explicitly name one authorized full `RuntimePlanRef`. An absent/undeclared/forbidden plan makes the candidate invalid. #129 does not specify adapter payload variants or default preference beyond this explicit ref.

`DeploymentRevisionId = sha256(canonical {deployment_id, normalized revision payload, previous_revision_id, change_kind})`; `change_kind` is `publish` or `rollback`. Sequence number, creation timestamp, actor display name, and request timing are metadata, not digest inputs. The parent link makes a rollback a distinct revision even when its effective configuration equals an older revision. A retry of the same publish command against the same parent is idempotent. Revision content and all references are immutable after insert.

### Exposure projection and catalog identity (#130/#89 own)

The Deployment Revision carries only the projection references/configuration accepted by the versioned #130 projection schema. #129 does not enumerate projection variants, rewrite schemas, or define the projection compiler. Projection remains independent of Runtime Plan selection. #130 owns the capability/projection vocabulary and compiler boundary; #89 owns catalog cache lifetime and protocol surface implementation.

`ExposureProjectionId` is a versioned opaque digest over the #130-normalized projection for one full `CapabilityRef`. `CatalogRevisionId` is a versioned digest over the canonical sorted projected protocol surface, excluding Workspace/Deployment IDs, provider refs, credentials, dynamic adapter readiness and worker state. Equal projected surfaces therefore have equal catalog IDs across equivalent replicas/deployments. Changing only the selected Runtime Plan must not change the protocol catalog digest; changing a capability schema/projection may change it. #130/#89 acceptance defines exact projection payload/digest fields before that compiler slice begins.

Keep catalog surface identity separate from dispatch authority. A catalog cache may reuse an identical protocol surface after a source-only Package Revision or plan change, but its handler must carry an unambiguous projection/capability target and invoke the resolver with full refs/`Current`; it must not retain a closure to an old mutable package path or Package Revision. At Run admission, the transaction pins the resolved immutable snapshot. A Run already admitted on N still uses N. #89 owns exact catalog-handler interfaces and dispatch/cache behavior.

### Resolved execution snapshot (handoff to #83)

`DeploymentResolver.resolve(workspace_id, deployment_id, revision: RevisionSelector, capability: CapabilityRef, plan: PlanChoice, caller_context) -> ResolvedExecutionSnapshot | ResolutionError` reads exactly one Deployment Revision, verifies every reference in that Workspace and selects exactly one declared plan. `Current` reads the current pointer; `Retained(ref)` selects only that full Deployment Revision after authorization. An explicit plan is a full `RuntimePlanRef`, not a package-local string. `UseDeclaredDefault` resolves only the declared default in the selected revision. No path chooses the first plan in an array. If a `Current` resolution is repeated after the head changes, all supplied full refs must still match the new selected revision; otherwise it fails closed and the caller refreshes refs rather than redirecting to a guessed capability or plan.

```text
ResolvedExecutionSnapshot = frozen {
  schema_version: 1,
  workspace_id: WorkspaceId,
  deployment_ref: DeploymentRevisionRef,
  package_ref: PackageRevisionRef,
  capability_ref: CapabilityRef,
  capability_schema_digest: Sha256,
  runtime_plan_ref: RuntimePlanRef,
  runtime_plan_header: RuntimePlanHeader,  # verified equal to the pinned Package Revision
  binding_refs: sorted tuple[BindingReferenceSnapshot, ...],
  worker_profile_ref: WorkerProfileRevisionRef,
  policy_revision_ref: WorkspacePolicyRevisionRef,
  catalog_revision_id: CatalogRevisionId,
  resolution_digest: Sha256
}
```

The snapshot does not copy the adapter-specific Runtime Plan payload. The immutable Package Revision is its source of truth. `runtime_plan_header` is only the generic `RuntimePlanHeader` (including `runtime_kind`, `plan_schema_version`, opaque `contract_id`, adapter version range, required features, and `compatibility_identity_digest`); the resolver verifies it equals the selected header in the pinned Package Revision. #83 persists both that Package Revision reference and this header summary.

`resolution_digest` hashes the canonical immutable fields above. It excludes actor/authorization decision, idempotency/effect token, `observed_at`, adapter/worker availability, cache warmth, selected worker ID, local paths, and secret material. #83 separately records actor/authorization decision, idempotency/effect scope, Run state, Attempt/owner/lease/epoch and timestamps. This split makes two replicas agree on static resolution while permitting explicitly dynamic admission observations to differ.

`AdmissionSnapshot` has a required positive `schema_version` and a `resolution_digest` exactly equal to the supplied static snapshot's digest. #143 owns all other fields and their mode/outcome/evidence/freshness semantics. #83 rejects an unsupported admission schema or digest mismatch before persisting or executing a Run. Dynamic observations and admission outcomes do not alter the static `resolution_digest`.

The internal boundary is:

```text
DeploymentResolver.resolve(workspace_id, deployment_id, revision, capability, plan, caller_context)
    -> ResolvedExecutionSnapshot | ResolutionError
AdmissionService.admit(snapshot, normalized_inputs, dynamic_observations) -> AdmissionSnapshot  # #143
RunService.create_pinned(snapshot, admission, revision_selector, idempotency_key) -> Run  # #83
RunService.retry(run_id) -> new fenced Attempt using stored snapshot; never calls resolve()
RunService.restart_as_new(old_run_id, plan_choice) -> resolve Current then create a new Run
```

#129 owns `DeploymentResolver` and the immutable snapshot contract. #143 owns the common `AdmissionService` implementation and dynamic reason/outcome schema after #134 proof. #83 owns the Run/Attempt API and the Run-admission transaction that persists the snapshot before execution. That single transaction must serialize against Deployment pointer/state writes, require `state == active`, and, for `Current`, confirm that the pointer still equals `snapshot.deployment_ref`. If a pointer change committed first, it creates no Run and returns `resolution_stale`; the caller re-resolves and readmits Current. For `Retained`, it reauthorizes and confirms the exact retained revision but does not require it to remain current. If pause/retirement commits first, no new Run is admitted. If Run admission commits first, that Run keeps its exact snapshot. A transport/API handler must not rebuild these fields or parse package files on its own.

## State transitions, consistency and error behavior

### Publish/update and rollback

1. Parse the candidate against strict versioned schemas; reject unknown fields and malformed/dangling IDs.
2. Resolve every Package/plan/profile/provider/policy reference in the same Workspace and validate compatibility and authorization. The candidate has no published state and makes no pointer change on failure. `preview(candidate)` is read-only and may return `needs_binding` so a user can finish configuration; `publish(candidate)` requires every required binding to resolve within policy, otherwise it returns a stable validation reason and persists no revision/pointer change. A later revocation or missing local secret/profile is reported by admission for an already-published revision.
3. Compute its canonical revision digest and catalog identity. Check static policy constraints; do not silently use a different plan to make the candidate pass. Required bindings must be mapped for publish; a transient preview may report `needs_binding` without persisting an incomplete revision. Adapter/provider/worker availability remains a dynamic admission observation and does not make an otherwise valid immutable plan choose another adapter.
4. Every create/publish/rollback command supplies an idempotency key. Before comparing an ETag or attempting CAS, the transaction looks up `(workspace_id, deployment_id, idempotency_key)`: if the stored operation and canonical request digest match, return its original result even if its former `If-Match` is now stale; if the same key was used for another operation/content, return `idempotency_conflict`. Otherwise, in one transaction, insert the immutable revision and normalized reference indexes, record the request digest/result, then compare-and-swap `Deployment.current_revision_id` against the caller's `If-Match`. If another writer advanced it, return `revision_conflict` / HTTP 409 and leave no request result, pointer change, or partial candidate behind. An existing revision digest may be treated as idempotent only after canonical payload bytes are compared; different bytes under the same identity are corruption.
5. New Runs admitted after that transaction commits resolve the new pointer. Existing Runs and their replacement Attempts retain their stored snapshot.

First publication creates the Deployment identity, first immutable revision, revision indexes, pointer, and idempotency result in one transaction using `If-None-Match: *`; retries use the same idempotency-key replay rule. Updates require `If-Match` on the current revision. Rollback uses `POST .../deployments/{id}/rollback` with a full target `DeploymentRevisionRef` and `If-Match` current revision. It copies the target's immutable configuration into a new revision with `previous_revision_id=current` and `rollback_of=target`; only the Deployment pointer advances. It does not decrement sequence, rewrite provenance, mutate N/N+1 Runs, or reopen a failed Run. Old revisions remain readable; the first implementation retains all revisions rather than ship premature GC.

`DeploymentRevisionRequestDigest = sha256(JCS_v1({domain: "actions.deployment-command/v1", canonicalizer_version, request_schema_version, workspace_id, deployment_id, operation_kind, parent_etag_or_create_precondition, candidate_revision_digest_or_rollback_target_ref}))`. It binds the key to command kind, target, parent precondition, and candidate/rollback target. Actor display name, request time, and transport metadata are excluded. The repository compares the stored digest before CAS and never returns a prior result for a key reused with different content.

The linearization point for “new Runs only” is the #83 Run-admission transaction, not HTTP request start. It serializes with pointer and state changes, checks `state == active`, and checks the pointer against the resolved revision for `Current`. If N+1 or pause/retirement commits first, no stale/new Run is committed: `Current` is re-resolved and readmitted, while a retained request is reauthorized against its exact reference and still requires an active Deployment. If Run admission commits first, it pins N.

Revoking a provider/adapter/profile blocks new Runs and causes an old pinned Run's retry to report blocked/unavailable against its original reference; it cannot adopt a newer provider or adapter. A security-policy revocation may cancel/reject the active operation per the policy/Run owner, but it never rewrites the pinned snapshot. No arbitrary business migrations run as a Deployment side effect.

### Resolution/admission errors

Use stable typed errors/outcomes rather than exception-message inspection:

- `not_found`: no object in the requested Workspace; also used at the public boundary for a foreign-Workspace ID.
- `forbidden`: caller lacks required Workspace/object/plan/provider permission; do not reveal foreign names.
- `invalid_reference` / `workspace_mismatch`: malformed, stale or cross-scope persisted reference; publish rejects it before pointer movement; sanitized external response is `404` or `422` as appropriate.
- `invalid_revision`: unsupported schema/normalization version, missing package capability, undeclared plan, required unknown feature, invalid binding/projection; publish returns field-path reason codes and persists no current revision.
- `revision_conflict`: stale `If-Match`, HTTP 409 with current revision identifier only if the caller may read it.
- `runtime_unavailable`, `runtime_auth_required`, `runtime_incompatible`, `no_eligible_worker`, `needs_binding`, `forbidden`, `unknown/partial_evidence`: #143 admission reasons attached to the exact snapshot, not a trigger to try another plan.
- `resolution_stale`: current Deployment pointer changed between preflight and Run commit; commit no Run. Re-resolve/readmit only for `Current`. A deliberate `Retained(ref)` request stays on that ref, is reauthorized, and is never redirected.

If the selected plan's adapter, provider profile, platform, or Worker Profile is missing/incompatible, `admit` returns the exact blocker. Under every admission mode, hard identity, authorization, adapter, provider and worker-compatibility checks remain fail-closed; shadow/off modes cannot authorize silent substitution or simulated success. Whether a blocked intent is recorded as a durable blocked Run is #83's API/state decision. The default handoff contract creates no executable Run until #83 accepts the snapshot/admission; a future durable blocked-request projection must still pin the same snapshot.

### Retry versus restart

- Retry/Attempt replacement: read `Run.resolved_snapshot` and reuse its exact DeploymentRevision, PackageRevision, capability schema, Runtime Plan, binding/profile/policy revisions and catalog identity. Never call `resolve(current)` and never select a fallback. If any old reference is unavailable, return a typed blocked state with no replacement plan.
- Restart as new: explicit new Run command invokes resolver with `Current` and a `PlanChoice`; current policy can choose/require another allowed full plan ref. It has a new Run and idempotency scope. It does not mutate old Run state.

## Minimal persistence and API boundaries

### Suggested schema after current migration 12

Use the existing DB/migration substrate after #84's current-head backend contract is accepted. The inspected registry currently ends at ID 12; if this slice lands first, name it migration 13. If a prerequisite migration is integrated first, allocate the next sequential unused ID on the integrated branch. Do not edit historical migrations or reserve colliding numbers across branches. Keep immutable canonical JSON payloads as source of truth and enough normalized owner/reference columns for scoped queries and composite referential checks. Define one DDL/bootstrap helper used by `migration_add_deployment_revision_graph.migrate(db)`, `create_db()`'s fresh SQLite/test path, and `migrate_db()`'s fresh PostgreSQL path. Do not rely on the current generic `create_tables(get_model_db_rules())` path alone for new join tables: it iterates registered dataclasses and cannot by itself express this packet's typed composite reference constraints. Keep domain models frozen/Pydantic and put persistence reads/writes behind `DeploymentRepository`, which parses typed JSON values and uses the shared `Database` transaction/SQL surface.

```text
workspace(
    workspace_id PK,
    name NOT NULL,
    created_at NOT NULL
)
installation_metadata(
    key PK,
    value NOT NULL
)
installation_default_workspace(
    singleton_key PK CHECK(singleton_key = 1),
    workspace_id NOT NULL UNIQUE,
    FK (workspace_id) -> workspace(workspace_id)
)
package(
    workspace_id NOT NULL,
    package_id NOT NULL,
    name NOT NULL,
    legacy_source_kind NULL,
    legacy_source_id NULL,
    PK (workspace_id, package_id),
    FK (workspace_id) -> workspace(workspace_id)
)
package_revision(
    workspace_id NOT NULL,
    package_id NOT NULL,
    revision_id NOT NULL,
    schema_version NOT NULL,
    source_artifact_digest NOT NULL,
    capability_manifest_digest NOT NULL,
    manifest_json NOT NULL,
    created_at NOT NULL,
    PK (workspace_id, package_id, revision_id),
    FK (workspace_id, package_id) -> package(workspace_id, package_id)
)
provider_profile(
    workspace_id NOT NULL,
    provider_profile_id NOT NULL,
    current_revision_id NULL during creation, NOT NULL after commit,
    PK (workspace_id, provider_profile_id),
    FK (workspace_id) -> workspace(workspace_id)
)
provider_profile_revision(
    workspace_id NOT NULL,
    provider_profile_id NOT NULL,
    revision_id NOT NULL,
    config_generation_id NOT NULL,
    locator_refs_json NOT NULL,
    target_identity_digest NULL,
    capability_set_digest NOT NULL,
    created_at NOT NULL,
    PK (workspace_id, provider_profile_id, revision_id),
    FK (workspace_id, provider_profile_id)
       -> provider_profile(workspace_id, provider_profile_id)
)
worker_profile(
    workspace_id NOT NULL,
    worker_profile_id NOT NULL,
    current_revision_id NULL during creation, NOT NULL after commit,
    PK (workspace_id, worker_profile_id),
    FK (workspace_id) -> workspace(workspace_id)
)
worker_profile_revision(
    workspace_id NOT NULL,
    worker_profile_id NOT NULL,
    revision_id NOT NULL,
    profile_json NOT NULL,
    created_at NOT NULL,
    PK (workspace_id, worker_profile_id, revision_id),
    FK (workspace_id, worker_profile_id)
       -> worker_profile(workspace_id, worker_profile_id)
)
workspace_policy(
    workspace_id NOT NULL,
    policy_id NOT NULL,
    current_revision_id NULL during creation, NOT NULL after commit,
    PK (workspace_id, policy_id),
    FK (workspace_id) -> workspace(workspace_id)
)
workspace_policy_revision(
    workspace_id NOT NULL,
    policy_id NOT NULL,
    revision_id NOT NULL,
    policy_digest NOT NULL,
    policy_json NOT NULL,
    created_at NOT NULL,
    PK (workspace_id, policy_id, revision_id),
    FK (workspace_id, policy_id) -> workspace_policy(workspace_id, policy_id)
)
deployment(
    workspace_id NOT NULL,
    deployment_id NOT NULL,
    name NOT NULL,
    current_revision_id NULL during creation, NOT NULL after commit,
    state NOT NULL CHECK(state IN ('active', 'paused', 'retired')),
    PK (workspace_id, deployment_id),
    FK (workspace_id) -> workspace(workspace_id)
)
deployment_revision(
    workspace_id NOT NULL,
    deployment_id NOT NULL,
    revision_id NOT NULL,
    sequence NOT NULL CHECK(sequence > 0),
    previous_revision_id NULL,
    rollback_of_revision_id NULL,
    canonical_snapshot_json NOT NULL,
    catalog_revision_id NOT NULL,
    created_at NOT NULL,
    change_kind NOT NULL CHECK(change_kind IN ('publish', 'rollback')),
    PK (workspace_id, deployment_id, revision_id),
    UNIQUE (workspace_id, deployment_id, sequence),
    FK (workspace_id, deployment_id)
       -> deployment(workspace_id, deployment_id),
    FK (workspace_id, deployment_id, previous_revision_id)
       -> deployment_revision(workspace_id, deployment_id, revision_id),
    FK (workspace_id, deployment_id, rollback_of_revision_id)
       -> deployment_revision(workspace_id, deployment_id, revision_id),
    CHECK((change_kind = 'publish'
           AND rollback_of_revision_id IS NULL
           AND ((sequence = 1 AND previous_revision_id IS NULL)
             OR (sequence > 1 AND previous_revision_id IS NOT NULL)))
       OR (change_kind = 'rollback'
           AND sequence > 1
           AND previous_revision_id IS NOT NULL
           AND rollback_of_revision_id IS NOT NULL))
)
deployment_revision_package(
    workspace_id NOT NULL,
    deployment_id NOT NULL,
    revision_id NOT NULL,
    package_id NOT NULL,
    package_revision_id NOT NULL,
    PK (workspace_id, deployment_id, revision_id, package_id),
    UNIQUE (workspace_id, deployment_id, revision_id, package_id,
            package_revision_id),
    FK (workspace_id, deployment_id, revision_id)
       -> deployment_revision(workspace_id, deployment_id, revision_id),
    FK (workspace_id, package_id, package_revision_id)
       -> package_revision(workspace_id, package_id, revision_id)
)
deployment_revision_binding(
    workspace_id NOT NULL,
    deployment_id NOT NULL,
    revision_id NOT NULL,
    package_id NOT NULL,
    package_revision_id NOT NULL,
    binding_requirement_id NOT NULL,
    provider_profile_id NOT NULL,
    provider_profile_revision_id NOT NULL,
    granted_scope_json NOT NULL,
    PK (workspace_id, deployment_id, revision_id, package_id,
        package_revision_id, binding_requirement_id),
    FK (workspace_id, deployment_id, revision_id)
       -> deployment_revision(workspace_id, deployment_id, revision_id),
    FK (workspace_id, deployment_id, revision_id, package_id,
        package_revision_id)
       -> deployment_revision_package(workspace_id, deployment_id, revision_id,
                                      package_id, package_revision_id),
    FK (workspace_id, provider_profile_id, provider_profile_revision_id)
       -> provider_profile_revision(workspace_id, provider_profile_id, revision_id)
)
deployment_revision_package_source_provider_ref(
    workspace_id NOT NULL,
    deployment_id NOT NULL,
    revision_id NOT NULL,
    provider_profile_id NOT NULL,
    provider_profile_revision_id NOT NULL,
    granted_capabilities_json NOT NULL,
    PK (workspace_id, deployment_id, revision_id, provider_profile_id,
        provider_profile_revision_id),
    FK (workspace_id, deployment_id, revision_id)
       -> deployment_revision(workspace_id, deployment_id, revision_id),
    FK (workspace_id, provider_profile_id, provider_profile_revision_id)
       -> provider_profile_revision(workspace_id, provider_profile_id, revision_id)
)
deployment_revision_adapter_artifact_provider_ref(
    workspace_id NOT NULL,
    deployment_id NOT NULL,
    revision_id NOT NULL,
    purpose NOT NULL CHECK(purpose IN ('runtime-artifact', 'environment-content')),
    runtime_kind NOT NULL,
    provider_profile_id NOT NULL,
    provider_profile_revision_id NOT NULL,
    granted_capabilities_json NOT NULL,
    PK (workspace_id, deployment_id, revision_id, purpose, runtime_kind,
        provider_profile_id, provider_profile_revision_id),
    FK (workspace_id, deployment_id, revision_id)
       -> deployment_revision(workspace_id, deployment_id, revision_id),
    FK (workspace_id, provider_profile_id, provider_profile_revision_id)
       -> provider_profile_revision(workspace_id, provider_profile_id, revision_id)
)
deployment_revision_worker_profile_ref(
    workspace_id NOT NULL,
    deployment_id NOT NULL,
    revision_id NOT NULL,
    worker_profile_id NOT NULL,
    worker_profile_revision_id NOT NULL,
    PK (workspace_id, deployment_id, revision_id, worker_profile_id,
        worker_profile_revision_id),
    FK (workspace_id, deployment_id, revision_id)
       -> deployment_revision(workspace_id, deployment_id, revision_id),
    FK (workspace_id, worker_profile_id, worker_profile_revision_id)
       -> worker_profile_revision(workspace_id, worker_profile_id, revision_id)
)
deployment_revision_policy_ref(
    workspace_id NOT NULL,
    deployment_id NOT NULL,
    revision_id NOT NULL,
    policy_id NOT NULL,
    policy_revision_id NOT NULL,
    PK (workspace_id, deployment_id, revision_id, policy_id, policy_revision_id),
    FK (workspace_id, deployment_id, revision_id)
       -> deployment_revision(workspace_id, deployment_id, revision_id),
    FK (workspace_id, policy_id, policy_revision_id)
       -> workspace_policy_revision(workspace_id, policy_id, revision_id)
)
deployment_revision_request(
    workspace_id NOT NULL,
    idempotency_key NOT NULL,
    deployment_id NOT NULL,
    operation_kind NOT NULL,
    request_digest NOT NULL,
    parent_revision_id NULL only for initial create,
    result_revision_id NOT NULL,
    created_at NOT NULL,
    PK (workspace_id, idempotency_key),
    FK (workspace_id) -> workspace(workspace_id),
    FK (workspace_id, deployment_id)
       -> deployment(workspace_id, deployment_id),
    FK (workspace_id, deployment_id, parent_revision_id)
       -> deployment_revision(workspace_id, deployment_id, revision_id),
    FK (workspace_id, deployment_id, result_revision_id)
       -> deployment_revision(workspace_id, deployment_id, revision_id),
    CHECK((operation_kind = 'create' AND parent_revision_id IS NULL)
       OR (operation_kind <> 'create' AND parent_revision_id IS NOT NULL))
)
```

All abbreviated `PK`, `UNIQUE`, and `FK` declarations above mean named SQL
constraints over exactly the listed columns, in that order. No foreign key
references a bare object ID when the target is Workspace-scoped. The cyclic
current-pointer constraints, omitted from the table blocks only to make the
creation phases explicit, are exactly:

```text
provider_profile(workspace_id, provider_profile_id, current_revision_id)
  -> provider_profile_revision(workspace_id, provider_profile_id, revision_id)
worker_profile(workspace_id, worker_profile_id, current_revision_id)
  -> worker_profile_revision(workspace_id, worker_profile_id, revision_id)
workspace_policy(workspace_id, policy_id, current_revision_id)
  -> workspace_policy_revision(workspace_id, policy_id, revision_id)
deployment(workspace_id, deployment_id, current_revision_id)
  -> deployment_revision(workspace_id, deployment_id, revision_id)
```

A NULL `current_revision_id` is allowed only between owner insertion and
pointer publication inside the same write transaction; a database CHECK
cannot enforce “non-null at commit”, so the helper/repository must guarantee
that invariant and test rollback on failure. Similarly, ancestry is checked by
the exact same-Deployment composite keys above: initial revision has both
ancestry refs NULL; ordinary publish has `previous_revision_id` equal to the
parent/current revision and `rollback_of_revision_id` NULL; rollback has both
`previous_revision_id` equal to the old current revision and
`rollback_of_revision_id` equal to the retained target revision. A trigger or
repository invariant must enforce these relationships and sequence=`parent + 1`
inside the serialized publish transaction; the FK alone proves existence/scope,
not correct ancestry.

These are contract-level table and tuple definitions, not generated SQL or a
claim about current schema. See the migration section for executable DDL
ordering, backend parity, and failure recovery.

The tuple declarations above are the required scoped-FK matrix, including all names and column order. The effective ownership/reference tuples are:

| Child row | Exact referenced tuple(s) |
|---|---|
| `installation_default_workspace` | `(workspace_id) -> workspace(workspace_id)` |
| `package` | `(workspace_id) -> workspace(workspace_id)` |
| `package_revision` | `(workspace_id, package_id) -> package(workspace_id, package_id)` |
| each profile/policy identity | `(workspace_id) -> workspace(workspace_id)` |
| each provider/worker/policy revision | `(workspace_id, owner_id) -> owner(workspace_id, owner_id)` |
| `deployment` | `(workspace_id) -> workspace(workspace_id)` and cyclic current pointer tuple above |
| `deployment_revision` | `(workspace_id, deployment_id) -> deployment(workspace_id, deployment_id)`; `(workspace_id, deployment_id, previous_revision_id)` and `(workspace_id, deployment_id, rollback_of_revision_id)` each reference `(workspace_id, deployment_id, revision_id)` in `deployment_revision` |
| `deployment_revision_package` | `(workspace_id, deployment_id, revision_id) -> deployment_revision`; `(workspace_id, package_id, package_revision_id) -> package_revision(workspace_id, package_id, revision_id)`; its unique five-column key is the exact parent tuple for bindings |
| `deployment_revision_binding` | `(workspace_id, deployment_id, revision_id) -> deployment_revision`; `(workspace_id, deployment_id, revision_id, package_id, package_revision_id) -> deployment_revision_package`; `(workspace_id, provider_profile_id, provider_profile_revision_id) -> provider_profile_revision(workspace_id, provider_profile_id, revision_id)` |
| package-source and adapter-artifact provider grant rows | `(workspace_id, deployment_id, revision_id) -> deployment_revision`; `(workspace_id, provider_profile_id, provider_profile_revision_id) -> provider_profile_revision` |
| worker-profile grant row | `(workspace_id, deployment_id, revision_id) -> deployment_revision`; `(workspace_id, worker_profile_id, worker_profile_revision_id) -> worker_profile_revision` |
| policy grant row | `(workspace_id, deployment_id, revision_id) -> deployment_revision`; `(workspace_id, policy_id, policy_revision_id) -> workspace_policy_revision(workspace_id, policy_id, revision_id)` |
| `deployment_revision_request` | `(workspace_id) -> workspace`; `(workspace_id, deployment_id) -> deployment`; `(workspace_id, deployment_id, parent_revision_id) -> deployment_revision`; `(workspace_id, deployment_id, result_revision_id) -> deployment_revision` |

All listed unique/primary tuples must exist on the referenced tables before creating their FKs. The child’s `workspace_id` is always part of a scoped reference; it is never checked separately from an object ID when that would allow cross-Workspace aliasing. For normalized join tables, the deployment-revision FK composes the Workspace scope through the deployment owner. The singleton default Workspace FK is direct and explicit.

### DDL execution and backend parity

The current generic `Database.create_table_sql()` only builds single-column
`*_id -> id` constraints from `DBRules`; it cannot express these tuples or
cyclic current pointers. The implementation therefore needs one explicit
deployment-schema helper using `db.execute()` inside the existing
`Database.transaction()` boundary, not model registration as a substitute.
That helper is called by upgrade migration 13, fresh SQLite `create_db()`, and
the fresh-PostgreSQL initialization branch. Use the same table, key, check,
index, and immutability-trigger inventory on every entry path.

SQLite can parse a `CREATE TABLE` FK that names a table created later, so its
helper creates all tables with all four current-pointer FKs declared inline.
PostgreSQL cannot add those pointer constraints until the targets exist; its
helper first creates owner/revision tables and all non-cyclic constraints,
then issues named `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY` statements
for the four exact tuples above. Both backends run this work in the caller's
schema transaction with SQLite foreign-key enforcement enabled. Bootstrap
inserts owner rows with a NULL pointer, inserts their first immutable revision,
then sets the pointer before commit. Migration failure must roll back both DDL
and the default-Workspace/bootstrap rows; do not toggle SQLite foreign keys
off to make ordering succeed.

Immutable revision and normalized reference rows are insert-only in both
engines. Implement backend-specific update/delete rejection triggers for
`package_revision`, `deployment_revision`, the three profile/policy revision
tables, their derived deployment join tables, and idempotency request receipts.
The helper must create and inspect the same trigger inventory on fresh and
upgrade paths. Mutable pointer/state rows are updated only by repository
commands inside a transaction. If trigger shape differs across engines,
record that as a parity failure rather than relying on application convention.

Required migration order is: acquire the existing PostgreSQL schema advisory
lock through `migrate_db`; begin the database transaction; create tables and
unique owner/revision keys; create non-cyclic scoped FKs; create the four
current-pointer FKs using the backend procedure above; create checks, indexes,
and immutable-row guards; seed/retrieve the single stable default Workspace;
validate the final FK/index/trigger graph and default pointer; stamp migration
13 last; commit. Fresh database paths call the same helper and only then stamp
`CURRENT_VERSION`. Never rewrite migrations 1–12. SQLite `PRAGMA foreign_key_check`
and backend-native constraint catalog queries must be clean before commit.

The `deployment_revision_request.parent_revision_id` FK is mandatory, nullable
only for an initial `create` request. The composite FK is
`(workspace_id, deployment_id, parent_revision_id) ->
deployment_revision(workspace_id, deployment_id, revision_id)`; its CHECK
requires NULL exactly for `operation_kind='create'`, and non-NULL for every
other operation. Its result revision has a separate FK with the same scoped
target shape. Deployment revision ancestry is similarly enforced with the two
explicit self-FKs; sequence succession and whether the parent equals the
current pointer remain transactional repository checks and receive adversarial
tests. FK existence alone does not prove correct ancestry or CAS behavior.

These are design requirements only. No migration helper, trigger, SQLite DDL,
PostgreSQL DDL, or database parity receipt is included or claimed by this
packet.

`canonical_snapshot_json` in each immutable revision is the authority. The repository derives normalized join/index rows from that JSON in the same transaction; on read/resolve it verifies they match or fails closed. Binding requirement IDs live inside the exact immutable Package Revision JSON, so `publish` and every `resolve` validate that the requirement exists in that Package Revision and that the binding row points through the matching `deployment_revision_package` tuple. Do not invent a database FK to a JSON member or treat the join rows as a second authority. Use separate typed join tables so every SQL FK has one known target instead of a nullable `profile_kind` bag. RuntimePlan and Capability are inside the immutable canonical Package Revision manifest; resolver verifies the full referenced IDs against it. Catalog cache entries remain #89's concern, not a new service/table by default.

Rows in the immutable package/deployment/profile/policy revision tables are insert-only. A mutation attempt is an integrity conflict, not an update. Only the profile/policy/Deployment current-revision pointers and Deployment operational state are mutable; Deployment sequence is read through the current revision pointer. Pointer advance is conditional and transactional; the next sequence is `max(sequence) + 1` under the same serialization boundary and protected by the scoped unique constraint. The source/package-artifact provider itself remains #136, RCC Environment Artifact remains RCC/#133/#134, and output artifacts remain #86: three distinct artifact planes.

### Proposed API surface

Retain all legacy routes. Add a narrow versioned domain surface; exact route names can be aligned with existing route conventions at implementation:

```text
GET  /api/workspaces/{workspace_id}/deployments
POST /api/workspaces/{workspace_id}/deployments   If-None-Match: *; Idempotency-Key
GET  /api/workspaces/{workspace_id}/deployments/{deployment_id}
GET  /api/workspaces/{workspace_id}/deployments/{deployment_id}/revisions
PUT  /api/workspaces/{workspace_id}/deployments/{deployment_id}/revision   If-Match: current revision; Idempotency-Key
POST /api/workspaces/{workspace_id}/deployments/{deployment_id}/rollback   If-Match: current revision; Idempotency-Key
POST /api/workspaces/{workspace_id}/deployments/{deployment_id}/retire      Idempotency-Key
POST /api/workspaces/{workspace_id}/deployments/{deployment_id}/resolve    read-only; RevisionSelector + full refs
POST /api/workspaces/{workspace_id}/deployments/{deployment_id}/runs        delegates to #83 with resolved snapshot
```

The local CLI/old routes resolve a `DefaultWorkspaceContext`; they do not duplicate policy or parse `package.yaml` independently. The `resolve` request names a `RevisionSelector`, full `CapabilityRef`, and `PlanChoice`; it returns the exact `deployment_revision_ref`, `package_revision_ref`, `capability_ref`, selected `runtime_plan_ref`/generic header, `resolution_digest`, `catalog_revision_id`, and versioned #143 `AdmissionSnapshot` (redacted). The create-run route passes the same snapshot, admission digest, and selector to the #83 `RunService`; it does not redo resolution in a second code path. Mutating commands require an `Idempotency-Key`; create uses `If-None-Match: *`, and update/rollback use `If-Match`. Publish/rollback returns the new immutable revision ref and sequence. There is no endpoint that takes raw provider URL/token or adapter executable path.

## Compatibility/migration path preserving local standalone use

1. Add schema and create one default Workspace transactionally on all three entry paths: the next sequential upgrade migration (13 on the inspected registry), fresh SQLite `create_db()`, and fresh PostgreSQL initialization. Generate the Workspace UUID once and persist it in `installation_metadata`; never derive it from filesystem/port/process. Existing `ActionPackage`, `Action`, `Run`, schedule, Robot and artifact rows are preserved byte-for-byte.
2. Keep existing model/routes in an explicitly named `legacy` mode during the additive rollout. Legacy Runs remain legacy history; do not invent PackageRevision/Deployment pins for old Runs.
3. Once #130 and #135 are accepted, a compiler/importer snapshots each eligible current v2 Action package into a Package Revision and creates a default local Deployment/Deployment Revision selecting its one declared plan and preserving current direct Action projection behavior. The Package record may retain a `legacy_source_id` solely as migration provenance. New Runs must use the new pinned snapshot path after cutover.
4. If a package fails safe snapshotting/compilation, record a precise blocked import status; do not make it active, follow a mutable directory as if immutable, or guess RCC/uv. Preserve its source and historical Runs for inspection and give the local UI/CLI a repairable message. The Runtime can still start; one invalid package does not poison unrelated packages.
5. Existing Robot Task import uses the same PackageRevision/Capability/Deployment model once #148's import boundary and #144/#135 compiler are ready. Work Items remain optional execution context. No second Robot registry or RCC environment identity is introduced.
6. Advance Deployments one at a time. The current migrator makes a SQLite file copy before an upgrade, but does not provide an automatic PostgreSQL backup; operators must take the configured PostgreSQL backup before production migration. In both backends the migration DDL/bootstrap transaction must roll back on any error, and a retry after rollback must be safe. Do not claim migration rollback for failures outside that database transaction. Retain legacy paths until active new revisions are readable by the shipped Runtime. Before a revision is activated or a writer rolls forward, #140's compatibility gate must verify that every Runtime version which can receive that Deployment can read its stored schema/canonicalizer versions; if any reader is unknown or incompatible, leave the pointer unchanged and fail closed. A Runtime encountering an unknown revision/schema never guesses, down-migrates, or executes it. #140 owns the rollout gate and must test the supported old-reader/new-writer matrix; this contract adds no service or adapter migration.

This bridge is intentionally not implementation detail for #129 to own. #135 owns safe source snapshot/compile, #148 owns unsafe archive/URL import hardening, #136 owns immutable source distribution, and #140 owns packaging/upgrade operations.

## Object-model alternatives considered

### Mutable Deployment row versus immutable revision plus current pointer

**Mutable row:** overwrite plan, binding, and profile fields on one Deployment record, then copy some values into Runs. It has fewer tables but creates an unclear transaction boundary; a request can observe a mixture of new/old fields, a retry can accidentally resolve current values, and rollback is a manual restoration that risks losing provenance.

**Immutable revision plus atomic pointer (recommended):** Deployment contains one mutable current-revision pointer; every content change is a new immutable revision; one DB transaction advances the pointer with optimistic concurrency. The Run stores the selected immutable snapshot. This directly satisfies #129's N/N+1 and rollback acceptance, supports concurrent editors with `If-Match`, and keeps the local topology to one database and one process. It adds revision rows but removes mutation ambiguity and makes retry semantics testable.

### Generic Runtime Plan header and owner-specific payload schemas

The #129 Deployment model stores a full `RuntimePlanRef` and the versioned generic `RuntimePlanHeader` only. The immutable Package Revision carries the complete plan payload as canonical content. #130 owns Package manifest and payload syntax; #143 owns the adapter-specific descriptor and payload schema after #134 proof. Those owners may use a strict tagged representation, but #129 does not enumerate adapter variants, impose RCC/uv fields, or design a plugin registry. This keeps a non-RCC Runtime Plan from acquiring fake RCC fields without pre-freezing #143.

## Small source slices and TDD acceptance packet

Keep each slice separately testable and reviewable. Slice 1a (pure canonical values and reference parsers) can proceed independently of #84 migrations and #134 lifecycle proof once its serializer is locked below. Source schema/migration work waits for #84 current backend/package gates. Adapter descriptors, adapter payload tests, and dynamic admission work wait for #134 proof and #143's resulting contract. Package compiler/source/provider implementation belongs to #130/#135/#136; Deployment projection schema belongs to #130/#89.

### Slice 1 — typed IDs, canonical values and runtime-plan envelope

**Slice 1a paths:** `action_server/src/actions/server/deployments/ids.py`, `canonical.py` (new package); `action_server/tests/action_server_tests/test_deployment_canonical_values.py` (new). Keep adapter payload/contracts out of this slice.

**Tests first:**
- Raw-byte fixtures cover strict UTF-8, duplicate raw keys, duplicate keys created by NFC, lone surrogates, NaN/Infinity, invalid/underflow/overflow numbers, safe-integer boundary and rejected next values.
- Verify `rfc8785==0.1.4` byte output against committed RFC 8785 vectors plus domain vectors for `-0`, `1.0`, exponent boundaries, map order and domain separation; test the explicit NFC pre-pass separately.
- Identical valid input serializes byte-for-byte and hashes identically in a fresh process. Generic canonical JSON preserves array order; sort only set-valued fields declared by an owning schema.
- Runtime-validated UUID, typed hash, and full-reference constructors reject malformed/noncanonical public inputs and Pydantic coercion; Workspace/package/deployment scoping is checked at their typed boundaries. Digest kinds use distinct Python types; repository validation verifies each digest against its owning canonical object.
- Opaque `ContractId` is not parsed as a version; the generic PEP 440 range parser accepts/rejects according to one grammar. This tests only the frozen header primitives, not any adapter descriptor or payload.
- No Package/RuntimePlan/Deployment digest preimages or source-artifact filesystem walk are implemented here; #130/#135/#143 own the canonical payloads and compiler outputs.

### Slice 2 — additive schema and stable default Workspace

**Paths:** `_models.py` or typed model module, `migrations/migration_add_deployment_revision_graph.py`, migrations registry, `test_deployment_migrations.py` (new).

**Tests first:**
- Fresh SQLite creates migration 13+ objects, one persisted default Workspace and no duplicated Workspace on repeated startup.
- Fresh PostgreSQL initialization, which stamps the current registry after direct table creation, invokes the same DDL/bootstrap helper and creates the same default Workspace/scoped keys as migrated SQLite/PostgreSQL.
- Existing current database with ActionPackage/Action/Run/schedule/artifact records migrates without changing or deleting any row; old Run remains explicitly legacy with no synthetic pin.
- Inject failure after each DDL/bootstrap phase and immediately before migration-stamp insertion; prove transaction rollback removes newly created schema/default rows and leaves original tables/records/read paths intact; rerun succeeds. Verify the documented SQLite backup exists, and verify PostgreSQL recovery via an explicitly captured pre-migration backup plus transaction rollback.
- Same Workspace ID is returned after database close/reopen and by two Runtime instances sharing the database; it is independent of datadir name, port, environment, or PID.
- Inspect/assert every exact tuple in the scoped-FK matrix above from SQLite `PRAGMA foreign_key_list` and PostgreSQL `information_schema`/`pg_constraint`/`pg_attribute`, including child/parent column order. Require current-pointer FKs on all four owner kinds, same-deployment `previous_revision_id`, `rollback_of_revision_id`, and request `parent_revision_id` plus `result_revision_id`, exact binding→deployment-package and binding→provider-revision tuples, and package/provider/worker/policy owner tuples.
- For each scoped tuple family, attempt a cross-Workspace and same-Workspace-wrong-owner insertion and require FK rejection. Specifically prove request parent/revision cannot name another Deployment's revision; ancestry cannot name another Deployment's revision; binding cannot pair package A's requirement with package B's Package Revision; and grant rows cannot pair a revision with another provider/worker/policy owner. Run each negative in a savepoint/rollback so later cases remain independent.
- On SQLite, prove forward/cyclic DDL creation with foreign keys enabled, owner→first revision→pointer publication in one transaction, pointer failure rollback, `PRAGMA foreign_key_check`, and all four `PRAGMA foreign_key_list` entries. On PostgreSQL, prove pointer constraints are absent during the owner-table phase, installed after revision-table creation, validated, and then match the same normalized constraint graph.
- Attempt UPDATE and DELETE against every immutable revision, derived join, and idempotency receipt; each must fail. Verify only pointer/state rows mutate through publish/pause/resume/retire operations.
- Verify initial revision NULL ancestry, publish parent=current plus exact next sequence, rollback parent=current plus rollback target, stale-CAS leaves no revision/request/pointer partial writes, and cross-owner ancestry is rejected independently of those repository checks.
- Assert canonical revision JSON remains authority and normalized indexes are derived/checked. Validate manifest-embedded binding requirements on publish and resolve. Assert no `current_sequence` column or pointer/sequence drift.
- PostgreSQL run is a separately recorded gate under #84 current-head evidence; do not infer it from SQLite parity.

### Slice 3 — immutable revision repository and pointer CAS

**Paths:** `deployments/repository.py`, `deployments/publish.py`, `test_deployment_revision_repository.py`.

**Tests first:**
- Insert two immutable revisions; a second write to same revision digest/scope with identical bytes is idempotent, but different payload under same identity fails as corruption.
- Publishing with current ETag advances pointer atomically; stale ETag returns conflict and leaves pointer/revision graph unchanged.
- Two independent processes race to publish from N; exactly one N+1 wins; the losing writer can reread and resubmit against the new head.
- Same idempotency key + same operation/request digest replay after pointer advance returns the original result before stale-ETag CAS. Reuse with different command kind, target, parent ETag, candidate digest, or rollback target returns `idempotency_conflict`.
- Initial Deployment + revision + pointer + idempotency receipt is one atomic `If-None-Match: *` create; a failed initial transaction leaves no identity, and a replay returns the same generated IDs.
- Rollback from N+1 to N creates a new N+2 identity with `rollback_of=N`, `previous=N+1`, and config equal to N; N/N+1 provenance remains unchanged.
- No source/binding/profile/projection/config mutation is accepted after insert.

### Slice 4 — scoped plan resolver and deterministic snapshot

**Paths:** `deployments/resolver.py`, `deployments/authorization.py` boundary protocol, `test_deployment_resolution.py`.

**Tests first:**
- Two processes/Runtime replicas reading identical DB state produce identical package/capability/plan/binding/policy/WorkerProfile/catalog/resolution digests.
- Two packages with the same package-local capability and plan keys/digests still resolve through distinct full `CapabilityRef`/`RuntimePlanRef`; cross-package selection fails closed.
- `UseDeclaredDefault` returns only its full declared ref; an explicit full plan ref must be allowed by that capability in the selected revision; absent/default/undeclared refs and duplicate policy are rejected. There is no “first compatible plan” or fallback order.
- Cross-Workspace refs for every object kind fail safely (no pointer change, no data leak, public not-found); same content digest in two Workspaces does not make references interchangeable.
- `Current` and `Retained(full DeploymentRevisionRef)` are distinct; retained is separately reauthorized and never redirected. A full ref from a second package or Workspace is rejected.
- If N+1 or pause commits before `RunService.create_pinned`, a Current request creates no stale Run; it re-resolves/readmits. If pause/retirement commits first, new admission is blocked. If N's admission commits first, the Run pins N. Retained N remains exact only while authorized and Deployment is active.
- Snapshot stores only the full selected refs plus the generic `RuntimePlanHeader`; it contains no adapter payload. Resolver verifies copied header equals the selected Package Revision header.
- Wrong/missing/unsupported AdmissionSnapshot schema and digest mismatch are rejected at the #83 handoff; #143 defines all further admission reasons, dynamic observations and modes in its later owned slice.

### Slice 5 — bindings, policy/profile revision pinning

**Paths:** `deployments/bindings.py`, `profiles.py`, repository joins, `test_deployment_bindings.py`.

**Tests first:**
- `preview(candidate)` with a required logical binding missing returns `needs_binding` and writes nothing; `publish(candidate)` rejects until that mapping exists; optional binding omission remains explicit.
- A binding accepts only a provider revision within its Workspace and requested capability/scope. Same profile ID in a second Workspace is rejected.
- Rotation to a new provider/profile/policy revision creates a new Deployment revision and resolution digest; old Runs still reference the exact older profile/config generation. If the owner-local old config is absent, a retry blocks rather than resolves current.
- Runtime provider reference and business secret/data bindings remain distinct typed grants even if one profile store implements both.
- No credential/URL is serialized into PackageRevision, DeploymentRevision, catalog, Run pin, audit event, log, or worker protocol payload.
- Worker Profile requirements remain distinct from actual worker ID or cache locality; #90/#138 and #143 define dynamic placement/admission outcomes.

This slice is downstream of #130's binding-requirement schema, #91's authorization mapping, and #143's admitted profile/requirement interpretation; do not implement fields outside those contracts.

### Slice 6 — projection and catalog identity

**Paths:** `deployments/projections.py`, existing catalog revision integration owned with #89, `test_deployment_projection.py`.

**Tests first:**
- After #130 accepts projection vocabulary, round-trip its typed schema and verify projection remains independent of Runtime Plan selection.
- Sorting/normalization yields the same catalog digest across registration order and Runtime replicas; equivalent surfaces get equal digest.
- #130/#89 tests reject duplicate external names and invalid schema transforms; that exact vocabulary is not predeclared here.
- Projection/schema change changes catalog digest; plan/provider/worker availability change alone does not.
- Existing Action/Robot exposure behavior remains under #130's accepted projection/import contract; no arbitrary shell tool is introduced.

### Slice 7 — API/Run handoff and local compatibility

**Paths:** `/_api_deployments.py`, `api.py` router registration, resolver→#83 `RunService` protocol adapter, legacy routes as compatibility bridge, `test_deployment_api.py`.

**Tests first:**
- Create/read/list/update/rollback/retire API obey Workspace scoping, `If-Match`/`If-None-Match`, idempotency replay/conflict, redaction and auth boundary.
- `resolve` and `runs` share the same full-ref resolver; if preflight N loses a race to N+1 or pause before Run commit, no stale Run is admitted. Current retries resolve/readmit current; Retained is reauthorized and never redirected.
- The #83 create call receives exactly the resolved snapshot and a schema-versioned `AdmissionSnapshot` whose digest equals it; retries read the pinned snapshot and never call current resolver; restart-as-new calls Current.
- A locally migrated/default package continues to appear/expose through the supported legacy-compatible local UI/CLI after successful #135 compile; one bad package reports blocked without preventing unrelated packages from starting.
- Regression tests prove all legacy Run/API/Robot/history/artifact endpoints remain readable. No test fabricates pins for old history.

This end-to-end slice waits for #83's Run contract and the #130/#135 import/projection bridge; it must not define a new blocked-Run outcome or adapter fallback.

### Acceptance matrix tied to #129

| #129 criterion | Design element | Required proving test |
|---|---|---|
| 1. Two Runtime replicas agree | Canonical snapshot and full revision/reference digests | Slice 1a canonical bytes; Slice 4 independent-process equality after schema gates |
| 2. N/N+1 and retries | CAS current pointer plus #83 pinned snapshot | Slice 3 concurrent publish; Slice 4/7 Current selector and Run admission race |
| 3. Rollback affects new Runs | Rollback publishes N+2; prior pins are immutable | Slice 3 rollback and replay; Slice 7 asserts old pins unchanged |
| 4. Test/production reuse Package Revision | Package Revision stays separate from Deployment bindings/profile | Slice 5 two Deployment Revisions share exact Package ref and differ in binding/profile refs |
| 5. Explicit Runtime Plan/no fallback | Full refs and explicit `RuntimeSelection`; payload semantics remain #130/#143-owned | Slice 4 confirms default/explicit allowed full-ref selection and rejects stale/foreign refs; #143 separately tests adapter absence |
| 6. Ineligible worker declines | Worker Profile reference pins eligibility policy; #90/#138/#143 own live selection | Not a #129 adapter test; require those owners' worker/admission conformance |
| 7. Provider reference omits URL/credentials | Provider-profile revision pins config generation and locator refs | Slice 5 redaction and old-generation retry blocking |
| 8. Non-RCC plan has no fake RCC fields | #129 pins full plan ref and generic header only; #143 owns payload tags | #143 schema/conformance tests after #134 proof; no adapter union in Slice 1a |
| 9. Same lifecycle local | Default Workspace, local Worker Profile and additive bridge | Slice 2 migration; Slice 7 local API/CLI compatibility after #130/#135 |
| 10. Single/multi Workspace safe | Full scoped refs, exact composite constraints and safe errors | Slice 2 cross-scope DB negatives; Slice 4 duplicate package-local ref tests |
| 11. Restart current vs retry pinned | `Current` versus `Retained(ref)`; retry uses pinned snapshot | Slice 4/7 race, retained authorization, retry/restart tests |
| 12. Mixed versions fail safely | Unknown schema fails closed; activation gate is #140-owned | #140 reader/writer matrix blocks pointer activation if any serving reader is incompatible |

## Dependency edges and non-circular ownership

```text
#84 accepted shared DB/migration behavior
          |
#129 identity + Deployment/Revision + ResolutionSnapshot contract
    |                 |                   |
    v                 v                   v
#130 Package v3   #83 Run/Attempt    #143 adapter/preflight contract
    |               (consumes pin)    (after remaining #134 proof)
    v                 ^                   |
#135 compiler ------+                    v
    |                                  #139 conformance
    v
#136 Package source/cache             #90/#138 worker placement/protocol
```

More precisely, #129 does not wait for a new #143 service or a second adapter. It sets only the package-reference and selected-plan envelope required for a Deployment revision and Run snapshot. #130 owns the authoritative Package/Capability/RuntimePlan manifest schema and projection vocabulary; #129 cannot invent compiler behavior. #135 produces that manifest from trusted source; it does not get to create Deployment bindings. #143 owns runtime descriptors, admission outcomes/modes and adapter lifecycle; #129 stores an allowed plan identity and hands it to #143, but does not implement RCC/uv methods. #83 stores the immutable `ResolvedExecutionSnapshot`; it does not recompute the current Deployment. #90/#138 choose/lease a worker matching the pinned WorkerProfile; they do not change the plan. #136 distributes source artifact by digest; RCC’s artifact/provider/lease plane remains RCC-owned.
