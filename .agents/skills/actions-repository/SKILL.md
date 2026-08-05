---
name: actions-repository
description: Use when implementing, reviewing, debugging, testing, releasing, or investigating code anywhere in the Actions Python monorepo, including Action Server, work items, MCP, shared packages, templates, CI, and documentation.
---

# Actions Repository

## Start Here

1. Read root `AGENTS.md` and `docs/skills/README.md` completely.
2. Inspect `git status --short --branch`, the affected package's `pyproject.toml`, tests, and package-local documentation before changing files.
3. Read the relevant canonical guide. For Work Items, read `docs/skills/work-items.md`.
4. Use `rcc:action-server` for Action Server package/API behavior. Use `rcc:rcc-workitems` for queues, adapters, producer/consumer flows, and attachments.

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
