# Portable expectation corrections

Patch `portable-contract-expectations.patch`, SHA256 `cb9323f09dffc99e3eec4cc5b9267cb1982e9e28d549b32051c62170f95084f1`. Base/current root test bytes at d4093af079ac311223326e68b1869a58ff2b3b0a; identity.json records exact before/after hashes. Root apply-check and Ruff passed. Three test/snapshot files only; no source/migration/version/dependency change.

Inspected `/workspace/actions-recovery-327/evidence/a35-frozen-portable-bounded/pytest.log`. The four named failures occur at stale assertions: database exact table list, root help snapshot, declared Core floor, emitted wheel Core floor. Later PostgreSQL connection-refused errors after the interrupted run are separate root-owned accounting; no full-suite pass is claimed here.

## Changes and independent evidence

1. `test_database.py::test_migrate` retains its explicit table assertion and adds exactly five names: foundry_source_revision, foundry_provider_revision, foundry_provider_availability (migration19), run_execution_intent (migration20), run_task_receipt (migration21). Provider MODEL_CLASSES is exactly those three provider models. Migration21 also adds run_pin.state_updated_ms, which remains covered by the existing full column comparison. The test still checks all migration rows, exact columns and indexes against fresh create_db, plus historical Action data/enabled semantics. No dynamic expected-table derivation, schema relaxation or skip.
2. `test_cli/test_help_-h.txt` adds providers-local to both command enumerations and its exact registered help text. `_cli_impl.py` explicitly registers that existing offline saved-owner command; no CLI behavior change.
3. `test_active_contracts.py` changes only the actions-core minimum from1.1.0a2 to1.1.0a3 in the source metadata assertion and wheel METADATA assertion. Current Runtime pyproject explicitly requires>=1.1.0a3,<2.0.0 and Core package is1.1.0a3. Work Items0.5.0a2 and intentional negative Runtime candidate-version assertions remain unchanged.

## Validation

- red.log:1 expected help failure plus2 setup errors because the default feedback fixture sought scratch RCC. No RCC ran. Added scratch-only conftest feedback override, excluded from patch.
- red-verified.xml/log: all3 small target tests reproduced their exact stale assertion failures.
- green.xml/log: all3 target tests PASS,0skip,0.58s: SQLite v0->21 full migration/schema/index parity; root help snapshot; Runtime declared dependency metadata.
- retained-wheel-metadata.json: read-only inspection of retained installed-a35 Runtime wheel, with exact wheel SHA256, confirms emitted `Requires-Dist: actions-core (>=1.1.0a3,<2.0.0)`. No build, installation or uninstall execution.
- lint.log: configured Ruff clean. Root git apply --check clean.

The complete clean-wheel dual-uninstall-order test was intentionally NOT rerun under this lane's storage/bounds restriction. Only its failed metadata assertion was checked against an existing retained a35 artifact. Root owns full portable rerun and full wheel qualification. No RCC/cache/container/credential/live configuration/root mutation occurred.

## Exact canonical guide delta

Target `docs/skills/repository-operations.md`, release regression guidance:

> When advancing the migration chain or private candidate floor, update independent test expectations alongside the contract. The v0 migration test must retain an explicit table list and fresh-versus-migrated column/index comparison; add only tables justified by named migrations rather than deriving the expected list from current models. A Core candidate floor appears in both Runtime source metadata and emitted wheel assertions; keep both aligned while preserving unrelated SDK floors and intentional negative version cases. Root help snapshots must include each explicitly registered offline operator command. Reading an existing wheel's metadata validates its dependency assertion, but does not replace clean installation/uninstall-order qualification.

Evidence: migration19/20/21 source, current CLI registration, declared package floors, three red->green small tests, and SHA-recorded retained-wheel metadata inspection. Exact proposal only; sole integrator owns canonical guide edit.

Upstream disposition: none. All failures are Actions-owned expectation drift; no dependency defect or external mutation.
