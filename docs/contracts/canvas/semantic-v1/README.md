# CanvasSpec v1

`../canvas-spec-v1.schema.json` is the public, cross-language semantic Canvas
contract. `canvas-spec-v1.fixture.json` is its canonical positive fixture;
the `invalid-*` fixtures exercise unresolved logical bindings, unknown fields,
and unsupported versions. Python validates the same files through the public
`actions.canvas_contract` module; the Canvas renderer consumes these exact
JSON bytes and the schema. The validator bounds canonical UTF-8 documents to
64 KiB, node nesting to 8, total nodes to 128, and logical binding IDs to 32.
Cross-field uniqueness and binding-reference checks are semantic rules in
addition to the JSON Schema structure.

The document is declarative. V1 nodes are `stack`, `text`, `form`, `table`,
`status`, and `artifact`; the closed node vocabulary has no HTML, JavaScript,
Python, URL, filesystem path, or executable expression fields. Renderers treat
text as text and do not invoke bindings while showing a static preview.

`stack.children` preserves layout order. A `form` contains bounded fields with
text, integer, or boolean types; their names are the submitted JSON keys, and a
dispatch adapter receives them only after explicit submit. `table.rowsKey`
selects the row array and each column's `key` selects a plain property. `status`
projects that binding's pending/result/error state. An `artifact` label names a
result artifact for the runtime's typed artifact adapter; the Canvas document
never contains an artifact URL or grants access.

`bindingIds` and each node's `bindingId` are logical names only. Runtime code
resolves them against server-owned typed capability references and applies
Workspace, Deployment, and authorization policy. A CanvasSpec never embeds
those common IDs and a binding label does not grant access. The `visibility`
array preserves the MCP Apps `model` and `app` audience projection; it is not
backend authorization.

The Python model is frozen and serializes to canonical UTF-8 JSON. Revisions
are immutable bytes supplied to the owning lifecycle API; the CanvasSpec does
not repeat Workspace, Deployment, or Package revision identities.

Public document validation uses the schema's camelCase keys exactly:
`CanvasSpec.from_json` and `validate_canvas_spec` reject Python field names such
as `schema_version` and `binding_id`. Python callers that prefer field names
can use `CanvasSpec.from_python`. An empty `visibility` list means no host
audience and must remain empty; it is neither expanded to a default nor an
authorization decision.
