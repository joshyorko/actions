# Owned frontend CDN retirement review

Disposition: approved bounded correction, no blocking finding. Reviewed current root `action_server/tasks.py`, deletion of `.github/workflows/action_server_build_cdn.yml` and `.github/workflows/frontend-build-cdn.yml`, new `devutils/tests/test_owned_frontend_source.py`, and retained owned release workflow. Exact surviving source hashes are in source-sha256.json. No root edits or test execution performed by this review.

The retired task now raises before any import, context execution, filesystem or network operation. Error directs callers to `inv build-frontend`, accurately identifying the owned checkout/lockfile path for both Runtime and Canvas entrypoints. Keeping a failing task symbol gives old automation an actionable error rather than silently substituting upstream binary frontend bytes. Both dispatchable CDN workflow callers are removed; current owned runtime binary workflow still invokes build-frontend.

New regression executes the actual AST-extracted function with imports/context execution trapped and confirms no temporary files, while the workflow regression forbids retired task reachability in current .yml files and requires the owned release build. Root retained the original two failures and corrected green receipt. Those are source/workflow assertions, not native release or installed frontend acceptance. Test coverage assumes current workflow suffix .yml; future .yaml workflows should be included if added, but none are present in the reviewed directory.

Exact canonical guide proposal, target docs/skills/repository-operations.md:

“Owned frontend builds consume the repository's Runtime and Canvas sources and lockfile through build-frontend. The legacy build-frontend-cdn entrypoint is intentionally a fail-fast compatibility tombstone: it must reject before imports, network access or filesystem mutation. Do not restore a workflow that downloads an upstream executable to extract embedded HTML; such bytes do not establish source-bound ownership or the two-entrypoint build contract. Keep the retired-call failure and workflow reachability regression together.”

Scope: the bounded CDN correction only; no assertion that all vendor dependencies or URLs are remediated, and frozen installed f905 is unaffected. Upstream disposition: none, local owned-build policy correction. No external writes.
