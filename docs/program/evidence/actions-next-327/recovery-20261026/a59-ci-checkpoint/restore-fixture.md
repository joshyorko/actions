# POSIX restore fixture follow-up

## Change and verification

Updated only `action_server/tests/action_server_tests/test_datadir_restore.py` in the repository. The existing `require_posix_manifest_capability()` admission now serves both `snapshot()` and `test_restored_attachment_passes_unchanged_sdk_containment`. The direct SDK relocation test calls it before making `source/`, constructing the adapter, or creating SQLite/attachment state. All original SDK containment, source readback, restored readback, and manifest equality assertions remain intact.

- RCC focused restore plus refusal modules: `27 passed in 2.75s` (25 restore cases, two all-platform refusal assertions).
- `ruff format --check`: one file already formatted.
- `isort --check-only`: passed.
- `git diff --check` for the changed test file: passed.
- No Windows execution was available. The test reports the POSIX-only feature as skipped there; unsupported-platform refusal coverage does not establish a restore PASS.

Across the focused 56-test set, fixture-dependent Windows skips remain 43 total: 24 restore cases (23 through `snapshot()` and this direct SDK case) plus 19 local authorization cases. Thirteen portable checks stay enabled. This clarifies the prior note’s attribution: the restore count is still 24, with one case using direct setup instead of `snapshot()`.

## Documentation consolidation proposal

Consolidate the prior proposal in `posix-fixture-admission-327.md` into `docs/skills/work-items.md` after the offline datadir restore guidance. Preserve this exact verified rule:

> Gate every successful POSIX-only restore setup before creating datadir state, including tests that call `capture_offline_manifest` directly through an SDK relocation path instead of the shared snapshot helper. Keep the direct SDK containment/readback assertions on POSIX, and keep portable acknowledgement/schema checks and actual API refusal tests enabled on every platform. These skips represent an unsupported platform feature, not successful restore coverage.

Evidence: the shared helper and early call in `test_restored_attachment_passes_unchanged_sdk_containment`, plus RCC focused result `27 passed`; focused collection remains 56 tests total, of which 24 restore cases require POSIX admission.

Upstream disposition: none. No upstream defect was found or reported.

Documentation improvement:
- Canonical file changed or proposed: proposed consolidation to `docs/skills/work-items.md`; no canonical file changed in this lane.
- Durable learning captured: direct SDK relocation setup also needs the same pre-state POSIX capability admission as helper-backed restore tests.
- Evidence: source/test inspection, focused RCC run, Ruff formatter, isort, and diff check.
- Stale or ambiguous guidance removed: proposes correcting the earlier probe’s attribution of all 24 cases to `snapshot()`; one case uses direct setup.
- Remaining uncertainty: native Windows execution and successful POSIX behavior on other POSIX hosts remain unverified.
