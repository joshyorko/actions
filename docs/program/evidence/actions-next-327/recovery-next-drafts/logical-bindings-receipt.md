# Logical requirement / immutable binding prerequisite receipt

Patch `logical-bindings.patch`: SHA256 `f56f927ecc2aeac9729a86d8ceefcfae66f7b87c6289e0e983c8dc288fd2da48`.

Base HEAD `c97e7bbd814fed7e1b5731761eeb02f00b940dbc`. Scratch archive overlaid the exact then-current integrated a28 Python dependencies; `base-overlay.json` records their hashes. All nine patch paths were unchanged from HEAD in the shared checkout at capture. Patch includes only the seven scoped source files, focused tests and archived old-verifier fixture. `source-hashes.json` pins final files. Read-only `git apply --check` against current shared checkout passed. No shared writes, pushes, RCC/cache use or production provider configuration occurred.

## Implemented prerequisite

- Frozen, strict `LogicalBindingRequirement` declares a logical ID/kind and bounded named versioned operations. Each operation defines typed parameter/result fields, explicit read/write effect, and row/byte/time limits. Unknown configuration fields, defaults containing arbitrary values, duplicate IDs/fields and unsupported types are rejected. Requirements, operations and fields normalize deterministically. There are no provider/DSN/path/endpoint/credential fields in this Package declaration.
- Generated compiler admission includes the canonical declaration and capability requirement IDs. Artifact verification checks their exact correspondence. `FoundryPackageRegistry` projects requirements from verified manifest bytes, not mutable Action records or caller-owned schema objects.
- Explicit `backend.logicalRequirements` and separate authoring `dataBindings` choices are supported. A choice is `{bindingId, requirementId, provider}`. The binding ID must identify a selected Canvas capability, and its requirement ID must resolve exactly within that compiled capability. Extra, missing, duplicate, cross-Workspace and colliding alias assignments fail closed.
- `RuntimeDeploymentSelection(..., provider_compatibility=None)` retains its legacy method and adds `select_specification_with_bindings(..., choices)`. The optional trusted `ProviderCompatibilityPort.operations(actor, provider_ref, kind)` returns typed operation declarations. Every requested named operation must match schema/effect/bounds exactly; no coercion, policy weakening or provider fallback is inferred. No port is configured by ordinary bootstrap in this checkpoint. Requirements without explicit choices/port fail closed.
- Selections become existing immutable `BindingAssignment` entries, sorted by exact requirement reference. Existing common Deployment authorization owns stage/resolve/replay scope checks. A/B provider references produce different Deployment revisions with the same compiled Package bytes; retained resolution keeps A while current selection becomes B. Provider execute revocation blocks later retained resolution.
- Newly compiled source-owned requirement references follow the existing explicit trusted new-Package admission grant path, like its Package/capability/plan references. No provider grant is created, restored or inferred. Re-admitting an existing Package does not restore revoked grants.

## Format gate and compatibility

`PACKAGE_SCHEMA_VERSION = actions.package-revision/v1-draft` remains exact for empty requirements, including its identity domain and serialization. Observed precheckpoint SHA256 values are in `legacy-baseline.json`; tests pin manifest, source archive and runtime plan hashes against those bytes. Empty `GeneratedBackend.logicalRequirements` is omitted from its wire form, preserving legacy authoring fingerprints.

Only nonempty declarations use `PACKAGE_BINDINGS_SCHEMA_VERSION = actions.package-revision/v2-bindings-draft`. The verifier enforces schema/requirement presence, canonical declaration order, capability requirement IDs and digest domain; unknown schema and mismatched presence are rejected even after recomputing the manifest digest. This is the explicitly reviewed older-reader fail-closed gate.

`test_logical_binding_checkpoint/legacy_package_verifier_c97e.py.txt` contains the exact old verifier core function from c97e7bbd814fed7e1b5731761eeb02f00b940dbc. Its function source SHA256 is `61435130e9821cb511aff4e4d94af520ea809b1774f31ad05427f9b1a971b5a4`. The test executes that function with unchanged shared helper algorithms/types: it accepts legacy output and rejects the new schema before native projection/admission. This is actual archived verifier-code evidence, not a mock predicate. It is not an installed-old-Runtime downgrade/restore test.

No worker/provider readiness claim follows from accepting this format. The later worker binding port needs its own runtime capability gate and execution qualification. Older readers must refuse requirement-bearing Packages rather than pretend they have no requirements.

## Tests and exact limitations

- `baseline-missing.log`: unchanged root compiler has no logical_bindings module (feature absence evidence).
- `first.xml`: 14 SQLite/contract passes; 12 PostgreSQL variants skipped before the owned container was started. These skips are not provider evidence.
- `dual.xml`: 37 passed, zero skips, SQLite plus owned common-SQL PostgreSQL.
- `regression.xml`: 114 passed, one genuine RCC test intentionally deselected, before the distinct schema gate.
- `versioned.xml`: repeated 37-case prior-source run after an edit script assertion aborted without changing files; not schema-gate evidence.
- `schema-version.xml`: 41 passed, zero skips; includes actual archived reader and rehashed-invalid-schema tests.
- **`final-regression.xml`: 122 passed, zero skips, one genuine RCC test explicitly deselected.** This final source group includes the compiler contract tests, native Package registry, runtime profile, authoring, Work Item authoring compatibility and all 45 new focused cases.
- `qualified-static.log`: mypy passed seven source files. Ruff check passed scoped source/tests.
- The broad gate used a temporary scratch-only override of the unrelated feedback fixture so it could not invoke RCC; `action_server/tests/conftest.py` was restored byte-for-byte afterward and is not in the patch. Actual compiler phases use the existing explicitly synthetic test executor. No RCC operation or cache access occurred.
- Owned PostgreSQL used the already present pinned image `postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81`, loopback-only random port, synthetic credentials, 768MiB memory and 512MiB tmpfs. Exact owned container `e60424d5fcc3c64d2348d123e4233fec51d0db90d09851b63acf8d1f8a132de0` was removed after tests.

Final gate command, under the already prepared Runtime interpreter, with explicit scratch source/test overlays and an owned PostgreSQL DSN:

```
python -m pytest \
  action_server/tests/contract_tests/test_package_revision_compiler.py \
  action_server/tests/action_server_tests/test_foundry_package_registry.py \
  action_server/tests/action_server_tests/test_runtime_execution_profile.py \
  action_server/tests/action_server_tests/test_foundry_authoring.py \
  action_server/tests/action_server_tests/test_authoring_work_item_policy.py \
  action_server/tests/action_server_tests/test_logical_binding_checkpoint.py \
  -q -k 'not genuine_generated_action_rcc'
```

The PostgreSQL proof concerns common SQL authority/immutable Deployment resolution. Provider compatibility is a typed injected test fixture, **not** actual DuckDB/PostgreSQL Data execution. No production provider registry, operator provider configuration, worker binding client, Knowledge ingest Task, public result query or installed flow was added. Those remain the separate #131 product integration gates documented in `data-knowledge-plan/README.md`.

## Exact canonical guide delta proposed

Update `docs/skills/repository-operations.md`, following “Bounded Knowledge collection provider proof” and its component/public-integration distinction:

> Generated Packages can declare bounded typed logical requirements through `backend.logicalRequirements`; authoring selects `dataBindings` by the exact Canvas binding ID and requirement ID, separately from Canvas UI and Work Item queue policy. The native registry projects these declarations only from artifact-verified Package bytes. RuntimeDeploymentSelection requires an explicitly injected ProviderCompatibilityPort, live deploy grants on requirement/provider references and exact operation schema/effect/bounds. Its default None does not provision a provider or infer a binding. Missing/extra/colliding assignments, wrong capability/workspace and revoked provider authority fail closed. Binding assignments remain in the existing immutable Deployment and later resolve through that retained revision; they do not replace it with a mutable default provider.
>
> Empty-requirement Packages retain the exact legacy `actions.package-revision/v1-draft` bytes and identity domain. Nonempty requirements use `actions.package-revision/v2-bindings-draft`, with a schema/presence invariant and matching digest domain. The archived c97e verifier accepts legacy output and refuses the newer schema; this proves parser refusal, not installed downgrade/restore qualification. Do not remove the format gate or allow older native readers to silently project an empty requirement set. New source-owned requirement reference grants follow only the existing explicit new-Package compilation admission; provider grants remain separate and are never minted by selection or replay.
>
> This is a declaration/immutable-selection prerequisite. Its real SQLite/PostgreSQL tests qualify common SQL state, not data-provider I/O. Ordinary startup still has no production provider compatibility registry, and this checkpoint does not implement an operator provider lifecycle, credential resolver, worker logical-operation port, durable Knowledge ingestion/Task or public query/result flow. Those require separate runtime readiness/capability enforcement and installed acceptance before claiming #131 completion. Fixed flat typed fields and exact compatibility are intentional bounded grammar; richer schemas or compatibility coercions require an explicit versioned extension, not silent fallback.

Ledger correction proposal: change only the “General operation/binding compiler missing” portion of row 576 to “typed generated requirement declaration and exact immutable binding-selection prerequisite qualified; provider/operator/worker/public execution still missing.” Leave all retained source proof, Parquet, public discovery/results, Knowledge lifecycle, durable ingestion and split-service gates open. Do not mark #131 completed.

## Mandatory receipt

Documentation improvement:
- Canonical file proposed: `docs/skills/repository-operations.md`; exact delta above, plus narrowly qualified ledger wording.
- Durable learning: distinction among UI binding IDs, Package requirements, immutable provider assignment and actual execution; old-reader refusal while retaining legacy bytes; no provider grants/defaults.
- Evidence: final-regression.xml, qualified-static.log, source hashes, archived verifier function and legacy baseline bytes.
- Stale/ambiguous guidance removed: generated logical declarations are no longer universally empty, but public Data/Knowledge integration is still absent; common SQL provider fixtures are not Data-engine or installed execution proof.
- Remaining uncertainty: full installed/package suite and actual RCC execution are integrator-owned; provider registry/operator/worker/Task integrations remain outside this checkpoint.

Upstream disposition: none. This is repository-owned integration work; no external targets were authorized or changed.

## Exact replacement of the now-integrated canonical section

The existing `Public Data and Knowledge integration boundary` section at repository-operations.md:5196 must have its stale first paragraph replaced, not merely followed by another claim. `canonical-guide.patch` is the exact delta against the current root document; `canonical-guide-replacement.md` contains the full replacement section. It preserves the existing Knowledge/Task/provider/installed/advanced-scope limitations while correcting only declaration/registry/selector prerequisite status and recording the format gate. No root documentation was edited in this lane.
