# Installed generated Knowledge ingestion and restart

Producer source: `0fb4999e52c2ed92f3585d088910c276d8dc72ed`, including generated
Knowledge source9e42a8f3. Fresh isolated checkout passed pinned RCC18.19.3 Doctor,
Bootstrap and ToolkitTest190. Clean archive rebuilt both frontends/public OAuth
inputs and installed Runtime1.1.0a39/Core1.1.0a4/WorkItems0.5.0a2. Exact hashes,
commands, pip consistency and isolated import-origin checks are in build-receipt.
Task-local compiler publication and native exec verified all53 Core Python members
against the freshly built wheel. No Core/Runtime versions or trust policy changed.
The compiler publish logged a nonfatal disabled default pip-cache warning; later
exec used an explicit owned pip cache. No host dependency fallback was used.

Observed compiler identities:

- package YAML: `sha256:6b8a37ed2abbb04c9fc6d1cb13654f226d73dda6e658ec0b5dca8254e5e3a4df`
- specification: `sha256:9dee42164c32a71de49bc33b47f60fe3cee391f062d2dd5612cf6ae43e8abed2`
- artifact: `sha256:75fe326e25341bd99e1b0133dc845267bd0810a092cd35a1e356314f3f5d6f63`
- Core wheel: `fe8fb01f5924837ebd221bb559cc4c36482a581921f81beba1d4c2a6c8e4b371`

The new fixture script uses public CLI/MCP only for changes. A read-only SQL query
discovers the saved Workspace. It provisions three owned UTF8 documents in real
DuckDB, authors a two-Action Package with explicit Knowledge mappings and semantic
form/status/artifact controls, activates it and authorizes its exact Deployment.
Corrected installed preparation passed30 CLI commands and four MCP calls, with
two graceful shutdowns. Build/import/tests all passed through public canvas_apply.
No application state, grants, Runs, Attempts, outputs or publications were SQL-seeded.

Actual generated ingestion completed through capability_invoke and tasks/get:
Run/Task `dda9a652-7e86-462f-bd32-d59c6ebc0225`, Attempt
`c24c7321-99a4-4d49-a0f0-2ab15287f3ca`, five retained output handles. A separately
restarted installed process replayed the original invocation and returned an
exactly equal terminal Task, including Run/Attempt/handles. Both lifecycles stopped
gracefully. This is genuine installed Task/native execution, not a simulated result.

## Failed authoring attempt and comparison evidence

The first public error was exactly `Canvas request unavailable, invalid or access
denied.` Its original response/receipt remain FAIL. The first request was not
captured at transmission; `authoring-first-request-reconstructed.json` is explicitly
a later reconstruction from the fixture and retained identities, not an original
wire capture. Installed DTO checks passed for CanvasSpec/backend/source inventory/
binding map/data bindings. Both bundle members declared requirement ID `documents`.
The installed registry's compile_trusted_bundle guard refuses duplicate requirement
IDs across members. Corrected declarations, Core accessor calls and dataBindings
use ingestion_documents/search_documents; the fresh public compile passed using
the same installed versions and prepared artifact. The corrected request and
response are captured directly. No production code or admission instrumentation
was changed. This does not establish the cause of the integrator's separate
second-application failure.

## Exact commands and remaining dependency

```bash
/workspace/lane-b-state/installed-a39-producer/consumer/bin/python -I \
  /workspace/lane-b-actions/action_server/scripts/lane_b_prepare_knowledge_lifecycle.py \
  --root /workspace/lane-b-state/knowledge-a39-corrected \
  --expected-prefix /workspace/lane-b-state/installed-a39-producer/consumer \
  --prepared /workspace/lane-b-state/compiler-a39/prepared.json \
  --package /workspace/lane-b-state/compiler-a39/package.yaml \
  --source-checkpoint 0fb4999e52c2ed92f3585d088910c276d8dc72ed
poetry run python /workspace/lane-b-state/qualify-a39-task.py
poetry run python /workspace/lane-b-state/replay-a39-task.py
```

The latter commands used the producer checkout's prepared package-local Poetry;
their retained scripts launch only the independently verified installed server.
Private fixture directories, provider files, credentials and compiler payloads are
not committed. The manifest can be regenerated with the public setup script.

HTTP is NOT_RUN here. At this source the ordinary output route is not mounted.
Task results expose handles without names; reading the generated Action receipt
through the authenticated output route is required to obtain the corpus handle
for the search invocation. No handle-order inference, direct service/SQL output
read, or app-scoped artifact substitution was used. Await the integrator's exact
mounted-route checkpoint, then rebuild and qualify readback/denials, authorized
search/paging/export and replay. Actual PostgreSQL lifecycle, revocation/cancel
and independent browser consumption remain separate outstanding gates.

## Exact canonical documentation proposal

Target: docs/skills/repository-operations.md. Add:

> Logical requirement IDs must be unique across all Actions in a Package bundle.
> Separate ingestion and search Actions need distinct IDs in their declarations,
> generated Core calls and provider bindings, even when they share a collection
> and provider. Valid request DTOs do not establish bundle admissibility; qualify
> the public compilation path. Generated Knowledge declares result_json:string;
> search maps all four required parameters explicitly and ingestion maps none.

Learning: cross-Action binding identity is a bundle invariant, separate from DTO
syntax. Evidence: installed source guard, preserved failed request/validation,
successful public compilation and actual ingestion/replay. Uncertainty: output
route wiring and remaining lifecycle matrix. Rollback removes only the new
fixture helper/evidence; this slice changes no production state/schema code.

Upstream disposition: none.
