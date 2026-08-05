# Action Server Dev Container Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the mutable personal-image Dev Container with a lean, reproducible Action Server environment whose first-class Work Items release gate runs through Poetry.

**Architecture:** A repository-owned multi-stage Dockerfile copies Node and uv into a digest-pinned Python slim runtime, installs pinned Poetry with uv, and runs as an unprivileged user. Small strict-shell lifecycle scripts own bootstrap and release verification; a dependency-free contract test and headless Dev Container/Docker smoke prove the configuration rather than relying on editor attachment.

**Tech Stack:** Dev Container specification, Docker BuildKit, Python 3.12.11, Node 22.18.0, uv 0.12.1, Poetry 2.1.1, Bash, Pytest, Ruff.

## Global Constraints

- Do not use `ghcr.io/joshyorko/ror`, `ghcr.io/joshyorko/room-of-requirement`, Microsoft Dev Container base images, Docker-in-Docker, or a host Docker socket.
- Pin `python:3.12.11-slim-bookworm` to `sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7`.
- Pin `node:22.18.0-bookworm-slim` to `sha256:752ea8a2f758c34002a0461bd9f1cee4f9a3c36d48494586f60ffce1fc708e0e`.
- Pin `ghcr.io/astral-sh/uv:0.12.1` to `sha256:cf4eedcaa81655197f625739489effcbe71b61ceb1506f332c3facae5deceded` and Poetry to `2.1.1`.
- uv bootstraps tools and caches downloads; Poetry and Poetry lockfiles remain dependency and release authorities. Do not add a uv lockfile or call `uv sync`.
- Do not bake RCC, credentials, datadirs, generated wheels, service databases, or editor state into the image.
- Every implementation/review lane returns and integrates the repository documentation receipt.

---

### Task 1: Define and satisfy the static Dev Container contract

**Files:**
- Create: `.devcontainer/tests/test_contract.py`
- Create: `.devcontainer/Dockerfile`
- Modify: `.devcontainer/devcontainer.json`

**Interfaces:**
- Produces: `python -m unittest .devcontainer.tests.test_contract` as a dependency-free static gate.
- Produces: image user `vscode`, workspace `/workspaces/actions`, and lifecycle command `.devcontainer/bin/bootstrap`.

- [ ] **Step 1: Write the failing contract test**

Create a `unittest.TestCase` that loads `.devcontainer/devcontainer.json` and `.devcontainer/Dockerfile`, then asserts: `build.dockerfile == "Dockerfile"`; `remoteUser == "vscode"`; `postCreateCommand == ".devcontainer/bin/bootstrap"`; Poetry and uv cache mounts exist; the Dockerfile contains all three exact digest pins and `POETRY_VERSION=2.1.1`; and neither file contains `ror`, `room-of-requirement`, `docker-in-docker`, or `docker-outside-of-docker`.

- [ ] **Step 2: Run the contract and verify RED**

Run: `python -m unittest discover -s .devcontainer/tests -p 'test_*.py' -v`

Expected: FAIL because the current JSON has no `build`, `remoteUser`, lifecycle command, or repository Dockerfile.

- [ ] **Step 3: Implement the minimal image and configuration**

Use three Dockerfile stages with exact `FROM` references from Global Constraints. Copy `/usr/local/` from the Node stage and `/uv`, `/uvx` from the uv stage. In the Python stage install `ca-certificates curl git build-essential` with `--no-install-recommends`, create UID/GID 1000 user `vscode`, set `UV_TOOL_BIN_DIR=/usr/local/bin`, and run `uv tool install "poetry==${POETRY_VERSION}"`. Add OCI source/title/version labels and switch to `USER vscode`.

Set Dev Container `name` to `Actions — Action Server`, build `.devcontainer/Dockerfile`, use `/workspaces/actions`, set `remoteUser` to `vscode`, enable `updateRemoteUserUID`, mount named volumes at `/home/vscode/.cache/uv`, `/home/vscode/.cache/pypoetry`, and `/home/vscode/.npm`, and configure Python/Ruff editor extensions without adding runtime features.

- [ ] **Step 4: Run the contract and verify GREEN**

Run the command from Step 2. Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `feat(devcontainer): add lean Action Server image`

### Task 2: Make Poetry bootstrap and Work Items verification canonical

**Files:**
- Create: `.devcontainer/bin/bootstrap`
- Create: `.devcontainer/bin/verify-work-items`
- Modify: `work-items/pyproject.toml`
- Create: `work-items/poetry.lock`
- Modify: `.devcontainer/tests/test_contract.py`
- Modify: `docs/skills/repository-operations.md`
- Modify: `docs/skills/work-items.md`

**Interfaces:**
- Produces: `.devcontainer/bin/bootstrap` with no arguments and idempotent exit status.
- Produces: `.devcontainer/bin/verify-work-items` with no arguments; nonzero on the first failed release gate.

- [ ] **Step 1: Extend the contract test and verify RED**

Assert both scripts exist and are executable, contain `set -Eeuo pipefail`, resolve `repo_root` relative to `${BASH_SOURCE[0]}`, and contain no `uv sync`. Assert verification names `poetry check --lock`, `ruff check src tests`, `pytest tests`, `poetry build`, all three public imports, and `git diff --check`.

Run the Task 1 test command. Expected: FAIL because scripts and Work Items lockfile are absent.

- [ ] **Step 2: Add the reproducible package toolchain**

Add `ruff = "^0.12.0"` to the Work Items Poetry dev group. From the Dev Container image, run `poetry lock` in `work-items/` and commit the generated lockfile. Do not update unrelated dependency constraints.

- [ ] **Step 3: Implement bootstrap**

The script prints versions, runs `poetry install --sync --no-interaction` in `work-items/`, then `poetry install --sync --no-interaction` in `action_server/`. Use a `run_in_package <directory> <command...>` helper so failures identify their package and command.

- [ ] **Step 4: Implement verification**

Within `work-items/`, run `poetry check --lock`, `poetry run ruff check src tests`, `poetry run pytest tests -q`, and `poetry build --output "$artifact_dir"`. Create temporary directories with `mktemp -d` and remove them through an EXIT trap. Create a fresh Python venv, install the wheel with `python -m pip --disable-pip-version-check install`, then assert alias object identity and `0.2.4` version equality in Python. Finish at repository root with `git diff --check`.

- [ ] **Step 5: Run static and host-level script checks**

Run the contract test, `bash -n .devcontainer/bin/bootstrap .devcontainer/bin/verify-work-items`, and `git diff --check`. Expected: all pass.

- [ ] **Step 6: Document verified commands and recovery**

Document headless build, bootstrap, verification, cache-volume removal, and image rebuild commands. State that uv bootstraps Poetry but never replaces Poetry resolution. Remove the stale instruction that host-tool fallback is the terminal release path when Docker is available.

- [ ] **Step 7: Commit**

Commit: `ci(work-items): add Poetry release gate`

### Task 3: Prove the image headlessly and publish the evidence

**Files:**
- Create: `.devcontainer/bin/smoke`
- Modify: `.devcontainer/tests/test_contract.py`
- Modify: `AGENTS.md`
- Modify: `docs/skills/repository-operations.md`
- Modify: `docs/skills/work-items.md`

**Interfaces:**
- Produces: `.devcontainer/bin/smoke`, callable inside the image from any current directory.
- Consumes: `bootstrap` and `verify-work-items` from Task 2.

- [ ] **Step 1: Extend the contract for smoke and verify RED**

Assert `smoke` is executable, strict-shell, checks non-root UID, exact major/minor tool versions, calls `bootstrap`, and calls `verify-work-items`. Expected: FAIL because smoke is absent.

- [ ] **Step 2: Implement smoke**

Reject UID 0. Assert `python --version` begins `Python 3.12.`, `node --version` begins `v22.`, `uv --version` equals `uv 0.12.1`, and `poetry --version` equals `Poetry (version 2.1.1)`. Invoke the two Task 2 scripts by absolute repository-relative paths.

- [ ] **Step 3: Build and run the Docker fallback**

Run:

```bash
docker build --pull=false -f .devcontainer/Dockerfile -t actions-devcontainer:test .
docker run --rm --user vscode -v "$PWD:/workspaces/actions" -w /workspaces/actions actions-devcontainer:test .devcontainer/bin/smoke
```

Expected: image builds; smoke runs non-root; Poetry installs succeed; all release gates pass; wheel imports pass.

- [ ] **Step 4: Run the Dev Container CLI headlessly**

Run:

```bash
npx --yes @devcontainers/cli up --workspace-folder . --remove-existing-container
npx --yes @devcontainers/cli exec --workspace-folder . .devcontainer/bin/smoke
```

Expected: lifecycle bootstrap and explicit smoke both pass. If the CLI itself cannot run, preserve the Docker fallback evidence and report the exact external failure without weakening the contract.

- [ ] **Step 5: Run final repository gates**

Run the static contract, shell syntax checks, Work Items Poetry verification inside the image, focused Action Server Work Items/startup tests inside the container, and `git diff --check`. Confirm `git status --short` contains only intended source changes.

- [ ] **Step 6: Update durable guidance**

Replace planned language with commands proven in Steps 3–5. Document that Dagger is intentionally absent and may later invoke `verify-work-items` without changing package authority or granting editor containers Docker access.

- [ ] **Step 7: Commit and update PR #70**

Commit: `docs: publish devcontainer workflow`. Push the branch and add exact image/tool/Poetry verification evidence and remaining uncertainty to PR #70.
