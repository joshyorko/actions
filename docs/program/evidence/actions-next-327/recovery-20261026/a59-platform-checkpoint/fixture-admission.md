# POSIX operator fixture admission probe

## Outcome

Changed only these test files in `actions/`:

- `action_server/tests/action_server_tests/test_datadir_restore.py`
- `action_server/tests/action_server_tests/test_local_authorization.py`
- `action_server/tests/action_server_tests/test_operator_platform_refusal_327.py` (new)

The restore `snapshot` helper now skips before creating its source tree unless the host is POSIX and has `O_NOFOLLOW`. The local authorization fixture skips before creating its datadir unless `os.name == "posix"`. There is no module-wide skip. The explicit acknowledgement/schema checks no longer need POSIX fixture setup and remain enabled. The local request schema rejection test now builds a minimal model directly.

The new all-platform regressions call the actual APIs with a module-local OS facade. Manifest capture sees a non-POSIX view without `O_NOFOLLOW`; local authorization sees `name="nt"`. Both are given missing paths, so the expected refusal proves the platform guard runs before the API inspects owned state. The facade leaves the process-global `os` and `pathlib` untouched.

All existing Linux success and negative assertions remain enabled, including refusing to restore onto the source itself. On unsupported platforms the expected collection has 43 fixture-dependent skips: 24 restore cases using `snapshot` and 19 local authorization cases using `local`. The other 13 cases remain enabled (one portable restore acknowledgement check, ten local authorization/schema/deployment/help cases that do not use `local`, and two platform refusal regressions). The skip reasons identify the respective POSIX requirement. This is platform refusal coverage, not a POSIX restore or authorization PASS.

## Evidence

- Baseline before editing: not run; the regression-path report and file inspection identified the fixture admission point before changes.
- RCC focused pytest through the activated `/workspace/actions-cloud/activate.sh` environment: `56 passed in 9.45s` on Linux; zero skips. This includes 25 restore cases, 29 local authorization cases, and two new refusal tests.
- Collection-only check: `56 tests collected`; it confirms 24 restore cases use `snapshot` and 19 local authorization cases use `local`.
- Configured formatter/import checks: `ruff format --check` reported `3 files already formatted`; `isort --check-only` passed.
- `ruff check` and `git diff --check` passed for the requested files.
- The first RCC attempt used the wrong `tasks` section for developer mode; after correcting the temporary probe robot to define both `tasks` and `devTasks`, the focused run completed. One initial test run exposed the schema test's old fixture reference after removing its fixture dependency; that test was corrected and the final run passed.
- No Windows execution was available in this lane. The all-platform refusal behavior is exercised on Linux using the module-local facades; hosted Windows behavior remains unverified.

## Canonical documentation proposal

Propose adding the following to `docs/skills/work-items.md` immediately after its offline datadir restore guidance (around the current paragraph beginning “Relocating a coordinated offline local datadir…”):

> The datadir capture and local authorization operator APIs rely on POSIX filesystem contracts. `capture_offline_manifest` requires explicit offline acknowledgement and `os.O_NOFOLLOW`; `run_local_authorization` refuses a non-POSIX `os.name` before checking external database configuration or reading owned paths. Successful restore also checks the target parent's POSIX owner and private mode. Keep POSIX success fixtures gated before creating their test state, while leaving portable acknowledgement/schema checks enabled. Test the actual capture and authorization refusal guards on every host with module-local OS facades and missing paths; do not patch global `os.name`, which also affects `pathlib`. These refusal tests establish early rejection only, not restore or authorization success on unsupported platforms.

Evidence: current guards in `action_server/src/actions/server/_datadir_restore.py` and `action_server/src/actions/server/_local_authorization.py`, plus the focused 56-test Linux run and the two new refusal tests. This is a proposal for the integration agent; no canonical guide was edited in this isolated fixture lane.

Upstream disposition: none. No upstream defect was investigated or reported, and no upstream issue target was authorized.

## Receipt

Documentation improvement:
- Canonical file changed or proposed: proposed delta to `docs/skills/work-items.md`; canonical file not changed in this isolated lane.
- Durable learning captured: POSIX-only success fixture admission belongs before datadir creation; API refusal can be tested on all platforms without global OS monkeypatching; portable schema/acknowledgement checks remain runnable.
- Evidence: source guard inspection, collected test IDs, focused RCC run (`56 passed`), and configured formatter/import checks.
- Stale or ambiguous guidance removed: none; proposed wording narrows the existing POSIX-only restore guidance.
- Remaining uncertainty: native Windows execution of these tests and successful POSIX operator flows on other supported POSIX hosts were not run.
