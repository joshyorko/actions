# Template Actions Dependencies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every shipped template resolve the currently published Actions libraries.

**Architecture:** A static contract test reads every shipped template manifest and enforces the supported Actions dependency declarations. The manifests then receive the minimal version-only edits, and the verified invariant is recorded in the canonical repository guide.

**Tech Stack:** Python 3.12, Pytest, YAML text manifests

## Global Constraints

- Pin `actions-core=1.0.0` in every template `package.yaml`.
- Pin `actions-work-items=0.4.4` only in the producer-consumer template.
- Do not add `actions-http-helper` or `actions-runtime` directly to templates.
- Do not rebuild template archives or publish packages.

---

### Task 1: Enforce and update template dependencies

**Files:**
- Modify: `action_server/tests/contract_tests/test_active_contracts.py`
- Modify: `templates/advanced/package.yaml`
- Modify: `templates/basic/package.yaml`
- Modify: `templates/data-access-kb/package.yaml`
- Modify: `templates/data-access-native/package.yaml`
- Modify: `templates/data-access-query/package.yaml`
- Modify: `templates/minimal/package.yaml`
- Modify: `templates/workflow-producer-consumer/package.yaml`
- Modify: `docs/skills/repository-operations.md`

**Interfaces:**
- Consumes: the template IDs declared by `templates/packaging/templates-prod.json` and `templates/packaging/templates-beta.json`
- Produces: a Pytest contract ensuring every supported `package.yaml` uses the approved Actions dependency pins

- [ ] **Step 1: Write the failing contract test**

Add a test that loads the supported template IDs, reads each `package.yaml`, asserts `actions-core=1.0.0`, rejects other `actions-core` declarations, and requires `actions-work-items=0.4.4` only for `workflow-producer-consumer`.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `rtk pytest action_server/tests/contract_tests/test_active_contracts.py -k actions_dependencies`

Expected: FAIL reporting `actions-core=1.6.4` and the stale Work Items range.

- [ ] **Step 3: Apply the minimal manifest and guide edits**

Replace every `actions-core=1.6.4` with `actions-core=1.0.0`, replace `actions-work-items>=0.2.4` with `actions-work-items=0.4.4`, and document those exact pins and package-boundary rationale in `docs/skills/repository-operations.md`.

- [ ] **Step 4: Verify GREEN and repository hygiene**

Run: `rtk pytest action_server/tests/contract_tests/test_active_contracts.py`

Expected: PASS.

Run: `rtk git diff --check`

Expected: no whitespace errors.

- [ ] **Step 5: Review the scoped diff**

Run: `rtk git diff -- templates action_server/tests/contract_tests/test_active_contracts.py docs/skills/repository-operations.md`

Expected: only dependency pins, their regression contract, and durable canonical guidance change.
