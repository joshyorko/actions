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

## Fix round 1/5

The earlier Task 2 outcome was incomplete: the release gate stopped at four Ruff `UP038` violations and did not prove tests, wheel imports, or the final diff check. This correction uses `bytes | bytearray` and `str | os.PathLike` in exactly those four checks, preserving the tested attachment behavior. The underscore public alias now explicitly exports the canonical `0.2.4` version so the clean-wheel check can compare all public aliases.

### RED and GREEN evidence

The extended static contract initially failed because cache variables/directories, `poetry sync`, and the Action Server `actions-work-items 0.2.4` lock entry were absent. After the Dockerfile, bootstrap, and Poetry 2.1.1 lock refresh, it passed. The new underscore-alias version regression failed with `AttributeError: module 'actions_work_items' has no attribute '__version__'`, then passed after exporting the canonical version.

The SQLite path/bytes attachment characterization passed before and after the four mechanical lint changes. Poetry 2.1.1 refreshed `action_server/poetry.lock` from the stale `actions-work-items 0.2.0` entry to `0.2.4`; all other resolved package versions remained unchanged, while the lock gained Poetry 2.1 group/marker metadata.

### Passing in-image release evidence

```text
docker build --pull=false -f .devcontainer/Dockerfile -t actions-devcontainer:task-2 .
docker run --rm --user vscode -v "$PWD:/workspaces/actions" -v actions-uv-cache:/home/vscode/.cache/uv -v actions-poetry-cache:/home/vscode/.cache/pypoetry -v actions-npm-cache:/home/vscode/.npm -w /workspaces/actions actions-devcontainer:task-2 .devcontainer/bin/bootstrap
docker run --rm --user vscode -v "$PWD:/workspaces/actions" -v actions-uv-cache:/home/vscode/.cache/uv -v actions-poetry-cache:/home/vscode/.cache/pypoetry -v actions-npm-cache:/home/vscode/.npm -w /workspaces/actions actions-devcontainer:task-2 .devcontainer/bin/verify-work-items
```

Result: image build passed; bootstrap completed both `poetry sync --no-interaction` commands with no dependency replacement; verification passed lock check, Ruff, 47 tests, sdist/wheel build, clean-wheel aliases/version, and `git diff --check`.

## Corrected documentation improvement receipt

Documentation improvement:
- Canonical file changed or proposed: `docs/skills/repository-operations.md`; `docs/skills/work-items.md`.
- Durable learning captured: pre-create and chown declared cache paths before switching to `vscode` so named volumes inherit usable ownership; Poetry 2.1 bootstrap uses `poetry sync --no-interaction`.
- Evidence: the rebuilt Task 2 image completed bootstrap and the full release gate with only the declared named cache volumes.
- Stale or ambiguous guidance removed: replaced Task 1 image commands and deprecated `poetry install --sync` guidance with the passing Task 2/`poetry sync` flow.
- Remaining uncertainty: `poetry check --lock` emits existing PEP 621 migration warnings, but exits successfully.
