# Repository Agent Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Install and validate repository-local guidance that forces every agent lane to improve durable documentation or skills with evidence.

**Architecture:** Root `AGENTS.md` defines the mandatory contract. A lean `.agents/skills/actions-repository` skill routes work. `docs/skills/` stores canonical operational knowledge without duplication.

**Tech Stack:** Markdown, Agent Skills specification, `quick_validate.py`, Luna pressure scenarios.

## Global Constraints

- Preserve evidence-backed current behavior; never document planned behavior as implemented.
- Every child/read-only lane returns the exact five-field documentation receipt.
- Detailed knowledge has one canonical home under `docs/skills/`.

### Task 1: Create canonical structure and repository skill

**Files:** create `.agents/skills/actions-repository/SKILL.md`, `.agents/skills/actions-repository/agents/openai.yaml`, `docs/skills/README.md`, `docs/skills/repository-operations.md`, and `docs/skills/work-items.md`.

- [ ] Initialize `actions-repository` with the official skill scaffolder.
- [ ] Write the minimal skill addressing the three observed baseline failures.
- [ ] Write indexed, evidence-backed repository and Work Items guides.
- [ ] Run `quick_validate.py` and `git diff --check`.

### Task 2: Replace root repository instructions

**Files:** modify `AGENTS.md`.

- [ ] Preserve useful package/build/style/security guidance and correct stale commands.
- [ ] Add canonical-guide routing, mandatory self-improvement contract, child receipt, and parent integration gate.
- [ ] Verify paths and commands against the checkout.

### Task 3: Forward-test and deploy

- [ ] Run the three baseline pressure scenarios with the new skill in fresh Luna contexts.
- [ ] Require exact receipts and evidence-backed changed/proposed deltas in all three outputs.
- [ ] Close loopholes revealed by testing, revalidate, commit, and push.
