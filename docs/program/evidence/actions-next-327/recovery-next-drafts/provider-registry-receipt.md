# Provider metadata registry prerequisite

Patch: provider-registry.patch SHA256 b39355beaf9e27c31d6584dfe3216ed13183a5dabebf07d16ad4a5ce40fa7cc5.
Base: frozen logical checkpoint f56f927ecc2aeac9729a86d8ceefcfae66f7b87c6289e0e983c8dc288fd2da48 plus logical preview da3863ca6749687b5a4f08f2a1c5b0fa795d13ebd6180f6a082732c9ea20608f. Delta is seven files only; root git apply --check passed. No root edits, commit, push, RCC, CLI/private operator implementation or credentials inspection. Bootstrap source remains byte-identical to baseline.

## Delivered interface

- deployments/provider_registry.py: strict SourceObject, SourceManifest and ProviderDescriptor; versioned domain-separated canonical digests, bounded ordered unique declarations. Source eligibility is sealed-files only (<=16objects, <=64MiB aggregate). Provider identity includes exact workspace/profile/source/typed operation contracts, but no provider engine, endpoint, DSN, path, secret or locator. This lets unchanged Package requirements bind explicit A/B profiles without becoming engine-specific.
- foundry/provider_models.py + common _models registration + migration19: immutable source/provider rows and independent availability generation. Canonical deterministic row IDs enforce the service's scoped identity; migration17's historical model list is unchanged. Adds no grants or second database.
- foundry/provider_registry.py: SqlProviderRegistry(db, SqlFoundryAuthorization, RetainedSourceEvidence|None), register(actor, descriptor, source, *, idempotency_key), describe(actor, ref), operations(actor, ref, kind) implementing existing compatibility port, set_enabled(actor, ref, *, expected_generation, enabled, idempotency_key). No broad discovery transport or mutable default/head.
- RetainedSourceEvidence(blobs: FilesystemOutputProvider, seals: Mapping[(workspace,digest),SealReceipt]) is a trusted host-only catalog, copied on construction. Public requests cannot supply a locator. The configured blob authority verifies sealed identity/digest/size on registration and reads. Missing catalog/evidence fails closed, including compatibility after restart. Blob errors expose no private object reference. Durable reconstruction/provisioning of this catalog is not implemented.
- Explicit workspace provider.register and exact-ref provider.inspect/provider.manage are independent permissions. Existing selector still requires deploy authority and exact typed compatibility; registry does not confer data.read/manage or execute. No startup/activation/replay permission minting; no _OWNER_OPERATIONS or owner fingerprint changes.
- Registration and availability changes own one existing FoundryRequest/Audit transaction. CAS rejects stale generations, audit failure rolls back, replay reauthorizes and returns historical receipt without changing state. Disabling does not need readable blobs; enabling does. Audit leaves Deployment ID empty because a provider is not a Deployment, and request receipt retains exact provider identity. No promise of successful concurrent duplicate registration: uniqueness conflicts fail closed and caller can retry the same key.

## Evidence and exact limitations

Prepared Runtime interpreter /workspace/actions/action_server/.venv/bin/python, with PYTHONPATH set to provider-registry-draft/action_server/src and its tests; pytest test_provider_registry.py -q. No installation or RCC commands. Tests use synthetic sealed fixture bytes and the existing synthetic compiler executor, never a real data engine operation.

- red.log: old logical baseline fails collection because registry module is absent (feature absence evidence, not a claimed behavioral regression).
- first.xml: initial SQLite17pass/17deselected.
- dual.xml: expanded SQLite/PostgreSQL52pass, zero skips.
- joined.xml: registry plus test_logical_binding_checkpoint.py97pass, zero skips. This includes actual schema16->17->18->19 common migration fixtures and real native Package/selection join on both SQL backends.
- final.xml: registry expanded to56pass, zero skips, including canonical source ordering/workspace catalog isolation/noncanonical retained descriptors.
- audit-final.xml: final audit receipt refinement12pass/44deselected across both backends. Tests assert exact provider receipt and empty Deployment audit field; replay/CAS, unavailable evidence and audit rollback covered.
- private-error-final.xml: final sanitized blob-error refinement8pass/48deselected across both backends. Tests assert private object reference absent.
- Ruff scoped source/test check PASS. static-final.log mypy4source files PASS with explicit package bases and MYPYPATH. Earlier mypy command lacked namespace package settings, then identified a string-vs-typed revision constructor; both corrected. Black is absent from this prepared Runtime interpreter; Ruff formatter was used, not host installation.

Owned pinned PostgreSQL container251a09b0829e053bc888178a2d280957534978131a4ca7a0497089fe22e979e2 used image postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81, loopback32796, synthetic credentials, memory768MiB/tmpfs512MiB. Exact owned container stopped/auto-removed after tests. No other service/cache touched. Test log outputs are helper receipts; root owns package-wide release qualification.

This proves common SQL metadata authority and retained sealed bytes, not semantic parsing of data formats, engine contract implementation, data queries, source materialization, mutable database snapshots, versioned Knowledge storage, host readiness, durable seal-catalog provisioning, CLI/operator/grant UX, MCP discovery, worker transport, Tasks, split-provider execution or installed-consumer compatibility. Runtime default None remains unchanged. Full #131 and full owner scope remain open. Source kind knowledge labels metadata only and does not make a Knowledge collection or historical version. Permission naming does not implement data.read/manage execution enforcement; that later operation seam must do so explicitly.

## Documentation improvement

Canonical file proposed: docs/skills/repository-operations.md, Public Data and Knowledge integration boundary. Exact replacement in canonical-guide.patch and canonical-guide-replacement.md. Replaces fixture-only compatibility wording with tested common-SQL metadata prerequisite, preserves ordinary bootstrap absence and full product gates; records sealed-bytes versus snapshot/engine readiness, distinct permissions, no owner bootstrap change, replay/CAS, private catalog dependency and local/shared operator limitations. Evidence: source interfaces plus receipts above. Remaining uncertainty: all host/operator/worker/source-materialization gates, migration integration and full package/installed qualification.

Upstream disposition: none. Repository-owned bounded implementation, no demonstrated dependency defect or external mutation. Provider design phase3+ remains pending separate authorization/review.
