# Shared Utilities

Shared utilities used by the Runtime application and future frontend apps.

This includes common types, utilities, and helpers.

Runtime HTTP state is queried through `src/queries/runtime.ts` and keyed by
`src/shared/runtime-query-keys.ts`. `RuntimeProviders` owns the single
TanStack `QueryClient`; WebSocket events only invalidate those keys through
`runtime-events.ts`, so reconnects and stale duplicate events cannot write a
second or older state store. The Canvas View entrypoint remains independent.
