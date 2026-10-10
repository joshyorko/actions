# Independent PR257 release review

Verdict: ACCEPT the bounded normal-workflow checksum source change for root integration review. This is not publication admission. No newly introduced release/security correctness blocker was demonstrated. Full lint is still FAIL on the inherited duplicate definitions; real native bytes, assembled candidate gates and hosted checks remain required.

Reviewed exact head `90c37991942aad12b1008bdb95ab8ee95e32d05c`, first change `0169a17eaae2edfbc7b44d802c41d42a23dd9e09`, base `ab9b1aaa95aacc3b40c23e4fcd4749c79e3fae47`. Binary Git diff SHA-256: `d705765afcf11669e16b8fad408593c3ac58ddb5e0f45fcf8ec6af9bfc61ea57`. Review ran only in detached `/workspace/work/community-resume/sol-native-review`. No tracked source changes, commit, push, integration merge, tag, release, tap change or process signals were made. The untracked `work/sol-pr257` directory holds only review scripts, small synthetic fixtures/results and logs. Root alone integrates.

## Changed behavior and trust boundary

All five changed files were inspected: authoritative workflow generator, generated native binary workflow, both modified test modules, and canonical guide. Supporting inventory, tag/version/community guards, platform matrix and recovery publisher were followed without an unrelated repository audit.

The generated inventory at `_gen_workflows.py:976` checks each exact expected leaf with `test -f`, rejects a symlink leaf, and requires exactly one immediate entry in each platform directory. The manifest hashes those same three fixed paths; there is no hashing glob. Its names match the three explicit upload `asset_name` inputs exactly, including Windows `.exe`. The fourth upload names and reads the generated `<tag>-sha256.txt`; all four uploads remain pinned to the same release action SHA and set `overwrite: false`. No new permissions, credentials or external destination were added.

Downloads are individually bound to this workflow run's named platform artifacts. The existing `needs: build` waits for all Linux/Windows/macOS rows, whose guards compare the peeled triggering ref commit to the event commit and require community ancestry. Version checks remain. Ubuntu x86_64, Windows x64 and macOS arm64 names/matrix are unchanged. The checksum hashes available artifact bytes; it does not itself establish architecture, executable behavior, signing, source authenticity or a cryptographic provenance attestation. The controlled release pipeline and separate exact-source/artifact receipts supply those claims.

The manifest/YAML contract was independently verified, but the uploader action's remote implementation and GitHub API collision behavior were not executed or independently audited in this lane. Retaining explicit no-overwrite inputs establishes configured intent, not an observed upload collision test. These workflows already require authority to alter release tags/source; no archive-only or unprivileged exploit was demonstrated.

## Independent verification

Commands entered through `source /workspace/actions-cloud/activate.sh` and pinned RCC18.19.3 `task script --no-build --robot developer/toolkit.yaml`, reusing the cached toolkit and `/workspace/actions/devutils/.venv/bin/python`. No Bootstrap, dependency install, native build or new package environment was created. Python source paths targeted this review worktree.

- Both affected release test modules: **93 passed in 6.96s**. Durable `focused.log` SHA-256 `cdc96958f5fb6e5ef9d1fd52125648265ee90fbd6a2d0ecf7acaee3efdfdc238`. This is independent focused evidence; the writer's reported full 126 is not independently certified by this receipt.
- Reconstructed `ActionServerBinaryRelease.full` equals parsed YAML; rendering it without writing source produces byte-identical checked-in YAML.
- Small fixture bytes hashed by the actual extracted inventory script verify with `sha256sum -c` after copying them to the advertised download names. Exactly three manifest lines, exact names and digest/content binding passed.
- Leaf symlink, parent-directory symlink, extra hidden entry, extra directory, missing file and directory-as-leaf each returned nonzero before producing the manifest. This is deterministic Linux shell/file evidence, not concurrent namespace race proof.
- Selected Isort/Black-profile check: PASS for both head and base. Git range `diff --check`: PASS.
- Selected Ruff check: FAIL, four F811 duplicate definitions already present at base: `run_shell_step`, `test_runtime_publisher_accepts_platform_tag_order_and_rejects_duplicate_slots`, `test_runtime_publisher_rejects_foreign_platform_or_build_tag`, and `test_generated_runtime_inventory_uses_exact_tag_set_verifier`. Head/base AST enumeration and Ruff output preserve the same names; line shifts come from the new test. Earlier definitions are overwritten during import, so test counts do not prove those earlier bodies ran. PR257 did not create this defect; root must reconcile it before a full lint claim.
- Selected Ruff format check: FAIL on `_gen_workflows.py`; head and base formatter diffs contain the same pre-existing formatting hunks, outside the changed manifest/upload blocks. Both new/modified test files are formatted. No waiver or false PASS is recorded.
- `developer/toolkit.py:164` explicitly excludes devutils from the package typecheck gate because no configured devutils typecheck exists. Status is **NOT_APPLICABLE**, not a successful invented mypy command.

Machine receipts: `probe-results.json` SHA-256 `fc11c20e6376d99eabf14640629bccbeb3fe2a95b74386b0fd9eba412c1b79de`; `baseline-static-results.json` SHA-256 `e0a6b0fef1b63c177662488843c032d990e722feaeeb46db956c846b9180e23b`. They record exact command argv/status and individual log hashes. RCC wrapper SUCCESS is not promoted to static PASS: the review runner deliberately records each diagnostic failure and continues.

## Recovery and publication limits

The unchanged recovery workflow's `_gen_workflows.py:1575` normalization constructs exactly THREE named binary files; its publisher at line1599 hashes that set, rejects unexpected existing assets, and verifies exactly those three names/digests before publishing. It keeps SHA-256 text in release notes, not a downloadable fourth checksum asset. An existing draft containing the new fourth checksum asset therefore fails its exact-set guard. An already public normal release also fails its draft-only admission. This protects existing bytes but is not a compatible four-asset recovery path.

The normal upload sequence is not atomic: a failure can leave a created release or some uploaded binaries; a rerun hits the first same-name asset and fails without replacing it. This change does not provide automatic checksum backfill or resume. Root should preserve the no-overwrite boundary and explicitly choose a separately reviewed digest-bound recovery plan if a real partial release occurs. Do not silently delete/replace assets or weaken the recovery exact-set guard.

No actual frozen/wrapper binary, signed/notarized artifact, final candidate native acceptance, GitHub upload, clean download of published assets, Homebrew install or assembled package/hosted gate was run here. Publication requires those exact bytes and their existing release gates. Nothing here closes full #134 or any other product contract.

## Documentation improvement proposal

Canonical file proposed: `docs/skills/repository-operations.md`, replace the new checksum paragraph's opening with this exact durable clarification (retain the generator/tap guidance after it):

> The normal tagged binary workflow generates and uploads `<tag>-sha256.txt` after the three binaries, with `overwrite: false`. Its sorted entries name the three exact download assets. Download all three files alongside the manifest to run `sha256sum -c <tag>-sha256.txt`; a full-manifest check requires every listed file. The manifest establishes content equality, not publisher signing or source provenance. The current recovery workflow still admits exactly three binary assets and records their hashes in release notes; it does not publish or resume the fourth checksum asset. Normal uploads are not atomic, and rerunning after a partial upload fails on existing names. Preserve existing bytes and require a separately reviewed, digest-bound recovery plan rather than deleting assets or weakening the exact-set checks.

Evidence: generator/upload/recovery source locations above, byte-identical generator/YAML reconstruction, actual three-name synthetic checksum verification and rejection probes. This removes ambiguity that a checksum file authenticates source or that existing recovery covers all four assets. The retained Homebrew owner/platform/manual-input guidance matches the current tap README inspected and saved at exact `ff879e20b92cdae2e8e921a3c677097544b3b91a`; the README is documentation evidence only, not an actual tap update/install proof. No API/package/schema implementation or future behavior is presented as implemented. Root records proposal disposition and performs any canonical edit.

Upstream disposition: **none**. Findings are inherited local Actions static/coverage defects and a local recovery contract boundary, not a demonstrated defect in RCC, the release action, GitHub or the Homebrew tap. No upstream issue, PR, comment, label, assignment or publication was created; no speculative upstream defect requires deduplication or reporting. Revisit only if actual immutable artifact/API behavior violates the supported owner contract.
