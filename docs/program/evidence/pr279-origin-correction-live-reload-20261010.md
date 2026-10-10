# Origin correction and actual watched failure recovery

Immutable companion receipt: `pr279-origin-correction-live-reload-20261010.json`,
SHA-256 `fb0ab983802e664393717462f8e364f3576cbb4c28ecec71908978dcd8aa21e8`.
Test-only checkpoint `508175cb2f07243f2bd337965fc9a612b87d193d`, tree
`5b65129512c876c55119edcfdd9457930850782c`, preserves `01c5d0b1` and merges
published `6a852ed` through `8ffee094`. Only the existing rollback test's child
source selection and a new live-reload test changed. Production source is unchanged.

| Exact-origin test | Result | Log SHA-256 |
| --- | --- | --- |
| Three complete-catalog rejection cells, repaired source | 3 passed, 27.65s | `a480a06c0142453e11c1b6c169cf294c197ea82f3291b7cf8413c7f74f6e5d0e` |
| Same three cells, all Runtime children on baseline `84b8c70a` | 3 failed, 7.66s | `4208746e2ad5775ab1162b42e5fcd49c9e251fc8776833e4df58e66c2c40c49e` |
| Two-package live watched failure/recovery with Core provenance | 1 passed, 9.94s | `faa743fd7f90ac8d8a3ffbee29071f9a182c9d2e4c6a18c86d56224c16b8b614` |

The exact-origin baseline fails at its first healthy `retained_tool` MCP call:
per-package startup synchronization disabled every A capability while importing
B. MCP reports error `-32603`, with server `KeyError: retained_tool`. All three
cells fail before candidate mutation or duplicate admission. This is the original
desired-set defect; it is not a new duplicate-key rollback baseline proof.

The earlier 101.91s baseline observation remains separately useful, with corrected
scope. `ActionServerProcess` inherited relative `PYTHONPATH=src:tests`, then changed
cwd and selected the repaired editable root for initial seeding. Its candidate
command used `actions_server_run`, which rebuilds absolute `PYTHONPATH` from pytest
sys.path and selected baseline source. It therefore proves mixed-seed
baseline-candidate admission failure, not a whole isolated baseline lifecycle.
Old logs are preserved. The initial 25.35s worker and 27.48s root positives remain
real repaired production behavior through matching production hashes; an isolated
pytest import alone did not prove isolated child origin.

The final live test explicitly pins absolute child Runtime source and reads each
owned child's `PYTHONPATH`. Selected handler/import/server/watcher bytes are hashed
before and after. Public `mcp.tool` callbacks return their actual Core module
origin, file hash and distribution version; every HTTP/MCP result checks those
against the installed Core 1.0.2 distribution. The observed Core module SHA-256 is
`d12241ee635dfc81051b391bfd1904922ab4fe97b8bef4c3dfff29a1988f74cc`.
Read-only persisted Run results independently retain all sixteen successful worker
outputs with that provenance.

The live sequence proves healthy A1/B1; a real watcher rejecting decorated malformed
B; unchanged catalog/revision, Action/ActionPackage rows, snapshot entries and old
source bytes while fresh workers still execute A1/B1; valid B2 watched convergence
and a changed surface revision; HTTP shutdown with natural exit 1; sync-free
restart preserving identical admitted catalogs/rows and A1/B2 execution; another
natural exit 1. Processes run sequentially, with at most two workers, unique
task temp storage and loopback ephemeral ports. Cleanup inspection found every
recorded Runtime PID absent and every recorded port closed. No production edits,
collector/worker stubs, downloads, toolchain mutation or RCC environment build.

Two test fixture diagnostics were preserved, rather than called product defects:
removing the decorator marker makes Core skip the malformed file and treat the
package as empty; separate catalog requests can straddle a valid generation
transition and carry different revisions. The final fixture keeps the marker and
polls a single tools response before comparing stable catalogs.

Remaining scope: this closes unmanaged executable failure/last-good/recovery in an
actual watched two-package Runtime. It does not close provider-specific real-RCC
rollback, frozen duplicate-key rollback, or in-flight worker draining. The opt-in
real-RCC test's hosted skip remains accurately recorded. Final published-head CI
and release decisions remain root-owned.

## Compatibility-policy reassessment

The stated requirement for a compatibility policy and rediscovery does not itself
require stable aliases. The implemented, documented policy identifies tools only
within the current catalog and requires rediscovery after catalog changes.
Deterministic unique current names, TTL 0/private responses and the shared
descriptor fingerprint support that policy. Original package/action whitelists
are applied before alias resolution; no internal alias-keyed authorization grant
was found. Under that accepted policy, unstable aliases are a documented boundary,
not an additional stable-alias implementation gate for #279.

The characterized stale alias can still bind a literal action after a transition,
and calls do not check a catalog revision. Thus neither historical identity safety
nor atomic list-to-call fencing is implemented. Do not describe the current policy
as either guarantee. External gateway/client alias grants remain unexamined.
This corrects the earlier gap wording that treated stable alias identity as an
explicit user requirement without establishing that stronger promise.

## Exact canonical guide proposal

Add beside CLI lifecycle proof in `docs/skills/repository-operations.md`:

> `test_cli_live_reload_multi_package.py` exercises actual unmanaged two-package
> watched failure and recovery. After malformed decorated B is rejected, it checks
> unchanged admitted DB/source/catalog and fresh HTTP/MCP execution of both old
> packages, then checks a valid B update and natural shutdown/restart. It measures
> the actual worker Core module origin/hash/version. This proof is separate from
> opted-in real-RCC provider rollback and from in-flight generation draining.

Add beside source-subprocess verification guidance:

> Pin an absolute Runtime source path in each CLI child's `PYTHONPATH` when its cwd
> differs from pytest's. Relative entries can silently select an editable install;
> the parent module origin does not prove the child's origin. Preserve public
> decorator markers in malformed collection fixtures: a file without a marker is
> skipped and may represent intentional removal. During watched convergence, poll
> one catalog response; separate list requests can straddle a valid generation
> change, so compare shared revisions only after the admitted surface is stable.

Documentation improvement: these deltas capture executed live recovery and remove
ambiguous source-origin and cross-request revision claims. Evidence is the exact
commands/hashes, observed child path, sixteen worker receipts, early baseline
failure and preserved fixture diagnostics. Remaining uncertainty is explicitly
scoped above. Upstream disposition: none; these are Actions-local proof boundaries.
