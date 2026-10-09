# Proposed ADR 0100: MCP App authoring boundary for Canvas

- Status: Proposed; contract evidence only, no public-API implementation
- Issue: [joshyorko/actions#100](https://github.com/joshyorko/actions/issues/100)
- Dependencies: [#99](https://github.com/joshyorko/actions/issues/99) owns the
  CanvasSpec renderer/schema; MCP Apps authoring remains deferred behind
  [#125](https://github.com/joshyorko/actions/issues/125), per the latest
  #100 architecture comments.
- Evidence revision: `ab9b1aaa95aacc3b40c23e4fcd4749c79e3fae47`

This document records the present source boundaries and the smallest contract
that a later, authorized implementation would need to satisfy. It does not
settle the CanvasSpec schema source, define a Python/TypeScript generator, or
authorize implementation. The public MCP Apps authoring gap remains open.

## Decision boundary

Use the stable MCP Apps wire contract for the eventual authoring surface:
tools associate a UI resource through `_meta.ui.resourceUri`; the resource uses
`ui://` and is read through MCP `resources/read` with
`text/html;profile=mcp-app`. Keep ownership separated:

- `actions-core` / `actions.mcp` is the intended public Python authoring seam
  for declarative tool and resource declarations.
- `actions-runtime` owns the MCP server and resource serving behavior.
- #99 owns the versioned CanvasSpec and binding schema, its renderer, and its
  TypeScript-side consumption.
- The protocol specification remains the source for MCP Apps wire semantics;
  this ADR does not create a competing schema for Canvas UI content.

Do not add `actions.canvas`, a new distribution, a Canvas runtime in Core, or
Runtime/frontend dependencies to ordinary `@action` authoring. Do not choose a
JSON-Schema/Python-model/code-generation direction until #99 publishes a
versioned schema and demonstrates the cross-language contract. The eventual
Python authoring extension should remain optional and declarative; Runtime
execution and the Canvas renderer stay outside Core.

## #71 use case this contract serves

#71's product contract describes a stable Canvas facade whose tool calls render
the `ui://action-canvas/v1/canvas.html` view, with UI interactions using the
standard MCP App bridge. The authoring gap is therefore the association between
the stable tool and its UI resource, plus registration/serving of that resource.
Generated app data and binding schemas belong behind the stable facade and are
owned by #99's CanvasSpec contract. This does not require app-generated tools
to enter `tools/list`, a second server, or Canvas-specific authoring APIs for
ordinary Actions.

The existing public API is not yet that contract. In this snapshot,
`actions.mcp.@tool` accepts title and tool hints, and `@resource` accepts URI,
MIME type, and size; neither decorator exposes a public `_meta` argument or a
tool-to-resource UI association. Runtime tests that construct internal
`Action.options["_meta"]` directly prove that the MCP server can preserve
metadata, not that Python package authors have a supported public API. The
Canvas View Vite entry is only a placeholder boundary, and no `CanvasSpec` or
binding schema exists in the public Python or TypeScript source.

## Minimum future authoring contract

Once the #125 deferral clears and the schema contract in #99 is concrete, an
implementation proposal should cover only the supported public path:

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
5. The chosen versioned CanvasSpec/binding schema is consumed consistently by
   Python and TypeScript. Fixtures for Python -> JSON -> TypeScript round trips
   are gated on #99 selecting and publishing that schema; this ADR does not
   invent its fields.

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
  assigns the versioned CanvasSpec schema and renderer. The #125 body and
  comments are preserved in the evidence capture for this checkpoint.
- The stable protocol source cited by #100 is
  [MCP Apps specification 2026-01-26 at immutable commit `10195ad`](https://github.com/modelcontextprotocol/ext-apps/blob/10195ad91851502134930e9b80ec2c04e277a720/specification/2026-01-26/apps.mdx).

## Acceptance and remaining work

This ADR records architecture evidence, not issue completion. The live #100,
#71, #99, and #125 bodies/comments were read on 2026-10-09 and captured under
`architecture-evidence/issue-100/`. No Python API, Canvas schema, renderer,
runtime feature, generated fixture, or new distribution was added here.

Remaining before any authoring implementation: resolve #125's explicit
deferral; have #99 establish the versioned CanvasSpec/binding schema and
cross-language source of truth; then review a concrete public decorator/resource
API and its end-to-end installed-package conformance gates against the full
current #100 acceptance contract.
