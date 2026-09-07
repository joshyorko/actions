# ADR 0129: Workspace-scoped capability deployments

- Status: Accepted
- Issue: joshyorko/actions#129

## Decision

Actions models deployment as a Workspace-owned, immutable control-plane
snapshot. Package content declares capabilities and compatible Runtime Plans;
the deployment supplies visibility, policy, bindings, and worker requirements.
No package, adapter, worker, filesystem path, process, or Kubernetes object is
an authority for deployment state.

### Objects

| Object | Mutability | Responsibility |
| --- | --- | --- |
| Workspace | managed identity | Trust, authorization, providers, quotas, and audit boundary |
| Package | stable identity | Reusable package identity |
| Package Revision | immutable | Signed source, capability graph, and declared Runtime Plans |
| Runtime Plan | immutable | Normalized adapter contract, digest, requirements, and namespaced adapter specification |
| Deployment | stable Workspace identity | Current pointer and lifecycle for one deployed capability projection |
| Deployment Revision | immutable | Package Revision, projection, plan policy, bindings, worker profile, limits, and provenance |
| Binding | immutable reference | Logical requirement to an authorized Workspace provider reference; never a secret value |
| Worker Profile | immutable | Runtime/adapter features, platform, resources, trust, network, and placement constraints |
| Run Snapshot | immutable | Exact resolution used by a Run and every replacement Attempt |

Deployment, Package, Runtime Plan, Binding, Worker Profile, and Run Snapshot
records carry `workspace_id`. References across Workspaces are rejected even
when the caller knows the referenced identifier or digest.

### Runtime Plan and selection policy

A Runtime Plan has at least `runtime_kind`, `plan_digest`, schema version,
adapter contract/version/features, platform/architecture/ABI requirements,
supported capability IDs, provenance, and an adapter-namespaced specification.
An RCC specification may retain Environment and provider-profile references;
those references are not generic Deployment fields. A non-RCC plan does not
receive fabricated RCC fields.

A Deployment Revision records, per capability, the declared plan IDs, an
optional explicit default, whether caller selection is allowed, and adapter,
feature, provider-profile, conformance, and placement constraints. Resolution
is valid only when the selected plan is declared, authorized, and compatible
with the policy and eligible Worker Profile. There is no fallback order: an
unavailable or forbidden default blocks the Run. Caller selection is allowed
only when the revision explicitly permits it.

### Binding and projection

Bindings map logical requirements such as `secret`, `oauth`, `data`, `queue`,
`artifacts`, `package-source`, `runtime-artifact`, and `network` to
Workspace-scoped provider references plus policy/version metadata. Plaintext
secrets, credentials, arbitrary provider URLs, and provider object indexes are
never stored in Package Revisions, Deployment Revisions, Run Snapshots,
catalogs, or logs.

Capability projection (MCP, HTTP, event, workflow, CLI, or App surface) is
stored independently from Runtime Plan selection. Projection changes therefore
produce a new Deployment Revision and cannot alter package source identity.

### Resolution and pinning

Before execution, the resolver atomically records a Run Snapshot containing:

```text
workspace, deployment, deployment_revision,
package_revision, capability, capability_schema,
runtime_plan, runtime_kind, plan_digest,
adapter_contract/version/features, adapter_specification_policy,
binding_references/policy_versions, worker_profile,
catalog_revision, authorization_decision, idempotency/effect_scope
```

Every replacement Attempt reads this snapshot. A retry never resolves the
current Deployment, selects another adapter, adopts a newer runtime artifact,
or changes bindings or worker policy. An explicit restart creates a new Run
and may resolve the current revision and another allowed plan.

### Lifecycle

Publishing a change validates package, plan, adapter, provider, and worker
compatibility, then atomically advances `Deployment.current_revision_id`.
Existing Runs retain their snapshots while new Runs use the new revision.
Rollback advances the pointer to an existing revision and has no effect on
in-flight Runs. Revisions, plans, artifacts, bindings, and worker profiles are
retained while referenced by Runs, Attempts, Tasks, Work Items, artifacts,
catalogs, or audit records; garbage collection is reference-aware and never
rewrites provenance.

Revocation blocks new resolutions and records an explicit blocked/manual
recovery result for Runs whose pinned plan can no longer be satisfied. Mixed
runtime/worker/adapter versions fail closed when they cannot enforce the
snapshot contract.

## Required resolver checks

1. Verify Workspace authorization and all referenced object boundaries.
2. Load the current Deployment Revision (or an explicitly requested revision).
3. Verify capability projection and Package Revision identity.
4. Select exactly one declared Runtime Plan according to its policy.
5. Resolve authorized bindings and an eligible Worker Profile without exposing
   secret material.
6. Persist the complete Run Snapshot before execution; reject partial or
   ambiguous resolution.

The same algorithm applies to local single-binary mode and distributed mode.
Local mode may synthesize one Workspace and use SQLite/local providers; neither
mode changes object identity or pinning semantics.

## Acceptance scenarios

- Two replicas resolving one revision produce identical object IDs, plan
  digest, binding policy versions, worker profile, and catalog revision.
- Publishing N+1 routes new Runs to N+1 while N retries remain on N; rollback
  changes only new resolution.
- Test and production Deployments reuse a Package Revision but use distinct
  authorized bindings, plans, and Worker Profiles.
- A package declaring RCC and uv uses the explicit default; missing or
  unavailable selection fails without fallback.
- An ineligible worker, unauthorized provider, cross-Workspace reference, or
  package-provided adapter authority is rejected.
- RCC keeps its namespaced Environment/provider policy; a non-RCC plan has no
  fake RCC identity. Local mode exercises the same lifecycle.

