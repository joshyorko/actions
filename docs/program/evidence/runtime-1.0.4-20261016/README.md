# Runtime 1.0.4 robot qualification

Cloud Linux checkpoint, 2026-10-16. Publication belongs to Josh. These receipts do
not admit either repair to the frozen Runtime 1.0.3 campaign.

| Review item | Exact source |
| --- | --- |
| Draft [#317](https://github.com/joshyorko/actions/pull/317), artifacts #316 | `dd5ccf3ae76451536012f15e3bf1b1adc728f9eb` |
| Draft [#318](https://github.com/joshyorko/actions/pull/318), inputs #315 | `ffa6ed49726c4ece12c6648c021058e06927ddb8` |
| Combined Draft [#320](https://github.com/joshyorko/actions/pull/320) | `38b16fc489c48462c4952eec65b9b17572d8958a` |
| Separate staging base, unchanged | `670765e35c96871cb0302ba85469120fa196cc8f` |
| Combined tree | `59a4f704b3d2db2297460d4e4fcd7447b8ed909e` |

`hosted-source-identity.json` distinguishes source heads from GitHub merge
checkouts. #317 is tested as `c03d570a` with staging-base changes; both repaired
production modules have identical blobs to #317. #320 is tested as `cc52d97c`
with a whole tree exactly equal to its source head. Native completed-job log
excerpts bind that checkout to the retained artifact IDs.

The candidate contains normal local merges of both repairs onto the separate
1.0.4 staging base. Its GitHub PR merge tree equals its source tree. No existing
PR was merged, no integration base was advanced, and no release/tag/template was
published. Source package metadata remains 1.0.3. A detached build worktree changes
only `pyproject.toml`'s version and `actions.server.__init__`'s version constants to
build the private `1.0.4rc2` wheel; see `wheel-provenance.json` for that exact adapter.

## Repair and review

Original failed Windows run [38896151900, job 116956987509](https://github.com/joshyorko/actions/actions/runs/38896151900/job/116956987509)
reported six failures. Rewriting a file caused pathname/descriptor ctime
comparison to reject unchanged bytes. The supported Windows CPython 3.12.15 code
maps pathname ctime to birthtime but returns descriptor change time; this is
already tracked in [CPython #157671](https://github.com/python/cpython/issues/157671).
The repair uses explicit birthtime across the two APIs, keeps full ctime/birthtime
comparisons within each API, and preserves device/inode, mode, link-count, size
and mtime checks. All seven new timestamp regression cases failed before repair;
they now accept the API difference and reject observed identity/mutation changes.

Five unsafe-name failures came from fixtures that did not create literal entries
on Windows: devices, trimmed names, alternate streams and path separators.
Literal-filesystem tests now verify the actual enumerated name before asserting
collector rejection. Five additional inventory-boundary tests always exercise
rejection before pathname access, independently of platform fixture support.
No collector name, containment, link/reparse, hardlink or size/depth/entry rule
was relaxed. Partial retention, immutable initial binding and private collection
error behavior remain covered by the focused suite.

Self-review checked the repair diff and the combined API merge: input validation
still precedes Run/counter/artifact admission, selected-task declarations remain
exact, protected controls remain blocked, the private RCC task environment is
removed, and completion snapshots still run for successful and failed tasks.
This is an owner self-review; no new independent-review claim is made.

## Fresh local gates

All package commands used RCC 18.19.3's prepared Poetry gateway. Doctor,
Bootstrap and ToolkitTest passed in both isolated implementation/candidate
worktrees; each ToolkitTest ran 179 tests.

| Gate | Result |
| --- | --- |
| #317 `poetry run invoke test-not-integration` | 1,485 passed, 14 skipped, 16 existing warnings |
| #317 collector/lifecycle/storage selection | 138 passed, one native-Windows skip |
| #317 configured lint/typecheck | PASS; 359 files typechecked; optional Markdown lint unavailable |
| Combined `poetry run invoke test-not-integration` | 1,526 passed, 15 skipped, 16 existing warnings |
| Combined configured lint/typecheck | PASS; 361 files typechecked; optional Markdown lint unavailable |
| Combined focused inputs/collector/lifecycle/storage with real RCC | 180 passed, one native-Windows skip |
| Whitespace check | PASS |
| Private wheel source and installed-member identity | PASS; 204 tracked Python members, 220 installed Runtime wheel members |
| Clean install dependency check | PASS; published Core 1.0.2, HTTP helper 1.0.3, Work Items 0.4.4 |
| Template08 A / B / C | PASS / PASS / PASS |
| Authenticated process-restart retrieval | PASS; all 26 artifacts unchanged |
| Hosted full/native gates | Both heads: native-build, wheel/sdist, Work Items and audit PASS; full tests/toolkit still running at this checkpoint; see `hosted-ci.json` |

The combined focused command was:

```sh
ACTIONS_ROBOT_INPUT_RCC=/workspace/actions-cloud/bin/rcc \
rcc task script -r developer/toolkit.yaml -- \
  python /tmp/runtime104-package.py /workspace/runtime104-candidate action_server \
  run pytest tests/action_server_tests/test_robot_run_inputs.py \
  tests/action_server_tests/test_robot_artifacts.py \
  tests/action_server_tests/test_robot_run_artifacts.py \
  tests/action_server_tests/test_artifact_storage.py -q \
  --basetemp=/tmp/r104qual \
  --junitxml=/workspace/runtime104-evidence/combined-focused.xml
```

`runtime104-package.py` imports that checkout's `developer/toolkit.py` and calls
`toolkit.poetry(package, *arguments)`. No host Poetry/pip fallback was used.
Integration-marked tests excluded from portable suites, native-platform skips and
unavailable external-service gates are not passing evidence. The real RCC test
executed three tasks consuming two distinct literal values (including quotes,
Unicode, backslash and newline) and then the default with absent inputs.

## Wheel and Template08 scope

Wheel SHA-256: `52602dc18a6e39d49082370280f8f58914ba83257a07941e39a2ce05497b4958`.
It was built by RCC-provided `poetry build --format wheel`, installed into a
fresh environment outside every source checkout, and checked byte-for-byte
against both the adapted Git source and every Runtime wheel member. `uv`'s
`direct_url.json` records the wheel path with an empty `archive_info`; no installer
hash is claimed. The independently computed wheel SHA and installed-member
inventory establish the byte comparison. The wheel is private, not published.

Template input: robot-templates PR #8 source
`ee2f6c1d7dbc7f84312b046f66d019a09a9c6a50` with the sole declaration
`ValidateBatch.inputEnvironment: [INVOICE_INPUT]`. Its checked-in Runtime lock
remains 1.0.2; B explicitly uses the private candidate wheel adapter. A/C use
checksum-verified RCC 18.19.7; Runtime B uses bundled checksum-verified RCC
18.19.3. A/C tests ran through the existing Template08 comparison harness;
B ran its existing `_execute_mode` using an isolated wheel-backed Runtime.
`qualification-harness.py` is the exact successful B/restart harness, preserved
with its SHA in `provenance.json`. It uses explicit sandbox paths and contains no
credential values. Recreate those worktree/install paths before rerunning it
through `rcc task script -r developer/toolkit.yaml -- python <harness>`. It clears
inherited RCC interpreter selectors before starting the installed Runtime; the
first preparation attempt exposed `PYTHON_EXE` selecting the outer toolchain
instead of the isolated installed environment. That failed attempt supplied no
acceptance evidence; the successful run uses the sanitized child environment.

`combined-abc.json` binds each mode to the same source digest. A validates
default/repeat/alternate truth, deliberate failure and no-build reuse. C validates
strict signed-provider acquisition, provider-down reuse, archive-only execution,
strict leased execution and unknown-signer rejection. C remains separate from the
unimplemented Runtime artifact worker D; no D acceptance is claimed.

B used real import/catalog/run/poll/download routes and independent read-only
SQLite checks. Baseline and alternate downloads match fixed report/CSV truth;
the task consumed the declared alternate input. The failed task retained exact
`failure.json` bytes with its expected error. Missing/wrong credentials returned
403 for artifact list, text and binary retrieval. Full bytes and bytes 0-3 ranges
were checked for every artifact. Then the first Runtime exited, its original
robot path was renamed out of reach, and a new process reopened the same datadir
and database. All 26 artifact names/hashes, statuses, full bytes, ranges and
selected text payloads were verified again. See `restart-retrieval.json`.

All execution in this campaign used the selected Cloud Linux environment or
GitHub-hosted runners. Existing CI harness/artifact names containing `dakota`
are historical labels; no Dakota or Devsy machine was accessed.

Public evidence contains fixed-fixture workload files, curated receipts and
sanitized summaries only. Machine paths use named roots. Homes, credentials,
signing keys, databases, raw logs, environment archives and generated binaries
are excluded. `provenance.json` retains raw receipt digests; sanitized files have
their own hashes in `SHA256SUMS`.

## Handoff and remaining decision

Keep all three PRs Draft until fresh hosted results and owner review are accepted.
The recommended single union review is #320 into the separate 1.0.4 staging
branch. Alternatively #317 then #318 produces the same union after base integration;
recheck its final tree and hosted results. Do not merge both routes redundantly.
No merge is authorized by this evidence.

After approval, use the separate staging branch to prepare an explicit Runtime
1.0.4 release version/changelog and native artifacts, qualify the exact resulting
release source and real wheels, then have Josh perform publication and registry
verification. Coordinate the eventual base with the 1.0.3 release owner; the
current freeze, PR #221/#319 and publication remain outside this campaign.
Template08's declaration and eventual published-Runtime lock update require their
own reviewed template change; the private adapter is not a shipped lock.

The exact next decision is whether Josh accepts the union and authorizes its
merge into 1.0.4 staging after the outstanding hosted/native gates pass. Final
package/template publication remains Josh's separate decision.

## Required receipts

Documentation improvement:
- Canonical file changed: `docs/skills/repository-operations.md`, in repair commit `dd5ccf3a`.
- Durable learning: cross-API Windows ctime semantics and literal-name fixture preconditions; retain portable inventory-boundary tests on every platform.
- Evidence: the failed Windows job, versioned CPython source, seven red/green timestamp cases and five added inventory rejection cases.
- Stale/ambiguous guidance removed: implicit equality of pathname/descriptor ctime and successful-write-as-literal-name assumptions.
- Remaining uncertainty: native/hosted gates listed in the current CI receipt; source namespace trust and non-atomic snapshot limits remain explicit.

Upstream disposition:
- Candidate: python/cpython, consumed Windows CPython 3.12.15.
- Classification: known cross-API timestamp discrepancy; existing #157671 matches the observed failure and versioned implementation.
- Deduplication: searched issues and pull requests for `fstat ctime`; no new issue filed or upstream source changed.
- Disposition: existing issue linked; narrow local compatibility repair.
- Follow-up: revisit when supported CPython versions resolve that discrepancy; maintain same-API mutation checks.
