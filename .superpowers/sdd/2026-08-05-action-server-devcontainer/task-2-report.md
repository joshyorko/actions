# Task 2 report: Poetry Work Items release gate

## Outcome

Added strict, argument-free Dev Container bootstrap and Work Items verification scripts. Work Items now locks the Poetry dev toolchain, including Ruff, and the static contract verifies that Poetry—not `uv sync`—owns the release sequence.

## TDD evidence

### RED

Before either script or `work-items/poetry.lock` existed:

```text
python -m unittest discover -s .devcontainer/tests -p 'test_*.py' -v
```

Result: failed with `missing .../.devcontainer/bin/bootstrap`.

### GREEN

After implementing the scripts and generating the lockfile:

```text
python -m unittest discover -s .devcontainer/tests -p 'test_*.py' -v
bash -n .devcontainer/bin/bootstrap .devcontainer/bin/verify-work-items
git diff --check
```

Result: two static tests passed; both shell scripts parsed; the diff check passed.

## In-image evidence

The Task 1 image generated `work-items/poetry.lock` with Poetry 2.1.1 after adding `ruff = "^0.12.0"`. The first lock command failed after fetching PyPI metadata because the image's inherited Poetry cache was not writable by `vscode`:

```text
docker run --rm --add-host pypi.org:151.101.0.223 --user vscode -v "$PWD:/workspaces/actions" -w /workspaces/actions/work-items actions-devcontainer:task-1 poetry lock
```

Error: `Connection broken: PermissionError(13, 'Permission denied')` while Poetry retried `/simple/ruff/`.

Using an explicitly writable cache completed lock generation:

```text
docker run --rm --add-host pypi.org:151.101.0.223 --user vscode -e POETRY_CACHE_DIR=/tmp/pypoetry -v "$PWD:/workspaces/actions" -w /workspaces/actions/work-items actions-devcontainer:task-1 poetry lock
```

The in-image bootstrap then completed the Work Items and Action Server Poetry installs. `poetry check --lock` passed in the image, with Poetry's existing PEP 621 migration warnings.

`verify-work-items` returns nonzero at its first failed gate as designed. Its Ruff command found four existing `UP038` findings in Work Items (`_docdb.py`, `_redis.py`, and two locations in `_context.py`) and therefore did not continue to tests or wheel build. This task does not alter unrelated Work Items source or weaken the configured Ruff command.

## Self-review

- Both scripts are executable, strict-shell, resolve the repository from `BASH_SOURCE`, reject arguments, and do not use `uv sync`.
- Bootstrap prints Python, uv, and Poetry versions and installs Work Items before Action Server through a package-reporting helper.
- Verification checks the lock, Ruff, tests, wheel build, isolated wheel aliases/version, then the repository diff; temporary directories are removed by an EXIT trap.
- Canonical guides document headless build, bootstrap, verification, cache recovery, rebuild, and Poetry authority. No smoke script or Task 3 documentation was added.

## Documentation improvement receipt

Documentation improvement:
- Canonical file changed or proposed: `docs/skills/repository-operations.md`; `docs/skills/work-items.md`.
- Durable learning captured: Docker-available release evidence uses the repository Dev Container and Poetry; uv only bootstraps/caches Poetry and does not replace lockfile resolution. The named cache volumes are the scoped recovery target.
- Evidence: the Task 1 image completed bootstrap and `poetry check --lock`; the static contract verifies the scripts name the Poetry commands and reject `uv sync`.
- Stale or ambiguous guidance removed: replaced the implication that host-tool fallback can be terminal when Docker is available; identified it as diagnostic-only.
- Remaining uncertainty: the Poetry cache supplied by the Task 1 image is not writable by `vscode` without the Dev Container's named cache volume (or an explicit writable `POETRY_CACHE_DIR`). The release script currently stops at four pre-existing Ruff `UP038` findings.
