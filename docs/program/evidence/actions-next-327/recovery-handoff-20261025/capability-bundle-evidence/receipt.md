# Bounded capability bundle prerequisite

Frozen patch `capability-bundle.patch`, SHA256 `609ec189a7c49bc283f4a9e915f8183ca8a1ff9dfbb9800b6a4a5be446bf012c`. Three NEW files only; no root source, existing legacy compiler/reader, versions, registry, bootstrap or database changes. Inspection base b23df406f1e32e508e9a951f2469c6f57fa8c703; parent advanced to 4f437a10bebfb41299c18170eaf3014cdca2e3cb during lane. Patch apply-check passes there; exact legacy compiler SHA identical at original base and qualification (identity.json).

## Implemented interface

- `CompiledCapabilityBundle(manifest_json: bytes, source_archive: bytes)`: closed canonical `actions.capability-bundle/v1-draft` metadata, <=512KiB, 1..8 sorted distinct capabilities. Shared immutable source archive stays separate from JSON. Bundle revision is domain-separated digest of all canonical preimages, not one member's legacy revision.
- `assemble_bundle(tuple[CompiledPackageRevision,...])`, `verify_bundle`, `encode_bundle`, `decode_bundle`: reuse unchanged complete legacy source/schema/plan/manifest verification for every member. Require same package identity/compatibility/source/build identities. Preserve each member's Work Item and logical declarations. Reject duplicate/unordered capability IDs, duplicate plans, unknown shape/version, malformed types/boolean schema version, corrupt preimages and source. One exact Action/RCC plan per member; no inferred shared-plan equivalence.
- `select_capability(bundle, exact_bundle_revision, capability_id, exact_plan_digest)` returns immutable `VerifiedCapabilitySelection`. Member's `compiled.package_revision_id` is an integrity preimage ONLY; registry must retain selection.package_revision_id as authoritative bundle revision. No index-zero or unknown-plan fallback.
- `BundleCompilationPolicy(tuple[PythonCapabilityPolicy(action_name, PackageCompilationPolicy),...])`, `compile_generated_python_bundle(...) -> BundleCompilationOutcome`, `verify_bundle_compilation_outcome`: one bounded frozen source snapshot, explicit trusted-developer admission, serial existing real pinned RCC build/import/test executor calls for each declared Action. Exact complete metadata set checked on every inspection; duplicate/missing/unlisted/escaping Action and changing normalized inspections fail. All receipts bound to exact sorted members. Failure returns no partial bundle and bounded phase code.

Compiler executes each of the three bounded existing phases per Action, at most eight Actions. This conservative implementation repeats builds/imports/tests; no cached synthetic phase success, invented shared plan, optimization or coordinator source import. Actual prepared RCC executor is supported by signature but not run in this lane. Only Python Action/RCC routes accepted; no Robot declaration route is advertised or silently mapped to Action. Typed Robot adapter support is a remaining follow-on, not acceptance evidence.

## Verification

Before implementation, regression collection failed on missing new module (`red.txt`). After implementation initial14 boundary tests passed. Expanded final focused file: **29 PASS, zero skips, 0.57s** (`final-tests.txt`). Tests use synthetic executor and real legacy immutable verifier; no installed/runtime execution claims. Final Ruff/isort checks passed (`lint.txt`); Mypy two new modules passed (`types.txt`). `git apply --check` passed at freeze HEAD. Full suites, SQL registry integration and native RCC not run by this bounded lane.

Command:

```
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /workspace/actions/action_server/.venv/bin/python -m pytest -q /workspace/actions-recovery-327/capability-bundle-draft/action_server/tests/contract_tests/test_capability_bundle.py
```

Scratch-only conftest inserts ONLY the new deployment module directory in existing package search path; excluded from patch. Existing Runtime prepared venv and legacy modules supply dependencies. No new venv/install/full checkout archive. Initial14-test iteration accidentally used auto-loaded logging plugin; final25/29-test iterations explicitly disabled plugin autoload to avoid unnecessary instrumentation/disk growth. No RCC/container/native process/cache claimed. Root compiler and frozen suites untouched.

## Proposed registry seam (not implemented)

Add explicit evidence tag for this bundle. Persist canonical bundle metadata/shared archive AND exact successful ordered phase receipts through existing compiler-issued pending outcome/Foundry Request/Audit path. Verification is integrity, not author permission or evidence issuance; never accept arbitrary client-authored bundle as compiler-issued.

Add `load_verified` tagged legacy-or-bundle and exact `selection_for(capability, plan)`. Legacy-only `load` MUST reject bundle instead of choosing its first member. `get_capability/schema_for/get_binding_requirement` use exact selected member; `get_runtime_plan` advertises only that member. Use bundle revision in PackageRevisionRef, deployment pins and Run snapshot; do not expose or admit singleton member revision as a separate package. Registry constructor/context supplies workspace+Package UUID scope; pure compiler package_id is portable metadata, not authorization. No new migration inherently required; do not rewrite legacy rows/hashes. Execution bridge must validate selected adapter/entrypoint and selected bundle revision before spawn/publication; current singleton runner is not wired.

Native proof requires exclusive released Core a3 prepared RCC home from parent: real two distinct generated Actions, actual import/build/tests, deterministic repeat, correct selected schemas/policies with original source removed. After registry/runner wiring, both actual Runs/Attempts/output provenance, installed restart/rollback are still required. Robot RCC and direct-framework adapters, Task/worker dispatch and full owner scope remain open.

## Documentation improvement

- Canonical file proposed: docs/skills/repository-operations.md, package/compiler compatibility section.
- Exact durable insertion:

> A capability-bundle compiler may compose independently verified singleton preimages without changing legacy formats. Its bundle revision must cover every member and the shared immutable source; each selected capability retains its own schema, Work Item declaration, logical requirements and exact plan. The inner singleton revision is verification evidence, not a second package identity. Registry and Run references must pin the outer bundle revision and reject unknown capability/plan pairs rather than selecting the first entry. Successful compiler phase receipts must match the ordered member preimages; codec integrity alone does not authorize registry admission. Synthetic executor tests qualify these boundaries only. Native compilation and canonical execution of every selected capability remain separate acceptance gates, and unsupported Robot routes must refuse explicitly.

- Evidence:29 focused tests, unchanged legacy verifier SHA, explicit format/version/member checks and receipt verifier in patch.
- Stale/ambiguous guidance removed: proposal removes implication that manifest lists or a selected member's revision establish multi-capability registry/execution support. Existing legacy guides need not claim new integrated support before root wiring.
- Remaining uncertainty: native compiler behavior/performance, registry issuance/projection and installed runner/Robot adapters unqualified. No supported real runtime behavior newly claimed.

Upstream disposition: none. Local compiler integration work; no established upstream defect or external mutation.
