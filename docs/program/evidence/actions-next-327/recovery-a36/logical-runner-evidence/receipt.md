# Bounded logical runner source checkpoint

Patch: `logical-runner.patch`, SHA256 `6491a09be86b56db57cdcf89969d25337040885200d14d5c1d0b7b9602ad3b1c`.
Base: `c7d94ca647395856e662de335353974ca01f89ff`.
Dependency: frozen logical-domain.patch SHA256 `818a3b312b8eb314b886cb152445dad8624c801a9df8e9b7eec1ee83c22fa49b`. Exact copied dependency modules/test hashes are recorded in source-identity.json and excluded from this patch. Root `git apply --check` passed. Nine owned files; no bootstrap/version/source-root edits, commits, pushes or external mutations.

## Implemented public host seams

- GeneratedRccExecution optional keyword `logical_execution`; absent preserves legacy behavior/constructor calls and exact old helper bytes. Data requirements require configured shared DB/registry port and supported domain wrappers; reviewed invoice and unsupported non-data requirements remain refused.
- PinnedGenericRccRunner, DetachedActionWorker, DetachedTaskHost carry the optional host port. Zero-port constructor calls omit the new keyword, preserving existing fixed-signature test/adapter contracts.
- LogicalExecution.begin_preparation(actor,fence,cancelled=Event,deadline=absolute) returns a reachable owned preparation; release_preparation(owner,prepared) is exact transfer release. close(timeout_seconds) stops/settles supervisor and returns false while any issued object remains. Closing is permanent; no new preparation afterward.
- Supervisor maximum four outstanding owners; non-daemon preparation threads; result/exception handoff only after thread exit; late unclaimed release exactly once. Transferred preparation cannot be stolen by supervisor close. Preparation thread uses LogicalExecution.prepare's own Database.connect scope; main runner retains SQL cancellation/dual-fence heartbeat duties.
- LogicalPreparationCleanupIncomplete subclasses RccCleanupIncomplete and retains the exact owner. TaskHost can retry settling that specific unclaimed preparation on close, stays failed, and never admits/retries work. Existing RCC uncertainty stays latched; transferred preparation remains reachable and issued on such uncertainty.
- Bound runner shares one deadline from execute entry through preparation/capture/stage/publication, writes private context, uses separate private Core SDK helper, keeps issued domain publication binding through staging/publication, and releases only after cleanup. Safe logicalReads summary is in v2 launch/terminal; context is not an artifact. Outer common output envelope remains version1.
- Bound journal readers use the dependency's strict codec and cached projection during active publication binding. Detached seed version derives from exact immutable requirements. Model handle projection validates generated versions/bound terminal receipt before resolving handles.

## Verified evidence

- `final.xml` / `final.log`: **185 passed, 2 actual opt-in cases deselected, zero skips**,113.54s. Includes initial26 new cases plus complete affected Generic model/Detached authority/Task host boundary suites on SQLite/PostgreSQL and existing provider fixture variants.
- `focused-freeze.xml` / `focused-freeze.log`: final complete **27 new cases passed, zero skips**,16.92s after adding reachable cleanup exception, no-reprepare launch replay, and exact exception-type assertions. Source implementation unchanged since the185-case pass; test additions/tightening separately requalified as a complete focused set.
-6 of the27 cases join real eager reads and both SQL backends to **synthetic RCC output**, proving strict v2 publication, four outputs, total-deadline reuse and issued release on success/pre-spawn/stage failure. They explicitly do not claim native RCC execution.
-8 of the27 cases use real generic consumer SQL: main-thread heartbeat renews independent Work Item claim and Attempt; preparation uses a different thread/connection; deadline/callback revocation/claim-loss settle without launch.
- Remaining13 cover supervisor capacity/ownership/late cleanup, archived v1 helper hash, actual installed private SDK context helper in-process (success/digest/symlink/size/action/import failure/reset), and TaskHost cleanup retention. In-process Python helper is not RCC/installed Runtime qualification.
- `types-final.log`: mypy six changed source modules clean. `lint-freeze.log`: Ruff clean; `isort-final.log`: configured import check clean. Formatting used configured Ruff/isort, no installs.
- `source-identity.json`: all owned and copied module hashes, dependency/base identity, and qualification-only conftest overlay hash. `freeze.py` reproduces diff generation from exact archived base. No ignored/private OAuth config was read or copied.

Commands use existing prepared `/workspace/actions/action_server/.venv/bin/python`, scratch `action_server/src:action_server/tests` plus existing common/devutils on PYTHONPATH, `ACTIONS_REQUIRE_INVOICE_PROVIDERS=1`, owned loopback PostgreSQL, `-p no:robocorp_log_pytest`, and retained XML/stdout. Later tests disable instrumentation at root request after storage pressure. Earlier readable HTML/raw traces remain retained in owned evidence.

Qualification-only scratch `action_server/tests/action_server_tests/conftest.py` disables telemetry-feedback RCC startup and substitutes `/usr/bin/true` only for constructor path checks in existing synthetic Task host tests. It is excluded from patch. Those tests already stub RCC version/execution boundaries. No native RCC command or cache access was performed.

## Preserved failures and corrections

- red.log: expected missing new lifecycle module.
- first.log: existing autouse feedback fixture required absent scratch RCC; corrected test-only fixture without running RCC.
- postgres-initial-failure.log: owned disk-backed PostgreSQL failed initdb with ENOSPC; exited1. Replaced with separate bounded256MiB tmpfs fixture; no shared cleanup.
- sql-first.log: ENOSPC before pytest collection/log initialization, not a test failure/pass.
- sql-second.log:9PASS/2FAIL; deliberately shortened1-second lease expired under instrumentation before heartbeat. Corrected fixture15-second initial leases; actual guard correctly rejected expired authority.
- sql-third.log:14PASS/6FAIL; reset assertion expected RuntimeError but public scan correctly raises ValueError. Corrected assertion, not SDK behavior.
- compat-first.log:155PASS/4FAIL; new optional None keyword broke a legacy fixed-signature synthetic executor. Product caller now omits optional kw when absent; complete185-case rerun passed.
- types-first.log: seven narrow optional/type annotations corrected; final six-module mypy clean.

## Resource release and limits

Own disk PostgreSQL container `actions-logical-runner-pg` exited1 before tests. Own tmpfs PostgreSQL `actions-logical-runner-pg-memory`,ID4815f7af54117e4d7bc21032973f7795103511d1c0d1f18a66950f4f166e2d76,port32840,was stopped after final tests. Per-test TLS PostgreSQL fixtures stopped their own containers. No RCC cache was claimed; Runtime venv was used read-only and is no longer in use by this lane.

Remaining root gates: review/integration; ordinary bootstrap/lifetime injection; strict v2 Task/managed/read projections where still v1-only; genuine installed Core a3 RCC consumer/standalone data execution on DuckDB/owned TLS PostgreSQL, restart and artifact evidence; full package/source/consumer gates. This patch does not claim Knowledge requirements, Robot, interactions, effect recovery, or READY FOR DAKOTA. SQL/native connect or filesystem calls that do not cooperate with cancellation can overrun the deadline until returning; the supervisor preserves ownership rather than claiming hard thread preemption.

Documentation improvement: exact durable insertion and evidence in guide-delta.md for docs/skills/repository-operations.md, covering one deadline, dual fences, reachable cleanup, transferred ownership and qualification boundaries.

Upstream disposition: none. Actions-owned integration; no confirmed upstream defect and no external mutation.
