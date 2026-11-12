Proposed canonical repository-operations.md addition:

The frontend npm test gate runs Runtime and Canvas suites, but a successful exit can include a skipped Python/TypeScript interchange test when its explicit fixture paths are absent. Report that conditional skip separately from test:quality's deliberate topology-name filter skips. Quality topology/UI-system counts repeat tests already in the full suite and must not be added as unique passes. Frontend unit/quality gates do not substitute for browser or authenticated host acceptance.

Verified against combined source a5eaa1cb: full359passed/1conditional skip; quality topology6passed/281filtered skips and UI-system6passed. No broader acceptance inference.
