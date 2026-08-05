# Action Server Dev Container Design

## Goal

Provide a lean, repository-owned Dev Container that reproduces the Action Server and Work Items Poetry release gates. Opening the repository must produce a usable Python 3.12 and Node 22 environment without relying on a mutable personal toolbox image.

## Decisions

- Build from a digest-pinned `python:3.12-slim-bookworm` base.
- Install only the operating-system packages required for repository development and native Python builds: certificates, curl, Git, and a C/C++ toolchain. Remove package-manager indexes in the same layer.
- Include Node 22 because `action_server/frontend` is part of the Action Server build and test boundary.
- Include pinned `uv` as the fast tool bootstrap and cache layer. Use it to install pinned Poetry; do not use `uv sync`, introduce uv lockfiles, or reinterpret Poetry dependency resolution.
- Keep Poetry and existing `poetry.lock` files authoritative. Create a Work Items lockfile so its release environment is reproducible.
- Run as an unprivileged `vscode` user whose UID/GID can be aligned by the Dev Container runtime.
- Persist package download caches in named volumes, not generated virtual environments in the repository.
- Do not bake RCC into the image. Action Server continues to download and verify the repository-pinned RCC version.
- Do not include Docker-in-Docker, a mounted Docker socket, cloud CLIs, databases, browsers, or Dagger in the default image.

## Repository Layout

The existing one-line `.devcontainer/devcontainer.json` is replaced by:

- `.devcontainer/devcontainer.json`: workspace wiring, mounts, editor settings, lifecycle commands, and resource requirements.
- `.devcontainer/Dockerfile`: the digest-pinned toolchain image.
- `.devcontainer/bin/bootstrap`: idempotent environment installation for Work Items and Action Server.
- `.devcontainer/bin/verify-work-items`: the canonical Poetry release gate.
- `.devcontainer/bin/smoke`: a host/headless contract that checks required tools and delegates to `verify-work-items`.

Scripts use strict shell mode, resolve the repository root from their own location, and work independently of the caller's current directory.

## Lifecycle

Image build installs Python, Node, uv, and Poetry. `postCreateCommand` runs `bootstrap`, which verifies tool versions and performs locked Poetry installation for Work Items and Action Server. `postStartCommand` performs no network mutation.

The Work Items verification command runs, in order:

1. `poetry check --lock`
2. configured Ruff over `src` and `tests`
3. the complete Pytest suite
4. `poetry build`
5. installation of the newly built wheel into a fresh temporary environment
6. import/version/alias smoke checks for all three public import paths
7. `git diff --check`

Build output and temporary environments live outside tracked source or are removed on exit. The script fails on the first missing or failed gate and prints the exact command being executed.

## Reproducibility and Security

Base image, Node source, uv, and Poetry versions are explicit. Downloads use HTTPS and checksum or digest verification where an upstream artifact supports it. The container runs unprivileged and does not receive the host Docker socket. Cache mounts contain only disposable package downloads. No credentials, RCC state, Action Server datadir, or generated package artifacts are persisted into the image.

The image receives standard Open Containers labels identifying the repository and tool versions. Renovation tools can discover version arguments and image references without parsing shell scripts.

## Testing

Configuration is tested from outside VS Code with the Dev Container CLI when available. A Docker fallback builds the same Dockerfile, bind-mounts the checkout, and runs `.devcontainer/bin/smoke` as the non-root user. Verification must demonstrate:

- Python 3.12, Node 22, pinned uv, and pinned Poetry are present;
- Poetry installs from repository configuration;
- all Work Items release gates pass inside the image;
- the checkout remains clean except for intentional source changes;
- the runtime user is non-root.

A JSON/configuration check should fail against the old one-line image reference before implementation and pass only when the repository-owned Dockerfile and lifecycle commands are wired.

## Dagger Boundary

Dagger is deferred from the base image. The canonical verification script is intentionally runtime-neutral so a later Dagger pipeline can mount the repository into the same image and invoke one command. Dagger adoption is justified only when it replaces duplicated CI orchestration; it must not require every editor session to receive privileged Docker access.

## Documentation

Root agent guidance and `docs/skills/repository-operations.md` identify the Dev Container as the preferred release environment when host Poetry is unavailable. They provide headless build, bootstrap, verification, cache-reset, and failure-recovery commands. Planned behavior is not described as available until the corresponding image and smoke test pass.
