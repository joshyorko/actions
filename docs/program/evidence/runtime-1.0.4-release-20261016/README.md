# Runtime 1.0.4 versioned-wheel qualification checkpoint

This records actual version 1.0.4 at **87acac608dca272d0f9f11956717e7a21ee3e7cf**,
complete source tree **62dd004a447c265889bc45f25ef716affab4c953**. It carries the
accepted 1.0.3 security repairs plus the distinct #317/#318 robot fixes, followed
by version/changelog and release-fixture repairs. It supersedes private rc1/rc2
as versioned-wheel evidence. The separately reviewed release-button change in
[#323](https://github.com/joshyorko/actions/pull/323), head
**1db830e73a6f9041616be40dadcad624e95e9ecf**, is now merged normally into the
isolated preparation branch as this source. Its full Devutils suite passes
**208 tests**, including interrupted-write recovery and no-op reruns. Hosted
qualification of this complete source is still pending; this is a checkpoint,
not a completed release approval. The preceding versioned checkpoint remains
[immutable at05e80839](https://github.com/joshyorko/actions/blob/05e80839fcd26701a46c2cd6acd971931ca51035/docs/program/evidence/runtime-1.0.4-release-20261016/README.md).

- Approved combined #320 was merged normally as **d234fda2dec409ee54d45af9aa7f7cf4b2e16fac** into separate 1.0.4 staging. No individual #317/#318 merge operation was performed. GitHub marks those original draft PRs closed/merged by ancestry through #320; do not merge their changes a second time.
- #321 is the release preparation review; #322 is the community promotion review. Both current tested merge trees equal this exact source tree (see `source-identity.json`). Neither publication nor a final tag is performed by this evidence push.
- Prior 1.0.3 accepted community source **20ccdae585b621a02080f545808fb3036f656e58** was carried forward by normal merge **e4189907f515c324a49ddcebd40976163ee57451**. Its source branch/tag/assets were not changed. Independent public reads at 17:01 UTC confirmed PyPI/native 1.0.3 exists and 1.0.4 does not (`publication-state.json`).

## Local and hosted gates

`local-gates.json` binds retained private logs to SHA-256 and gate outcomes.
Runtime full suite: **1544 passed, 15 skipped**; Toolkit: **179 passed**;
Devutils: **179 passed**; strict release-version controls: **135 passed**;
Runtime lint/type checks and strict Twine: **passed**. The full Runtime suite ran
at 14b1c0b9; ec5 changes only the historical measured-receipt test fixture and
canonical documentation, with production/package/workflow inputs unchanged.
The subsequent controller/workflow changes do not change Runtime production,
Runtime tests, frontend, build script or lockfile inputs. The final wheel
build/install and real-wheel integration ran fresh at87acac. The208-test
controller/Devutils suite ran on the exact complete tree merged as87acac.
Skipped tests remain unverified. `ci-checkpoint.json` is a timestamped exact-head
snapshot; pending workflows are not reported as passed. Use final hosted checks
before merging or publishing a subsequent candidate.

The preceding ec5 source passed its PyPI/native lanes; those receipts remain
historical for this changed complete tree. Fresh87acac hosted Linux/macOS wheel
lanes and sdist passed, and their new producer receipts were independently
verified (`hosted-wheel-controls.json`). Windows, aggregate PyPI, source and
other hosted gates must finish; consult `ci-checkpoint.json` and live exact-head
checks. No pending gate is counted as passed. This local functional
wheel is Linux CPython3.12, not the full portable release inventory:

| Private artifact | SHA-256 |
|---|---|
| `actions_runtime-1.0.4-cp312-cp312-linux_x86_64.whl` | `2a03feab07f156b60b0e85e614ee97de8e7de07fa4572d9e0fcfaf576fc9b894` |
| `actions_runtime-1.0.4.tar.gz` | `ad6a88dabd10b0e3ac00d747697c0a9f77ee9b98d431709c48cc08a6e6ddc716` |

`wheel-provenance.json` proves no version adapter, all **221** Runtime wheel
members match installed bytes, all **205** installed Python members were checked,
and tracked Python members match the exact Git source. Installation was isolated,
with exact published Core1.0.2/Helper1.0.3 URL/hash receipts, `pip check`, private
Core import scans, and **26** request-boundary controls. Those dependencies,
registry URLs/digests and security constraints were retained.

## Meaningful Template08 and restart acceptance

`combined-abc.json` records fresh **A/B/C PASS** against
`joshyorko/robot-templates` source **ee2f6c1d7dbc7f84312b046f66d019a09a9c6a50**.
The sole template declaration adapter is
`ValidateBatch.inputEnvironment: [INVOICE_INPUT]`; its checked-in runtime lock
remains1.0.2 and was not pushed/published. Mode B explicitly runs the isolated
1.0.4 wheel. A/C use RCC18.19.7; B uses bundled RCC18.19.3 with the pinned digest.
Baseline/repeat/alternate outputs demonstrate declared input values are consumed;
deliberate failure retains exact `failure.json` bytes. Fixed synthetic outputs
and curated C receipts are included, without raw machine/library inventories.

`restart-retrieval.json` verifies **26** retained artifacts both before and after
restarting into a fresh Runtime process using the same database/datadir. The
original imported robot path was made unavailable by renaming it. Every listing,
full download, text view, byte hash and Range response matches after restart;
missing/wrong authentication remains403. The original Runtime exited before the
new one started. Successful and failed task outputs both remain retrievable.

## Review and handoff boundary

The original Windows non-integration regression was repaired in #317 at
dd5ccf3ae76451536012f15e3bf1b1adc728f9eb. #318 remains
ffa6ed49726c4ece12c6648c021058e06927ddb8. Their original combined/source/native
qualification is separately retained in the earlier evidence branch. This
checkpoint qualifies their versioned union with the carried-forward security
repairs; it does not weaken portable path, reparse/link, inventory bounds,
privacy or process-lifecycle contracts.

Qualify this final hosted head, complete the normal staging/promotion
preparation sequence, then exercise only non-publishing preparation/validation.
`controller-review.json` records the reviewed permission, provenance and retry
controls and their deliberate limits. The manual route refuses any configured
native signing credential; it cannot silently replace a signed release with an
unsigned one. Cross-service publication is not atomic; original-bundle retries
finish missing bytes without replacement. Josh retains the final `publish` action.
No final1.0.4 tag, package, native release, template or deployment is authorized
in this campaign. Do not merge #317/#318 a second time or mix the work back into
1.0.3.

Machine roots are replaced by named placeholders in public JSON. Secret values,
private homes, databases, archives, binaries and raw logs are excluded.
`provenance.json` contains original private-receipt hashes; sanitized public
bytes differ. `SHA256SUMS` covers the public evidence files.
