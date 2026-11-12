# Nonterminal Knowledge ingestion preparation

Base109666a5c0add7809dba6c9def2251d4ba7714a3, detached isolated checkout
/workspace/actions-knowledge-prepare. Production mutation only
`action_server/src/actions/server/data_queries/knowledge_execution.py` plus focused
tests and exact canonical documentation delta. No root/GitHub/version changes.

Apply knowledge-preparation.patch SHA256
9ec942092b2ccacf5e4baa8ac882b7e0eaf620dd810e697d77e6626b8645b3b4
and documentation.patch. Source SHA inventory is included.

## Closed host contract

prepare_ingestion(actor, fence, cancelled, *, operation_id=None,
output_name="knowledge-corpus.json", mapped_inputs=None) -> PreparedKnowledgeIngestion.

Defaults preserve standalone operation_id=RunID, corpus filename and exact
knowledge-ingestion/v1 receipt bytes. Actual admitted inputs must be empty unless
the trusted generated host supplies exactly built-in mapped_inputs={} after
artifact-verified empty mapping. Nonempty/subclass projections fail; underlying
admitted inputs/fingerprint, snapshot, actor and Attempt remain authoritative.
Generated callers must choose stable per-Run/requirement/operation IDs (ASCII
alphanumeric/_/- length1..128) and distinct portable output names (UTF-8<=255bytes,
no slash/backslash/NUL/dot/dotdot). Invalid identities fail before provider writes.

Frozen issued DTO fields: actor, binding, fence, output (OutputRef), corpus_digest,
corpus_size, operation_id, output_name, input_mapping_applied, budget (ReadBudget),
receipt_json (immutable bytes), provider_pin and output_pin (SQLRecordPin).
receipt property returns fresh nested dictionary. Weak issuance registry avoids
retaining completed preparations; caller keeps object alive until publication.
A dataclass clone or another service cannot authenticate it as issued.

recheck_prepared_ingestion(actor, fence, prepared) -> None is SQL-only and never
publishes. Caller must encompass it and canonical publish in one transaction.
It checks issuer, actor/fence, Run admission/fingerprint, live Knowledge read/manage
and source read/inspect, canonical retained definition, provider availability pin,
output SQL identity/provisional state/digest/size/name/expiry, and budget. It locks
PostgreSQL grants and pinned rows. No providers.describe/_read/_verify, VersionStore
read/write or blob open/stage is permitted during recheck; tests trap these calls.

Standalone execute delegates preparation, rechecks and publishes its same v1
receipt. prepare/recheck leave Run RUNNING and outputs provisional; even provider
write success cannot supply search readiness. _published generated-envelope
support is intentionally unchanged and remains root's integration responsibility.
Binding selection remains one exact binding per snapshot/service; multi-operation
hosts must explicitly select services/bindings, not install ambiguous duplicates.

## Verification

All package checks used prepared RCC gateway and existing Action Server env.
Runner asserts isolated source path. Existing standalone76cases were preserved;
new56cases span control SQLite/PostgreSQL x corpus DuckDB/PostgreSQL. Final selected
132passed/0failed/0skipped in38.66s. This includes unchanged independent-process
search/reconstruction tests. Owned pinned PostgreSQL container was stopped in
finally. No provider credential or fixture/datadir is included in delivery.

Initial red36failed/76passed: missing factoring API. First implementation112passed.
Expanded final attempt124passed/8failed: new tests omitted canonical FenceRejected
(RuntimeError) from expected durable-cancel/terminal rejection types; tests only
were corrected. Final-fixed132passed. All counts overlap; prior failures remain
failures. Initial static lint had two intentional exact-type E721 comparisons;
local explanatory suppressions fixed that check. Final Isort/Ruff format/check,
focused mypy and git diff --check pass. Full historical Action Server suite was
not rerun; this is the bounded disjoint factor inventory requested by parent.

## Documentation improvement

Canonical proposal: docs/skills/repository-operations.md; exact documentation.patch.
Durable learning: issued nonterminal DTO, default compatibility, explicit trusted
empty-input projection, distinct operation/output identities, SQL-only final
check and requirement to share the canonical publication transaction. Evidence:
132selected tests, I/O traps, real SQL/provider matrix and static receipts.
Stale/ambiguous guidance removed: previous monolithic execute-only description is
extended with the concrete nonterminal seam without claiming generated readiness.
Remaining uncertainty: generated host selection, actual RCC execution and generated
receipt/Task validators remain root-owned and are not proved by this patch.

Upstream disposition: none.
