# PR256 `a1904783` packaged-browser gate diagnosis

Reviewed at 2026-10-09 23:22 UTC; read-only. No rerun, source edit, build, install, or artifact download.

## Exact workflow identity and result

- Run: `38003443132`, event `pull_request`, workflow `Action Server Build (Unauthenticated)`.
- Checkout/head: `a1904783c0ec1950beab59d5fb7c9d76fb90a1e8` on `devsy/workitems-consumer-acceptance-20261009`.
- Ubuntu job `114066685828`: FAIL at `Verify packaged Work Items browser acceptance (frozen)`.
- Windows job `114066685514`: FAIL at the same step and same assertion.
- macOS job `114066685889`: PASS; both `Verify packaged Work Items browser acceptance (frozen)` and `(Go wrapper)` were SKIPPED by workflow conditions.
- Both failing jobs completed all earlier native build, component-manifest recording, Work Items consumer checks, process-ownership checks, and broad frozen/Go browser and large-history checks. The failure occurs before the newly scoped Work Items browser scenario proceeds: `packaged_runtime_identity()` rejects the frozen package-tree digest.

## Exact failure and comparison

Both Linux and Windows logs end with:

`AssertionError: manifest field frozen_package_tree_sha256 does not match build input`

The failing regression is `test_packaged_work_items_ui_create_keyboard_narrow_and_storage_recovery`. The prior 5d9 checkpoint failed earlier because the four component digest fields were absent. The a190 writer and harness now emit and require those fields, but the exact hosted run exposes a different problem: the recorded frozen-tree digest disagrees with the tree observed at the acceptance test. This is not evidence of a browser interaction regression; the browser test fails its provenance preflight before browser acceptance.

The writer and consumer both hash relative path, permission mode, symlink target, directory/file kind and file bytes. The consumer uses `stat.S_IMODE` while the writer masks `st_mode & 0o777`; those expressions differ if special permission bits are present. I cannot establish from hosted logs whether that accounts for either mismatch. Since the same frozen-tree field mismatches on Linux and Windows while macOS does not run this test, the exact changed path/cause remains unverified. Do not rehash after the fact or relax the assertion without identifying the path-level delta.

## Action for the existing owner

Preserve the current source manifest and add a sanitized pre/post path inventory around the operations between “Record native binary and embedded component provenance” and this acceptance test. Compare relative paths, entry kind, mode, symlink target, and content digest; first identify whether runtime smoke tests mutate the frozen tree or whether manifest/test mode normalization differs. Then bind only immutable build outputs or explicitly separate any runtime-mutated files under a documented, regression-tested policy. Keep the exact failing run and both platform failures as historical evidence.

## Documentation proposal and limits

Durable canonical guide delta for `docs/skills/work-items.md`: “If the recorded frozen package-tree digest differs at native acceptance, preserve the pre/post path inventory and identify the changed entries before adjusting the digest boundary; do not overwrite the build manifest after runtime tests. Distinguish immutable build inputs from explicitly documented runtime-generated files and retain a regression for the discovered mutation.” The current failure provides evidence for this diagnostic rule, but not for a particular mutation cause.

No upstream issue proposed: this is a local workflow/harness provenance-boundary failure. Publication/upload did not run on Linux/Windows; macOS uploaded artifacts despite skipping the Work Items browser-specific gate. This run does not establish full cross-platform packaged Work Items browser acceptance.
