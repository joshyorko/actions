# Canvas library frontend review receipt

Scope: read-only review of `McpCanvasView.tsx`, `semantic-renderer/canvas-library.tsx`, `canvas-library.test.tsx`, and producer contracts in `foundry/authoring.py`, `foundry/sql_authoring.py`, and `foundry/discovery.py`. No tracked files changed and no tests run in this review; parent reports RED 4 failed/11 passed and GREEN 16 passed, with hosted pinned reproduction.

## Concrete issue

- **The authoring-library parser omits the producer's 200-entry bound.** `sql_authoring.py` queries at most 201 rows and rejects over 200 (`open`, around lines 144-154), and the separate discovery producer caps `CanvasLibrarySnapshot.apps` at `MAX_LIBRARY_APPS = 200` (`discovery.py:28, 125-131`). `canvas-library.tsx:60-65` accepts any `applications` array length, while only the `apps` projection branch checks `<= 200` (`:121-128`). A malformed or incompatible `actions.canvas` authoring payload can therefore pass the 1 MiB byte limit and produce a larger DOM list than either producer contract permits. Mirror the 200-entry bound in `authoringLibrary` and add a focused 201-entry rejection test.

## Other review findings

- The authoring shape matches `_summary_result`: exact keys `applicationId`, `title`, and nullable `activeRevisionId`; its parser accepts null or a SHA-256 digest, and the UI displays entries without action controls.
- The discovery shape matches `CanvasLibraryDiscovery.open`: exact top-level `apps/currentApp/empty/emptyMessage`, exact projected app keys, and a 200 item bound. Projected CanvasSpecs are parsed by the existing strict `parseCanvasSpec`, titles must agree, IDs are unique, and `currentApp` must match an entry.
- The discriminator keeps authoring/discovery library shapes separate from app and preview shapes. App parsing still delegates to unchanged `parseCanvasViewMetadata`. Library results carrying appSession/reviewed/generic execution metadata are rejected. The library view renders no buttons or links and does not call server tools; transitions clear execution state in the event handler.
- No authorization or execution validation was weakened in the reviewed change. No other concrete issue found.

## Documentation improvement proposal

- **Canonical file proposed:** `docs/skills/repository-operations.md`, after the Canvas UI resource guidance near line 6493.
- **Exact delta:** append: “The model-facing `canvas_open` authoring result is `applications` with entries from `_summary_result` (`applicationId`, `title`, nullable `activeRevisionId`). The separate read-only `CanvasLibraryDiscovery` result is `apps`, `currentApp`, `empty`, and `emptyMessage`, with at most 200 app projections. A host UI adapter should discriminate these library shapes from strict app/preview metadata, retain the 200-entry bound for both shapes, reject execution metadata on library results, and render the list without controls or tool calls.”
- **Durable learning captured:** `canvas_open` has two distinct producer-backed shapes (authoring listing and read-only discovery projection); both have different entry field names but share the 200-entry safety bound, and neither grants execution.
- **Evidence:** `authoring.py:445-455,501-533`; `sql_authoring.py:144-154`; `discovery.py:28,125-131,155-224`; reviewed frontend parser/view and component tests.
- **Stale or ambiguous guidance removed:** none (proposal only).
- **Remaining uncertainty:** no new frontend suite was run; parent-provided GREEN 16 result is the verification evidence for the implemented feature.

Upstream disposition: none.
