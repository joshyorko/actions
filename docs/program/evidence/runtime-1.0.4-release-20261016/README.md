# Runtime 1.0.4 qualification and release-button handoff

The qualified source is **9e8cfd7caa602031db4eba75f545b1211f882561**, complete
Git tree **c426aad8258a61da8dbf592696ea37a5499e5bb4**. All **17 exact-head
PR-event workflow runs pass**, including both full Runtime suites, both complete
PyPI matrices, both six-lane toolkit matrices, all six native jobs, Core, Helper,
coverage, audit and Work Items verification. Final receipts retain each exact
run/job identity; skipped publishing jobs are expected and do not represent a
publication.

The explicitly approved normal merges are complete: #321 into separate 1.0.4
staging at **70b5cbfe97535615f69feef8e90a5c07b058858e**, then #322 into
`community` at **d222f94edca26953c1506ab258adc458ded17c56**. Both complete trees
were independently verified equal to the qualified tree. Josh's fresh explicit
numbered approval resolved the earlier automatic approval-review rejection; that
initial rejected attempt did not execute. Final publication remains Josh's action.

## Source and review points

| Item | Exact source / state |
|---|---|
| #317 artifact retention Windows repair | `dd5ccf3ae76451536012f15e3bf1b1adc728f9eb` |
| #318 declared input forwarding | `ffa6ed49726c4ece12c6648c021058e06927ddb8` |
| Approved #320 combined source | `38b16fc489c48462c4952eec65b9b17572d8958a` |
| Normal #320 staging merge | `d234fda2dec409ee54d45af9aa7f7cf4b2e16fac` |
| #323 release-button bulk change | `1db830e73a6f9041616be40dadcad624e95e9ecf`, normal prep merge `87acac608dca272d0f9f11956717e7a21ee3e7cf` |
| Qualified preparation / promotion head | `9e8cfd7caa602031db4eba75f545b1211f882561` |
| Normal #321 staging merge | `70b5cbfe97535615f69feef8e90a5c07b058858e` |
| Normal #322 community merge / release source | `d222f94edca26953c1506ab258adc458ded17c56` |
| Published preceding 1.0.3 source | `20ccdae585b621a02080f545808fb3036f656e58` |

The original [Windows failure](https://github.com/joshyorko/actions/actions/runs/38896151900/job/116956987509)
was reproduced: CPython Windows pathname and descriptor APIs disagree on ctime
semantics for rewritten stable files. The repair compares explicit birthtime
across APIs while retaining full ctime/birthtime mutation checks within each
API and all other identity fields. Seven regression cases failed before the
repair and passed afterward. Native unsafe-name fixtures now verify the actual
created entry; five unconditional inventory-boundary controls enforce forbidden
names on every platform. Existing [CPython #157671](https://github.com/python/cpython/issues/157671)
is linked; no upstream issue or comment was created. Original repaired-head
full/native CI and the combined rc2 trial are retained in the
[earlier robot evidence](https://github.com/joshyorko/actions/blob/15c69ff8d1591e6aedfb6cf719f3b7e7fb08f92e/docs/program/evidence/runtime-1.0.4-20261016/README.md).
The fresh actual 1.0.4 source and wheel proof below supersede historical rc1/rc2
acceptance as release qualification.

GitHub closed the original #317/#318 drafts as merged by ancestry through #320;
no separate merge operations were performed. Do not merge their changes again.
The preparation carries forward the accepted 1.0.3 static-path namespace and
streamed-form security guards. Its package, Runtime identity, strict installed
verifier and exact Runtime changelog heading all agree on 1.0.4; dependency/RCC
pins and the historical Action Server changelog are unchanged.
`source-identity.json` binds both tested PR merge commits to the identical
complete tree. Those exact builder commits are preserved on qualification refs.
The evidence branch includes reports and a qualification harness beyond the
qualified source; its HEAD is not the release source.

## Passed artifact and functional gates

The actual source-built 1.0.4 wheel has **no version adapter**. A clean isolated
install binds **221 total Runtime members**, **205 Python members**, and every
tracked Runtime Python member to the named source. Exact public Core 1.0.2 and
Helper 1.0.3 registry URLs/digests, `pip check`, private Core import scanning and
**26 request-boundary controls** pass. `wheel-provenance.json` records the proof.
The local functional wheel is separate from the six supported hosted release
wheels plus sdist; `hosted-wheel-controls.json` records current Linux, macOS and
Windows producer scans, all 205 members and repeated 26-control passes.

| Private functional artifact | SHA-256 |
|---|---|
| `actions_runtime-1.0.4-cp312-cp312-linux_x86_64.whl` | `2a03feab07f156b60b0e85e614ee97de8e7de07fa4572d9e0fcfaf576fc9b894` |
| `actions_runtime-1.0.4.tar.gz` | `ad6a88dabd10b0e3ac00d747697c0a9f77ee9b98d431709c48cc08a6e6ddc716` |

Fresh Template08 **A/B/C PASS** at the final source. Template source is
`joshyorko/robot-templates` **ee2f6c1d7dbc7f84312b046f66d019a09a9c6a50**;
the only private declaration adapter is
`ValidateBatch.inputEnvironment: [INVOICE_INPUT]`. Its checked-in runtime lock
remains 1.0.2 and no template was published. B explicitly uses the isolated 1.0.4
wheel and bundled RCC 18.19.3; A/C use RCC 18.19.7. Baseline, repeat, alternate
input and deliberate-failure outputs prove values are consumed and artifacts
survive both task outcomes. C verifies strict provider acquisition, provider-down
warm reuse, archive-only execution and unknown-signer rejection; it does not
claim the future Runtime artifact-worker mode D.

`restart-retrieval.json` verifies all **26 artifacts** before and after a fresh
Runtime process opens the same database/datadir while the original imported
robot path is unavailable. Listings, full downloads, text views, hashes and HTTP
ranges match. Missing and wrong credentials return 403, and deliberate
`failure.json` bytes are exact. The old Runtime exited before restart.

Controller/Devutils: **213 passed**, with Ruff/format/isort passing. The historical
full local Runtime baseline is 1544 passed/15 skipped at 14b1c0b9, whose Runtime
production/test/frontend/build/lock inputs remain unchanged; current hosted
full source qualification is independent. Skipped external-service tests remain
unverified. An earlier private C trial failed when disposable RCC stores filled
the cloud workspace; its result was not admitted. The final-source A/B/C trial
passed after capacity was restored while preserving receipts, outputs and Git.

## Release-button implementation and qualification

The source adds **Prepare Actions Runtime Release** and **Publish Actions Runtime
Release**, using RCC's reviewed preparation run/source/version/manifest pattern
and Room's explicit owner/triggering-owner publication guard. The writer is
restricted to Josh, uses the existing `pypi` credential and job-scoped
`contents: write`, and publishes retained bytes directly. It does not depend on
a GITHUB_TOKEN-created tag triggering legacy tag-push publishers.

Preparation verifies current source/version/full tree, complete canonical jobs,
seven distribution producer receipts, archive digests, and native binary plus
both frozen/Go-wrapper acceptance/history receipts. Publication defaults to
read-only validation, reserves a manifest-owned private native draft before any
PyPI upload, accepts only exact matching existing bytes, uploads only missing
files, and creates the immutable tag/public native release after the full PyPI
set is confirmed. It never overwrites assets, retargets tags or blindly skips
existing files. Cross-service publication is not atomic: a prefix may remain on
PyPI until an original-bundle retry finishes. Original successful preparation
attempt identities remain valid after a refused accidental rerun only while the
original artifact remains available; full preparation reruns were observed to
remove it, so the current button cannot recover that lost artifact. Any configured native
signing credential blocks the unsigned manual route instead of bypassing it.

The isolated helper is reviewable on
`qualification/runtime-release-button-20261016`, final checkpoint
**2baf0b544344017a1ff9cb48c257dd50f61eb41c**. Its eight contract tests and Ruff
pass. It uses `contents: read`/`actions: write` with a fixed dispatch allowlist,
hardcodes `operation=validate`, and carries no package credential. It is not
release source and must not be merged into community. It preserves accepted
preparation/rerun identities instead of repeating their writes on recovery.

The actual owner preparation **38951733318**, attempt1, succeeded on community
source **d222f94edca26953c1506ab258adc458ded17c56**. The independent cloud
review verified the full 271,548,672-byte GitHub ZIP and all **34 retained
members**, including six supported wheels, sdist, four native release assets,
producer and native acceptance/history evidence. The artifact expires
**2026-11-15T19:02:03Z**. Its manifest SHA-256 is
**1a77f6c8e09869d6bd45df1b14e6a9ce3f908bcf09351b76cee26a209504878a**;
the archive digest is recorded separately. The untouched original bundle is
also preserved privately in the cloud workspace.

Actual default-branch button checks are complete:

| Gate | Result / run |
|---|---|
| Owner preparation | PASS, `38951733318`, original attempt1 |
| Owner read-only validation | PASS, `38953955933` |
| Repeat same owner validation | PASS, `38954043063` |
| Wrong reviewed digest | Expected refusal, `38954149205`, exact digest-mismatch marker |
| Missing rehearsal artifact | Expected refusal, `38953883654`, exact missing-artifact marker |
| Publisher in every validation | SKIPPED; no publication write |
| Original artifact retrieval after full preparation rerun | FAILED, rehearsal `38951953388`, artifact `12069241955` now404 |

The final isolated helper run `38953832412` intentionally remains **FAILED**
because it preserves that failed recovery gate; its report separately records
`owner_bundle_qualified: true`. It does not turn an unavailable artifact into a
passing qualification. [qualification-report.json](release-button/qualification-report.json)
retains all dispatch inputs, exact run identities and the untouched owner bundle.
All seven post-merge push workflows on community also passed, including native
builds and toolkit; `postmerge-ci.json` records their exact source and run IDs.

**Failed recovery gate:** separate rehearsal preparation **38951953388**
succeeded on attempt1. Its deliberate all-jobs rerun correctly refused rebuilding
on attempt2, but GitHub removed original artifact **12069241955** before that
refusal. The original-attempt API still reports success; artifact listing is
empty and direct artifact lookup returns404. Retrieving the original bundle
after a full preparation rerun therefore fails. This is the existing external
lifecycle limitation in [actions/upload-artifact#323](https://github.com/actions/upload-artifact/issues/323).
No duplicate upstream report or comment was published. A prior helper also
failed while reading the refused job's log. Its final diagnostic proved that
GitHub CLI rejected terminal escape sequences; captured log reads now explicitly
admit and strip those controls without rendering raw responses. Failed helper
receipts remain retained; bounded reads alone did not repair the CLI refusal. The source/bundle checks
were not relaxed. The lost-artifact gate remains failed.

[Draft #324](https://github.com/joshyorko/actions/pull/324), head
**6e2b050167bd1607757f211d51d13a274195d2bf**, proposes the exact canonical
guide correction. It is unmerged and changes only documentation. Current
publication cannot import a local backup after original artifact loss. Never
rerun the owner preparation or rebuild/substitute artifacts after publication
has begun. The earlier blanket claim that original-attempt validation alone
preserves accidental-rerun recovery is withdrawn.

The shell GitHub credential expired; the existing connected app performed the
authorized normal merges and pushed the isolated harness/evidence without
changing credentials or security settings. No approval denial remains pending.

## Exact owner decision and publication inputs

See [OWNER-PUBLISH-HANDOFF.md](release-button/OWNER-PUBLISH-HANDOFF.md) for the
single GitHub Actions button and exact inputs. The source merges are finished;
Josh alone decides whether to publish using the preserved original preparation
and documented retention limitation, or require a separately reviewed durable
recovery extension first. Final tag/package/native publication is unrun.

| Input | Value |
|---|---|
| Workflow branch | `community` |
| `operation` | `publish`, only when Josh chooses final publication |
| `preparation_run_id` | `38951733318` |
| `source_sha` | `d222f94edca26953c1506ab258adc458ded17c56` |
| `expected_version` | `1.0.4` |
| `manifest_sha256` | `1a77f6c8e09869d6bd45df1b14e6a9ce3f908bcf09351b76cee26a209504878a` |

No manual tag or local package command is needed. Publication retries must retain
these same immutable inputs and the still-available original artifact. Actual
live partial-publication recovery, Template08 future mode D and skipped
external-service tests remain unverified.

No final 1.0.4 tag, PyPI/native release, template, Homebrew dispatch or deployment
was performed. `publication-state.json` independently confirms public 1.0.3 and
absence of 1.0.4. Raw secrets, homes, databases, environment archives, binaries
and logs are excluded. Public JSON uses named root placeholders; original raw
receipt hashes differ from sanitized copies. `SHA256SUMS` covers public files.
