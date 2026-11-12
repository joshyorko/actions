# Robot source admission and prebound selection

Patch: `robot-admission.patch`, SHA256 `9d6b12e3cd63a5f68fb857227b74b2c83e9bfe25b13aa6c27a5a10151cc8b3d1`.
Base: `20639810107cbe4b28e7f1acc5e2ac68bdde06b6`. Tests ran against this base plus the five dirty isolated files hashed in `source-manifest.json`; the base commit alone is not the tested tree. No root edits, commit, push, schema migration or environment installation was performed.

## Host ports

- `FoundryPackageRegistry.prepare_trusted_robot(request, *, logical_package_key, trusted_actor, workspace_id, application_id, preparation) -> RobotAdmissionEvidence`. Host preparation is existing `DirectRobotPreparation | RccRobotPreparation`. Host admission enum and live generation/deploy grants are required.
- `admit_robot(actor, workspace_id, evidence) -> PackageRevisionRef`: exact in-process issued evidence only, scoped to original actor/workspace; existing SQL source rows/seals/request/audit/grants. Ref derives actual canonical source/plan/revision bytes. Independent transaction required; replay cannot regrant revoked authority.
- `robot_admission_evidence(ref) -> RobotAdmissionEvidence` reloads a measured record, not a fresh in-process admission ticket. Fields: `package: AdmittedRobotPackage`, `verification='source-and-plan-verified'`, `execution='not-qualified'`. There is no `.ready`, fabricated build/import/test receipt, or `CompilationOutcome` conversion.
- `selection_for(capability, runtime_plan)` explicitly returns `RegistryRobotSelection` for Robot (`package_revision`, `capability`, `runtime_plan`, `.robot: AdmittedRobotPackage`); Python/bundle selection remains `RegistryCapabilitySelection` with `.compiled`. Old Python-only `load()`/`evidence()` refuse Robot.
- `prepare_robot_selection(outputs, registry, actor, fence, *, require_current) -> PreparedRobotSelection`: requires the exact registry and database installed in RunOutputService; prepare before any caller transaction. It validates the retained artifact outside SQL and pins the Package row. Returned object is callable with `(actor,fence,snapshot,inputs)` and supplies `.source_archive` plus `.selection`. Only issued callbacks work.
- The callable uses SQL-only checks and can run inside journal/publication transactions. **The required trusted `require_current(actor,fence,snapshot)` callback must enforce current Deployment revision and any independent Work Item claim using SQL.** A test no-op is not production authority. Do not call provider/load/schema IO from that callback. This slice does not wire that authority, Task protocol, lifecycle, current-head logic or terminal publication.
- Robot builder currently imports execution -> RCC -> registry, so registry imports Robot values lazily at runtime (type-only annotations remain explicit). Do not replace these with eager imports without breaking that dependency cycle deliberately.

## Validation

Prepared RCC package-command gateway, isolated Runtime+Core imports asserted. Final exact command is in `joined-final-receipt.json.b64`. Existing pinned tools and an owned ephemeral PostgreSQL container were used, without transferring its secret into evidence.

- First run: import cycle failed before collection; `first.log` retained, no XML generated.
- Second run: 15 passed, 16 PostgreSQL skips, 1 failed (cancellation fixture lacked the separate authoring cancel grant). Fixture now explicitly grants `cancel_execution`; authorization was not weakened.
- Owned first: 32 passed, 0 skipped, SQLite + PostgreSQL.
- Owned expanded: 44 passed, 0 skipped, including independent-connection races and SQL rollback/replay.
- Final joined: 96 passed, 0 skipped, 0 failures: 44 new admission/selection cases plus 52 unchanged Python/bundle registry regressions. Exact executed inventory: `selected.json`. Counts overlap earlier runs and must not be added into a campaign total.
- Scoped isort/ruff format/ruff lint and mypy: final pass, 3 production files typed. Initial lint failures and initial namespace/type-check failures are retained. The existing pytest anyio assertion-rewrite warning remains, not a failed test.

XML/log/receipt files are base64 transport, not redaction. `evidence-filemap.json` gives decoded length/hash and original location. Logs were checked for PostgreSQL credential-bearing DSNs. No fixtures, DBs, caches, artifacts or secrets are in the delivery. Root must run its publishing guard before committing evidence.

## Remaining gates

These are source/component tests with synthetic host preparation, including synthetic typed RCC identities; no real Robot subprocess, actual RCC job, installed consumer or recovery qualification is claimed. Root must wire authoring/bootstrap, true current Deployment/independent claim callbacks, lifecycle/journal and atomic fresh-authority terminal publication, then qualify installed execution/recovery. Existing Python/bundle formats and regression tests remain unchanged. Failed staged SQL admission can leave an unreferenced object intentionally; it is not an admitted source or permission to relaunch.

Exact canonical guide proposal: `guide-delta.md`. Upstream disposition: none (no external defect report or mutation).

## Integrator rerun

At base f905c388 plus this exact patch, all 96 joined admission/selection/Python/bundle registry cases passed on SQLite and owned PostgreSQL, zero skips. `integrated-source.json` identifies the dirty tested production bytes. `joined/` retains exact commands, selected inventories, XML, logs and cleanup receipt. The source/component limits above still apply. The patch is retained as base64 to preserve its exact whitespace.
