# Runtime Data Access Implementation Plan

> **For agentic workers:** Inline execution in the authorized worktree; no delegated writer.

**Goal:** Make Runtime HTTP state typed and canonical in TanStack Query, with WebSocket events acting only as freshness signals.

**Architecture:** Add a small typed Runtime API and stable key module, expose the existing Runtime `QueryClient` as the sole cache authority, and adapt the existing WebSocket events to invalidate or safely update those keys. Keep the existing Runtime context as a compatibility projection for current pages and leave the independent Canvas entrypoint untouched.

**Tech Stack:** React 18, TypeScript, TanStack Query v5, Vitest, existing WebSocket transport.

## Global Constraints

- Scope only frontend Runtime HTTP/query/event paths and focused tests/documentation.
- Do not add dependencies, change backend contracts, or modify Canvas behavior.
- Tests precede production changes; preserve `.serena/` and `.codex/`.
- Keep production changes within the requested path budget.

### Task 1: Typed Runtime contracts and RED acceptance

**Files:**
- Create: `action_server/frontend/src/shared/runtime-api.test.ts`
- Create: `action_server/frontend/src/shared/runtime-query-keys.test.ts`
- Create: `action_server/frontend/src/shared/runtime-events.test.ts`

- [ ] Write tests for typed list/detail/mutation/error/cancellation behavior, stable keys, one cache authority, event freshness, duplicate/out-of-order events, and Runtime/Canvas boundaries.
- [ ] Run the focused Vitest files and confirm failure because the new modules do not exist.

### Task 2: Implement the canonical Runtime data layer

**Files:**
- Create: `action_server/frontend/src/shared/runtime-api.ts`
- Create: `action_server/frontend/src/shared/runtime-query-keys.ts`
- Create: `action_server/frontend/src/shared/runtime-events.ts`
- Create: `action_server/frontend/src/queries/runtime.ts`
- Modify: `action_server/frontend/src/app/RuntimeProviders.tsx`
- Modify: `action_server/frontend/src/shared/context/actionServerContext.ts`
- Modify: `action_server/frontend/src/shared/api-client.ts`
- Modify: `action_server/frontend/src/core/pages/Actions.tsx`
- Modify: `action_server/frontend/src/core/pages/RunHistory.tsx`

- [ ] Implement typed request/error/signal handling and canonical keys.
- [ ] Replace the import-time model store with Query-backed context projection and event invalidation.
- [ ] Route action/run refreshes through the same QueryClient.
- [ ] Run focused tests and configured frontend checks.

### Task 3: Durable evidence and handoff

**Files:**
- Modify: `action_server/frontend/src/shared/README.md`
- Modify: `docs/skills/repository-operations.md`
- Create: `/tmp/actions-pr110-implementation-receipt.txt`

- [ ] Document only verified Runtime cache/event behavior and exact gates.
- [ ] Run builds, bundle/artifact checks applicable to the changed Runtime path, `git diff --check`, and inspect the final diff budget.
- [ ] Commit one descendant, push normally, verify local/remote/PR SHA, and update PR #110 without merging.
