# Proposed ADR 0100: MCP App authoring boundary for Canvas

- Status: Proposed; contract evidence only, no public-API implementation
- Issue: [joshyorko/actions#100](https://github.com/joshyorko/actions/issues/100)
- Coordination: [#99](https://github.com/joshyorko/actions/issues/99) owns the
  CanvasSpec semantic schema and renderer; #100 owns the canonical
  cross-language source-of-truth decision in coordination with #99. Public
  authoring implementation remains deferred behind
  [#125](https://github.com/joshyorko/actions/issues/125), per the latest
  #100 architecture comments.
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

Once the #125 deferral clears, an implementation proposal should coordinate
with #99 on the versioned semantic schema while retaining the #100
source-of-truth decision. It should cover only the supported public path:

1. A Python author can declare the UI resource URI associated with a tool using
   the MCP Apps metadata contract, without depending on Runtime or Canvas.
2. A Python author can declare the associated UI resource through the existing
   MCP resource authoring seam; Runtime advertises and serves it through
   standard `resources/list` and `resources/read`, including the specified
   MIME type.
3. The Runtime validates the declared association/resource relationship and
   returns conforming MCP metadata and resource content. The authoring package
   does not own HTTP routes, persistence, rendering, or transport lifecycle.
4. Ordinary `@action` users and Core installations without Canvas remain usable
   and acquire no Canvas-specific required dependency.
5. If #100 accepts this proposal, its versioned JSON Schema artifact defines
   the cross-language CanvasSpec serialization contract; #99 supplies semantic
   fields and the renderer. Python and TypeScript consume the same artifact.
   Golden fixtures prove Python -> JSON -> TypeScript round trips. This ADR
   does not invent CanvasSpec fields or claim those fixtures exist.

When implementation is authorized, acceptance must exercise an actual public
decorated Python package through the built/installed Core + Runtime path and
assert `tools/list`, `resources/list`, and `resources/read` results. Internal
`Action` construction alone is insufficient. Preserve Core's no-Canvas
dependency/install contract, and include the package-size and dependency
receipt required by #100.

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

## Acceptance and remaining work

This ADR records architecture evidence, not issue completion. The live #100,
#71, #99, and #125 bodies/comments were read on 2026-10-09 and captured under
`architecture-evidence/issue-100/`. No Python API, Canvas schema, renderer,
runtime feature, generated fixture, or new distribution was added here.

Remaining before any authoring implementation: coordinate #100's proposed JSON
Schema source choice with #99's semantic CanvasSpec fields and renderer; resolve
#125's explicit deferral; then review a concrete public decorator/resource API
and its end-to-end installed-package conformance and Python/JSON/TypeScript
round-trip gates against the full current #100 acceptance contract.
