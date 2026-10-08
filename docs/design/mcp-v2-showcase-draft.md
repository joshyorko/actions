> Paused draft, October 8, 2026. Not approved, implemented, or ready to merge. Published only to preserve existing work for adversarial review.

# MCP v2 Showcase Design Candidate and Implementation Plan

> Design-only candidate for parent review. No repository source, manifest, bundle, issue, branch, or remote state was changed. The implementation plan is proposed, not authorized for execution by this document alone.

## Design candidate

### Contract and intent

**G1 — Goal:** Ship one community-owned, self-contained MCP v2 showcase template that lets a developer create the project from Action Server's embedded package and exercise the current public stateless MCP contract locally.

**A1 — Required behavior:**
- Demonstrate MCP `2026-07-28` discovery, followed by independent, stateless requests at `/mcp`.
- Expose and call at least one tool; list/read one direct resource and one resource template; list/get one prompt.
- Show typed tool inputs and a structured object result using the existing Core `Response` / `Table` contract.
- Show one catalog SHA-256 revision consistently across tool/resource/template/prompt listings and explain `ttlMs: 0`, `cacheScope: private` as immediate staleness / no shared cache. Explain that the revision fingerprints the registered surface, not changing resource content or tool results.
- Carry one canonical `X-Request-ID` through a request and document the safe request metadata boundary. Include an expected, bounded application error with a fixed safe message.
- Demonstrate opening and closing the stateless Streamable HTTP GET/SSE channel. Do not imply this server emits tool-progress notifications.
- Keep source and test dependencies public; project creation must be satisfiable from the deterministic embedded bundle with no template-host request.

**Non-goals:** MCP Apps / SEP-1865 UI resources, Canvas, `ui://` authoring/serving, private/product endpoints or packages, `/sse`, `initialize`/`initialized`, `Mcp-Session-Id`, new distributions, a generic MCP framework, remote APIs, persistent state, or a new Action Server runtime feature.

**Authority / appetite:** This is a read-only design plus a small TDD plan for the authorized #126 lane. It proposes changes only to the new template, existing template inventories/generated bundle/tests, and one canonical guide paragraph after implementation proof. No runtime implementation is proposed unless the bounded tests expose a necessary runtime prerequisite; such a prerequisite must return for parent admission.

### Issue and dependency reconciliation

- Current #126 body says #128 cleanup is merged, asks to reconcile only relevant remaining #125 acceptance, and specifically says not to wait on the obsolete cleanup branch. It requires a separate approved design/spec, deterministic generated-bundle integration, end-to-end examples, boundary tests, public dependencies, offline packaging, and no private/product/legacy-session paths. [#126](https://github.com/joshyorko/actions/issues/126)
- #126 has older comments saying the work is deferred behind #125. The newer body supersedes that branch-level dependency: #125's accepted inventory/bundle contract still applies, but the four-template baseline is not a prohibition on the explicitly requested fifth template. #125's current body requires manifest-owned IDs, regenerated matching bundle assets, offline project creation, public dependencies, and canonical template-inventory guidance. [#125](https://github.com/joshyorko/actions/issues/125)
- The #126 clarification excludes MCP Apps authoring/renderer work. #99/#100 are optional future consumers only; they are not design or implementation dependencies for this core-MCP showcase. [#126 clarification](https://github.com/joshyorko/actions/issues/126#issuecomment-5320624827)
- Release choice: keep the beta and production inventories separate as the repository does today. A conservative default is: admit the new ID to beta only for a beta trial if needed; do not add it to production until every issue acceptance gate below has passed. On promotion, add the same ID to both manifests in the same change so beta retains the accepted showcase; regenerate the embedded production bundle from `templates-prod.json`. No question to the user is needed for this routine release sequencing choice.

### Source-backed design

The current source provides the needed core authoring and server contract:

- `actions.mcp.tool`, `resource`, and `prompt` are public Core decorators. `tool` accepts title plus read-only/destructive/idempotent/open-world hints; `resource` accepts URI, MIME type, and size. There is no public UI metadata parameter. [Core MCP API](https://github.com/joshyorko/actions/blob/8bdce09944c9e370917a8222243cd1a239ea7060/actions/src/actions/mcp/__init__.py)
- Action Server mounts public MCP SDK 2.0.0's `streamable_http_app(..., json_response=True, stateless_http=True)` on `/mcp`; the lock pins `mcp==2.0.0`. [Route setup](https://github.com/joshyorko/actions/blob/8bdce09944c9e370917a8222243cd1a239ea7060/action_server/src/actions/server/_api_action_routes.py#L145-L195), [Runtime lock](https://github.com/joshyorko/actions/blob/8bdce09944c9e370917a8222243cd1a239ea7060/action_server/poetry.lock)
- `McpServerSetupHelper` materializes tools, resources, resource templates, and prompts; maps object output schemas to `structured_content`; copies `_meta`; and decorates all four catalogs with one canonical sorted-surface SHA-256 `actions.catalogRevision`, `ttlMs=0`, and `cacheScope=private`. [Adapter](https://github.com/joshyorko/actions/blob/8bdce09944c9e370917a8222243cd1a239ea7060/action_server/src/actions/server/mcp/setup_mcp_server_v2.py)
- Existing integration helpers implement raw `server/discover` and per-request headers/body metadata for `2026-07-28`; tests already assert `/sse` returns 404, a stateless call has no `Mcp-Session-Id`, structured output maps to `structuredContent`, and catalog revisions/staleness metadata stay consistent. [MCP integration tests](https://github.com/joshyorko/actions/blob/8bdce09944c9e370917a8222243cd1a239ea7060/action_server/tests/action_server_tests/mcp/test_mcp_integration.py)
- Existing `test_server_parent_pid.py::test_mcp_sse_does_not_starve_server_or_sigterm` opens `GET /mcp` with `Accept: text/event-stream`, verifies the server remains responsive, then verifies SIGTERM and child cleanup. It is sufficient transport lifecycle evidence to reuse; the showcase may include a stdlib example that opens the stream and closes it cleanly. [Lifecycle regression](https://github.com/joshyorko/actions/blob/8bdce09944c9e370917a8222243cd1a239ea7060/action_server/tests/action_server_tests/test_server_parent_pid.py#L28-L100)
- The Action-side `McpResponseHandler` currently implements `set_run_id` and `set_async_completion` as no-ops. There is no source/test evidence of an Action-to-MCP progress notification path. Therefore limit streaming claims to Streamable HTTP GET/SSE transport lifecycle; do not claim progress, resumable events, or cancellation.
- Existing community templates pin `actions-core=1.0.1`; the new template can use the same single PyPI dependency. A standard-library client example avoids introducing an MCP SDK or HTTP client dependency into the Action package. [Current template manifest](https://github.com/joshyorko/actions/blob/8bdce09944c9e370917a8222243cd1a239ea7060/templates/minimal/package.yaml)
- Templates are generated from independent beta/prod JSON inventories. `build_embedded_bundle.py` creates a deterministic aggregate ZIP, YAML SHA-256 metadata, and per-template ZIPs. The Action Server package includes the aggregate ZIP and YAML metadata, and `test_template_bundle.py` currently pins the production list to four IDs. [Template generator](https://github.com/joshyorko/actions/blob/8bdce09944c9e370917a8222243cd1a239ea7060/templates/packaging/build_embedded_bundle.py), [bundle tests](https://github.com/joshyorko/actions/blob/8bdce09944c9e370917a8222243cd1a239ea7060/action_server/tests/action_server_tests/test_template_bundle.py), [packaging contract](https://github.com/joshyorko/actions/blob/8bdce09944c9e370917a8222243cd1a239ea7060/action_server/pyproject.toml#L9-L18)

### Proposed template shape

Create `templates/mcp-v2-showcase/` as a single small, runnable package:

- `package.yaml`: follow the existing public template contract (`spec-version: v2`, Python 3.12.12, `actions-core=1.0.1`, standard pytest/Ruff dev tools only). Do not add `mcp`, `httpx2`, Canvas, MCP Apps, product packages, Git dependencies, private registries, or runtime network clients to the Action environment.
- `showcase_actions.py`: define deterministic, local-only examples using `from actions import Response, Table, mcp`:
  - `search_demo_catalog(query: str, limit: int = 2) -> Response[Table]`, with bounded input and static sample rows. Decorate as read-only, non-destructive, idempotent, and closed-world.
  - `lookup_demo_item(item_id: str) -> Response[LookupResult]`, where `LookupResult` is a small Pydantic model; unknown IDs return `found=false`, code `unknown_item`, and fixed message `No demo item matches this ID.` without echoing arbitrary input or secrets.
  - direct JSON resource `showcase://catalog/overview` and resource template `showcase://items/{item_id}`, both returning static sample data and explicit `application/json` MIME types.
  - `build_demo_prompt(item_id: str, tone: str | None = None) -> str`, with a required ID and optional tone.
- `examples/mcp_client.py`: standard-library `urllib` client. For each JSON-RPC call, send `Mcp-Protocol-Version: 2026-07-28`, matching `Mcp-Method` header/body, `_meta` protocolVersion/clientCapabilities, `Accept: application/json`, and a fresh canonical UUID in `X-Request-ID`. It should call `server/discover`, all four list methods, then one tool call, resource read, template read, and prompt get, printing the revision and immediate-staleness fields. Each operation is a separate POST; no initialize/session handshake or cookie/session storage.
- `examples/open_close_sse.py`: standard-library `http.client` example with finite socket timeout. Open `GET /mcp` with `Accept: text/event-stream`, verify status/content type, and close immediately. Document that this is a transport lifecycle example, not tool-progress output.
- `tests/test_showcase_actions.py`: local deterministic function tests for typed inputs, structured result, bounded not-found result, resources, and prompt output. No live service or credentials.
- `README.md`: create/start the project using the existing Action Server quickstart; show the stdlib client commands; explain `/mcp` stateless flow, resource/template/prompt surface, structured result, revision and `ttlMs=0`/`cacheScope=private`, request correlation, safe domain error, and open/close SSE lifecycle. State that the revision fingerprints registered descriptions/schemas, not returned data; no MCP Apps UI or progress stream is part of this core showcase.
- Existing template conventions may add `.gitignore`, `LICENSE`, and `CHANGELOG.md`; no generated image, lockfile, new distribution, or package-specific dependency is needed.

The read-only evidence does **not** establish what exact JSON-RPC envelope the SDK returns for an unexpected exception from an action: the adapter logs and re-raises tool exceptions. Keep the showcased error on the explicit safe-result path. Add a separate negative protocol boundary test with a fixed malformed/mismatched metadata payload, expecting rejection without echoing that payload. If #126 acceptance requires generic exception masking beyond these current public boundaries, treat it as a narrowly scoped Action Server prerequisite only after a test shows it is missing; do not hide it in sample code.

### Acceptance gates

1. `mcp-v2-showcase` appears in the intended inventory; the generated production YAML metadata, aggregate ZIP, and per-template ZIP reflect the exact source bytes. Bundle generation is byte-for-byte deterministic.
2. `action-server new --name <temp-name> --template mcp-v2-showcase` succeeds using the embedded bundle without contacting a template host; the created package contains the complete action/example files. This proves offline **creation**, not an offline RCC dependency solve.
3. The new project starts locally and the example client exercises `server/discover`, each advertised list/read/call surface, typed arguments, structured content, catalog revision/staleness fields, and correlated request IDs using independent stateless POSTs.
4. Negative boundary coverage rejects inconsistent `Mcp-Method` header/body metadata with bounded output; `/sse` is 404; no call needs `initialize`/`initialized` and no response uses `Mcp-Session-Id`.
5. The existing SSE lifecycle regression remains green, or a parameterized version runs the same finite GET/SSE + unrelated-route + SIGTERM/child-cleanup checks against the showcase-created project. Do not add tests for action progress notifications.
6. Public dependency/static contract tests pass for template source and both selected inventories. No new dist, server, Canvas, MCP Apps, private package, or private endpoint is introduced.
7. Run relevant Action Server package tests, template-local tests/lint, generated-bundle determinism, offline create smoke, and `git diff --check`. A passing source test alone is not bundle/offline acceptance.

### Exact implementation file map

Create:
- `templates/mcp-v2-showcase/package.yaml`
- `templates/mcp-v2-showcase/README.md`
- `templates/mcp-v2-showcase/showcase_actions.py`
- `templates/mcp-v2-showcase/examples/mcp_client.py`
- `templates/mcp-v2-showcase/examples/open_close_sse.py`
- `templates/mcp-v2-showcase/tests/test_showcase_actions.py`
- optional convention files: `.gitignore`, `LICENSE`, `CHANGELOG.md`

Modify:
- `templates/packaging/templates-beta.json` (beta trial only, if used)
- `templates/packaging/templates-prod.json` (only after all production acceptance gates pass)
- `action_server/tests/action_server_tests/test_template_bundle.py` (new expected ID; test bundle content and both-inventory determinism as needed)
- `action_server/tests/action_server_tests/test_create_new_project.py` or `test_quickstart_validation.py` (embedded create smoke; prefer a focused new `test_mcp_v2_showcase_template.py` if the existing files grow too broad)
- `action_server/tests/action_server_tests/mcp/test_mcp_integration.py` (one focused live sample-contract test; reuse existing `_modern_request` / `_post_modern_mcp` helpers)
- `action_server/tests/contract_tests/test_active_contracts.py` only if the existing active-surface scan needs an explicit public-dependency assertion for the new template
- generated by the repository-owned packager: `action_server/src/actions/server/templates/action-templates.yaml`, `action-templates.zip`, and `zips/mcp-v2-showcase.zip` (plus any changed per-template ZIPs produced by the generator; do not hand-edit)
- `docs/skills/repository-operations.md` after implementation proof, replacing its stale exact-four production inventory sentence with the accepted new inventory and beta/prod boundary.

No change is planned to `actions/src/actions/mcp/__init__.py`, `setup_mcp_server_v2.py`, `action_server/pyproject.toml`, or frontend packages unless accepted tests uncover a concrete prerequisite.

## MCP v2 Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one community-owned offline-created MCP v2 showcase template with deterministic embedded packaging and end-to-end proof of its current public stateless contract.

**Architecture:** Keep all examples in one Action Server template using the existing Core decorators and runtime adapter. Use a standard-library JSON-RPC client so the package introduces no MCP/client dependency; demonstrate GET/SSE only as an open/close transport lifecycle. Promote the ID to production only when the implementation and acceptance gates pass, and keep the beta inventory in sync if beta packaging is used.

**Tech Stack:** Python 3.12.12; `actions-core=1.0.1`; Action Server's locked MCP SDK 2.0.0 at protocol `2026-07-28`; existing deterministic Python template packager; pytest/Ruff.

**Spec:** `docs/design/mcp-v2-showcase-draft.md` (design candidate above).

## Global Constraints

- Use only the public `actions.mcp.tool`, `resource`, and `prompt` APIs and current `2026-07-28` `/mcp` wire contract.
- Use only public dependencies; the Action package pins `actions-core=1.0.1` and adds no client SDK, HTTP client, Canvas, MCP Apps, product, or private package.
- Project creation is embedded/offline; it performs no template network request.
- No `/sse`, `initialize`/`initialized`, `Mcp-Session-Id`, private endpoints, new distributions, MCP Apps, Canvas, progress notification, or new generic framework.
- Do not weaken the existing four-template cleanup test; update its expected manifest-owned inventory when the new production ID is admitted.
- Generate embedded assets using `templates/packaging/build_embedded_bundle.py`; never hand-edit ZIPs or YAML metadata.

## Review Focus

- Manifest drift: beta/prod IDs, generated metadata, aggregate and individual ZIPs disagree. Test deterministic regeneration and exact embedded IDs.
- Accidental dependency creep: private/unlisted package, MCP SDK/client dependency, or remote endpoint. Test manifests and active source surface.
- Misleading transport claims: no progress-notification support exists in `McpResponseHandler`; test only GET/SSE lifecycle and document the limitation.
- Wire mismatch: header method, protocol header, and JSON body `_meta` disagree. Pin the header/body match and safe rejection in integration tests.
- Hidden state/session coupling: a client call succeeds only after a prior session handshake. Use fresh per-request calls and assert no `Mcp-Session-Id` or legacy route.

---

### Task 1: Pin the showcase contract with failing tests

**Files:**
- Create: `action_server/tests/action_server_tests/test_mcp_v2_showcase_template.py`
- Modify: `action_server/tests/action_server_tests/test_template_bundle.py`
- Modify: `action_server/tests/contract_tests/test_active_contracts.py` only for an explicit public-dependency assertion if the existing scan is insufficient

**Interfaces:**
- Consumes: existing `ActionServerProcess`, `actions_server_run`, `_modern_request`, and bundle test helpers.
- Produces: regression names for embedded package presence/create, exact production inventory, public dependency boundary, and MCP showcase contract used by later steps.

- [ ] Write failing inventory tests that require `mcp-v2-showcase` in the accepted production manifest, bundle metadata, and aggregate archive, and require any beta-listed copy to have matching archive evidence.
- [ ] Write failing offline project-create test using the existing CLI helper and exact `--name ... --template mcp-v2-showcase` contract; assert README, package, action module, examples, and tests are materialized.
- [ ] Write failing package manifest/source assertion requiring `actions-core=1.0.1` and rejecting private/package-only/UI dependencies or remote endpoints.
- [ ] Run from `action_server/`: `poetry run pytest -q tests/action_server_tests/test_mcp_v2_showcase_template.py tests/action_server_tests/test_template_bundle.py tests/contract_tests/test_active_contracts.py`; record the expected initial failures.

### Task 2: Add the self-contained public template

**Files:**
- Create: `templates/mcp-v2-showcase/package.yaml`
- Create: `templates/mcp-v2-showcase/README.md`
- Create: `templates/mcp-v2-showcase/showcase_actions.py`
- Create: `templates/mcp-v2-showcase/examples/mcp_client.py`
- Create: `templates/mcp-v2-showcase/examples/open_close_sse.py`
- Create: `templates/mcp-v2-showcase/tests/test_showcase_actions.py`
- Optional: `.gitignore`, `LICENSE`, `CHANGELOG.md` following adjacent templates

**Interfaces:**
- Consumes: existing public `actions.Response`, `actions.Table`, and `actions.mcp` decorators.
- Produces: `search_demo_catalog(query: str, limit: int = 2) -> Response[Table]`; `lookup_demo_item(item_id: str) -> Response[LookupResult]`; direct resource `showcase://catalog/overview`; template `showcase://items/{item_id}`; `build_demo_prompt(item_id: str, tone: str | None = None) -> str`; stdlib client taking an MCP base URL; stdlib SSE open/close demonstration.

- [ ] Add a failing template-local test suite for deterministic sample actions and expected safe not-found output.
- [ ] Run `cd templates/mcp-v2-showcase && pytest -q tests/test_showcase_actions.py` and confirm it fails before implementation.
- [ ] Implement the minimum decorated actions with static in-repository data only; cap `limit`, use fixed error code/message, and do not echo the raw search key in failures.
- [ ] Implement the stdlib client so each POST contains a fresh JSON-RPC id/UUID request correlation id, protocol header and matching method header/body, plus `2026-07-28` client metadata.
- [ ] Implement the SSE example with a finite timeout and guaranteed `finally` close. It should verify only a 200 `text/event-stream` response, not wait for or claim an event.
- [ ] Add README steps and protocol boundary notes; do not cite MCP Apps as included.
- [ ] Run `cd templates/mcp-v2-showcase && pytest -q tests/test_showcase_actions.py && ruff check . && ruff format --check .` using the package's declared dev tools.

### Task 3: Integrate manifests and regenerate the offline bundle

**Files:**
- Modify: `templates/packaging/templates-beta.json` if running a beta trial
- Modify: `templates/packaging/templates-prod.json` after production gates pass
- Modify: `action_server/tests/action_server_tests/test_template_bundle.py`
- Modify generated: `action_server/src/actions/server/templates/action-templates.yaml`
- Modify generated: `action_server/src/actions/server/templates/action-templates.zip`
- Generate: `action_server/src/actions/server/templates/zips/mcp-v2-showcase.zip` and any other generator-owned ZIPs

**Interfaces:**
- Consumes: complete template source tree and the production/beta JSON inventory entries.
- Produces: production metadata with the new ID and archive hashes matching all packaged source files; separate beta bundle output when beta inventory includes it.

- [ ] Add the new manifest entry with stable ID `mcp-v2-showcase`, visible name `MCP v2 Showcase`, and a concise description that says core MCP (not MCP Apps).
- [ ] Keep `templates-beta.json` and `templates-prod.json` inventory decisions consistent with the release decision above; preserve each manifest's intentional existing differences.
- [ ] Run the exact repository generator from repo root: `python templates/packaging/build_embedded_bundle.py --config templates/packaging/templates-prod.json --template-root templates --output-dir action_server/src/actions/server/templates`.
- [ ] Extend bundle tests to unzip and inspect the showcase source files and compare metadata IDs to manifest IDs; run the generator twice in temp directories and assert byte equality.
- [ ] Run from `action_server/`: `poetry run pytest -q tests/action_server_tests/test_template_bundle.py tests/contract_tests/test_active_contracts.py`.

### Task 4: Prove the running sample and protocol boundaries

**Files:**
- Modify or create: `action_server/tests/action_server_tests/mcp/test_mcp_integration.py` (or focused `test_mcp_v2_showcase_template.py`)
- Reuse without modifying unless the new sample exposes a gap: `action_server/tests/action_server_tests/test_server_parent_pid.py::test_mcp_sse_does_not_starve_server_or_sigterm`

**Interfaces:**
- Consumes: embedded CLI-created project; helper `_modern_request(method, request_id, params)`; current public `/mcp` route.
- Produces: one end-to-end assertion set that every advertised surface and example call works with independent requests and the sample's no-dependency package.

- [ ] Add a failing integration test that creates the project via `actions_server_run`, starts it via `ActionServerProcess`, then sends `server/discover`, `tools/list`, `resources/list`, `resources/templates/list`, and `prompts/list` as separate requests.
- [ ] Assert the four catalog results share a 64-character revision and carry `ttlMs == 0` / `cacheScope == "private"`; assert typed tool input schema and `structuredContent` object output.
- [ ] Issue separate `tools/call`, `resources/read` (direct and template URI), and `prompts/get` calls; verify exact safe sample result values and no implicit stored session between calls.
- [ ] Preserve a canonical request UUID and assert the response `X-Request-ID` matches; send a body/header mismatch containing a sentinel and assert bounded rejection does not echo the sentinel.
- [ ] Assert response headers omit `Mcp-Session-Id`; retain/add `/sse` 404 and invalid initialization checks as appropriate without duplicating the existing generic coverage.
- [ ] Run `cd action_server && poetry run pytest -q tests/action_server_tests/mcp/test_mcp_integration.py::<new_test_name> tests/action_server_tests/test_quickstart_validation.py::test_public_quickstart_creates_project_and_serves_mcp`.
- [ ] Run `cd action_server && poetry run pytest -q tests/action_server_tests/test_server_parent_pid.py::test_mcp_sse_does_not_starve_server_or_sigterm`; if using the showcase for this test, keep finite route/termination bounds and child cleanup assertions unchanged.

### Task 5: Close acceptance and canonical documentation

**Files:**
- Modify: `docs/skills/repository-operations.md` after evidence is green
- Review: all files listed above and generated bundle outputs

**Interfaces:**
- Consumes: passing focused tests, exact manifest/bundle contents, and clean diff.
- Produces: truthful guide inventory statement and final acceptance receipt; no unverified claims.

- [ ] Run `cd action_server && poetry run pytest -q tests/action_server_tests/test_mcp_v2_showcase_template.py tests/action_server_tests/test_template_bundle.py tests/action_server_tests/test_create_new_project.py tests/contract_tests/test_active_contracts.py`.
- [ ] Run the focused MCP integration and SSE lifecycle gates from Task 4 and template-local tests/lint from Task 2.
- [ ] Regenerate into two temporary output roots and compare byte-for-byte output; compare the checked-in generated production directory with a fresh production generation.
- [ ] Run the documented offline `action-server new` smoke using the embedded manifest/bundle and verify it does not attempt hosted template metadata/archive transport. Separately run Action Server on the created project for functional proof; do not label dependency resolution itself offline unless it was actually isolated from the network.
- [ ] Update `docs/skills/repository-operations.md` by replacing the stale four-template production sentence only after the production ID is accepted. Proposed exact durable delta: “Production owns `minimal`, `basic`, `advanced`, `workflow-producer-consumer`, and `mcp-v2-showcase`; the separate beta inventory is `templates/packaging/templates-beta.json`. Regenerate embedded assets from the production manifest with `templates/packaging/build_embedded_bundle.py`; a new template's source, manifest entry, metadata, aggregate ZIP, per-template ZIP, offline-create test, and inventory expectation must move together. Beta deployments use `create-templates-package.sh templates-beta.json`; preserve intentional inventory differences and test beta output when the new ID is beta-listed.”
- [ ] Verify the guide change against actual test names and generator output; remove any four-only statement that becomes contradictory, but leave the unrelated exact-four artifact/release claims intact.
- [ ] Run `git diff --check`; review the generated artifact and package source diff for scope creep.

## Verification status and remaining uncertainty

- This packet is repository reconnaissance only. No builds/tests were run and no repository code was edited.
- **Progress-streaming gap:** the server's SSE transport is present, but `McpResponseHandler` progress hooks are no-ops. If the intended acceptance means tool progress notifications rather than stream connection lifecycle, current public implementation does not prove that requirement; a separate runtime prerequisite would be needed.
- **Exception error gap:** the adapter logs and re-raises tool exceptions. Current checked tests prove trusted metadata boundaries and safe correlation telemetry, but not the exact v2 wire representation or log sanitization for arbitrary action exceptions. The design confines the sample to an explicit static safe-result error and proposes one negative metadata rejection test; do not claim all unexpected exceptions are safely masked unless added proof establishes it.
- **Manifest release timing:** current #126 does not specify beta-to-production promotion timing. The plan recommends beta trial if useful, then production inclusion only after gates; beta and production should share the ID after promotion.
- **Routing:** requested Luna/xhigh in parent packet; effective routing metadata is unavailable in this child, so requested/effective route cannot be verified.
