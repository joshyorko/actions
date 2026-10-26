# Independent release qualification slice

Source examined: `da928b69e0558917c3e88af9297ddfd3bec818e8` (PR 328, freshly fetched).
This slice does not authorize release or qualify the full Actions Next product.

## Observed CI failures

Read-only commands: `gh run view RUN --repo joshyorko/actions --log-failed`.

- Runtime run **40194908636**: Linux reports 10 failed, 2817 passed,
  1226 skipped, 33 errors. Failures include stale a37 version expectation,
  historical migration schema comparisons, a sealed-read deadline, and compiler
  error-message expectations. Knowledge PostgreSQL cases require an owned fixture.
  Diagnose migration differences before deciding whether fixtures or production
  migrations are wrong; do not mask them with conditional schema creation.
- Toolkit run **40194908757**: Linux primary and N-1 smoke expect a18 while
  distribution metadata is a38. Windows fails during checkout with `Filename too
  long`, before RCC setup. Repository contains 30 paths longer than 220 characters.
- Core run **40194908626**: Linux/macOS docs checks report generated API changes
  for Canvas/Data/Knowledge. Windows fails checkout on the same evidence paths.
- Runtime macOS tests invoke a Linux-only filesystem output provider and tests
  requiring unavailable Docker. These failures are not native acceptance passes.
- Current PR check snapshot also has cancelled Linux/macOS wheel jobs and skipped
  publication. A green sdist or unauthenticated binary job does not prove wheel
  reproducibility, signatures, SBOM completeness, or installed recovery.

Integrator corrections proposed: shorten/archive deeply nested evidence while
preserving a digest/path manifest; regenerate Core API documentation through the
canonical toolchain; reconcile candidate-version assertions with authoritative
metadata; classify platform/service-required tests and run them in explicitly
provisioned required gates. Do not simply skip mandatory product acceptance.

## Issue 332 trust boundary

The workflow `runtime-release-publish.yml` defaults to read-only validation and
requires both actor and triggering actor to be Josh for publishing. Its writer
has `contents: write`, `actions: read`, and uses `PYPI_TOKEN_ACTIONS_RUNTIME`.
It checks out the workflow SHA without persisted credentials. Existing tests
cover same-repository/head identity, lookalike forks, source tree/workflow
binding, altered manifests/archives, and unauthorized callers.

Read-only `gh api repos/joshyorko/actions/environments/pypi` returned
`protection_rules: []` and `deployment_branch_policy: null` on 2026-10-25.
An environment name alone therefore provides no independent reviewer boundary.
A stolen sole-owner credential can satisfy actor checks; exact-byte checks do
not establish independent human review. Actual PyPI token scope and account
protections were not inspected. Propose an owner decision on independent approval
and/or short-lived publisher identity; neither is changed by this slice.

The dedicated tests add producer-download admission negatives for expired,
duplicate, absent, misnamed, zero/oversized metadata and failed/truncated archives.
They use the real publisher code and synthetic API/transport responses. No live
GitHub/PyPI writes, credentials, network policy, or release metadata are changed.

## Remaining acceptance boundaries

Only Linux x86_64 execution is available locally. CI defines Ubuntu 22.04,
Windows 2022 and macOS 15 Runtime cells; native Windows/macOS remain unqualified
locally. Public 1.0.4 floor checks remain separate from candidate acceptance.
Rebuilt wheels/native/images, SBOM/hash reproducibility, homelab operation without
mandatory GitHub/GHCR, coordinated SQLite/PostgreSQL/shared-service backup,
upgrade/downgrade, cache loss and active-job recovery require separate fresh
installed gates. Historical evidence is not reclassified as current acceptance.
Celld #326 remains NO-GO; no Dakota task is launched.

## Exact canonical documentation proposal (integrator-owned)

Append to `docs/skills/repository-operations.md`:

> Release qualification must inspect failed job logs at the candidate SHA before
> classifying infrastructure failures. A checkout path-length failure means no
> native toolchain or tests ran. Keep committed evidence paths short enough for
> the supported Windows checkout prefix, preserving archived bytes with a
> digest/path manifest. A green build or sdist does not qualify cancelled wheel
> jobs or skipped recovery gates. For publisher approval claims, inspect actual
> environment protection rules through the read-only API: `environment: pypi`
> and actor-name checks alone do not establish independent approval. Record
> credential-scope uncertainty without reading or changing credential values.

Evidence: source workflow plus the exact CI runs and environment API above.
Stale/ambiguous claim removed: environment naming or generic green checks imply
approval/platform qualification. Uncertainty: credentials, policy changes after
inspection, and platform results beyond the cited jobs.

Initial upstream disposition: none. The subsequent cache diagnostic candidate
and draft-only disposition are recorded in [cache-followup.md](cache-followup.md).
Rollback: remove the dedicated test and this evidence directory; no production
state, migrations, dependencies or release controls change.

## Executed slice

All commands used Josh RCC 18.19.3 (SHA256
`7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428`) and
its prepared Poetry 2.1.1. Doctor/Bootstrap used task-local RCC/Poetry caches;
the initial wheel commands omitted cache overrides, corrected in the follow-up.
Initial disk budget
was 30 GiB free; 25 GiB remained after bootstrap/build. No optional Python
Robocorp tracing was enabled for Runtime tests; stdout and JUnit were retained.

- Root: `./devutils/bin/develop.sh Doctor`, then `Bootstrap`, then `ToolkitTest`:
  PASS; ToolkitTest 190 passed.
- In `devutils`: `poetry run pytest tests/test_release_qualification_327.py tests/test_runtime_release_button.py tests/test_runtime_release_backup.py -q --junitxml=.../security.xml`:
  **78 passed** (8 new admission negatives).
- In `devutils`: `poetry run pytest tests -q --junitxml=.../devutils-full.xml`:
  **275 passed, 1 failed**. The full suite independently reproduces the stale
  a18/a38 release assertion; no version metadata or existing test was changed.
- In `action_server`: `poetry run pytest -p no:robocorp_log_pytest tests/contract_tests/test_release_publisher_adversarial.py tests/action_server_tests/test_datadir_restore.py -q --junitxml=.../restore-source.xml`:
  **40 passed**. Full Runtime suite not rerun in this bounded slice; current CI
  failures remain open above.
- In `action_server`: `poetry build -f wheel -o /workspace/lane-d/wheels`, then
  `poetry run python scripts/qualify_installed_restore_327.py --wheel /workspace/lane-d/wheels/actions_runtime-1.1.0a38-cp312-cp312-linux_x86_64.whl --evidence /workspace/lane-d/installed-restore`:
  **PASS**, fresh offline no-dependency install, actual installed helper bytes,
  SQLite relocation, unchanged source database, changed-attachment rejection.
  Wheel SHA256: `34f5b7c1db29d4def4ba84214d225f6b82d037fa39e3b819eab6fe1ff15898ce`.
  This is not full installed Runtime dependency/CLI acceptance. Initial wrong
  universal-wheel filename failed before install; its receipt is preserved.
- Changed Python files: package-local Ruff check/format and Isort check passed;
  `git diff --check` passed. No new dependencies.

Integrate only the two dedicated Python files and this evidence directory.
Cherry-pick the lane commit; do not copy task caches, virtualenvs or wheels.
The script requires a new absent evidence directory on each invocation and
retains failed subprocess output. Rebuild the wheel after integration and rerun
against the combined source; this wheel does not qualify later commits.

Follow-on reproducibility attempt: a second `poetry build -f wheel -o
/workspace/lane-d/wheels-repeat` failed with `All attempts to connect to pypi.org
failed`, before producing a wheel. The original successful wheel remains intact;
byte-for-byte build reproducibility was initially **unverified**, not passed. Failure stdout
is retained in `wheel-repeat.log.gz`. No host dependency fallback or network
policy change was attempted.

Resolved follow-up: [cache-followup.md](cache-followup.md) establishes the wrapped
read-only-cache error, successful supported cache override and matching repeated
wheel hashes. Wider cross-host/platform reproducibility remains unverified.
