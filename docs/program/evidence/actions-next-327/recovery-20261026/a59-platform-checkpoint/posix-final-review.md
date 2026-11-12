# A59 POSIX typing patch review

Reviewed the exact source and documentation diff from commit `d878068e` to `123e772ee36c44cfd96ea62a6c599bb4f55c8f1b` (tree `7d6658bc3f2d536519c8698503f8b379c7b3ed56`). This was a read-only, bounded review of the seven POSIX typing modules, adjacent refusal/capability tests, and canonical guide changes. No source files were edited, tests were not run, and nothing was pushed.

## Findings

No security or capability-regression findings in the reviewed POSIX typing changes.

The module-local helpers check each flag as an integer and reject booleans; callable APIs are checked before casting. There is no zero-flag or Windows permission fallback. Existing runtime admission remains in place for offline authorization, offline provider setup, task policy loading, and Linux-only Robot execution. The POSIX-only provider/catalog and private restore helpers fail closed if called directly without the required OS API. `GeneratedRccExecution._extract_snapshot` resolves `fchmod` before creating its destination, so a missing callable cannot leave a partially created destination. POSIX archive mode handling remains intact where the operation is supported.

The added source tests cover compiler materialization bytes/archive mode identity, missing or non-callable compiler `fchmod`, descriptor closure on a real `fchmod` failure, explicit operator refusal, and RCC extraction refusal before destination creation. These tests were inspected but not rerun in this review.

## Claim limits

The parent supplied current evidence reports Windows-target mypy passing across 665 files, 96 affected private execution/provider tests passing with 33 explicit PostgreSQL/RCC skips, joined operator fixtures at 75 passed/0 skipped, and configured Ruff, formatting, import-order, and Linux mypy passing. This review did not independently reproduce those runs. These results do not establish Windows runtime support for POSIX-only APIs or a Windows runtime acceptance pass. The two running browser gates remain outside this review.

## Documentation disposition

Consolidate the platform typing guidance already added to `docs/skills/repository-operations.md`; it captures the durable rule that Windows typing uses checked, precisely typed `getattr`, missing security flags fail closed, and required capabilities are resolved before destination creation. The `work-items.md` addition separately documents the POSIX restore/authorization refusal boundary and fixture strategy. No further documentation delta is needed from this review.

Upstream disposition: none.

Documentation improvement:
- Canonical file changed or proposed: consolidation approval for the existing `docs/skills/repository-operations.md` guidance; no new delta proposed.
- Durable learning captured: optional POSIX APIs require checked callable/integer admission and must fail closed before owned destination state is created.
- Evidence: exact diff to commit `123e772e`, capability/refusal tests in that diff, and the existing module patterns cited by the guide.
- Stale or ambiguous guidance removed: none needed in the reviewed changes.
- Remaining uncertainty: this review does not independently validate the supplied test/typecheck receipts or resolve the two active browser gates; it makes no Windows runtime-pass claim.
