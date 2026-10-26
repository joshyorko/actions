# D336 bounded integration delivery

Coherent patch: `integration.patch` SHA256 `008bdcd8d8f8451fd3393311b7a536a4b9385148f59e3effe137085ace511f61` (2,173,641 bytes), exact tree delta from integrated `806dcf573c59f52b2d28084f953d1fbe623287d5` to `630b6f123845f87c89274befb55f9986979afb2e`. `git apply --check` passed against root f905c388 without modifying root. Alternate split: `tooling.patch` plus `evidence.patch`; do not apply these in addition to the combined patch. `filemap.json` identifies all 101 changed paths by Git blob, SHA256 and length. Compressed receipts and raw declared SBOM bytes remain exact Git objects.

`ordered-ancestry.txt` records every parent and subject. This is ten linear commits, no merges:

1. fffc12834ba10eb8d9f5ee976b7e7c03b1b1d216 — graph validation/tests/proposal, separately flagged below.
2. bcc68f0e83a49c4d99cf922c0b8259d0db58ed9c — optional pinned producer.
3. 1d21a71a7f602e34eeb26c111b1ac9c0032b15a8 — declaration explanation/contract proposal.
4. 4edd85a390d53d566ef6f299de3eae6d59918b19 — separate declared/active evidence.
5. 00ad01b8a29a84fb21ebc9ce87a45304138456e9 — bounded streams/actual consumer prefix.
6. e6db8576780a5ade79a8b6293036fd2eb219dc6d — Linux frozen build/smoke evidence.
7. 74244af8a261b2822f11dc1d10590a69158982b8 — helper/Common provenance evidence.
8. 0958911f16e77ded0748d82ff6e8b0968f3a32d3 — narrow Common proposal after decoupling.
9. 7aaaa0ebe0ea1dcace0ae45595e8cf104ce22002 — native Action/restart evidence and replaced-vendor guard.
10. 630b6f123845f87c89274befb55f9986979afb2e — correct source-bound Core version explanation.

The first commit was not named among the initial approved SHAs. Parent subsequently instructed separate review/inclusion of the required dependency, rather than silently omit it. `intervening-fffc128.patch` isolates it. Reviewed: it adds the exact active-edge comparator imported by the later producer, rejects missing/duplicate/dangling nodes/edges, and retains a failing inventory/declaration interpretation as proposal evidence. Later commits explicitly separate declared-graph explanation from active-graph parity. Recommend integrating this bounded dependency with the named sequence; no other intervening commits exist. This is not blanket permission for later branch history.

## Review

No blocking finding in the bounded tooling join. Production/tooling changes are three standalone qualification scripts plus optional devutils group/lock; no Runtime service/admission/authorization module changes. Existing lock name/version entries are retained. There are 36 added name/version entries (some platform/Python alternatives), and four existing entries acquire sbom group markers without version/hash changes; see `lock-review.json`.

The producer pins cyclonedx-bom7.5.0 in optional tooling, targets an explicit distinct installed interpreter, checks its actual prefix and candidate wheel payload bytes, snapshots inspection before/after, bounds subprocess output/time and retains failures. It intentionally trusts that interpreter and site/.pth execution; it is not a sandbox. POSIX descendant cleanup is broader than Windows direct-child cleanup, which is documented.

Raw CycloneDX declared edges remain unchanged. The active selected-profile graph and explained inactive marker edges are separate files. Retained bounded producer receipt still says `strict_active_graph.result=failed` with 29 explained inactive edges; its top-level pass is inventory/provenance evidence only, never release admission or active parity. No prior failure was converted to a pass.

Replaced vendor checks normalize and inspect every installed package name and every Requires-Dist target before marker/extra filtering. Thus inactive declarations of sema4ai-http-helper or sema4ai-common are rejected too. This is an owned-consumer dependency guard, not a new broad vendor audit.

## Qualification and remaining scope

Exact four-module collection: 33 cases; prepared existing devutils RCC gateway execution: **33 passed, 0 skipped**. `collect.log`, `tests.log`, `tests.xml` retain commands and isolated import identity; selected test inventory is `selected.json`. No dependency installs, producer invocation, build, native acceptance rerun or external writes occurred. Historical native/build/installed receipts remain tied to their recorded source/candidate, not f905 or a new installed release. Native Action evidence explicitly uses owned Core1.0.2 fixture, not source20639810 Core1.1.0a5 semantics.

Retrieval used harmless GitHub compare/commit/tree reads, then read-only isolated Git fetch because the connector decodes blob responses and cannot preserve compressed binary receipts. Local objects and extracted sources are outside root. No source branches/PRs/commits were created.

The publishing guard's duplicate-key/credential-field parser checked 22 changed JSON/decompressed JSON.gz files with zero findings (`content-guard.json`). This is content inspection, not an index-based publishing check or a general secret audit; root must still stage exact reviewed paths and use its publication guard. `guide-delta.md` is the verified canonical guide proposal. Upstream disposition: none; declaration-versus-selected-graph semantics are not newly classified as an upstream defect. No external mutation authorized/performed.

## Integration verification

Joined root devutils suite:324 passed, zero failures/skips. The new checker was also executed against frozen installeda41: it failed because MCP2.3.0 differs from Runtime lock2.0.0. Preserve that failure; old handoff constraints are not a full lock export. No new current-consumer SBOM, native/platform or release-ready claim follows from this source/tooling checkpoint. Exact local inspection hash and runner are retained.
