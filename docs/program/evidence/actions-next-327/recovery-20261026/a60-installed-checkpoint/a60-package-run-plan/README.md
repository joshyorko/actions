# a60 Data Package → Run execution readiness

**Disposition: not ready to execute this acceptance run from an existing supported fixture without changing its scope or preparing a new fixture.** This is a read-only readiness review. No test, CI query, build, compiler execution, database mutation, grant creation, credential access, network/container operation, or additional materialization was performed.

## Exact fixture finding

There is no single existing test fixture that proves the requested installed immutable Data Package → capability → Run/Attempt path using the real prepared Core 8/RCC 18.19.3 receipt at `327-probes/a53-claimed/compiler/prepared.json` without new fixture preparation:

- `actions/action_server/tests/action_server_tests/test_generic_work_item_execution.py` has an opt-in `real=True` branch which loads `ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT`, uses `PinnedRccPackageBuildExecutor`, compiles a generated generic Work Item package, admits its capability, creates a Deployment and Run/Attempt, and executes it. It does not provide a logical Data binding. Its path compiles/builds during the test and may allocate an RCC holotree view; the existing prepared environment is not proof that this test would avoid a new materialization.
- `actions/action_server/tests/action_server_tests/test_logical_execution.py` supplies `records.scan/v1`, compiles with `logical_requirements`, selects provider bindings, admits a Run, and prepares/rechecks logical read context. Its module docstring explicitly identifies a **synthetic compiler** and says it makes no RCC claim. It does not bridge that data-bound package into the real-RCC generic execution path.
- `actions/action_server/tests/action_server_tests/test_generated_knowledge.py` similarly binds logical requirements and constructs deployment/run state, but uses the test registry/compiler path; it is not an existing real-RCC Data Package execution fixture.
- The installed a59 Data SQLite fixture recorded at `327-probes/a59-installed-data/service-path/package-run/README.md` has provider/source state only. It has no Package, Deployment, Run/Attempt, pins, or output state; grants are limited to provider operations. The README already specifies that the immutable compiler-verified Data Package and authorized Run fixture are absent.

The narrowly appropriate engineering preparation would be to make one existing fixture compose the already supported real-RCC generated execution path with the existing logical binding and sealed provider execution path, while retaining the exact compiler-verified Package/capability identity through Deployment and Run/Attempt. This is a fixture/integration gap, not evidence that the product feature is absent and not an automatic owner decision. Do not hand-build a compiled object or treat synthetic compiler evidence as RCC evidence.

## Authority and execution boundary

The test helper `grant(...)` in `test_generic_work_item_execution.py` inserts synthetic `FoundryAccessGrant` rows into its test database. The real branch uses the same helper for the workspace execution permissions, worker/policy/output-provider reference permissions, deployment queue permissions, and Run output control-plane grant. The logical test additionally constructs test provider/source authorization for `provider.inspect`/`data.read` and deployment selection. These are local synthetic fixture rows, not operator PostgreSQL roles, passwords, live grants, or protected profiles.

The fixture data needed for a composed run would therefore include those synthetic test-only Package/deployment/provider/queue/output grants in an ephemeral SQLite test DB. This review did not create them. The PostgreSQL setup proposal remains denied before execution; do not substitute a new role, credential, DB grant, security setting, container, or alternate PostgreSQL route. Do not read protected authorization profiles.

## Dependency order and disk constraint

1. Establish an existing compiler-verified immutable Package manifest with the required logical Data operation and identity. None is present in the retained installed SQLite fixture.
2. Compose it with the supported sealed provider fixture and persisted Package admission, binding selection, Deployment, Run/Attempt, exact revision/plan pins, output publication/readback and restart semantics.
3. Execute that exact pinned Package via the existing real-RCC path using the supplied prepared receipt, then verify the same package/capability/deployment/run identities and result bytes.

The first two pieces currently exist only in different tests with different compiler scopes. Since the real-RCC test compiles during the test, it may create another RCC view/materialization. Current free space is 10,875,568,128 bytes; a 10 GiB floor is 10,737,418,240 bytes, leaving **138,149,888 bytes**. The exact incremental peak for the composed RCC test has not been measured, so it cannot be shown to fit this headroom. Do not run it until an already-materialized, identity-matched fixture or a separately approved capacity plan proves the peak without crossing the floor.

## Original mandatory rows in scope

- **Row 7 — generated Python / immutable Package and RuntimePlan:** retain historical compiler and common admission component receipts at their exact sources. The a60 real-RCC generic fixture still lacks a logical Data binding; logical Data tests use a synthetic compiler. Minimal next proof is one same-identity compiler-verified Data Package → capability/RuntimePlan → admitted Run/Attempt → real RCC execution/result readback path.
- **Row 11 — named open Data/result plane:** retain the a59 installed CSV/Parquet + SQLite authority service component proof; the relevant Data modules are byte-identical in the a60 wheel. Do not revive stale blanket “Parquet missing” wording. That bounded component does not close immutable Data Package/Run execution, PostgreSQL, retained source lineage, paging/export/cost/cancel or scoped negatives. Minimal next proof for this review is the same Data-bound Package/Run integration above; remaining independent row-11 requirements stay open.
- **Row 15 — pinned Run/Attempt and real RCC worker:** retain historical exact-source execution/restart component receipts. a39’s clean E2E proof of two apps, RCC and restart remains valid for its exact source, not current a60 acceptance. a59’s installed PostgreSQL/object Run/readback remains a bounded component, not a Data Package Run or full Runtime acceptance. Minimal next proof here is the same exact-wheel pinned Package→Run/Attempt→RCC execution with revision pins and result/restart readback; the full matrix’s supported-host/client and recovery/retention criteria remain separately open.

All earlier evidence remains source/artifact/profile scoped; older matrix scope claims are historical, not current a90/a60 acceptance. The immutable a57 owner lane is untouched.

## Canonical documentation proposal (not applied)

Propose an addition to `actions/docs/skills/repository-operations.md` in the installed sealed-Data qualification section:

> Keep Data qualification evidence layered. A sealed provider/SQLite service PASS does not prove immutable Package admission or Run execution. A Package-to-Run claim requires one compiler-verified immutable Package manifest with the logical Data binding, the same Package/capability/plan identity through persisted Deployment and Run/Attempt, and result readback bound to that Run. Existing synthetic compiler tests and test-only SQLite `FoundryAccessGrant` rows are contract-fixture evidence; they do not prove RCC execution or establish operator PostgreSQL authority. Reuse a prepared RCC environment only when its receipt and compiled Package identity match the run; otherwise account for new materialization and verify disk headroom before execution.

**Documentation improvement receipt**

- Canonical file changed or proposed: propose `actions/docs/skills/repository-operations.md`; no file changed in this read-only lane.
- Durable learning captured: exact division between real-RCC generic execution, synthetic-compiler Data binding tests, and installed provider-only service evidence; how to compose a truthful Package→Run claim and distinguish test fixture grants from operator authority.
- Evidence: the three test modules above; `327-probes/a59-installed-data/service-path/package-run/README.md`; prepared RCC receipt `327-probes/a53-claimed/compiler/prepared.json`; measured free-space output.
- Stale or ambiguous guidance removed: propose replacing any claim that existing tests already combine Data binding and real-RCC Run, and retain the a59 Parquet component pass rather than a blanket missing-Parquet claim.
- Remaining uncertainty: exact incremental RCC materialization/peak disk for the required composed fixture; no current installed Data Package/Run fixture exists to reuse.

**Upstream disposition: none.** No upstream defect was identified; no external authority or issue action was used.
