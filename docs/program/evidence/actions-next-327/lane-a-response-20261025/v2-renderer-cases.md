# V2 renderer cases prepared for accepted foundation

No executable contract-dependent code is committed. Use helper-owned exports and
projection-state types when supplied; do not derive readiness from execution
metadata or a resolved dispatch Promise.

## Structure ready to implement

- Exact v1 fixture still renders with unchanged serialization/digest; v2 card
  containing the existing six node types renders a titled section.
- Nested card/stack traversal counts both toward global node/depth limits;
  depth 8 accepted and 9 rejected, total 128 accepted and 129 rejected.
- Empty card renders its title; duplicate node IDs or undeclared bindings fail.
- v2 bar and line each expose a named visualization and equivalent accessible
  table using the same admitted rows and original order.
- v2 log is a named keyboard-scrollable ordered snapshot; not an aria-live whole
  history and no streaming subscription.
- v2 inspector is a named definition list exposing declared own fields only;
  inherited/undeclared keys, HTML strings and prototype-property names cannot
  create executable content or expand the declared projection.
- Unknown versions/nodes/properties reject truthfully; v1 nodes do not acquire
  v2 fields merely because the reader supports v2.

## Projection boundary cases, awaiting helper-owned normalized interface

- Chart 200 rows accepted / 201 rejected; label 256 code points accepted / 257 rejected;
  finite numbers only; canonical unsafe-integer/-0 decisions remain helper-owned.
- Log 500 accepted / 501 rejected; message 1024 code points accepted / 1025 rejected.
- Inspector 16 declared fields accepted / 17 rejected; string 4096 code points
  accepted / 4097 rejected; permitted scalar values only; unknown own fields hidden.
- All projections enforce 64KiB canonical UTF8 limit, including multibyte labels,
  astral characters and escaped JSON; no byte calculation using JS string length.
- Oversized or malformed payloads produce an error, never a plausible truncated
  chart/log/inspector; preserve prior error receipts.
- Distinct not-run/loading/error/empty/ready states consumed from helper-owned
  typed projection state. No inference from truthiness, metadata or array length
  before success is established.
- A response with matching binding but foreign Run/Attempt/revision must not
  replace current data. Resubmit/failure/auth denial invalidates old projections
  under the helper's authoritative lifecycle contract.

## Browser and lifecycle cases

- 320px/1280px, keyboard scrolling, focus visibility, headings/labels, readable
  tables and empty/error/loading states; system/host theme only after actual
  standard style-variable application is wired by its owner.
- Every v2 node mount and preview/audience projection has zero dispatch, fetch,
  artifact open or subscription. Count calls; do not infer from disabled controls.
- Scope/revision/Run/Attempt changes clear stale content; delayed previous
  response cannot repopulate the current view. Test through real adapter when
  helper provides the typed output/lifecycle join.
- Actual generated Python output, installed build resource and authenticated host
  are separate acceptance rows; synthetic projection tests cannot close them.

Pending foundation: exported v2 node/document union, strict bridge parse behavior,
normalized typed output/projection state and current Run/Attempt invalidation
semantics, canonical byte/Unicode/number rules. Card structure can start once
node types land; data nodes must not guess the unresolved projection interface.
