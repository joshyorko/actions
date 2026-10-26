# Windows POSIX typing proposal

Source evidence: `/workspace/327-probes/windows-runtime390-207300bf.md`, `/workspace/327-probes/windows-scope-current-luna.md` (including its caller/helper review addendum), and parent-run current Windows mypy output `/tmp/327-platform-win32-type-red.log`. This read-only proposal covers all 34 current diagnostics across 7 files. It excludes the now-resolved `package_revision_compiler.py` diagnostic, which is no longer in the current run.

## Proposed patch

`windows-posix-typing-proposal.patch` contains typed, fail-closed capability helpers for every current missing POSIX member:

- `_datadir_restore.py`: `O_DIRECTORY`, `O_NOFOLLOW`, and `getuid`. The existing capture entry rejects when `O_NOFOLLOW` is unavailable and the module describes a private offline POSIX restore flow. The helper also refuses missing flags or `getuid` for direct internal calls; no Windows restore behavior is added.
- `foundry/provider_catalog.py`: `getuid`, `O_DIRECTORY`, `O_NOFOLLOW`, `O_NONBLOCK`, and `fchmod`. The acceptance scope audit identifies this private FD provider as Linux-only. Missing/non-callable APIs fail closed before the corresponding private operation; no permission fallback is introduced.
- `foundry/rcc_execution.py`: checked callable lookup for `fchmod` in source extraction. Source-boundary review ties this extraction to generated private-provider execution, while Robot execution also has explicit Linux x86_64 admission. This preserves extraction’s POSIX mode-setting requirement without asserting Windows mode semantics.
- `foundry/robot_execution.py`: `O_NOFOLLOW` and `O_NONBLOCK`; the constructor and execution entry require Linux x86_64 before instance execution, and Robot validation first constructs this guarded adapter.
- `_local_authorization.py`: `getuid`, `O_DIRECTORY`, and `O_NOFOLLOW`; `run_local_authorization` rejects non-POSIX before private ownership checks and blob opening.
- `_local_provider_setup.py`: `getuid`, `O_NOFOLLOW`, `O_NONBLOCK`, and `O_DIRECTORY`; `run_local_provider_setup` rejects non-POSIX before private operations.
- `run_outputs/task_host.py`: `getuid`, `O_NOFOLLOW`, and `O_NONBLOCK`; `load_task_policy` rejects non-POSIX before ownership checks and file opening.

The proposed helpers follow existing module patterns in `_community_expose_lifecycle.py` and `run_outputs/filesystem.py`: retrieve optional APIs with `getattr`, check integer flags or callability, then cast to the precise type. Missing flags never become zero. Runtime refusals and security semantics remain fail-closed. The patch is not applied to tracked files and was not tested or typechecked; `git apply --check` succeeds against the current checkout.

## Canonical guide delta proposed

Target: `docs/skills/repository-operations.md`, near its existing platform-boundary guidance.

Exact addition:

> For Windows mypy checks of explicitly POSIX-only operations, retain the runtime capability refusal at the operation boundary and express the API through a small `getattr` helper with a precise callable or integer type. Check that flags are integers and functions are callable; never substitute zero for an unavailable security flag. Do not use `type: ignore`, broad Windows permission fallbacks, or casts that bypass a missing-capability check. Before treating a typing diagnostic as typing-only, trace its callers and retain a fail-closed capability boundary for direct internal calls.

Evidence: the current 34-error Windows mypy output; the repository’s checked helper patterns; `_datadir_restore`’s explicit POSIX capture refusal; the Linux-only private provider acceptance boundary; `RobotExecution`’s Linux x86_64 constructor/execution checks; and the offline authorization, local provider setup, and task policy runtime guards. This delta is proposed only; no canonical guide was edited.

## Completion receipt

Upstream disposition: none. The observed issues are owned Actions POSIX call boundaries and Windows typing; no maintained upstream defect is indicated.

Documentation improvement:
- Canonical file changed or proposed: proposed exact `docs/skills/repository-operations.md` delta above.
- Durable learning captured: POSIX typing needs checked `getattr` access plus an operation-boundary refusal; security flags must fail closed instead of falling back to zero.
- Evidence: named report/logs and source-boundary evidence above.
- Stale or ambiguous guidance removed: none; this is a proposal.
- Remaining uncertainty: none for the typing boundary in the current 34 diagnostics. The patch does not claim Windows runtime support for any explicitly POSIX-only operation.
