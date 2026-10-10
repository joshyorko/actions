# Proposed ADR 0100: MCP App authoring boundary for Canvas

- Status: Proposed; contract evidence only, no public-API implementation
- Issue: [joshyorko/actions#100](https://github.com/joshyorko/actions/issues/100)
- Coordination: [#99](https://github.com/joshyorko/actions/issues/99) owns the
  CanvasSpec semantic schema and renderer; #100 owns the canonical
  cross-language source-of-truth decision in coordination with #99. #100-A
  owns the small public MCP Apps authoring contract; #100-B owns CanvasSpec
  serialization. Verify each implementation's consumed package, SDK,
  template, and security criteria on the actual candidate instead of treating
  unrelated #125 work as a blanket prerequisite.
- Evidence revision: `ab9b1aaa95aacc3b40c23e4fcd4749c79e3fae47`

This document records the present source boundaries, proposes the
cross-language schema source-of-truth decision owned by #100, and defines the
smallest contract that a later, authorized implementation would need to
satisfy. It does not define CanvasSpec fields or authorize implementation. The
public MCP Apps authoring gap remains open.

## Decision boundary

Use the stable MCP Apps wire contract for the eventual authoring surface:
tools associate a UI resource through `_meta.ui.resourceUri`; the resource uses
`ui://` and is read through MCP `resources/read` with
`text/html;profile=mcp-app`. Keep ownership separated:

- `actions-core` / `actions.mcp` is the intended public Python authoring seam
  for declarative tool and resource declarations.
- `actions-runtime` owns the MCP server and resource serving behavior.
- This ADR proposes that #100 select one versioned JSON Schema artifact as the
  canonical cross-language CanvasSpec contract. Python and TypeScript would
  consume that same schema. If language-specific models are introduced, they
  must conform to it; this ADR does not choose handwritten versus generated
  models or a code-generation direction.
- #99 owns CanvasSpec semantic fields, UI binding declarations, and the
  TypeScript renderer, coordinating its schema work with #100's source choice.
- Provider bindings for secrets, OAuth, data, artifacts, and queues continue to
  consume the shared contracts named by #71 (#129/#87/#131/#132); they do not
  become Canvas-only schema semantics owned by #99.
- The protocol specification remains the source for MCP Apps wire semantics;
  this ADR does not create a competing schema for Canvas UI content.

Do not add `actions.canvas`, a new distribution, a Canvas runtime in Core, or
Runtime/frontend dependencies to ordinary `@action` authoring. If accepted,
the proposed JSON Schema decision would resolve #100's source-of-truth choice
without moving CanvasSpec semantics out of #99 or requiring duplicate Python
model authority. The eventual Python authoring extension should remain optional
and declarative; Runtime execution and the Canvas renderer stay outside Core.

## Source-of-truth options

The proposal prefers one canonical JSON Schema artifact shared by Python and
TypeScript. It matches #99's semantic schema boundary and avoids placing
CanvasSpec models or dependencies in Core. Python models exported as JSON
Schema would favor typed Python authoring, but would make generated schemas a
second language/toolchain contract for TypeScript and require compatibility
tests for that conversion. One-way code generation could provide typed models
to one consumer, but adds a generator, pinned toolchain, stale-output checks,
and generated-file review without evidence that either consumer needs it. No
such generator or public CanvasSpec model exists in the cited source snapshot.

This is a recommendation, not an accepted architecture. Even if accepted,
schema conformance, validator choice, compatibility/version rules, and real
Python -> JSON -> TypeScript round trips still need implementation evidence.

For the first #99 fixture, the current bounded reuse direction is a thin
Actions-owned React renderer using existing owned UI primitives and the
official ext-apps bridge. This is a recommendation pending a working fixture,
not proof or a generic grammar freeze. Inspection found json-render React peers
compatible but its Zod catalog would need a JSON Schema adapter; A2UI would add
message/user-action profile mapping and has a distinct specification/package
version boundary. Those alternatives were inspected, not integrated or tested.
The selected small fixture must still prove interoperability, offline/CSP
behavior, accessibility, typed dispatch, and license/dependency compatibility
before the renderer choice is accepted. The inspected json-render candidate is
Apache-2.0 [`v0.21.0`](https://github.com/vercel-labs/json-render/tree/3ad381881194e7011ad3ccd6d668033495a06c29);
the inspected A2UI sources are Apache-2.0 protocol [`v0.9`](https://github.com/google/A2UI/tree/19919ef4c8ad3185867f70386fa4669284d7714c)
and React/core packages `@a2ui/react@0.9.1` / `@a2ui/web_core@0.9.2`. No
candidate package was installed and no fixture was rendered.

## #71 use case this contract serves

#71's product contract describes a stable Canvas facade whose tool calls render
the `ui://action-canvas/v1/canvas.html` view, with UI interactions using the
standard MCP App bridge. The authoring gap is therefore the association between
the stable tool and its UI resource, plus registration/serving of that resource.
CanvasSpec's semantic UI fields and UI binding declarations are #99's scope;
provider bindings consume shared contracts (#129/#87/#131/#132) as #71's latest
comment requires. This does not require app-generated tools to enter
`tools/list`, a second server, or Canvas-specific authoring APIs for ordinary
Actions.

The existing public API is not yet that contract. In this snapshot,
`actions.mcp.@tool` accepts title and tool hints, and `@resource` accepts URI,
MIME type, and size; neither decorator exposes a public `_meta` argument or a
tool-to-resource UI association. Runtime tests that construct internal
`Action.options["_meta"]` directly prove that the MCP server can preserve
metadata, not that Python package authors have a supported public API. The
Canvas View Vite entry is only a placeholder boundary, and no `CanvasSpec` or
binding schema exists in the public Python or TypeScript source.

## Minimum future authoring contract

The #100-A public authoring slice can be implemented independently of the
complete CanvasSpec renderer, while retaining #100 ownership of the
cross-language source-of-truth proposal and coordinating semantic fields with
#99. It should cover only the supported public path:

1. A Python author can declare the UI resource URI associated with a tool using
   the MCP Apps metadata contract, without depending on Runtime or Canvas.
   The public `meta` input is a detached, bounded JSON snapshot: reject cycles,
   non-finite numbers, non-string object keys, excess depth/size, and malformed
   supported `ui.resourceUri`, `ui.visibility`, or `ui.csp` values. Preserve
   unrelated namespaced JSON metadata for compatible extensions. Visibility
   must never grant backend authorization.
2. A Python author can declare the associated UI resource through the existing
   MCP resource authoring seam with `ui://` identity and
   `text/html;profile=mcp-app`; Runtime serves it through `resources/read` at
   its advertised URI. Do not require UI-only resources to appear in
   `resources/list`; the stable Apps contract permits that omission.
3. Before atomic catalog publication, Runtime verifies that each tool
   association resolves to the declared UI resource with the required MIME
   type. Missing or wrong-type resources fail the new catalog and leave the
   previous catalog active.
4. The Runtime returns conforming MCP metadata and resource content. The
   authoring package does not own HTTP routes, persistence, rendering, or
   transport lifecycle. App-only visibility is a host/catalog routing
   declaration, not backend authorization. A particular host's renderer or
   optional host-projection behavior is a separate conformance gate.
5. Ordinary `@action` users and Core installations without Canvas remain usable
   and acquire no Canvas-specific required dependency.
6. If #100 accepts this proposal, its versioned JSON Schema artifact defines
   the cross-language CanvasSpec serialization contract; #99 supplies semantic
   fields and the renderer. Python and TypeScript consume the same artifact.
   Golden fixtures prove Python -> JSON -> TypeScript round trips. This ADR
   does not invent CanvasSpec fields or claim those fixtures exist.
7. Keep these identities separate in implementation and release receipts: core
   MCP protocol version, Python MCP SDK version, MCP Apps wire version,
   `@modelcontextprotocol/ext-apps` package version, and CanvasSpec version.
   One does not imply or substitute for another.

The #100-A checkpoint must exercise an actual public-decorated Python package
through the real Core-source/Runtime-candidate path and assert `tools/list` and
`resources/read`; internal `Action` construction alone is insufficient. Its
source-pairing result is not published-wheel compatibility. Keep text and
structured Action outputs explicit in tests. This first slice does not prove
that one rich result can carry complete `content`, `structuredContent`, and
`_meta` together; that full result-preservation acceptance remains open.
Preserve Core's no-Canvas dependency/install contract and include package-size
and dependency evidence before any publication claim.

## Evidence at the cited revision

- Public decorator signatures and argument validation:
  [`actions.mcp.@tool`](https://github.com/joshyorko/actions/blob/ab9b1aaa95aacc3b40c23e4fcd4749c79e3fae47/actions/src/actions/mcp/__init__.py#L54-L180)
  and [`actions.mcp.@resource`](https://github.com/joshyorko/actions/blob/ab9b1aaa95aacc3b40c23e4fcd4749c79e3fae47/actions/src/actions/mcp/__init__.py#L190-L301).
- Runtime consumes internal `_meta`, applies it to tool/resource objects, and
  preserves result metadata:
  [`setup_mcp_server_v2.py`](https://github.com/joshyorko/actions/blob/ab9b1aaa95aacc3b40c23e4fcd4749c79e3fae47/action_server/src/actions/server/mcp/setup_mcp_server_v2.py#L381-L420)
  and [internal-metadata tests](https://github.com/joshyorko/actions/blob/ab9b1aaa95aacc3b40c23e4fcd4749c79e3fae47/action_server/tests/action_server_tests/mcp/test_setup_mcp_server.py#L217-L335).
- The independent Canvas View entry is a placeholder, and its HTML carries
  only the artifact content-type marker:
  [`main.tsx`](https://github.com/joshyorko/actions/blob/ab9b1aaa95aacc3b40c23e4fcd4749c79e3fae47/action_server/frontend/apps/canvas-view/src/main.tsx#L1-L14)
  and [`index.html`](https://github.com/joshyorko/actions/blob/ab9b1aaa95aacc3b40c23e4fcd4749c79e3fae47/action_server/frontend/apps/canvas-view/index.html#L1-L12).
- #100 comments
  [5283421605](https://github.com/joshyorko/actions/issues/100#issuecomment-5283421605),
  [5320598118](https://github.com/joshyorko/actions/issues/100#issuecomment-5320598118),
  and [5320625322](https://github.com/joshyorko/actions/issues/100#issuecomment-5320625322)
  define the decision and clarify its MCP Apps scope/dependency. #71's latest
  comment [5324901913](https://github.com/joshyorko/actions/issues/71#issuecomment-5324901913)
  keeps Canvas as a consumer of shared package/deployment contracts. #99's
  comment [5283411258](https://github.com/joshyorko/actions/issues/99#issuecomment-5283411258)
  assigns versioned CanvasSpec semantic schema and renderer work to #99; #100's
  first comment [5283421605](https://github.com/joshyorko/actions/issues/100#issuecomment-5283421605)
  owns the source-of-truth choice and round-trip acceptance. The #125 body and
  comments are preserved in the evidence capture for this checkpoint.
- The stable protocol source cited by #100 is
  [MCP Apps specification 2026-01-26 at immutable commit `10195ad`](https://github.com/modelcontextprotocol/ext-apps/blob/10195ad91851502134930e9b80ec2c04e277a720/specification/2026-01-26/apps.mdx).
- The current candidate `3fee279256e674c9cbe0eaeaf2f98e01f51cd08d` retains
  the public decorator gap at
  [`actions.mcp`](https://github.com/joshyorko/actions/blob/3fee279256e674c9cbe0eaeaf2f98e01f51cd08d/actions/src/actions/mcp/__init__.py)
  while Runtime v2 accepts internal `_meta` during collected-action
  registration and publishes a complete catalog through a pointer swap in
  [`setup_mcp_server_v2.py`](https://github.com/joshyorko/actions/blob/3fee279256e674c9cbe0eaeaf2f98e01f51cd08d/action_server/src/actions/server/mcp/setup_mcp_server_v2.py).
  That source pairing is not published-wheel compatibility evidence.

## Acceptance and remaining work

This ADR records architecture evidence, not issue completion. The live #100,
#71, #99, and #125 bodies/comments were read on 2026-10-09 and captured under
`architecture-evidence/issue-100/`. No Python API, Canvas schema, renderer,
runtime feature, generated fixture, or new distribution was added here.

Remaining after a #100-A implementation checkpoint: hosted/source-to-wheel
consumer verification, a Core package-size/dependency receipt, rich MCP result
preservation, the #100-B schema/version/round-trip contract, the selected #99
fixture proof, and separate host acceptance. The #125 record is still relevant
where an implementation consumes its package/template/security boundaries,
but is not a blanket prerequisite to this authoring slice.
