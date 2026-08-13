# Opaque Resource Telemetry Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent MCP resource identifiers from exposing opaque URI payloads or sensitive URI components through structured telemetry and logs while retaining bounded safe resource observability.

**Architecture:** Keep request identity validation unchanged and harden the existing `_sanitize_identifier` boundary used by `McpRequestMetadata`. Classify only explicitly supported safe URI schemes, return a bounded safe basename/type only when the parsed value is provably non-sensitive, and otherwise return a constant redaction sentinel. Preserve existing strict method/name bounds and observer behavior.

**Tech Stack:** Python 3.12+, Starlette ASGI middleware, `urllib.parse`, Poetry, pytest, Ruff, mypy, compileall.

## Global Constraints

- Scope only gateway metadata sanitization, tests, canonical docs, and PR body.
- Preserve `.serena/`, the exact base, one normal descendant, and all unrelated worktree changes.
- No frontend, database, release, workflow, merge, rebase, amend, squash, or force-push changes.
- Resource telemetry must not expose opaque scheme-specific content, userinfo, credentials, query, fragment, token-looking paths, or arbitrary full URIs.
- Keep normal safe resource names bounded and keep observer, exception/context, CORS, and protocol behavior green.

---

### Task 1: Add failing opaque-resource regression coverage

**Files:**
- Modify: `action_server/tests/action_server_tests/mcp/test_mcp_gateway_metadata.py`

- [ ] **Step 1: Add a direct middleware/log-capture test** covering `mailto`, `data`, `urn`, a custom opaque scheme, URL userinfo, query/fragment, and a token-looking path. Assert each secret sentinel is absent from every emitted record and extra/telemetry field, while safe resource behavior remains bounded.
- [ ] **Step 2: Run the focused new test** from `action_server/` with Poetry and confirm it fails because opaque payload content remains in `actions.mcp.name`.

### Task 2: Implement the minimal sanitization boundary

**Files:**
- Modify: `action_server/src/actions/server/mcp/gateway_metadata.py`

- [ ] **Step 1: Update the existing identifier sanitizer** so opaque URI schemes and unprovably sensitive resource identifiers become a constant redaction sentinel; allow only the explicit safe scheme classification and a provably safe bounded basename/type.
- [ ] **Step 2: Run the new regression and existing metadata tests** and confirm all pass without changing method/prompt bounds or observer semantics.

### Task 3: Record durable operational guidance

**Files:**
- Modify: `docs/skills/repository-operations.md`

- [ ] **Step 1: Replace the current URI-redaction statement** with the verified invariant that resource telemetry uses explicit safe scheme classification and redacts opaque, credentialed, query-bearing, fragment-bearing, token-looking, and otherwise unprovable identifiers.
- [ ] **Step 2: Keep the guide factual** and cite the focused tests and verification commands in the final receipt.

### Task 4: Verify and deliver the surgical repair

**Files:**
- Modify: PR #108 body through the GitHub CLI.
- Create: `/tmp/actions-pr108-opaque-uri-repair-receipt.txt`

- [ ] **Step 1: Run focused metadata and integration tests with httpx**, then Ruff check/format, compileall, and `git diff --check`.
- [ ] **Step 2: Review the diff and changed-file scope**, commit one normal descendant with a Conventional Commit, and push without merge or force-push.
- [ ] **Step 3: Update the PR body with the exact new behavior and fresh evidence**, then verify local HEAD, remote branch HEAD, and PR head agree.
- [ ] **Step 4: Write the receipt with the commit, tests, docs delta, PR state, and remaining uncertainty.
