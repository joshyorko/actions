# Confined source staging cleanup follow-up

Verdict: independent review APPROVED the bounded staging change at `1531460594941e64c8025e220b1409e2401f77b8`, tree `750ef174ae7598815363c39179ba86cf67094f92`. A guide-only child records the failure-test conditions at `2194668700042fdd25a942c0387bda683f1bbea9`, tree `5e4a48a10b2d9a346c0355f0a9f2a565d134a22b`. The approved implementation commit is preserved unchanged as the child’s parent. The branch ancestry is `5e3b61125bc17aafe6d7ee92db6b9f14a34b82fa` → `b5347094e9b08eb350e3cd205fbe618073f816e5` → `1531460594941e64c8025e220b1409e2401f77b8` → `2194668700042fdd25a942c0387bda683f1bbea9`.

The implementation records a directory path as unresolved immediately after successful `mkdir`, captures a no-follow identity before opening the directory, and checks both the opened descriptor and current name against that identity. Failure cleanup removes only identity-matched entries. If identity cannot be captured or cleanup cannot verify ownership, the original exception is re-raised with an explicit note naming the unresolved path; cleanup does not blindly delete that entry. Tests cover injected failures after `mkdir` at identity observation, directory open, and `fstat`, including nested ancestors and descriptor ownership.

The destination must be empty, owner-private, and exclusively writable by the caller for the duration of staging. `mkdir` and the following identity observation are not atomic. Hostile concurrent writers sharing the caller’s effective UID are outside this boundary; the code does not claim race-proof binding against them. This remains a proposed staged inventory over copied and re-read bytes, not source authorization, complete selection, global atomic snapshot, compiler proof, Package Revision, or Runtime Plan.

## Verification

The baseline regression was reproduced before the fix. With nested `a/b/input`, injected post-`mkdir` open failure and injected post-open `fstat` failure each failed the cleanup assertion and left `staging/a` with the nested path beneath it. The repaired tests confirm those errors clean all observed created directories. The identity-observation failure test confirms the original exception survives, names `a/b` in the unresolved-cleanup note, and leaves the unverified path in place. All cases confirm borrowed source-root and destination descriptors remain valid and helper-opened directory descriptors close.

Author test command, from the source worktree, using the prepared interpreter and existing deployment-value dependencies:

```sh
PYTHONPATH=action_server/src:/tmp/work/deployment-values-deps/site-packages /tmp/work/multipackage-runtime-acceptance/venv-primary/bin/python -m pytest -p no:robocorp_log_pytest -p no:cacheprovider --basetemp=/dev/shm/actions-source-staging-20261010/pytest-final-rerun --confcutdir=action_server/tests/contract_tests action_server/tests/contract_tests/test_source_manifest.py action_server/tests/contract_tests/test_source_read.py action_server/tests/contract_tests/test_source_staging.py -q
```

Result: 102 passed. The 99 pre-existing focused tests remain; three parametrized nested-directory failure cases were added.

Configured static checks passed:

```sh
/workspace/actions/action_server/.venv/bin/ruff check --no-cache action_server/src/actions/server/deployments/source_staging.py action_server/tests/contract_tests/test_source_staging.py
/workspace/actions/action_server/.venv/bin/ruff format --check action_server/src/actions/server/deployments/source_staging.py action_server/tests/contract_tests/test_source_staging.py
/workspace/actions/action_server/.venv/bin/isort --check-only action_server/src/actions/server/deployments/source_staging.py action_server/tests/contract_tests/test_source_staging.py
```

Mypy passed from the `action_server` cwd:

```sh
MYPYPATH=src:/tmp/work/deployment-values-deps/site-packages /workspace/actions/action_server/.venv/bin/mypy --explicit-package-bases --config-file pyproject.toml --cache-dir /dev/shm/actions-source-staging-20261010/mypycache src/actions/server/deployments/source_staging.py tests/contract_tests/test_source_staging.py
```

`git diff --check` passed. Independent reviewer approval at exact implementation commit/tree included this focused test command, run from the source worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/work/actions-worktrees/source-confined-staging-20261010/action_server/src:/tmp/work/deployment-values-deps/site-packages /tmp/work/multipackage-runtime-acceptance/venv-primary/bin/python -m pytest -p no:cacheprovider -p no:robocorp_log_pytest action_server/tests/contract_tests/test_source_staging.py -q
```

Result: 20 passed. The reviewer also reported a separate 25-case copy-failure/FD probe with zero leaked descriptors; its command/artifact path was not supplied. These independent results are distinct from the owner's 102-test run above.

RCC consumer/import proof: NOT RUN. No unrelated RCC Home was used, no package installs/downloads were performed, and no GitHub or registry writes occurred.

## Export and documentation

The reviewed chain was exported from integration base `5e3b61125bc17aafe6d7ee92db6b9f14a34b82fa` with:

```sh
python /workspace/work/export_git_checkpoint.py /workspace/actions 5e3b61125bc17aafe6d7ee92db6b9f14a34b82fa 2194668700042fdd25a942c0387bda683f1bbea9 /workspace/work/source-staging-export
```

The exporter reported final head `2194668700042fdd25a942c0387bda683f1bbea9`, tree `5e4a48a10b2d9a346c0355f0a9f2a565d134a22b`, base tree `ede73323c44225ec4d7187aac1f261be0cd21375`, three changed files, and 14 content chunks. Export metadata is `/workspace/work/source-staging-export/metadata.json`.

Canonical guide: `docs/skills/repository-operations.md`, source staging paragraph. The guide records exclusive-writer assumptions, unresolved cleanup behavior, and the exact injected-failure cases. This is a bounded Actions implementation, not an upstream defect; upstream disposition: none.
