# Closed generated Knowledge operation contract

Baseec514752ae52be847427e8a4302d675100b8c990 in isolated detached
/workspace/actions-knowledge-contract. New production file knowledge_operations.py
and focused test_knowledge_operations.py only; exact canonical guide delta
separate. No root/DTO/version/database/external modifications.

Apply knowledge-operations.patch SHA256
84d3bdfb8cd54d39c75235371ddb88d1d6fe5aa5882cb3161f567fe7978d0a7d
and documentation.patch. Source member digests are included.

## API

knowledge_contract(operation: BindingOperation) -> Literal["ingest","search"]
revalidates the typed DTO (including copied/bypassed values) without mutating it.
Name lower-case prefix1..57 with .ingest/v1 or .search/v1; correct write/read
effect; ingest no parameters; search exactly required ingestion_handle/query
strings, offset/limit integers. Exactly required result_json:string result.
It is for root's explicitly selected mapped generated contract, not old Data
or standalone Knowledge metadata requirements.

encode_result(operation, envelope) -> {"result_json": canonical_JSON_string}
checks fixed inner versions/keys/types, canonical KnowledgeRevisionRef and output
handles/digests. Staged keys:version/revision/corpusHandle/corpusDigest/status;
version actions.knowledge-ingestion-staged/v1 and status staged only.
Search retains existing version/revision/ingestionHandle/corpusDigest/query/
offset/limit/total/hits. Hit keys id/source/ordinal/text/values; canonical digest
ID, bounded source name, portable nonnegative ordinal, nonempty NUL-free text,
JSON object values. Hit IDs unique and (source,ordinal) strictly increasing;
no assumption of contiguous ordinals after filtering. Exact returned cardinality
min(limit,max(total-offset,0)); query<=512, offset<=100000, limit1..100,total<=10000.
No source schema/grant/publication claim is made by this shape validator.

Inner JSON permits nested/null values with depth<=8 (envelope root0), object<=64,
array<=10000; exact built-in scalar/container types, finite portable numbers and
canonical positive floating zero. Cycle/depth/aggregate lower-bound checks happen
before encoding. Final max_bytes measures complete outer object including escaping.
Rows=1 for staged metadata, len(hits) for search. Return data is freshly encoded;
caller mutation cannot alter an existing encoded result. Core consumers must
explicitly json.loads(result["result_json"]). Root owns admission/eager execution,
provider schema bounds, fixed context/receipt and actual generated publication.

## Evidence

Final54focused cases passed,0failed,0skipped; initial43passed before extra hit/
boundary cases. Initial red was missing new module at collection (retained).
First static lint failed after formatter moved exact-type E721 comments; local
explanatory annotations corrected it. Final Isort/Ruff format/check/mypy passed;
git diff --check passed. Prepared RCC gateway uses existing package env; final
runner explicitly proves new module origin in isolated source. Original failures
retained. No provider/native/full historical suite rerun: this pure module's root
integrated generated scaffold is being qualified separately by parent.

## Documentation improvement

Canonical proposal: docs/skills/repository-operations.md; exact documentation.patch.
Durable learning: truthful primitive result_json contract, staged-vs-completed
version distinction, inner bounds independent of Core's string result, outer
escaping-aware byte limit and row semantics. Evidence:54focused tests and static
checks. Stale/ambiguous guidance: prevents interpreting BindingField result as
implicit nested document metadata; old DTO promises remain unchanged.
Remaining uncertainty: root integration, actual installed RCC/Task/provider
acceptance and receipt authorization are not established by this helper.

Upstream disposition:none.
