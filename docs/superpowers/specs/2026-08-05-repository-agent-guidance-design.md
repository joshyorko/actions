# Repository Agent Guidance Design

## Goal

Make repository-local operational knowledge discoverable and require every agent lane to improve durable guidance with evidence, including read-only reviews and delegated child work.

## Baseline Evidence

Three fresh Luna pressure scenarios used the current `AGENTS.md` without proposed guidance:

- A rushed Ruff-fix lane said documentation would remain untouched.
- A read-only SQLite race review explicitly excluded documentation recommendations.
- A bounded child implementation lane would update documentation only when the API contract required it.

The failure is structural: current instructions have no canonical knowledge location, mandatory receipt, or parent integration gate.

## Structure

- `AGENTS.md` is the mandatory repository contract: package map, exact validation commands, coding/testing/security rules, and the self-improvement gate.
- `.agents/skills/actions-repository/SKILL.md` is the discoverable router for any implementation, review, debugging, reconnaissance, release, or verification work in this monorepo.
- `docs/skills/README.md` is the canonical guide index.
- `docs/skills/repository-operations.md` contains cross-package workflows and evidence rules.
- `docs/skills/work-items.md` contains verified Work Items contracts, supported backend tiers, safety invariants, and commands.

Detailed knowledge lives in `docs/skills/`; the skill routes agents to the relevant guide and enforces the receipt without duplicating the guides.

## Mandatory Self-Improvement Contract

Every parent and child lane must return:

```text
Documentation improvement:
- Canonical file changed or proposed:
- Durable learning captured:
- Evidence:
- Stale or ambiguous guidance removed:
- Remaining uncertainty:
```

Mutating lanes update the canonical guide in the same commit as the evidence-producing change. Read-only or isolated lanes propose an exact delta. Cosmetic prose, session diaries, plans described as implemented behavior, and unsupported claims do not satisfy the contract.

The integration agent cannot complete the parent task until every receipt is integrated or rejected with a reason and canonical guides contain no contradictory claims.

## Skill Behavior

The repository skill triggers for work anywhere in this checkout. It requires initial branch/status/package inspection, routes Action Server package authoring to `rcc:action-server`, routes adapter-heavy work to `rcc:rcc-workitems`, names package-specific commands, and requires evidence-backed documentation improvement before completion.

## Validation

- Validate skill structure with `quick_validate.py`.
- Forward-test the same three pressure scenarios with the new skill.
- Success requires all lanes to return the exact receipt and either make or propose a durable evidence-backed delta despite pressure to omit documentation.
- Run Markdown/link/path checks, `git diff --check`, and inspect every instruction for conflicts with current code or commands.
