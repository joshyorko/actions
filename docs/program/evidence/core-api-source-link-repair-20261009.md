# Core API source-link repair evidence

**Base:** `011c5482285ea516f39292100c429a905e6e3e36` (published `community`)
**Branch:** `docs/api-source-links-20261009`
**Pushed head:** `25026da07d6d8cb01ef2badbc21c059380bf6060` (PR #255 successor)
**Scope:** local documentation source-link repair; no product behavior or release claims.

## Finding and repair

The Core API generator passed `devutils.invoke_utils.REPOSITORY_URL` to lazydocs. At the base, that URL pointed to `sema4ai/actions/tree/master/`, so generated docs sent readers to the wrong owner and obsolete branch. It now points to `https://github.com/joshyorko/actions/blob/community/`.

An initial generation in a shared environment exposed the `actions` namespace from `actions-core`, Runtime, and Work Items together. LazyDocs emitted Runtime and Work Items pages into Core's output. That contaminated generated patch was preserved at `contaminated-generated-core-docs.patch` (SHA-256 `df14f133ddf863b3b2b76aa899eec73265e513b8394156495ad76d06d512f97f`) and excluded from the final changes. The isolated Core environment at `/workspace/work/community-resume/wheel-inventory/actions/.venv` resolved `actions` only from its Core source directory; `actions.server` and `actions.work_items` were unavailable. Regeneration from that environment produced eight Core API documents and no Runtime or Work Items API pages.

## Verification

- RCC v18.19.3 Doctor passed; Poetry 2.1.1, Python 3.12.15, Invoke 2.2.0, Node 20.19.3, Go 1.23.6 were present.
- Package-local `invoke docs` completed; package-local `invoke docs --check` completed with staged output unchanged.
- All 57 generated source links use `joshyorko/actions/blob/community/actions/src/` and their target files exist in the checkout.
- The initial full `devutils` Ruff check found an unused `typing.Sequence`
  import in `runtime_conformance.py`. Source inspection found no use beyond the
  import; it was removed without behavior changes.
- Final `devutils` tests: 109 passed; full Ruff passes. Core `invoke docs --check`
  passed using the isolated Core environment; later changes only removed the
  unused import and clarified this guide.
- `git diff --check` and staged diff check pass.
- No upstream defect was confirmed or filed; upstream disposition: none. This is a local repository-owner/source-link correction.

## Canonical guidance

`docs/skills/repository-operations.md` now records that Core API generation must use its package-local isolated environment, that a shared namespace can contaminate LazyDocs output with Runtime/Work Items APIs, and the concrete namespace checks required before accepting generated output. It also records the maintained repository source-link base and directs maintainers to regenerate rather than hand-edit API docs.

## Shared-helper impact review

`REPOSITORY_URL` is passed by the shared `build_common_tasks` helper used in
`actions/tasks.py`, `action_server/tasks.py`, `work-items/tasks.py`, and
`actions-http-helper/tasks.py`. Their sources live in this same repository and
the Runtime and helper package metadata identify `joshyorko/actions` as owner.
The updated base will therefore correct future source links for those package
docs too. No broad regeneration was run; only `actions/docs/api` was generated
and verified in this task. The separate `mcp/docs/api` files retain the old URL
and are outside this helper's call sites, so they were left untouched.
