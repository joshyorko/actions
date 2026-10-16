# Runtime 1.0.4 qualification and release-button handoff

The qualified source is **9e8cfd7caa602031db4eba75f545b1211f882561**, complete
Git tree **c426aad8258a61da8dbf592696ea37a5499e5bb4**. All **17 exact-head
PR-event workflow runs pass**, including both full Runtime suites, both complete
PyPI matrices, both six-lane toolkit matrices, all six native jobs, Core, Helper,
coverage, audit and Work Items verification. Final receipts retain each exact
run/job identity; skipped publishing jobs are expected and do not represent a
publication.

**Current blocker:** automatic approval review rejected the normal merge of
PR #321 into separate 1.0.4 staging, citing the initial restriction on merging
draft work without further approval. No merge was executed. #321 is now ready
for review; #322 remains the separate community promotion draft. An explicit
numbered approval for these two normal merges is pending. The new buttons cannot
be exercised on `community` until their workflow files reach that default branch.
Final publication is reserved for Josh.

## Source and review points

| Item | Exact source / state |
|---|---|
| #317 artifact retention Windows repair | `dd5ccf3ae76451536012f15e3bf1b1adc728f9eb` |
| #318 declared input forwarding | `ffa6ed49726c4ece12c6648c021058e06927ddb8` |
| Approved #320 combined source | `38b16fc489c48462c4952eec65b9b17572d8958a` |
| Normal #320 staging merge | `d234fda2dec409ee54d45af9aa7f7cf4b2e16fac` |
| #323 release-button bulk change | `1db830e73a6f9041616be40dadcad624e95e9ecf`, normal prep merge `87acac608dca272d0f9f11956717e7a21ee3e7cf` |
| Final preparation / promotion #321 / #322 | `9e8cfd7caa602031db4eba75f545b1211f882561` |
| Published preceding 1.0.3 source | `20ccdae585b621a02080f545808fb3036f656e58` |

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

## Release-button implementation and remaining qualification

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
attempts remain valid after a refused accidental rerun. Any configured native
signing credential blocks the unsigned manual route instead of bypassing it.

A separately scoped helper is reviewable on
`qualification/runtime-release-button-20261016`, paused checkpoint
**8d452c186c26a27a67f8247457275f3046730aa8**. Its four contract tests and Ruff
pass. It uses `contents: read`/`actions: write` with a fixed dispatch allowlist,
hardcodes `operation=validate`, and carries no package credential. It is not
release source and must not be merged into community. It is paused pending
approved promotion, then will exercise two preparations, a refused preparation
rerun with original-attempt retrieval, repeated validation and wrong-digest
refusal. Those actual UI gates remain **unrun** at this checkpoint.

The cloud shell GitHub credential expired; the existing connected app successfully
pushed this harness without a credential/security-setting change. The actual
merge remains blocked by automatic approval review, not by the shell failure.

## Concrete handoff sequence

1. Approve normal merges #321 into `integration/runtime-1.0.4-robot-fixes`, then
   #322 into `community`, both at the exact qualified head above. Recheck both
   resulting trees equal the qualified tree; preserve 1.0.3 tag/assets/source.
2. Activate only the isolated qualification helper with that exact community
   merge SHA, retaining qualified head 9e8c. Run preparation/read-only validation
   and the safe-rerun negative controls; retain the original green owner-handoff
   preparation and independently reviewed manifest digest.
3. Give Josh the exact preparation run ID, community source SHA, version 1.0.4
   and `release-bundle.json` SHA-256. He selects `operation=publish` in GitHub
   Actions when final publication is authorized. No local Poetry or manual tag
   creation is needed.

No final 1.0.4 tag, PyPI/native release, template, Homebrew dispatch or deployment
was performed. `publication-state.json` independently confirms public 1.0.3 and
absence of 1.0.4. Raw secrets, homes, databases, environment archives, binaries
and logs are excluded. Public JSON uses named root placeholders; original raw
receipt hashes differ from sanitized copies. `SHA256SUMS` covers public files.
