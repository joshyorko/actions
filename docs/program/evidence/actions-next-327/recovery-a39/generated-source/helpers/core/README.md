# Core prepared Knowledge context

Base: e5330cb512ae3c47bf5018550431d179f2f18f6b in isolated detached
/workspace/actions-knowledge-core. No root checkout, shared Runtime, version,
dependency floor, lockfile, branch, or external mutations.

Apply core-knowledge-context.patch (SHA256
6b9bb6cf7b06f840a1443b4cc385226514292618b3c039bc830b6516774d539d)
and documentation.patch. Production scope: actions/data/_context.py and new
actions/knowledge/__init__.py; focused tests in test_knowledge_context.py.

Host hook remains install_context(payload, expected_digest=...). Old v1 wire
schema and scan API are unchanged. New actions.logical-context/v2 entries have
exact requirementId/operation/kind/parameters/result. Data entries use the legacy
flat scan validator; Knowledge entries are .ingest/v1 (empty parameters) or
.search/v1 (exact explicit ingestion_handle/query/offset/limit). Runtime owns
provider-specific limits, result schema, grants, fences and publication.

knowledge.ingest selects staged host result metadata, not completion authority.
knowledge.search exact-checks built-in string/integer parameters after explicit
0/20 defaults and returns a fresh deeply copied result. Changing parameters does
not perform work. Result root must be object; nested null/object/array supported
with depth8(root0), object64, array10000, aggregate256KiB/32lookups. Numeric rules
remain finite and portable. No provider/file/network/environment authority.

## Evidence

Prepared RCC gateway and canonical actions package environment; runner asserts
isolated source import and propagates isolated PYTHONPATH to subprocesses.
Focused final:79passed,0failed,0skipped (final.xml). Initial red:15failed/60passed;
first green75passed before four added boundary cases. Counts overlap.
Static first failed exact-type E721 lint checks; second passed Isort, Ruff format,
Ruff check and mypy on both production files with explicit package namespace.
Exact built-in parameter type comparisons retain explanatory local suppressions.
git diff --check passed. All original logs retained.

Full Core inventory:411cases, collected before execution. Full run and any
follow-up outcomes recorded separately in counts.json/README updates; no failed
run may be replaced by a later passing result. No installed Core wheel/RCC
Knowledge consumer claim is made here. Parent owns Core version/floor and build.

## Documentation improvement

- Canonical file proposed: docs/skills/repository-operations.md, exact patch.
- Durable learning: closed V2 context schema; Data compatibility; exact search
  parameter/default semantics; immutable deep-copy boundaries; staged ingestion
  versus canonical completion; nested result limits and host authority.
- Evidence: test_knowledge_context.py and unchanged test_data_context.py,
  isolated import proof, focused static checks.
- Stale/ambiguous guidance: no old v1 promise is replaced; new supported V2
  behavior is explicitly separate from existing v1 flat-only description.
- Remaining uncertainty: Runtime prepare/publish, generated receipt version,
  installed Core floor and real provider/Task joins remain parent integration.

Upstream disposition: none.

### Full inventory harness diagnosis

First full411 run:409passed/2failed/0skipped in108.39s. The two collector
failures were caused by external runner directory /workspace/knowledge-review
remaining on sys.path while fixtures lived below that directory. Collector
_get_root derived prefixed module names and imported package entry twice.
An immutable e5330cb5 archive prefix run reproduced both errors; that partial
archive additionally failed13Canvas contract cases because shared repository
fixtures were not included (15failed/32passed total; not a clean baseline suite).
Removing only the external script directory from runner sys.path made both
collection cases pass (collection-fixed.xml). Production source did not change.
Full corrected411 rerun is recorded separately, not substituted for the failure.
The documentation delta includes this verified harness requirement.

Final corrected full inventory:411passed/0failed/0skipped in107.09s; four
robocorp.log ast.Str deprecation warnings. RCC reported migrated PID27069 after
completion. Immediate inspection showed PPID1 state defunct (already exited),
not a live child; no kill/retry was attempted. Final fixture footprint68MiB;
filesystem remained12GiB free. No fixtures/datadirs are included in delivery.

Exact all-run counts are in counts.json. Source patch SHA remains unchanged.
Full fixed run is the package qualification result; all prior failed runs remain
failed historical receipts. No upstream defect is established by these harness
or process-reaping observations. Parent must still use its evidence-publishing
guard before committing receipts.
