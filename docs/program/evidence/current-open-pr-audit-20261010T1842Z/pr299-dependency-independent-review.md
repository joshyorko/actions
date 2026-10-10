# PR299 independent integration admission review

## Exact GitHub and Git state

- PR: https://github.com/joshyorko/actions/pull/299
- Read-only API: `GET /repos/joshyorko/actions/pulls/299`, captured 2026-10-10.
- State: open, draft=true, head `4cad04ca0e70d219f53452fa5911c6d61192fd0d`, tree `5154dfbbff12e85b75e85d6138bfb6ff8eef27d0`.
- Target: `integration/community-release-20261008` at `e886d26ebaefafa9189a69517f6707691b53662e`, tree `016664a8e0d01dec36accf4fe5d39cb0b7bebef7`.
- GitHub reports mergeable=true and mergeable_state=`clean`. Compare endpoint reports 16 commits ahead, 0 behind, and merge base exactly `e886d26...`. Local `merge-base --is-ancestor e886d26... 4cad04...` passed. The head is a two-parent merge commit and its combined tree is the exact tree above; no local checkout mutations were made.

## Checks and review state

`GET /commits/4cad04.../check-runs?per_page=100` reports **20 check runs, all completed with conclusion success**, including Linux/macOS/Windows devmode builds, toolkit matrix, coverage, wheel/sdist jobs, unauthenticated Action Server builds, audit, and publish validation. No check is pending, failed, or skipped at this head.

`GET /pulls/299/reviews` returned an empty list; the GraphQL review-thread endpoint returned no threads; PR metadata reports zero review comments and no requested reviewers. Draft status alone is not a source or mergeability blocker under the assigned direction. The repository rulesets endpoint returned `[]`. The classic target-branch protection endpoint returned HTTP 403 `Resource not accessible by integration`, so this lane cannot independently certify whether an out-of-band approval requirement exists. GitHub's PR API nevertheless reports `mergeable=true`, state `clean`.

## Independent acceptance mapped to the current private Run-output source

- Exact c931 source checkpoint `c931b31f7b258e3eec93369c4c5cd64885d0e5b6`, tree `a6980fc434b49eecd734c192abe375589ebfeb69`, has a focused private service/filesystem suite receipt of **50 passed, zero skips/errors** and an independent review that separately reran all 50. Receipt files: `/workspace/work/run-output-stage-cleanup-20261010/receipt.md` (SHA256 `38a5bd25f9c8953139ed78e4efa0ba32ae7f326dfd7e0ccbfc4ab964acac376c`) and independent review `/workspace/work/run-output-stage-cleanup-20261010/independent-review-luna/receipt.md` (SHA256 `1a800a93465566c5bb7b46bed67554046b99a6f9943e8cdc5577783a07898616`).
- Current PR head is not descended from c931 as a commit. The acceptance applicability is instead established by exact relevant blobs: `run_outputs/filesystem.py` `89170173`, `models.py` `ae75ceee`, `service.py` `55f5c09a`, `types.py` `cac30880`, `migrations/__init__.py` `7889794d`, and `tests/action_server_tests/run_outputs/test_service.py` `4fcd73a8` are byte-identical at c931 and 4cad. A path-scoped `git diff` across the full Run-output implementation and 50-test directory is empty.
- Real PostgreSQL acceptance at c931 used PostgreSQL **17.11**, migration 15, and reported 12 PostgreSQL suite nodes plus seven focused service/abort scenarios passing. Receipt SHA256 `4302048d86d85172fb2a58e4dde9e36f2b586f1b165b3c30e161f9cab811ec41` at `/workspace/work/shared-run-output-postgres-c931/postgresql-seal-abort-receipt.json`.
- On current head, the Run-output service/provider/model/type, migration registry, and test-service blobs are exact matches to that PG-tested source. The 11 PostgreSQL test function bodies in `test_database_shared.py` were compared through Python AST source segments between c931 and 4cad: all are identical; the parametric collision test yields the two recorded stdout/stderr cases. The file's intervening changes are confined to historical SQLite migration fixture cleanup and Windows SQLite path coverage. `_database.py` differs only by a rooted Windows-drive path normalization guard before URL parsing, not by PostgreSQL query/transaction behavior. Thus the PG17.11 receipt is applicable to the unchanged Run-output/PostgreSQL seam, with this precise bounded source delta; it is not a fresh whole-PR PostgreSQL run.
- A separate local combined-tree run at `4a2d3cdd5cd81d7fe61e2691e86e8b27698d54a3`, tree `c1113df7...`, recorded 51 relevant private/migration tests passing, but is not claimed as an exact remote-4cad test run. Current exact-head GitHub CI supplies the remote test gate.

## Admission conclusion and limits

**Recommendation for the declared PR292→PR299 dependency: WAIT.** PR299 exact head contains current PR292 head `d0e12c1e1a256664b506cd8b027292062c6e1109` in its ancestry, and its own 20 exact-head check runs are green. This proves the checked union passed ordinary hosted CI, including Windows devmode. It does not fulfill PR292's separately declared remaining gate for a fresh native artifact and affected acceptance: no specialized frozen/native resource-history acceptance check is present among PR299's 20 checks, and PR299's current body itself says native execution remains pending. PR292's current API state is open/draft, `mergeable_state=unstable`, with 19 check runs: 18 success and Windows devmode job 114257572296 still in progress. Its reviews and review threads are empty. The body of PR299 calls the work “stacked on #292”; therefore merging the union before its stated predecessor gate completes would need an explicit root decision to supersede or waive that gate. The green union checks are useful evidence and cover the Windows Runtime suite at a later source tree, but they do not silently substitute for the missing native acceptance. Wait for PR292's bounded native/affected gate (and its active hosted Windows result), or explicitly re-scope the dependency at root.

Source-level and backend review found no remaining blocker in the unchanged private Run-output seam; see the exact blob/test-body comparisons above. Do not promote this to full #83/#86/#129 acceptance. Public authenticated transport, production actor wiring, Canvas consumption, native frozen execution, object-store providers, and full owning-issue acceptance remain separate open gates. PR300 transport depends on PR299. Exact-head CI is not an actual PG backend run; the PG receipt is independent source-bound evidence at c931 as described above.

Repository-level caveat: neither PR has a submitted review or unresolved thread; the connector cannot read classic branch protection (403). If organizational policy requires an approving review, root must confirm it separately. No PR or ref was modified.


## PR292 dependency recheck (supersedes earlier technical-GO wording)

- PR292 current published head is `d0e12c1e1a256664b506cd8b027292062c6e1109`; API state is open/draft and `mergeable_state=unstable`.
- PR299 current head includes d0e12 in its history: its parent merge `25855955f1c58faf7d77161bbd3ef2d0be402e18` has parents `600fb4423dfdadb156840efd193e7522ecf35ec5` and d0e12; `600fb` retains the reviewed #292 line. The PR299 body calls this work “stacked on #292” (body pin 58b411 is an ancestor of current d0e12).
- PR292 has 19 exact-head check runs: 18 completed success and Windows devmode job `114257572296` is still in progress. PR299 has 20/20 successful runs on the later union tree, including a passing Windows devmode suite.
- PR292's own validation text explicitly retains fresh native artifact and affected acceptance as an open gate. PR299's standard check list has no frozen/native resource-history acceptance, and its body says native execution remains pending. Thus the green 4cad union is evidence for ordinary CI/source coverage, not a substitute for that specific native prerequisite. Both PRs have no submitted reviews or inline threads.
- Read-only APIs and local ancestry compare only; no merge, branch, or PR metadata was changed.

## Canonical guidance and upstream disposition

Documentation improvement proposal for `docs/skills/repository-operations.md`: add a compact admission rule that scoped backend evidence is reusable only when the tested implementation and selected test bodies are proven identical at the candidate tree, and that private Run-output predecessor acceptance does not close separate transport, Canvas, actor, native, or owning-issue gates. Evidence is this exact-source comparison and PR299's explicit private-predecessor body/remaining-scope statement. Existing PR documentation already records the detailed implementation and limits; this proposal is for durable admission practice, not a run diary.

- Stale or ambiguous guidance removed: none in this read-only lane.
- Remaining uncertainty: whether target branch settings require an approval that the read-only app cannot inspect.
- Upstream disposition: none; no upstream defect was identified.
