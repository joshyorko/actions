# SDK mock correction

After parent/integrator explicitly allocated the narrow test fix, added only
`useHostStyleVariables: vi.fn(),` to the SDK mock return object in
`action_server/frontend/apps/canvas-view/src/semantic-renderer/mcp-bridge.test.tsx`.
No shared production bridge/types changed. Local v2 commit80f8b8ce remains unchanged.

The same RCC18.19.3 full Canvas command from receipt.md now passes140 tests with
one existing Python interchange skip. All15 test files pass, including the eight
previously failing bridge cases. Original failures remain in v2-final-canvas files.

This closes the mock gate only. Runtime auth/freshness/installed E2 remain outside
these synthetic consumer and local SDK host checks. Canonical guide proposal and
Upstream disposition remain as recorded in receipt.md.
