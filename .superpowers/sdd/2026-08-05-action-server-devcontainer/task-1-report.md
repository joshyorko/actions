# Task 1 report: static Dev Container contract

## Outcome

Implemented the dependency-free static contract, a three-stage digest-pinned image, and the Action Server Dev Container wiring. Task 2 scripts and package dependencies were not modified.

## TDD evidence

### RED

After creating `.devcontainer/tests/test_contract.py` and before creating the Dockerfile or changing the JSON, ran:

```text
python -m unittest discover -s .devcontainer/tests -p 'test_*.py' -v
```

Result: `FAIL` (1 failure), with `None != 'Dockerfile'` because the legacy JSON had no `build.dockerfile` contract.

### GREEN

After implementing the Dockerfile and JSON, ran:

```text
python -m unittest discover -s .devcontainer/tests -p 'test_*.py' -v
```

Result: `OK`; one test ran and passed.

Also ran:

```text
git diff --check
```

Result: passed with no output.

## Implementation verification

Built headlessly with:

```text
docker build --pull=false -f .devcontainer/Dockerfile -t actions-devcontainer:task-1 .
```

Result: exit 0; image exported successfully.

The first build exposed that copied `/uv` and `/uvx` were not on `PATH`; `/usr/local/bin/uv` and `/usr/local/bin/uvx` symlinks were added. The next build exposed that root-installed Poetry resolved through `/root`; setting `HOME=/home/vscode` for the required `uv tool install` made the executable available to the unprivileged user. The final build passed.

Ran the final image as `vscode` and verified:

```text
id -u                 -> 1000
PWD                   -> /workspaces/actions
python --version      -> Python 3.12.11
node --version        -> v22.18.0
uv --version          -> uv 0.12.1 (x86_64-unknown-linux-musl)
poetry --version      -> Poetry (version 2.1.1)
```

The npm, npx, corepack, uv, and uvx links resolve to their copied package/tool paths.

## Node image correction

The brief's broad `/usr/local/` copy instruction was corrected before implementation. The pinned Node image was inspected with:

```text
docker run --rm --entrypoint sh node:22.18.0-bookworm-slim -c '...'
```

The image exposes `/usr/local/bin/node` and `/usr/local/lib/node_modules`, with npm, npx, and corepack package-bin links. Its `/usr/local` top level also contains unrelated `include`, `share`, `man`, `src`, `etc`, `games`, `sbin`, and other directories. The Dockerfile therefore copies only `/usr/local/bin/node` and `/usr/local/lib/node_modules`, then recreates the required npm/npx/corepack symlinks.

## Self-review

- Exact Python, Node, and uv digest pins are present.
- `POETRY_VERSION=2.1.1` is present.
- Runtime user is UID/GID 1000 `vscode`; no Docker socket or runtime feature was added.
- JSON wires the Dockerfile, `/workspaces/actions`, `vscode`, UID update, bootstrap lifecycle command, and named uv/Poetry/npm cache volumes.
- Forbidden personal image and Docker-in-Docker/outside-of-Docker terms are absent from the configuration and Dockerfile.
- Only Task 1 files are changed.

## Documentation improvement receipt

Documentation improvement:
- Canonical file changed or proposed: `docs/skills/repository-operations.md` (proposed; Task 1 write scope excludes canonical docs).
- Durable learning captured: Dev Container image verification must inspect copied tool paths and run the built image as UID 1000; when `uv` is copied to `/uv`, expose it on `PATH`, and when Poetry is installed during a root build, set `HOME=/home/vscode` so the non-root runtime can execute it. Node stages should copy only `/usr/local/bin/node` and `/usr/local/lib/node_modules`, recreating package-bin links, rather than copying all of `/usr/local`.
- Evidence: final `docker build --pull=false ...` exited 0; non-root runtime checks reported UID 1000, `/workspaces/actions`, Python 3.12.11, Node 22.18.0, uv 0.12.1, and Poetry 2.1.1. Node inspection listed unrelated `/usr/local` directories alongside the required paths. The two intermediate build failures demonstrated the `PATH` and root-home issues.
- Stale or ambiguous guidance removed: the plan's broad “copy `/usr/local/` from the Node stage” instruction was superseded for this task by the narrower, evidence-backed copy rule; no canonical guide was edited because the requested write scope excludes it.
- Remaining uncertainty: the direct interface example `python -m unittest .devcontainer.tests.test_contract` is not executable because Python treats the leading-dot directory name as an invalid module name; the specified discovery command is the passing static gate. Task 2 bootstrap behavior remains unverified by design.
