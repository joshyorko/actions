# Canvas library result transition correction

The parent captured an actual ChatGPT desktop failure at pinned source46488e59:
authenticated discovery succeeded, `canvas_get` returned normal active app-spec
metadata, then `canvas_open` returned an `applications` list on the same UI
resource. Neither response carried app-session/reviewed/generic execution metadata.
The view displayed `Canvas content could not be validated.` No action executed.
[The transferred shapes](host-payload-shapes.json) preserve the trusted summary,
not raw host bytes; IDs/digests are redacted. Test fixtures use valid surrogate
identifiers with the same relationships and captured content.

The ordered component regression proves `canvas_get` renders independently and
the subsequent list hits the old app-only parser. Original RED was4failed/11passed.
The separate source discovery projection also needed a library branch; it was
an initial hypothesis about the host payload, not the actual captured shape.
An incorrect out-of-list negative fixture was corrected to use an absent ID and
a valid later-selection control was added. The actual ordered failure is unchanged.

Runtime a57 source adds a discriminated content state and strictly validated,
read-only library rendering for both existing producer shapes. The app/preview,
session and execution parsers are unchanged. Lists retain closed fields, nullable
inactive revisions, producer200-entry bounds, projected-spec validation, unique
identities and exact current-selection matching. Library execution contexts fail
closed; no controls, links, calls or grants are introduced. State transitions clear
prior app/execution state. The [review](review.md) found one missing authoring-list
bound; its RED1failed/16passed was retained before the matching bound and positive
empty/200-entry controls were added.

Complete frontend verification through RCC18.19.3 passed287 Runtime tests and,
before the final bound control,200 Canvas tests/1existing interchange skip.
Final Canvas suite passed203tests/1same skip. Final quality passed configured
ESLint, TypeScript, Prettier, topology6passed/281filtered and UI-system6passed.
All supervisors report no remaining owned processes. Lossless stdout and receipts
are adjacent. Clean a57 build/install is recorded separately when complete.

This reproduces and repairs the captured renderer transition at source level.
It does not establish an actual ChatGPT retest, invoice E1 or full campaign PASS.
Pinned Dakota wheels and all handoff files remain unchanged. The new candidate
is separate; no local plugin, tunnel, credential, public release or deployment
was changed. Documentation improvement: the canonical guide now records both
library producer shapes, strict read-only rendering and ordered host acceptance.
Upstream disposition:none; this is an Actions-owned mismatch.
