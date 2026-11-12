# Bundle registry prerequisite: review packet

Patch `bundle-registry.patch`, SHA256 `dd9eb6c30b5ed7e46643cd57f799509a72e4aad7dbf7ebce959052013b021cf4`. Only foundry/package_registry.py and new test_bundle_package_registry.py. Exact base and resulting file hashes in identity.json; root registry source remained identical to captured base. Dependency: frozen codec/compiler patch609ec189a7c49bc283f4a9e915f8183ca8a1ff9dfbb9800b6a4a5be446bf012c and parent-owned narrowed CompiledPackage protocol (manifest_json/source_archive/package_revision_id). No legacy compiler, authoring, runner, Task, bootstrap or migration edit.

## Stable integration API for this private checkpoint

```
compile_trusted_bundle(entries, *, policy: BundleCompilationPolicy,
    trusted_actor: Actor, workspace_id: WorkspaceId,
    application_id: DeploymentId) -> CompilationResult

load_verified(ref: PackageRevisionRef)
    -> CompiledPackageRevision | CompiledCapabilityBundle

selection_for(capability: CapabilityRef, plan: RuntimePlanRef)
    -> RegistryCapabilitySelection
```

RegistryCapabilitySelection fields: package_revision (outer PackageRevisionRef), capability, runtime_plan, compiled (verified singleton compiler preimage). Runner must check returned outer refs against snapshot and keep outer bundle revision in all execution/Task identity fields. Inner compiled revision serves integrity verification only; no independent SQL revision is admitted. Legacy load returns only CompiledPackageRevision and rejects bundle evidence. No fallback to first member, unknown plan or another member's schema.

Compile uses same explicit generate_backend + Workspace deploy authority, configured trusted executor/developer-admission, and post-compile live reauthorization. Duplicate/conflicting requirement IDs across members reject before compiler execution and again on durable load. BundleCompilationOutcome and exact original bundle object identity remain in bounded pending host memory; existing admit_compiled rejects copied/fabricated objects, different actor/workspace or revoked authority. CompilationResult evidence derives readiness from verification of all ordered receipts, never a caller-supplied ready flag. Failed phases never create pending admission.

Same source provider seals shared bytes; same FoundryPackageRevision/FoundryRequest/FoundryAudit transaction and Workspace lock own admission. Exact one outer row, idempotency request and audit; no mirrored member rows or alternate authority. Existing trusted compilation admission policy grants only package/capability/plan/logical refs from this newly admitted bundle, with existing deploy/execute operations. Replay never resurrects revoked grants. Commit uncertainty retains source seal under existing policy, not speculative deletion.

New evidence discriminator `actions.local-capability-bundle-admission/v1-draft` is PRIVATE. Codec bundle version is also draft. Convert to a reviewed stable discriminator only at integration/release schema freeze; this patch does not advertise public compatibility. Existing `_SCHEMA` v1 evidence construction/bytes and legacy load remain unchanged. All bundle metadata/evidence/source sizes checked before loading; unknown tags, malformed receipts, mismatched sealed source, inventory or scoped refs fail closed.

## Evidence and limitations

- red.txt: three new SQLite tests failed on absent compile_trusted_bundle before implementation.
- initial.txt:2PASS/1fixture failure (test used nonexistent scope_kind instead of actual subject_kind), preserved.
- expanded.txt:11PASS/1fixture failure (test used output_schema_json instead of actual AdmittedActionSchema.output_schema), preserved.
- final-sqlite.txt: **26PASS, zero skips,26deselected,3.68s**. 19 new bundle boundary cases +7 unchanged legacy registry cases. SQLite real SQL/filesystem seals; synthetic compiler executor. PG cases explicitly deselected, not passed.
- lint/type/isort/apply-check passed. types.txt records one module Mypy success. Root narrowed protocol was used without copying or editing it.
- Legacy test file is a verbatim scratch copy of current test_foundry_package_registry.py renamed test_registry_legacy_compat.py to avoid import collision. Not in patch. Its restart test runs a genuine fresh interpreter against unchanged legacy root reader; this is legacy compatibility, not bundle process-restart proof. Bundle reload test reconstructs registry service in-process with sealed SQL bytes.
- Tests cover exact outer revision, member schemas/Work Item/logical contracts, missing selection, cross-member plan and cross-workspace rejection, duplicate/conflicting requirements, aggregate evidence roundtrip, phase failure, exact grant set, live compile/replay revocation, copied outcome rejection, transactional rollback and competing admissions converging to one row/request/audit, corrupt evidence/inventory/manifest refusal.
- No RCC, containers, native worker, shared cache, PostgreSQL execution, new venv, root edits, migration or external mutation. No resources retained/claimed by this lane.

Source command:

```
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /workspace/actions/action_server/.venv/bin/python -m pytest -q /workspace/actions-recovery-327/bundle-registry-draft/action_server/tests/action_server_tests/test_bundle_package_registry.py /workspace/actions-recovery-327/bundle-registry-draft/action_server/tests/action_server_tests/test_registry_legacy_compat.py -k sqlite
```

## PostgreSQL recipe (not run)

Use an explicitly owned synthetic PostgreSQL service, not live/user config. Set ACTIONS_INVOICE_TEST_POSTGRES to its DSN and ACTIONS_REQUIRE_INVOICE_PROVIDERS=1, then run the exact command above with `-k postgresql`. Existing foundry_fixtures creates a distinct random schema per case and drops it in finally. Expect26selected cases, zero skips; retain all failures. No new migration expected. Registry patch source proof remains SQLite-only until this gate passes.

## Documentation improvement

- Canonical file proposed: docs/skills/repository-operations.md, package/compiler compatibility guidance.
- Exact durable delta:

> Bundle registry admission must use the same trusted compile permissions, exact pending compiler-object identity, source seal and transactional Package/Request/Audit authority as singleton admission. Admit only the outer bundle revision; inner singleton revisions are verified preimages, not separate packages. Legacy load must reject bundle evidence. Use explicit tagged loading and exact capability/plan selection for per-capability schemas, Work Item policy and logical requirements. Because BindingRequirementRef is package-revision scoped, duplicate requirement IDs across members must be rejected before execution and on reload; do not let a first matching contract win. Derive CompilationResult readiness from all verified compiler receipts and preserve aggregate evidence on reload. Admission replay must not recreate revoked grants.

- Evidence:19 new real SQLite registry cases plus7 legacy cases; explicit pending-object/permission rechecks; duplicate requirement preflight/reload validation; exact reference projection and transactional admission patch.
- Stale/ambiguous guidance removed: prevents interpreting an inner revision or first matching requirement as bundle authority; no integrated runner support claim.
- Remaining uncertainty: PostgreSQL gate and root-owned authoring/runner/Task join, actual canonical multi-capability Run/Attempt and installed restart still pending. Native two-Action compiler proof remains separate, already accepted.

Upstream disposition: none. Local integration; no upstream defect/report or external mutation.
