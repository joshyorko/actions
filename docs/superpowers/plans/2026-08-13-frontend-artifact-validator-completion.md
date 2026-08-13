# Frontend Artifact Validator Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the default frontend artifact validation fail closed and independently scan both Runtime and Canvas artifacts for forbidden imports.

**Architecture:** Keep the existing top-level `tree_shaker`/`artifact_validator` import contract and make the tree scanner deterministic over only shipped source-like text extensions. The Invoke task will validate the two fixed artifact roots in sequence, retaining an explicit artifact helper for focused tests and reporting each root independently.

**Tech Stack:** Python, Invoke, pytest, Vite/npm, Ruff, Black, GitHub Actions.

## Global Constraints

- Scope only frontend artifact validation, task behavior, tests, and canonical docs.
- Do not touch Lane A workflow paths, MCP/database/release source, or `.serena/`.
- Do not retain an enterprise-path exemption or swallow scanner read errors.
- Preserve existing forbidden package rules and the top-level build-binary import contract.
- Default `inv validate-artifact` must visit both `frontend/dist` and `frontend/dist-canvas` independently.

---

### Task 1: Add RED coverage for scanner and task gaps

**Files:**
- Modify: `action_server/tests/build_system_tests/test_tree_shaker.py`
- Modify: `action_server/tests/contract_tests/test_artifact_validator_import.py`

- [ ] **Step 1: Add focused failing cases** for HTML scanning, enterprise-path scanning, supported extensions, ignored arbitrary assets, deterministic read failures, Runtime/Canvas default task coverage, and clean dual-artifact acceptance.
- [ ] **Step 2: Run the focused tests** and confirm failures are caused by the four known validator gaps.

### Task 2: Implement fail-closed dual artifact validation

**Files:**
- Modify: `action_server/build-binary/tree_shaker.py`
- Modify: `action_server/build-binary/artifact_validator.py`
- Modify: `action_server/tasks.py`

- [ ] **Step 1: Remove the enterprise-path early return** and scan only `.html`, `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`, and `.css` files in sorted recursive order.
- [ ] **Step 2: Propagate read failures as validation failures** with file context; keep non-source assets and maps outside import scanning.
- [ ] **Step 3: Keep focused artifact validation available while making the default task validate Runtime and Canvas independently, with missing roots and any failed root causing exit code 2.
- [ ] **Step 4: Run the focused tests green and inspect the diff for forbidden path overlap.

### Task 3: Update durable operational guidance

**Files:**
- Modify: `docs/skills/repository-operations.md`

- [ ] **Step 1: Replace any stale claim with the verified default task behavior and exact scanner extension/read-error contract.
- [ ] **Step 2: Run the documentation-relevant focused tests and `git diff --check`.

### Task 4: Complete repository and hosted evidence

**Files:**
- Create: `/tmp/actions-pr106-validator-completion-receipt.txt`

- [ ] **Step 1: Run package-configured validator/task tests, frontend npm install/quality/full tests, Runtime/Canvas builds, default task, poisoned cases, Ruff/format/compile checks, and all allowed static checks.
- [ ] **Step 2: Prove the five Lane A files are byte-identical to `0ad03aa2`.
- [ ] **Step 3: Commit one normal descendant, push without force, refresh PR state and checks, update the PR body, and write the exact evidence receipt.
