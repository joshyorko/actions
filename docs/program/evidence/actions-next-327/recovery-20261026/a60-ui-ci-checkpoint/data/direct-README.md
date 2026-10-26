# a59 installed CSV/Parquet component receipt

Status: **PASS_COMPONENT**, not #327 row 11/full acceptance. The installed product source is `123e772ee36c44cfd96ea62a6c599bb4f55c8f1b`, tree `7d6658bc3f2d536519c8698503f8b379c7b3ed56`. The frozen `actions-runtime-1.1.0a59` wheel SHA-256 is `cca5383bd331bfc68227bf5c2749f867cc3d9e7cc7daaeb3f13fbe9125d5960a`. The consumer interpreter reports Runtime `1.1.0a59` and DuckDB `1.4.1`; imported Runtime modules resolve only from `/workspace/327-probes/a59-data-consumer/consumer/lib/python3.12/site-packages` (per-module paths are retained in `result.json`). Installed implementation examined: `data_queries/sealed_sources.py::{decode_csv,ReadBudget}` and `data_queries/sealed_duckdb.py::{decode_parquet,scan_contract,_payload}`. Source tests reviewed: `action_server/tests/action_server_tests/test_sealed_scan.py` and `test_sealed_postgres.py`; no source tests or product modules were imported for execution.

The direct installed component probe staged two tiny synthetic sources through the installed `FilesystemOutputProvider`, constructed v2 `SourceManifest` and named read-operation metadata, and exercised the installed CSV/Parquet decoders. Both produced identical ordered, typed two-row results (147 decoded bytes). The receipt retains manifests, operation descriptors, seals, revisions, object hashes, and check outcomes. It also retains fail-closed negatives for source-revision substitution, unknown operation, parameterized exact scan, seal/object digest mismatch, already-cancelled read, and operation row/byte limits. `fixture.parquet` is generated with the installed DuckDB 1.4.1.

Exact command (the supervisor supplied pidfd ownership and subreaper cleanup):

```text
/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3 /workspace/327-probes/supervise_command.py --receipt /workspace/327-probes/a59-installed-data/supervisor.json --log /workspace/327-probes/a59-installed-data/supervisor.log --seconds 180 /workspace/327-probes/a59-data-consumer/consumer/bin/python /workspace/327-probes/a59-installed-data/run_installed_data_component.py
```

Supervisor exit 0; no remaining owned processes. The complete output directory measured 27,878 bytes after receipt completion, below the 50 MiB cap. Free space measured 11,162,214,400 bytes before and 11,162,198,016 bytes after final receipt write, and stayed above the 10 GiB floor at every script checkpoint. No PostgreSQL container, package install, rebuild, network access, source overlay, or external credential was used.

This composes synthetic metadata and local sealed-output authority around installed component APIs. It does not exercise `SqlProviderRegistry`, persisted principal grants/revocation/expiry, Package/Run admission, ordinary CLI or generated worker execution, PostgreSQL, paging/export/cost, or a restart readback. Therefore it establishes an installed CSV/Parquet/source-identity/bounded-operation component slice; it does not close the named open data/result-plane row or establish ordinary product authorization.

## Canonical documentation proposal (not applied)

In `actions/docs/program/actions-next-release-327.md`, row 739, append the following evidence to the current implementation/evidence cell:

> The frozen a59 installed wheel (SHA-256 `cca5383bd331bfc68227bf5c2749f867cc3d9e7cc7daaeb3f13fbe9125d5960a`) now passes a direct installed component gate: DuckDB 1.4.1 decodes manifest-backed sealed CSV and Parquet to identical typed rows; source revision, object digest, named-operation/parameter, row/byte-limit and pre-cancel negatives reject. This is synthetic component authority and does not qualify persisted user grants, Package/Run admission, ordinary worker execution, PostgreSQL, paging/export or source expiry.

Keep the acceptance state open and amend the remaining-gaps cell to say:

> Still required: unchanged immutable Package admission and execution over owned DuckDB CSV and Parquet plus real PostgreSQL; persisted scoped grant/revocation/expiry negatives; retained source/snapshot lineage across restart; paging/export/cost/cancel through the supported operation path. The direct a59 component receipt does not close these service-level gates.

Evidence: `result.json`, `supervisor.json`, `supervisor.log`, `run_installed_data_component.py`, and the sealed source objects in this directory. The existing row remains **open**. Upstream disposition: none.
