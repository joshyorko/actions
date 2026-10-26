# Proposed minimal semantic extension — integrator decision required

This is a proposal only; no schema, bridge, Python contract, authoring, registry,
package metadata or renderer node union was changed by Lane A.
The proposed derived JSON Schema passes Draft202012Validator.check_schema and
a four-node example validates in package-local Python; see proposal-schema.log.txt.
That mechanical check does not qualify production validators or renderer behavior.

## Compatibility

Current v1 is closed: `actions/src/actions/canvas_contract/_models.py` forbids
extra properties and uses a six-member discriminated union and exact version.
`mcp-bridge.ts` checks exact keys/version; `components.tsx::isRenderableSpec`
also requires v1. Optional new properties or nodes under v1 would not work on
existing consumers.

Propose `actions.canvas-spec/v2`, with readers accepting both unchanged v1 and v2.
Existing v1 serialization and retained revision digests remain unchanged. Old
readers explicitly refuse v2; never silently drop nodes, auto-upgrade retained
revisions, or claim forward compatibility. Integrator owns the version decision
and all associated package/artifact compatibility qualification.

## Exact proposed schema delta

Keep v1's canonical artifact unchanged. Derive a v2 artifact by copying its
envelope/definitions and changing `$id` to `urn:actions:canvas-spec:2`,
`properties.schemaVersion.const` to `actions.canvas-spec/v2`, and the description
to identify v2. Append four local references to `$defs.CanvasNode.oneOf`:
`CanvasCard`, `CanvasChart`, `CanvasLog`, `CanvasInspector`. All existing local
references in the copied schema remain local, so stacks/cards can contain any
v2 node. Add exactly these definitions:

```json
{
  "ShortText": { "type": "string", "minLength": 1, "maxLength": 256 },
  "CanvasCard": {
    "type": "object", "additionalProperties": false,
    "required": ["type", "id", "title", "children"],
    "properties": {
      "type": { "const": "card" },
      "id": { "$ref": "#/$defs/Identifier" },
      "title": { "$ref": "#/$defs/ShortText" },
      "children": { "type": "array", "maxItems": 128, "items": { "$ref": "#/$defs/CanvasNode" } }
    }
  },
  "CanvasChart": {
    "type": "object", "additionalProperties": false,
    "required": ["type", "id", "title", "bindingId", "rowsKey", "chartType", "labelKey", "valueKey"],
    "properties": {
      "type": { "const": "chart" },
      "id": { "$ref": "#/$defs/Identifier" },
      "title": { "$ref": "#/$defs/ShortText" },
      "bindingId": { "$ref": "#/$defs/Identifier" },
      "rowsKey": { "$ref": "#/$defs/Identifier" },
      "chartType": { "enum": ["bar", "line"] },
      "labelKey": { "$ref": "#/$defs/Identifier" },
      "valueKey": { "$ref": "#/$defs/Identifier" }
    }
  },
  "CanvasLog": {
    "type": "object", "additionalProperties": false,
    "required": ["type", "id", "title", "bindingId", "rowsKey", "messageKey"],
    "properties": {
      "type": { "const": "log" },
      "id": { "$ref": "#/$defs/Identifier" },
      "title": { "$ref": "#/$defs/ShortText" },
      "bindingId": { "$ref": "#/$defs/Identifier" },
      "rowsKey": { "$ref": "#/$defs/Identifier" },
      "messageKey": { "$ref": "#/$defs/Identifier" }
    }
  },
  "CanvasInspector": {
    "type": "object", "additionalProperties": false,
    "required": ["type", "id", "title", "bindingId", "valueKey", "fields"],
    "properties": {
      "type": { "const": "inspector" },
      "id": { "$ref": "#/$defs/Identifier" },
      "title": { "$ref": "#/$defs/ShortText" },
      "bindingId": { "$ref": "#/$defs/Identifier" },
      "valueKey": { "$ref": "#/$defs/Identifier" },
      "fields": {
        "type": "array", "minItems": 1, "maxItems": 16,
        "items": { "$ref": "#/$defs/CanvasTableColumn" }
      }
    }
  }
}
```

Retain existing Identifier syntax, 64 KiB canonical spec, depth 8, 128 nodes,
32 bindings, unique IDs and binding-reference validation. Extend tree traversal
to card children. Enforce unique inspector field keys as table column keys are
already enforced. No URLs, expressions, CSS, tool names or nested property paths.

## Proposed projection and renderer contract

Use the existing renderer and scoped binding result map. No new authority-bearing
adapter, dispatch, fetch, polling or subscription on mount. Read own properties
only. Distinguish absent/not-run data from a successful empty result, malformed
data and unavailable binding. Preserve audience, preview and scope-remount rules.

| Node | Renderer and bounded admitted result |
|---|---|
| Card | Titled accessible section wrapping children; counts toward existing tree limits. |
| Chart | Bar/line visualization plus equivalent accessible table; <=200 rows, string labels <=256 code points, finite numeric values, source order. |
| Log | Titled keyboard-scrollable ordered snapshot; <=500 rows, message strings <=1,024 code points. No whole-history live announcement and no streaming claim. |
| Inspector | Titled definition list; own plain-object value, declared fields only, scalar string/finite number/boolean/null, string <=4,096 code points. |

For each data projection, propose <=64 KiB canonical UTF-8 data; reject malformed
or oversized projections truthfully without silently partial charts. These data
limits require integrator/product acceptance; they are not current guarantees.
Long-running/streaming status remains the existing durable execution plane's
responsibility. A snapshot log component does not satisfy future streaming UX.

## Owned changes and small checkpoints

Integrator owns new canonical schema, Python models/exports/validation and
round-trip tests, `types.ts`, strict `mcp-bridge.ts`, renderer version admission,
authoring/serializer assumptions and version/artifact metadata. Lane A can consume
the accepted contract within `components.tsx`/CSS/dedicated tests, beginning with
card composition, then one shared bounded projection helper for the three data
views. Do not build a second renderer or duplicate backend storage/authorization.

Qualify unchanged v1 fixtures/digests, v2 round trips, old-reader rejection,
unknown versions/features, size/depth/identity limits, empty/error/loading states,
keyboard/mobile/offline behavior and no mount side effects. Then independently
qualify actual generated Python result delivery and installed host artifacts.
Synthetic data-view success cannot prove that backend join or full #71 acceptance.

## Exact canonical-guide proposal

Append to `docs/skills/repository-operations.md`:

> CanvasSpec v1 is a closed contract: Python rejects extra fields and unknown node
> discriminators, while the frontend bridge checks exact keys and version. Adding
> optional fields or node types under the same version is not compatible with
> existing clients. Preserve v1 serialization and retained revision digests;
> introduce a separately identified extension with explicit reader support,
> retain v1 acceptance, and test old-reader rejection. Rendered fixtures prove
> presentation only; bounded result projection, genuine backend delivery and
> installed-host acceptance remain separate gates.

Evidence: current strict Python models, frontend parseSpec/parseNode and
isRenderableSpec at base `82bbaef7f650f02097e9dd3fae968b1c3e459048`.
Learning: additive syntax under the same discriminator is not compatible with
these existing closed readers. Uncertainty: final version, data limits and host
result wiring require integrator decisions. No shared guide was edited.

Upstream disposition: none.
