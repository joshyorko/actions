---
name: actions-repository
description: Use when implementing, reviewing, debugging, testing, releasing, or investigating code anywhere in the Actions Python monorepo, including Action Server, work items, MCP, shared packages, templates, CI, and documentation.
---

# Actions Repository

## Start Here

1. Read root `AGENTS.md` and `docs/skills/README.md` completely.
2. Follow the RCC Doctor → Bootstrap → ToolkitTest onboarding sequence in `CONTRIBUTING.md`. RCC owns the outer toolchain; Poetry owns package dependencies and lockfiles. Do not bypass toolkit failures with host Poetry/pip installs.
3. Inspect `git status --short --branch`, the affected package's `pyproject.toml`, tests, and package-local documentation before changing files.
4. Read the relevant canonical guide. For Work Items, read `docs/skills/work-items.md`.
5. Use `rcc:action-server` for Action Server package/API behavior. Use `rcc:rcc-workitems` for queues, adapters, producer/consumer flows, and attachments.

## Specialized RCC skills

The specialist skills come from [joshyorko/plugins](https://github.com/joshyorko/plugins),
under `plugins/rcc/skills/`. Read the matching `SKILL.md` there when the plugin is
not installed in a cloud agent environment:

- [rcc-core](https://github.com/joshyorko/plugins/blob/main/plugins/rcc/skills/rcc-core/SKILL.md): RCC installation, version, and environment resolution.
- [rcc-ci-maintenance](https://github.com/joshyorko/plugins/blob/main/plugins/rcc/skills/rcc-ci-maintenance/SKILL.md): pinned CI setup and caches.
- [action-server](https://github.com/joshyorko/plugins/blob/main/plugins/rcc/skills/action-server/SKILL.md): ACTIONS packages, runtime, and build tasks.
- [rcc-workitems](https://github.com/joshyorko/plugins/blob/main/plugins/rcc/skills/rcc-workitems/SKILL.md): Work Items adapters and service gates.

If remote guidance is unavailable, report that limitation and continue with this
skill and `docs/skills/`; do not invent a replacement bootstrap. Repository
manifests, lockfiles, and task implementations remain authoritative.

## Repository Rules

- Work package-locally. Run Poetry commands from the package directory unless the root Invoke task explicitly spans packages.
- Preserve public aliases, schemas, protocols, serialized formats, and environment-variable contracts unless a reviewed migration authorizes a break.
- Diagnose before fixing and write regression tests before behavioral changes.
- Treat skipped external-service tests as unverified, not passing.
- Keep secrets, generated binaries, `.env`, datadirs, queue databases, and attachment artifacts out of commits.

## Mandatory Knowledge Improvement

Every implementation, review, debugging, reconnaissance, and verification lane must improve a canonical guide with durable evidence. Mutating lanes edit the guide in the same commit. Read-only or isolated lanes propose an exact delta for the integration agent.

Cosmetic prose and session diaries do not count. Never document planned behavior as implemented.

Every lane returns:

```text
Documentation improvement:
- Canonical file changed or proposed:
- Durable learning captured:
- Evidence:
- Stale or ambiguous guidance removed:
- Remaining uncertainty:
```

The parent task remains incomplete until every child receipt is integrated or rejected with a recorded reason.

## Verification

Run the smallest focused test while iterating, then the affected package's complete suite, configured lint/type checks, and `git diff --check`. For cross-package contracts, run every affected package suite. Report exact commands, results, skipped gates, and remaining uncertainty.

## Common Failures

- “Documentation is out of scope” → propose the exact canonical delta anyway.
- “No docs changed because this was read-only” → return a proposal with evidence.
- “The change is only mechanical” → record the reproducible command or invariant learned.
- “The parent did not request documentation” → this repository contract already did.
