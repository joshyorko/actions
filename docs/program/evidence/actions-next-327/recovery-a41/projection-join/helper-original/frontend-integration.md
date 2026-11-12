New files only. API: createGeneratedProjectionController(changed) returns getProjection(bindingId), begin(bindingId) -> requestId, fail(bindingId,requestId), and async load(bindingId,requestId,execution,readAuthorizedProjection).

Call begin on every submit BEFORE dispatch; retain returned generation in the trusted adapter closure. Call load only after the matching trusted execution has succeeded with exact Run/Attempt, supplying a loader for the app-only canvas_projection tool that extracts actions.projection. Call fail on dispatch/read/auth denial and when clearing the current request. Construction/getter never read or mutate Runtime. Renderer rerenders through changed. Run/Attempt/request generation remain adapter-owned, never taken from arbitrary dispatch metadata.

Wire requires exactly bindingId/runId/attemptId/canonicalJson/data. Data is parsed solely from bounded canonicalJson, exact canonical re-encoding rejects duplicate keys/noncanonical spelling/NFC violations/nonportable numbers/Unicode, wire data must canonicalize identically; recursive freeze prevents local mutation. Zero and false are ready; null and empty arrays are empty.

Focused test config is included outside source. Existing semantic-renderer/vitest.config.ts selects only *.test.tsx: integrator must include this new *.test.ts in its selected inventory/config. No dependencies added.

25 focused Vitest cases plus ESLint, strict tsc, and Prettier passed. Four Python canonicalize_json pairs independently cross-check NFC, astral-vs-BMP UTF16 sorting, numeric formatting/-0/safe-integer edge, and integer-looking object keys. This is not installed/client/browser acceptance.
