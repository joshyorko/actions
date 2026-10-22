# Action Canvas integration handoff

Goal: implement the original #71 first-boot authoring vertical through the
existing Runtime, semantic View, common Package/Deployment and Run services.

Authority: Josh confirmed parallel Actions foundry implementation on October 22
at 21:59:51 UTC. The coordinator owns cloud dispatch; this lane is the sole
writer of release/327-invoice-vertical-20261020 and draft #328. This supersedes
the earlier read-only scope-choice hold. It grants no merge, external package or
image publication, deployment, production, live credential/auth/tunnel change,
or other-repository mutation.

Protected baseline: `e2408a6e3051cdb4c44aede47618c3791807eba5`. Its invoice proof,
candidate bundle, source-specific receipts and failed/skip classifications stay
addressable. The coordinator reports all 13 workflows green at that head; this
does not qualify the new foundry or authenticated ChatGPT E1.

This handoff allocates files and integration contracts in the existing issue
graph. It is not a replacement tracker. Issue bodies and their October 9/10
amendments remain the acceptance authority.

## Exclusive ownership

| Lane | Files | Shared-file boundary |
| --- | --- | --- |
| #100 public spec | New Core semantic authoring module/tests; `docs/contracts/canvas/canvas-spec-v1.schema.json` and new schema fixtures | Existing Core exports, versions and dependency locks remain integration-owned. Historical owner review found no live owner; coordinator admitted the replacement lane. |
| #99-A renderer | New `action_server/frontend/apps/canvas-view/src/semantic-renderer/**` and colocated tests | No existing entrypoint, invoice component or shared build edits. Integration owns `McpCanvasView.tsx` and contract adaptation. |
| #130/#135 compiler | New existing-architecture compiler/manifest modules under `action_server/src/actions/server/deployments/` and new compiler tests | Reuse source_manifest/read/staging and existing Package schemas. No shared migration, legacy loader, Run or deployment-pointer edits. |
| #129 deployment | New `deployments/foundry_values.py`, `foundry_repository.py`, `foundry_service.py`; `tests/action_server_tests/test_foundry_deployments.py` | Use a borrowed Runtime Database and existing canonical refs. Supply model/DDL needs to integration. No private DB, global migration edits or Run-store replacement. |
| #71 authoring | New `foundry/authoring.py`, `authoring_values.py`; `tests/action_server_tests/test_foundry_authoring.py` | Consume spec/compiler/deployment ports. No private persistence, central MCP registration or duplicate package/queue authority. |
| #99-B/#127 boot/template | New `foundry/boot.py`, `discovery.py`, their tests and new template fixtures/files | Existing CLI and template manifest/bundle wiring remain integration-owned. External plugin-repository changes require a separate handoff. |
| Integration | Shared models/migrations/DB wiring, central MCP/server/CLI, existing Canvas lifecycle/entrypoint, Run/Work Item/output seams, versions/locks/toolkit/CI and canonical guides | Review exact worker source, import provenance and tests before convergence. No worker edits another lane or the integration branch. |

Workers return exact tested commits and proposed canonical-guide deltas. The
integration owner edits shared guides to avoid concurrent changes to the same
large file. No lane independently builds changed release artifacts under the
published Runtime1.0.4/SDK0.4.4/Core identifiers or an earlier candidate's bytes.
Integration admits provisional versions before candidate wheel verification.

## Minimal spec proposal for owner review

The #100 lane owns the canonical schema and final validation implementation.
This proposal prevents competing protocols; coordinated changes must update the
renderer/authoring fixtures before any interface is considered frozen.

```json
{
  "schemaVersion": "actions.canvas-spec/v1",
  "title": "Application title",
  "bindingIds": ["search"],
  "root": {"type": "stack", "id": "main", "children": []}
}
```

First semantic nodes:

| Type | Required data beyond `type`/`id` |
| --- | --- |
| stack | `children`: bounded nodes |
| text | `text`: bounded plain text |
| form | `bindingId`, `fields`, `submitLabel`; each field has `name`, `label`, `type` in text/integer/boolean and an explicit required flag |
| table | `bindingId`, `rowsKey`, `columns`; columns select bounded plain property keys and labels |
| status | `bindingId` |
| artifact | `bindingId`, `label` |

Proposed limits: 64 KiB serialized spec, depth 8, 128 nodes, 32 bindings, unique
node/binding IDs. Unknown required versions/features and undeclared bindings
fail. A spec contains logical binding IDs only, never provider URLs, filesystem
paths, tool names, Python, credentials or executable expressions. The server
resolves those IDs to authorized typed capabilities. Defaults and result data
must not become cached renderer HTML or implicit execution on mount.

Core serialization is not authoritative Package/Deployment identity hashing.
Runtime consumes the existing canonical JSON service for protected identities.
Renderer consumers use the accepted schema/fixtures, not a second vocabulary.
The integration-owned `src/canvas-contract/**` seam can adapt validation/types
without giving #100 and #99 overlapping frontend ownership.

## Backend integration ports

Use existing Actor, WorkspaceId, PackageRevisionRef, DeploymentRevisionRef,
RuntimePlanRef and ExecutionSnapshot values. The following semantic envelopes
are review targets, not a new portable manifest syntax.

1. Compiler input is an explicitly selected, measured staged source inventory
   plus trusted build policy. Output is immutable canonical portable manifest
   bytes, source identity, capability declarations, declared runtime plans and
   build evidence. Portable bytes contain no installation Workspace, resolved
   binding values, credentials or worker-local paths. Compiler does not insert
   deployment rows or advance activation.
2. Deployment service receives actor/Workspace, a verified compiled revision,
   logical binding resolution, expected base revision and idempotency key.
   Resolution returns the exact pinned ExecutionSnapshot for an authorized
   capability. Missing adapter or policy never selects a fallback plan.
3. Authoring create/get/apply/preview/inspect/release consume those ports. Apply
   stages UI and, when explicitly requested, generated backend bytes. Release
   requires successful validation/build and compare-and-swap activation. A
   failed stage/build leaves the accepted active revision addressable. The
   authoring lane does not own another database or scheduler.
4. Final visible Package/Deployment/app selection and common Run admission use
   the Runtime SQL authority. Immutable source/UI blobs may be staged first;
   they are inaccessible until admitted references authorize them. Do not add
   competing active pointers across a Canvas side database and the common
   Deployment store. Integration reviews the storage adapter/transaction before
   wiring the services together; the existing private invoice profile remains
   supported.
5. A long build uses existing Run/Attempt evidence and returns inspectable
   identity; no Canvas build queue or internal LLM loop. Backend generation is
   external-model authored, trusted-developer code in confined staged files.
   RCC and iframe isolation are not backend Python security sandboxes.

## MCP and renderer boundary

One Runtime exposes six fixed model-visible authoring names:
`canvas_create`, `canvas_get`, `canvas_apply`, `canvas_preview`,
`canvas_inspect`, `canvas_release`. A separate read-only `canvas_open` accepts
exactly `{}` and opens the app library/current app. It never creates, applies,
releases, queries, approves or executes. Generated operations do not grow the
model catalog.

The integration adapter owns app-only typed dispatch, manifest/state, execution
status, cancellation and artifact access. Every operation uses trusted actor
context and exact authorized app/revision/binding/Run scope. UI visibility and
possession of an app ID or artifact handle are not authorization. Additional
query/page projections require actual named-operation conformance rather than
placeholder success.

Use the same stable `ui://action-canvas/v1/canvas.html` resource with versioned,
cache-safe renderer bytes and `text/html;profile=mcp-app`. Authorized initial
state travels in complete MCP result metadata; do not refetch/execute simply
because the View opened. A pure semantic renderer receives the validated spec
and injected typed dispatch/status/artifact adapters. It does not select an
arbitrary server tool/URL or persist authoritative business state.

## Integration tasks and verification

- [ ] Record reviewed owner contracts/fixtures and exact worker heads. Keep
  parent dispatch and the existing issue graph authoritative.
- [ ] Add central stable MCP/resource registration tests before implementation:
  empty user-package catalog, fixed model names, app-only caller denial,
  read-only empty-input launcher, reserved-name/resource collisions, complete
  result metadata and useful unsupported-operation failures.
- [ ] Implement shared Runtime SQL/model wiring against reviewed compiler and
  deployment values. Test concurrent CAS, changed-input idempotency conflict,
  cross-Workspace/revision denial, SQL rollback and fresh-interpreter reopen.
- [ ] Join the semantic renderer to the same adapter; run real browser tests
  without intercepted backend replies. Preserve invoice rendering/review tests.
- [ ] Prove existing-capability first-boot composition, then separately prove
  externally authored Python -> common immutable Package/Deployment -> real RCC
  Run/result -> revise -> failed validation -> rollback -> restart.
- [ ] Run pinned Doctor/Bootstrap/ToolkitTest and affected package/static/real
  SQL/installed-candidate/browser gates at frozen source. Recheck imports and
  artifact/source hashes. Preserve failures, skips and platform applicability.
- [ ] Push reviewed nonforce checkpoints to the assigned integration branch;
  update the existing issues/PR with exact evidence. No community merge,
  package/image publication, deployment or live authentication change.

Review focus: malicious spec authority; stale/concurrent revisions; old Run
pinning during N+1 activation; effect-free launch/remount; crash/SQL failure
between immutable blob staging and authoritative publication. Each must have
a boundary regression before its corresponding integration is accepted.

Authenticated ChatGPT E1 remains a separate operator gate. Existing Executor
read/write remains recognized and untouched. General effects, retention/restore,
independent distribution and celld NO-GO remain visible in the release ledger.
