# Explicit local provider operator and ordinary injection checkpoint

Frozen patch operator-bootstrap.patch SHA256 a277edccadf2305fba391cb149d4c014fc14c5cacf0cc1e5b858c91266fafdb6. Five files: _local_provider_setup.py, foundry/provider_bootstrap.py, _cli_impl.py, foundry/bootstrap.py, test_local_provider_setup.py. Apply after registry19 b39355..., codec/catalog/config6009eb..., atomic staging/CA c8c8a9.... Root apply --check passed; root source remains untouched by this lane. No migration20/21 changes, engine/network/RCC operation, upstream mutation or credential inspection.

## Public local flow and scope

`python -m actions.server providers-local --schema`
`python -m actions.server providers-local --datadir ABS --request ABS [--dry-run]`

Strict actions.local-provider-setup/v1 request uses saved owner workspace and explicit request_id. Operations are inspect, grant-owner, revoke-owner, import-source, register-revision, configure-host, recover-intent, set-enabled. The schema gives exact typed fields; fields carrying values outside the selected operation are rejected. No arbitrary recipient, SQL, locator/URL in Package/model, executable plugin or provider probe.

Sequence: explicitly grant workspace provider.register after dry-run CAS; import bounded private files matching an exact source/v2 manifest; register exact immutable metadata; separately grant exact-ref provider.manage/provider.inspect and any desired deploy/execute/data.read/data.manage; configure an allowlisted private host with expected catalog CAS. There is no implicit grant between these operations. Inspect exposes metadata/availability and the owner's CAS digest, not host configuration or secrets. Named data permissions are persisted explicitly but actual worker enforcement remains a future operation-port gate.

The command requires existing owned private POSIX datadir/server.db/request, saved bootstrap receipt/audit, canonical Runtime mutex, clean SQLite shutdown and no external database URL. Existing lock must be owned regular nonhardlinked state. It neither creates/migrates a DB nor kills Runtime. Same-user concurrent filesystem mutation remains excluded. Shared PostgreSQL administrative coordination is explicitly unsupported; common SQL registry and provider-engine PostgreSQL are distinct scopes.

Source import seals bounded bytes through the existing FilesystemOutputProvider and stores an immutable SourceSealRecord before SQL registration. Repeated source identity reuses and verifies the retained record. Missing/tampered seals fail closed; replacing lost seals with different private locators is not an automatic repair operation. Coordinated backup/restore of original pins or a separately designed explicit repair path remains required.

Private configuration supports the fixed DuckDB declaration or typed PostgreSQL connection fields with pinned password and optional CA versions. Secret imports are explicit owned files, bounded64KiB, stored as immutable private versions. No secrets are read on startup/config reconstruction; no connection/probe/query occurs. Absent secret versions may therefore remain configured-not-probed; this is not engine readiness. Rotation is an explicit new catalog operation and never changes source/codec identity implicitly.

## Publication authority and recovery

Private configuration/source references are retained in canonical private request files beside immutable intents. The SQL Request fingerprint binds this private request without persisting its values or private paths in SQL/public audit. Deterministic operation UUID is also catalog generation, so startup can locate and verify its exact committed request/audit.

Configure stages complete immutable files and intent, then commits a Request/Audit receipt whose status is publication-authorized, then rechecks live manage authority and publishes CURRENT under CAS. Only the post-publication CLI reply says configured-not-probed. Source/registry operations preserve their existing single request owner. Recovery is a distinct audited operator action and cannot substitute a private intent for a missing committed configuration receipt.

Both recovery and ordinary loading validate SQL owner/request/audit lineage, private request fingerprint, exact catalog target, old entries preserved and only the requested provider replaced with the exact config/source. A rehashed replacement catalog cannot redirect a valid receipt. Current manage permission is rechecked for explicit recovery/publication, but not needed merely to reopen an already authorized catalog; actual selection still checks live provider.inspect/deploy and availability. Revocation does not cause startup to mint replacement grants.

Absent provider-state means provider_compatibility=None and no directory or permission creation. Staged state without CURRENT is unavailable; startup never finishes intents. Configured state reconstructs trusted evidence, validates every SQL descriptor/source and injects SqlProviderRegistry into existing RuntimeDeploymentSelection. Corruption or missing publication proof yields a sanitized refusal. It never resolves password/CA files, probes an engine, executes an operation, grants permission or imports source bytes.

## Evidence

Prepared Runtime interpreter with explicit scratch source/test PYTHONPATH. Full CLI subprocess tests use the real `python -m actions.server providers-local` entrypoint. Initial realm/owned SQLite are synthetic fixture setup using existing bootstrap; provider grants/import/register/configure use the new public local route, not private grant calls. This is source-level route qualification, not an installed wheel claim.

- operator-red.log: prior checkpoint lacks the new operator module (feature absence).
- operator-first.xml8pass and operator-expanded.xml13pass during bounded construction.
- operator-binding.xml15pass before final startup-provenance join.
- operator-catalog-final.xml retained2failed/31passed: final receipt validation exposed that the SQL writer still stored configured-not-probed rather than publication-authorized. Writer corrected; receipt distinction now tested by actual successful recovery. This failed receipt is not discarded.
- operator-provenance.xml17pass: final source including full public CLI subprocess flow, fresh process reload, pre/post-SQL crashes, exact recovery target binding, missing audit rejection, no manage grant required for read-only startup, grant CAS/provenance/unrelated grants, source mutation, mutex/shared-PG refusal, disabled/missing blobs, private secret/CA boundaries and broken logging.
- operator-last-negatives.xml2pass/1test-instrumentation-failure; new tests cover revoked manage recovery and replaced staging inode cleanup. The rollback itself occurred; its inline comprehension assertion hit NameError under logging instrumentation. Corrected assertion uses explicit SQL selection; operator-audit-corrected.xml1pass. Thus all20 distinct operator cases have passing evidence, with the final three retained separately rather than claiming one20-case run.
- operator-static-all.log: mypy4source files PASS. Scoped Ruff PASS. No broad package or installed qualification claimed; parent integrator owns those gates.

Atomic follow-up catalog-atomic-ca.patch SHA c8c8a9cada082c18ff87b68a0e3e85fe9fb17f4b6675d0fa79ae193ba2a5da8c separately preserves the original6009 checkpoint. catalog-atomic.xml18pass, including interrupted write/fsync retry with prior CURRENT intact. Writes publish complete fsynced staging only after checking immutable target absence under the explicit exclusive-writer precondition; cleanup removes only the captured staging inode. Replaced-inode negative also passed in the operator final negatives. Optional pinned CA refs load without secret reads.

## Exact canonical documentation delta

Propose append to docs/skills/repository-operations.md, Public Data and Knowledge integration boundary:

“Explicit `providers-local` setup now provides a saved-owner, stopped-local-SQLite path for named provider grants, pinned source imports, immutable metadata registration and private host configuration. Grants remain separate: workspace provider.register; exact-reference provider.inspect/provider.manage/deploy/execute/data.read/data.manage. The existing bootstrap permission set/fingerprint is unchanged. Private immutable source/config/catalog files reconstruct retained evidence on restart; ordinary injection occurs only when CURRENT has matching committed operator Request/Audit provenance and an exact private request/catalog binding. Absent configuration remains None. Startup never imports, resolves secret/CA values, grants, probes or recovers intents.

“Configuration commits metadata authorization before CAS pointer publication. The SQL receipt means publication-authorized; only successful pointer publication returns configured-not-probed. Explicit recovery requires current manage permission and rejects absent SQL provenance, changed targets or stale generations. Immutable file writes stage and fsync complete bytes before publication, preserving existing targets; interrupted staging can retry, and cleanup checks its owned inode. These guarantees require the canonical local mutex and exclusion of concurrent same-user filesystem mutation; they are not an adversarial-filesystem claim.

“Source/v2 binds bounded CSV UTF-8/flat uncompressed Parquet codec declarations, preserving exact v1 metadata identity and refusing v1 at the executable-source declaration gate. No parser, data engine query or worker transport is implemented by this setup checkpoint. Private PostgreSQL configuration and pinned CA/password versions do not prove connectivity; actual engine execution, installed setup/upgrade/restore, immutable Knowledge ingestion/Tasks, shared PostgreSQL administrative coordination and split-provider qualification remain open.”

Documentation improvement: exact canonical addition above plus codec-catalog-config.md. Removes Mapping-only/restart ambiguity and premature readiness claims, records tested authority/crash/private boundary. Evidence receipts above. Remaining uncertainty: full package/integration compatibility and all actual engine/worker/coordinated product gates. No new Task, scheduler, database or provider default.

## Upstream disposition

No confirmed upstream defect or external mutation. An internal, unconfirmed logging-instrumentation candidate is retained in instrumentation-observation.md with minimal source/logs: installed robocorp-log3.1.2, valid empty-comprehension assertion passes plain Python but raises NameError under repository instrumentation, including --assert=plain. Current upstream ownership/source and deduplication were not verified; no public report is authorized. The product test uses a direct SQL result assertion; no dependency code was changed. See internal draft for follow-up limits. This does not block the provider implementation checkpoint.
