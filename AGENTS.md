# Repository Guidelines

## Project Structure & Module Organization

This repository is a Poetry-managed Python monorepo. `action_server/` contains the CLI, FastAPI service, frontend, build pipeline, and bundled RCC integration. `actions/`, `mcp/`, and `work-items/` provide agent-facing libraries. `common/`, `build_common/`, and `devutils/` contain shared runtime and build utilities. Package tests live under each package's `tests/`; generated starting points live under `templates/`.

Read [the canonical guide index](docs/skills/README.md) before changing code. Read [.agents/skills/actions-repository/SKILL.md](.agents/skills/actions-repository/SKILL.md) and use that repository-local `actions-repository` skill for implementation, review, debugging, testing, release, or reconnaissance work in this checkout.

## Build, Test, and Development Commands

RCC owns the outer developer toolchain; Poetry owns package dependencies and
committed lockfiles. Start from the repository root with Josh's RCC v18.19.3:

```bash
rcc run -r developer/toolkit.yaml --dev -t Doctor
rcc run -r developer/toolkit.yaml --dev -t Bootstrap
rcc run -r developer/toolkit.yaml --dev -t ToolkitTest
```

Without RCC, use `devutils/bin/develop.sh Doctor` (Windows: `develop.bat Doctor`),
then the same launcher with `Bootstrap` and `ToolkitTest`. Read
[CONTRIBUTING.md](CONTRIBUTING.md) for pins and setup failure handling.
Cloud agents must use this gateway, not ad hoc Poetry/pip installations or
upstream RCC `latest`. Package commands below assume the prepared toolchain.

- Toolkit `Bootstrap` delegates to root `invoke install` and isolated package-local Poetry environments.
- `poetry run pytest` from a package directory runs its complete suite; use `-k <scope>` only while iterating.
- `poetry run action-server start --auto-reload` starts the local server; add `--log-level debug` for diagnostics.
- `.devcontainer/bin/smoke` runs the non-root, pinned-tool, Poetry Work Items release gate from any repository subdirectory in the Dev Container.
- `invoke docs` rebuilds repository documentation bundles.
- `git diff --check` detects whitespace errors.

Use configured package commands for Black, Isort, Ruff, and type checks. A host-tool fallback can provide diagnostic evidence when Poetry is unavailable, but it does not replace the package's declared release gate. External-service tests that are skipped or unavailable remain unverified.

## Coding Style & Naming Conventions

Target the Python range declared by the affected package. Use type hints and contract-focused docstrings. Follow Black formatting, Isort import order, four-space indentation, `snake_case` functions/modules, `PascalCase` classes, and `test_<feature>.py` tests. Prefer dataclasses or Pydantic models for agent/API payloads. Preserve package boundaries and public aliases; do not widen a shared abstraction without contract tests.

## Testing Guidelines

Pytest drives Python suites. Add regression coverage before changing behavior, including happy, failure, and recovery paths. Protocol, serializer, CLI, queue, filesystem, and concurrency changes require boundary-level tests. Run the smallest focused test while iterating, then the affected package's full suite, configured lint/type checks, and `git diff --check`. Cross-package changes require every affected package suite.

## Mandatory Self-Improvement Contract

Every implementation, review, debugging, reconnaissance, and verification task must leave repository-local operational guidance measurably better in correctness, completeness, discoverability, determinism, testability, or recovery guidance.

- `docs/skills/` is the canonical home for durable operational knowledge. Correct or extend an existing guide before creating another and keep every guide listed in `docs/skills/README.md`.
- Document only behavior backed by code, tests, exact command output, observed failures, or authoritative versioned upstream behavior. Never present planned behavior as implemented.
- Replace stale or contradictory guidance when evidence changes. Do not add cosmetic prose, personal preferences, or per-run diaries.
- Mutating lanes update the relevant canonical guide in the same commit as the evidence-producing work. Read-only or isolated lanes propose an exact delta for the integration agent.

Every agent dispatch must include:

> Before completing, improve the relevant canonical guide or repository skill with durable, verified knowledge learned during this task. Do not add cosmetic prose or a session diary. Report the exact documentation delta and its evidence.

Every assignment must also pass this upstream-reporting instruction:

> If work uncovers a possible upstream defect, follow `docs/skills/upstream-reporting.md`. The task must state any authorized upstream target and issue-only scope; without that explicit authority, prepare a draft only. Include `Upstream disposition: none` or the factual report disposition in the normal completion receipt.

Every parent, child, remote, read-only, and review lane must return:

```text
Documentation improvement:
- Canonical file changed or proposed:
- Durable learning captured:
- Evidence:
- Stale or ambiguous guidance removed:
- Remaining uncertainty:
```

The integration agent may complete the parent task only after every receipt is integrated or explicitly rejected with a reason and canonical guides contain no contradictory claims. The final report lists documentation improvements from the full run.

## Upstream defect reporting

When implementation, review, debugging, release, or coordination finds a
possible defect owned by a maintained upstream dependency, follow
[`docs/skills/upstream-reporting.md`](docs/skills/upstream-reporting.md). The
guide governs evidence, ownership, deduplication, maintainer follow-up, and the
completion receipt. Every normal task completion receipt states
`Upstream disposition: none` if no upstream investigation was needed, or gives
the factual disposition. The guide does not grant credentials or authority to
mutate any repository: external issue creation requires explicit,
target-specific, issue-only authorization for a confirmed defect. Third-party
or out-of-scope reports remain drafts pending authority. Route
security-sensitive findings through the affected repository's private
reporting procedure.

## Commit & Pull Request Guidelines

Use concise Conventional Commit prefixes such as `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, and `chore:`. Keep commits independently reviewable. Pull requests summarize behavior and safety impact, link issues, disclose breaking changes, list exact verification output and skipped gates, and include screenshots only for visual changes. Request package-owner review for shared `common/` changes.

## Security & Configuration Tips

Keep credentials, raw secrets, `.env`, datadirs, queue databases, attachment artifacts, and generated binaries out of commits. Load secrets from environment or the local vault. Validate filesystem containment, ownership, serialized input, and OAuth/configuration changes at trust boundaries. Review dependency-pin changes carefully, especially templates and optional backends.
