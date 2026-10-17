# Runtime Release Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover the exact reviewed release bundle after original artifact loss, with two independent verified backups required before publication.

**Architecture:** Separate the original preparation identity from the transport run. Keep production workflow files unchanged; store independent copies on a dedicated backup branch and admit only a reviewed registry of immutable backup identities. Share manifest/source/content verification between the guarded publisher and a nonpublishing archive command.

**Tech Stack:** Existing Python3.12, GitHub Actions/artifacts, pinned RCC18.19.3/Poetry, existing packaging/twine verifiers; no new dependencies or credentials.

**Spec:** `docs/superpowers/specs/2026-10-16-runtime-release-recovery.md`

## Global Constraints

- Never rerun/delete owner preparation38951733318 or artifact12069321636.
- Preserve source d222f94edca26953c1506ab258adc458ded17c56 and original manifest/ZIP digests.
- Do not alter `.github/workflows` in the repair/default source; the dedicated backup workflow stays on its separate branch.
- No final tag/package/native release/template/deployment publication, secret or security-setting change.
- Preserve every existing owner, original-attempt, source/workflow, digest, bounds and remote collision/ownership gate.

## Review Focus

- A valid backup carrier must not become a different preparation/release owner.
- A registry entry must not admit another manifest/source/version or fork/workflow.
- Missing/expired/deleted independent copies must block publication, while one valid raw archive may reseed another copy read-only.
- ZIP envelope and every original member must remain exact across restore/reseed.
- Destructive tests must reject protected owner IDs and never repeat an uncertain write.

### Task1: Transport identity and recovery policy

**Files:** modify `action_server/scripts/runtime_release_button.py`; create `action_server/release-bundle-backups.json`; extend `devutils/tests/test_runtime_release_button.py` and add `devutils/tests/test_runtime_release_backup.py`.

**Interfaces:** `verify_bundle(args, *, require_backups=True) -> dict` owns existing original-manifest/source/content checks. `recovery_record(root, digest, manifest) -> dict` binds reviewed registry policy. `verify_backup(record, backup, *, archive_only=False) -> dict` owns canonical backup run/artifact metadata checks. `verify(args)` retains the current community publication controller guard.

- [x] Add regression tests for a different carrier with unchanged original preparation, missing/wrong registry, fork/run/workflow mismatch and original-attempt failure; observe red.
- [x] Implement exact identity resolution and two independent healthy-backup requirements without changing release ownership or workflows.
- [x] Run focused tests and existing ownership/partial-publication tests; add source fixtures for new policy checks without weakening assertions.
- [x] Update canonical operations guidance with implemented and tested guarantees; push a reviewable checkpoint.

### Task2: Nonpublishing archive and independent copies

**Files:** create `action_server/scripts/runtime_release_backup.py`; extend `devutils/tests/test_runtime_release_backup.py`; add the branch-only `.github/workflows/runtime-release-backup.yml` and a request JSON on `backup/runtime-release-bundles`.

**Interfaces:** archive command consumes original/registered carrier run ID plus reviewed source/version/manifest and a fresh output directory; emits unchanged `bundle/`, exact `archive/original-bundle.zip` and a bounded JSON receipt. It may read APIs and local files but never publish or mutate remote objects.

- [x] Add tests proving exact ZIP/member preservation, safe extraction, no remote writes, refusing rerun/unsafe controller, and reseeding from a single surviving registered raw archive; observe red.
- [x] Implement archive staging with original ZIP verification before extraction and full existing bundle verification afterward.
- [x] Run complete Devutils tests, configured lint/isort/format and `git diff --check` through RCC/Poetry.
- [x] Push source checkpoint and dedicated backup workflow. Create two independent owner backups without touching the original run; independently verify downloaded output and record their immutable metadata.

### Task3: Destructive rehearsal and review evidence

**Files:** branch-only recovery qualification helper/report; canonical operations guide and sanitized evidence; final registry contains owner backups only.

- [x] Create a new disposable canonical preparation, archive it twice, and record both registered identities in the qualification branch.
- [x] Deliberately rerun only that disposable preparation; verify original artifact loss and unchanged original-attempt success.
- [x] Recover the original exact ZIP/manifest/member bytes through each backup; reject wrong digests/identities and insufficient copies; reseed from a surviving raw archive.
- [x] Recheck protected owner preparation/artifact unchanged. Run final exact-head hosted checks and independent review of source/qualification evidence.
- [x] Push final reviewable repair PR and qualified evidence. Report actual passed/failed/unrun gates and the exact merge/activation step still requiring approval; never publish.
