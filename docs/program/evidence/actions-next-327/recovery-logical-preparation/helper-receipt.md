# Eager logical scan preparation checkpoint

Baseline root6c67055f5165100b422ce2b6038976041fbb1d79. Patch logical-execution.patch SHA256 `430491efd73c5f4f627e7a6b4fbbd0bf7c96802d7e564844151db6db423b4b1e`. Exactly two new modules and one test file; no bootstrap, RCC runner, generic domain, SDK, version, migration, root edit, push or installed proof.

## Interface and lifetime

ConfiguredProviderExecution(db, datadir, blobs) validates saved owner and committed CURRENT catalog/config/source lineage and SQL provider identities. No secret resolution or engine connection at construction. Explicit construction fails closed when catalog absent; ordinary loader/defaultNone wiring remains root-owned. open_provider(actor, exactref) revalidates CURRENT and selected configuration, owns a read-only PrivateProviderStore through engine execution, then checks current SQL/private state again. PostgreSQL resolver is limited to the selected config's exact password/CA refs. No secret bytes in Package/context/receipts. No shared blob provider close; Runtime owns it. Error wrappers sanitize private filesystem construction/check failures.

LogicalExecution(deployments, registry, canonical_outputs, configured).prepare(actor, fence, cancelled=Event, deadline=absolute_monotonic) -> PreparedLogicalReads. This requires exact base RunOutputService (not a domain output wrapper); existing queue/domain fencing remains independently owned by integration. Preparation resolves the retained Deployment/capability and artifact-verified requirement set, then eagerly executes every selected declared parameterless data read `.scan/v1`. Requirement/provider execute and provider.inspect/data.read checks remain explicit.

Context version actions.logical-read-context/v1 contains only version plus logical requirementId/operation/rows lookups. Host-only object retains exact Actor, Run/Attempt fence, ExecutionSnapshot, immutable Deployment/bindings, context digest, source/contract/result/config/catalog digests and SQL provenance pins. Only this component's issued object identity is accepted; a caller-built/replaced DTO cannot authorize recheck. release(prepared) removes in-memory authority and must be called by integration on completion/abort. Context is intentionally ephemeral; restart requires existing Run/launch reconciliation rules, not reconstructing an authority token from serialized context.

Aggregate budget256KiB includes canonical context envelope; maximum32 operations. Declared maximum output bytes plus wrapper overhead must fit before any engine call, otherwise refuse instead of narrowing. Actual canonical result count/byte/identity checks repeat. One cancellation Event view combines caller cancellation and absolute total deadline across all engines; no per-operation reset can extend it. Existing engine connect/filesystem blocking limitations remain; it guarantees no successful late result, not hard interruption of all OS I/O. This component does not renew Work Item leases or run its own worker/scheduler; caller's existing lifecycle must handle renewal, or fence expiration causes refusal.

recheck(actor,fence,prepared) is SQL-only and designed to be called inside the existing output publication transaction. It acquires common Run/Workspace fence, locks relevant PostgreSQL grant rows before reauthorization and exact pinned SQL authority rows FOR SHARE, rechecks immutable Package/Deployment/provider/source/config-publication metadata and provider availability. SQLite already owns the common writer. It does not call deployment.resolve, registry.load/provider._read, filesystem catalog validation, secrets or engines. No separate output stage/publish/audit ownership. PostgreSQL concurrency test demonstrates updates to grant/availability rows wait/fail lock_timeout until the outer transaction releases, then proceed. Existing domain queue/output guards must still execute; this is additive logical authority, not their replacement.

## Private pointer race boundary

Normal CLI start (_cli_impl.py:1079) holds action_server.lock; offline providers-local (_local_provider_setup.py:800) obtains the same lock with timeout0 and refuses a running Runtime. Existing test_local_provider_setup.py::test_runtime_mutex_blocks_operator exercises refusal. This excludes cooperating CLI writers and supports SQL-only publication without filesystem I/O. Direct in-process bootstrap/factory callers are NOT automatically mutex-protected, and arbitrary same-user private file/SQL mutation is not excluded. Root integration must preserve ordinary Runtime mutex lifetime. No claim of race-safe private pointer publication outside that precondition. check_current before/after preparation detects private changes in the bounded tests; publication validates captured SQL provenance only.

## Evidence

- initial.xml:4 fixture setup errors (RunOutputControlPlane was missing capabilities); corrected fixture only.
- base.xml:3passed1failed (tamper fixture tried to write immutable0400CURRENT); corrected owned fixture chmod/restore.
- expanded.xml:10passed2failed (grant fixture used wrong subject column, deadline expired before deliberate slow engine); corrected subject_id and generous entry deadline.
- joined.xml:14passed24.67s.
- locked.xml:14passed25.34s after explicit row locks/concurrency assertions.
- final.xml:16passed28.06s, zero skips. Includes real DuckDB prepared context, actual owned TLS PostgreSQL engine via public local configure/import route, real PostgreSQL control-plane authority clone, authority/source/Package/provenance tamper, forged receipt/fence, cancellation/deadline, declared aggregate/count bounds and result receipt mismatch.
- sanitized.xml:3passed7.34s after private error wrappers.
- receipt-pins.xml:final affected real SQLite/DuckDB, TLS PostgreSQL engine and PostgreSQL-control-plane tests after adding host-only config/catalog digest fields.
- static-final.log:mypy2modules pass; Ruff3files clean. Fixture synthetic compiler uses no RCC. Control-plane PostgreSQL uses copied synthetic canonical records in an owned schema, NOT a claimed public shared-PG provisioning route. Actual TLS fixture stops its captured owned container; no credentials/providers outside task fixtures.

Reproduce using prepared /workspace/actions/action_server/.venv/bin/python with scratch action_server/src,common/src,devutils/src,action_server/tests on PYTHONPATH, pytest test_logical_execution.py; retain junit/stdout/robocorp logs in owned evidence directory. Full root suite/installed qualification remain integration gates.

Documentation improvement:
- Canonical proposed file:docs/skills/repository-operations.md.
- Exact text:canonical-guide-delta.md.
- Durable learning:eager component context/lifetime, SQL-only publication row locks, real mutex precondition, no ordinary wiring claim.
- Evidence:above tests plus inspected CLI/operator lock code.
- Stale/ambiguous guidance removed:after integration distinguish absent ordinary worker join from now-tested preparation/factory component; retain absent installed SDK/context/runner wiring and full Data/Knowledge gates.
- Remaining uncertainty:SDK/runtime/journal integration, atomic integration into domain publication, installed unchanged-Package two-provider acceptance, shared-PG operator coordination, broader read/write/Knowledge and hostile native isolation.

Upstream disposition:none. Repository-owned join only, no upstream defect or external mutation.
