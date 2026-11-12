# Bounded vendor entrypoint retirement

Changed only:
- `action_server/tasks_cdn.py`: retain the alternate Invoke task name/argument compatibility, but raise a clear owned-build instruction before network, subprocess, filesystem or optional external imports. The collection imports only Invoke. No alternate URL or downloader introduced.
- `.github/workflows/action_server_update_downloads.yml`: deleted the manually dispatchable legacy vendor AWS/S3 index publisher. No workflow was invoked; no credentials, bucket, deployment target or other workflow changed.
- `action_server/tests/build_system_tests/test_retired_vendor_entrypoints.py`: actual alternate collection + Invoke Program dispatch under import/open/context-command traps, for omitted/default/pinned versions; absent publisher and global no-vendor-index-target assertions; owned binary-release source build preserved.

Validation through pinned repository RCC → package Poetry gateways:
- New regression baseline: 4 failed as expected (module import guard / existing publisher); retained `entrypoints-red.log/xml`.
- Corrected regression: 4 passed, no skips; `entrypoints-green.log/xml`.
- Ruff format check, Ruff check, Isort check and configured namespace-package Mypy: passed on both changed Python files; `entrypoints-static.log`.
- Existing default frontend/template publisher retirement regressions: 3 passed, no skips; `existing-retirement.log/xml`.
- Scoped `git diff --check`: passed.

No full Runtime suite, installed candidate, remote CI or publishing action was run by this bounded lane. No PostgreSQL workload. No commits/pushes. Other integrator changes untouched. Source hashes and deleted-file identity: `entrypoints-source-hashes.json`.

## Exact canonical guide delta for integrator

Append to owned dependency/build guidance in `docs/skills/repository-operations.md`:

> Both the default frontend CDN task and the alternate `tasks_cdn` Invoke collection reject retired upstream-executable extraction before external work, including default and explicitly pinned versions. Keep regression coverage on the actual alternate collection/Program dispatch; fixing only the default task does not close alternate entrypoints. Template and downloads-index vendor publishers are retired separately. Assert the vendor role/bucket targets are absent across dispatchable workflows while retaining the owned source-build release workflow. Historical index generation code and compatibility names alone do not authorize publication or establish full dependency independence.

Documentation improvement:
- Canonical file proposed: `docs/skills/repository-operations.md` (root owns edit).
- Durable learning: cover alternate executable entrypoints and independent publisher workflows, preserve owned build route.
- Evidence: four red→green guarded-dispatch/publisher regressions and existing retirement regression results; exact source hashes.
- Stale/ambiguous guidance removed: earlier audit's open alternate-task/download-publisher rows are superseded by this bounded source correction; remaining dependency rows remain OPEN.
- Remaining uncertainty: full package/platform/installed release gates and mandatory Core logging/truststore/scaffold/optional endpoint/tooling independence are unchanged.

Upstream disposition: none. These are owned policy corrections; no external issue or repository mutation performed.
