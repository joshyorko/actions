# PR273 current Runtime release-readiness snapshot

Observed 2026-10-10 06:02 UTC. This is a read-only hosted/repository snapshot, not a release approval.

## Source binding

- PR #273: open, draft, mergeable; head `3d077296d1469b99e9fe50327e98c03a6f0aa58f`, tree `b6ee7d0fb7d5e669c78929da4ca08055866d3353`; target `integration/community-release-20261008` at `6d438feb6c92f8bb01428f665ac423fb101b4017`.
- PR metadata/body source: GitHub PR 273 API; current commit status/check-runs were queried by the full head SHA.
- The multipackage native fixture change is included at this source: `test_cli_multi_package_sync.py` uses one invocation HOME from `tmp_path_factory.getbasetemp()` and creates a managed `package.yaml` under the frozen/Go-wrapper override. Its corresponding local source checkpoint is `3d6409e4b192ed6c543e9df68504ae543b16a889`; the file blob matches the current remote head. Local commit `3d6409e4` and connector-published `3d077296` have the same tree as reported in PR metadata.
- The earlier installed-wheel and frozen+Go-wrapper four-case passes were for head `d19e611c9ac58a797f8b8676aacb7892242b7f27`, tested merge `73504e4becef310334abd52370c722032c8b8ccd`, tree `c19b94a866b816fd5af9eeef7133294f0063616e`. They are historical evidence only; they do not certify `3d077296`.

## Fresh exact-head checks

Exact-head PR workflow runs observed at this snapshot:

- Native build/acceptance run `38029294071`: Ubuntu, Windows, and macOS jobs had completed build/provenance and were still running native acceptance. Linux/macOS provenance archives had uploaded early, but their jobs were unfinished; no artifact was downloaded or accepted here. Linux Go-wrapper Work Items browser verification was in progress; later Core/Work Items and native acceptance steps were pending. Windows binary build was still in progress.
- Runtime test run `38029294077`: all three Python 3.12 devmode jobs in progress.
- Runtime PyPI workflow run `38029294074`: sdist, Linux wheel, and macOS wheel succeeded; Windows wheel was still in progress. Its publish job was `skipped` for the PR event.
- RCC toolkit run `38029294099`: primary Windows and macOS plus n-1 Windows/macOS succeeded; primary Linux and n-1 Linux were still in progress.
- Measured coverage run `38029294069`: coverage job in progress.
- Work Items Release run `38029294083`: verify job succeeded; PR publish job was skipped. AI audit run `38029294076` succeeded.

The check-run API showed 20 total checks: 8 success, 1 skipped, 11 in progress. Thus the new Linux native artifact gate and final exact-head CI result were not yet complete. Provenance archives visible before job completion were Linux artifact `11661805921` (archive digest `sha256:059a674901fd26d6aaa6e2eceebd07411a3dba040d792f1e6beefb1bee4a1732`) and macOS artifact `11661581044` (digest `sha256:a518717e582da793c9bd1297a31871f277196acd84781956fe80fefce4104b15`). These archive digests are GitHub artifact digests, not verified inner executable or manifest hashes.

## Publication state and workflow limits

- PyPI `actions-runtime` JSON at `https://pypi.org/pypi/actions-runtime/json` reported latest `1.0.2` and an empty `1.0.3` release file list.
- GitHub `actions-runtime-1.0.3` release/tag lookup returned 404; `git ls-remote` likewise showed no `actions-runtime-1.0.3` tag. There is no verified Runtime 1.0.3 release asset.
- The current tap `joshyorko/homebrew-tools` main ref is `6ac930bd22d182b927f445039fb0c01cc6dca8cc`. `Casks/action-server.rb` remains at version `1.0.1`; this tap has no separate Runtime formula. Actions issue #211 remains open. No Runtime 1.0.3 tap update was observed.
- The Runtime PyPI workflow is tag-push-only for `actions-runtime-*` publication. It verifies tag/package version and ancestry, validates the exact seven-artifact sdist/wheel inventory and manifest, runs Twine strict checks, requires the protected PyPI environment credential, and uploads only on a tag push. The fresh PR build jobs are prepublication proof; they neither upload to PyPI nor authorize a tag. Repository guidance explicitly says never replace an existing tag or distribution file.
- No GitHub release, Runtime tag, PyPI upload, checksum announcement, or Homebrew update occurred as part of this review.

## Remaining gates at this snapshot

1. Complete all exact-head required hosted jobs and resolve any failures.
2. Wait for the Linux native build/acceptance job to finish, then validate its archive and internal manifest against head/tree `3d077296`/`b6ee7d0` before running the current-source four-case installed-wheel, frozen, and Go-wrapper acceptance. Prior `d19` results cannot substitute.
3. Obtain the corresponding Windows and macOS current-source native artifact acceptance, with exact source/artifact receipt binding.
4. Complete root-owned integration/release acceptance. Only then can separately authorized publication steps be considered. Runtime 1.0.3 remains unpublished, and issue #211/Homebrew remain downstream work.

Upstream disposition: no confirmed external defect; all candidate fixes are Actions-local. No upstream issue/report or external change was made.

## Follow-up status correction, 2026-10-10 06:03 UTC

The prior snapshot counted 11 in-progress checks correctly, but described the Runtime PyPI job too early: the `publish (3.12)` job was created after the first query and is now queued for the pull-request run. This is a staging/verification job in the generated workflow, not a PyPI upload authorization. On PR events it downloads the separately built artifacts, validates the exact seven-file Runtime inventory and checksum manifest, runs strict Twine checks and uploads a retained workflow artifact. Tag-version/ancestor verification, PyPI token check, and the `twine upload` step are guarded to `github.event_name == 'push'`. The PR job does not upload to PyPI. At 06:03 UTC, Runtime sdist and all three wheels had succeeded; the publish staging job was queued. All three native jobs remained in progress on their packaged acceptance steps; Linux provenance is available but the build job had not completed.

The documented no-replacement rule is not evidence of an explicit preflight query against PyPI: the verified release workflow validates the exact local artifact set and only invokes Twine on a tag push. Do not claim a PyPI preflight/overwrite check beyond the documented requirement to never replace an existing tag or distribution file and PyPI's immutable-file rejection behavior.
