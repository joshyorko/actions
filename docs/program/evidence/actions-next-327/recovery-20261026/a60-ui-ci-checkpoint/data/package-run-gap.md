# a59 Package/Run continuation: exact fixture blocker

Status: **NOT RUN** for immutable Package/capability -> Run/Attempt -> artifact result. This is a bounded blocker record after inspecting the retained installed service fixture and available a59 receipts; no product code, grant, database, or test fixture was changed in this subdirectory.

## Current SQLite fixture state

The measured fixture is `../control-6eeae4646a1b.sqlite`, created by the installed service gate in the parent directory. It contains these tables only: `workspace`, `foundry_access_grant`, `foundry_request`, `foundry_audit`, `foundry_source_revision`, `foundry_provider_revision`, and `foundry_provider_availability`. It contains no `foundry_package_revision`, deployment revision/head, `run`, `run_admission`, `run_pin`, `run_attempt`, `run_access_grant`, or run-output state.

Its persisted workspace grant is only `provider.register`. The exact provider-reference grants are limited to `provider.inspect` and `data.read`; one CSV grant is deliberately left revoked to `provider.inspect` following the prior revocation check. There is no `deploy`, `generate_backend`, or `execute` workspace grant and no deployment, worker, policy, or output-provider reference grant. I did not add any permissions or tables.

The actual v2 source/provider records already retained here are usable inputs to a future composed harness:

- CSV source revision `sha256:ae5c17541c9732fd0f2413b5f8c5f3dd6b122ee9d3f40f6381eee4411e82426f`, object `sha256:82deaa1b42aa71c43d2f189d5bd34e8da1cf4a1c1a5de119bfa80edefc61d84c`, and operation `records.scan/v1` (read, no parameters, 10 rows, 4096 bytes, 5000 ms).
- Parquet source revision `sha256:9102abb5c4cbcbe78d65aa7475cbd4ea762dc5e1de80805563e7e7f04eb94642`, object `sha256:195963e40c3c38c7a7d8af232db0062fa2a82f552497a752b9791231f25448ea`, with the same operation contract.
- A separate CSV provider has `max_rows=1` for the adapter row-limit negative.

The installed registry and authorization path successfully exercised these sources through DuckDB in `../result.json`. This does not create Package authority or Run state.

## Why the next step cannot be claimed from available fixtures

The installed Runtime exposes `FoundryPackageRegistry.compile_trusted_source` and `admit_compiled` in `actions/server/foundry/package_registry.py` and `RunOutputControlPlane`/`RunOutputService` in `actions/server/run_outputs/service.py`. The existing `action_server/tests/action_server_tests/test_foundry_package_registry.py` fixture composes real SQL/blob storage but uses `contract_tests.test_package_revision_compiler._FakeCompilerExecutor`; its own module docstring says fake compiler tests do not qualify generated execution. It cannot support this acceptance claim. The current a59 installed API receipt at `recovery-20261026/a59-ci-checkpoint/a59-installed/installed-api-proof.json` qualifies source snapshot/archive/materialization only and explicitly says no Runtime service.

No admitted, actual compiler-verified a59 `CompiledPackageRevision`/`FoundryPackageRevision` was found in the retained SQLite fixture whose immutable manifest declares a logical binding to either of these source revisions. The `postgres-object-restore/receipt.json` records a separate actual generated consumer Run with four artifact readbacks, but its composition is an owned PostgreSQL component; its scope has no sealed Data Package binding and it is outside this SQLite-only continuation.

An honest next Package/Run gate needs all three of these exact inputs together: (1) a previously compiler-verified immutable a59 Package/capability manifest containing the `records.scan/v1` logical data requirement and immutable binding identity, already available without starting RCC or materializing a new environment; (2) the current schema/migrated SQLite fixture containing that Package, deployment selection, Run/Attempt, pins, and output state; and (3) pre-existing authorized actor grants for deployment admission/execution and output reads. None is present in the retained SQLite service DB. This lane did not invent a compiled object, use the fake compiler, add tables/grants, or invoke RCC. Without the accepted compiled Data Package and its authorized Run fixture, producing a result would falsely imply Package/Run acceptance.

## Canonical guide proposal (not applied)

Propose adding the following durable guidance to `actions/docs/skills/repository-operations.md` under installed sealed Data qualification:

> Keep installed sealed Data evidence layered. A decoded-source or `DuckDBSealedScan` PASS establishes only that installed component/service path. A Package/Run claim also requires the same wheel-bound, compiler-verified immutable Package manifest to declare the logical data binding, persisted deployment selection and Run/Attempt authority, and artifact readback bound to that exact Run. Registry tests using `_FakeCompilerExecutor` can qualify SQL/blob admission logic but do not qualify generated compilation or execution. Reuse only an existing compiler-verified Package/Run fixture when compiler/RCC materialization is out of scope; do not replace it with a hand-built compiled object or test double. Keep persisted provider grants distinct from deploy/execute/output grants and report the exact missing authority before mutating any fixture.

Evidence: the installed service receipt and read-only SQLite table/grant inspection above; installed `package_registry.py` and `run_outputs/service.py`; `test_foundry_package_registry.py`’s `_FakeCompilerExecutor`; and the exact a59 installed API and restore receipts. No canonical files were edited. Upstream disposition: none.
