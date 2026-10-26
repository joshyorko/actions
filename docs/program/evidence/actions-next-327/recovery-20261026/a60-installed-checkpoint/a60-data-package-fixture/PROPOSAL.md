# a60 Data-bound Package/Run harness proposal

**Review status: concrete but blocked before execution.** This directory contains only a review proposal. No test, RCC command, provider execution, credential/profile read, DB grant mutation, network/container operation, PostgreSQL action, or materialization ran. The PostgreSQL action remains unapproved; do not execute it.

## Exact blocker found in the existing RCC fixture

`test_generic_work_item_execution.py::test_real_generic_rcc` currently calls `generic(..., real=True)`, which feeds `_generated_action_entries()` into `PinnedRccPackageBuildExecutor`. The literal fixture `package.yaml` there pins `actions-core=1.0.2`; its static SHA-256 is `5dcc9dadd6157278933f036532bcf26643b6c1e100d87fa176e6736f4e8e3bf8`. The prepared RCC receipt requires `sha256:a17d5208f646fa6741ce99cbeca6a1dd37c5cbc0bb752b8c6087b0bdbf823807`, which matches the exact public manifest retained at `327-probes/a53-claimed/compiler/package.yaml` (Core 1.1.0a8, work-items 0.5.0a2, Robot Framework 7.4.2). The current fixture therefore fails the executor’s manifest identity check before RCC. It cannot be reused unchanged.

The existing logical Data fixture in `test_logical_execution.py` compiles `records.scan/v1` requirements, binds provider revisions, admits Package and Run state, then exercises `LogicalExecution.prepare/recheck`. Its module explicitly calls its compiler synthetic. The existing a59 installed source fixture proves real DuckDB scans on CSV and Parquet, but not compiler-bound Package execution. These pieces can be composed through existing public server APIs, but the proposal needs a test delta: exact a53 manifest bytes, Data-aware generated action entries, two logical requirements and provider choices, installed a60 product imports, and a `GeneratedRccExecution` configured with the same canonical `LogicalExecution` instance.

## Concrete proposed acceptance flow

Use `/workspace/327-probes/a60-consumer/consumer/bin/python` as the interpreter for product imports and assert all imported `actions.server.*` modules resolve under that consumer’s `site-packages`. Freeze the a60 Runtime wheel identity from `consumer-ready.json` (`b4b039a47091eb2808c51ea9c3b8117c0c0f4d700c066d87dfe0321b7bcec0b7`) in the eventual receipt.

Use the existing fixed synthetic two-row CSV bytes from `a59-installed-data/service-path/run_installed_data_service.py` and the retained 717-byte Parquet fixture at `a59-installed-data/service-path/fixture.parquet`. Do not regenerate Parquet during the execution lane. The existing immutable source identities from the a59 service receipt are:

| Provider | Source revision | Object digest | Logical operation |
|---|---|---|---|
| CSV | `sha256:ae5c17541c9732fd0f2413b5f8c5f3dd6b122ee9d3f40f6381eee4411e82426f` | `sha256:82deaa1b42aa71c43d2f189d5bd34e8da1cf4a1c1a5de119bfa80edefc61d84c` | `records.scan/v1` |
| Parquet | `sha256:9102abb5c4cbcbe78d65aa7475cbd4ea762dc5e1de80805563e7e7f04eb94642` | `sha256:195963e40c3c38c7a7d8af232db0062fa2a82f552497a752b9791231f25448ea` | `records.scan/v1` |

Bind both provider revisions in one immutable generated Package, under distinct requirement IDs (for example `csv_records` and `parquet_records`), with the same exact typed operation contract. Generated action source imports `from actions import action, data`; its action calls `data.scan("csv_records", "records.scan/v1")` and `data.scan("parquet_records", "records.scan/v1")`, and returns both row lists. Its generated test asserts the stable typed rows and equality. These are the established `actions.data.scan` and context APIs, not a server bypass.

Persist using `FoundryPackageRegistry.compile_trusted_source` with the **real** `PinnedRccPackageBuildExecutor`, then normal `admit_compiled`; select both bindings through `RuntimeDeploymentSelection.select_specification_with_bindings`; persist and resolve through `FoundryDeploymentService`; admit one Run through `RunOutputService`; claim its normal Attempt fence; execute through `GeneratedRccExecution` with the same registry/DB/Run service and a `LogicalExecution` built over `ConfiguredProviderExecution`; then read the Run output through the ordinary output service and assert the stored logical receipt contains the two exact provider revisions/source identities. Do not hand-author compiled package records, runtime plans, pins, or logical receipts. The existing worker’s supported internal path supplies `logical-context.json` plus its context digest to the child; the generated action consumes it via `actions.data.scan`. No code should set `actions.data._context.install_context` directly in the test harness.

### Local synthetic test grants only

The normal test DB would need these exact fixture-scoped records, created only by a reviewed test in its disposable SQLite DB. This is a list for root review, not authorization to create them here:

1. Workspace actor: `provider.register` for registering the two test providers; `deploy`, `execute`, `generate_backend`, and `apply_revision` for normal Package admission/Deployment; then the execution scope’s `execute`, `cancel_execution`, `read_application`, and the existing managed-work-item permissions (`work_items.read`, `work_items.enqueue`, `work_items.claim`, `work_items.complete`, `work_items.retry`, `work_items.cancel`, `work_items.review`, `work_items.artifact.read`) used by generic dispatch.
2. Each exact provider reference: `provider.inspect`, `data.read` for the two sealed scans. The existing logical fixtures also use `execute`/`deploy` where deployment selection requires provider execution authority; grant only the exact operations required by the selected path.
3. Worker, policy, and output-provider references: `deploy`, `execute`; the persisted Deployment reference: the existing execution and work-item permission set required by dispatch/readback.
4. Run output control plane: existing test-only `execute`, `read`, `cancel` binding for the exact Deployment reference.

The rows are `FoundryAccessGrant` entries in a task-owned in-process SQLite fixture and must be labelled synthetic. Do not create PostgreSQL roles/passwords, operator grants, credentials, security settings, or containers. Do not inspect protected auth profiles. If the public test flow requires anything beyond these ordinary fixture grants, stop and return the exact missing gate rather than introducing a route.

## RCC invocation and capacity plan

Static code path count for one full compile + execution is **six RCC subprocess invocations**: compiler `build_environment` runs `rcc --version` and `env publish`; compiler `import_action` and `run_tests` each call `_run_exec`; `GeneratedRccExecution` verifies RCC version and invokes its final `rcc run`. This excludes no command and assumes one source compile, one action test phase, one Run attempt, and no replay. Terminal replay is a SQL rejection and must not invoke RCC.

The prepared executor marks each command no-build (`env publish --no-build`, `rcc run --no-build` and `RCC_NO_BUILD=1`). The reviewed execution plan permits **zero new holotree materializations**; if exact reuse cannot be proven, abort before RCC. The supplied a53 receipt’s original home was not validated as the acquired/compatible home for this run; the current manifest SHA mismatch independently blocks use of the unchanged generic fixture. Do not infer reuse from the receipt alone. Root must first validate a prepared home already contains the matching Core8 environment and arrange capacity independently. No RCC invocation count permits a hidden build; do not run while free space is about 10 GiB above the required floor.

## Static checks and remaining action

Static digest comparison confirmed the current fixture manifest mismatch and the retained a53 manifest is the receipt’s exact bytes. The two a59 source revisions, object digests, and the a60 consumer installed wheel identity were read from retained receipts. No behavioral claim was inferred from these checks.

Root review is needed for the proposed fixture delta and the bounded capacity plan before any execution. If accepted, a test delta must retain one Package/capability/RuntimePlan identity across both provider bindings, Deployment, Run/Attempt pins, RCC launch, logical read receipt, output bytes and terminal replay; it must not broaden into PostgreSQL, expiry, or new features.

## Canonical guide proposal (not applied)

Propose this precise addition to `actions/docs/skills/repository-operations.md`, near installed Data qualification:

> A real-RCC Data Package Run must use the same compiler-verified Package manifest and RCC artifact identity from package compilation through execution. Existing synthetic compiler Data-binding tests and generic real-RCC tests are separate evidence until one test composes both through normal Package, binding, Deployment, Run/Attempt and output services. Assert the prepared manifest digest before RCC. Require a receipt-verified compatible existing prepared home for no-build execution; treat any need to materialize an environment as a separate capacity prerequisite. Keep fixture-only SQLite grants distinct from operator DB authority.

**Documentation improvement receipt**

- Canonical file changed or proposed: `actions/docs/skills/repository-operations.md` proposed; unchanged by this isolated task.
- Durable learning captured: exact fixture composition, manifest mismatch (`actions-core=1.0.2` vs required a53 digest), product-supported `actions.data.scan` logical context route, grant types, and fail-closed no-build capacity prerequisite.
- Evidence: static source inspection of the named compiler/worker/test modules; a53 prepared receipt and exact `package.yaml`; a59 installed CSV/Parquet source/service receipts; a60 `consumer-ready.json` and wheel identity.
- Stale or ambiguous guidance removed: proposal clarifies that existing real generic RCC and logical Data tests do not already combine; says no RCC cache reuse unless receipt-verified; preserves the a59 installed CSV/Parquet service component as a bounded pass.
- Remaining uncertainty: compatible acquired Core8 home for this package was not verified; actual a60 composed Package/Run execution is unrun; exact peak disk is unmeasured.

**Upstream disposition: none.** No upstream defect identified; no external issue authority used.
