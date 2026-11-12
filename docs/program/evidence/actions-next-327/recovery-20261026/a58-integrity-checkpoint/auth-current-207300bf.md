# #327/#328 current-source auth acceptance audit

Source: `/workspace/actions` HEAD `207300bfda2228721ad9c7cdf3fe15cd14de3c9d`.

## Finding

`test_auth_route_inventory.py` captures and classifies the complete assembled route identity set (86 with optional shutdown; 85 with it disabled), but that classification alone is not direct authorization evidence. The existing assembled negative-auth matrix in `test_auth_route_enforcement.py` samples 18 of the default 54 `protected-api` identities, plus the dedicated missing/wrong HMAC tests and protected trigger-secret read/rotation cases in `test_trigger_secret_boundary_327.py`. Existing integration and browser-session tests add more representative probes but do not establish a direct missing/wrong bearer denial for every configured-key route method.

At this source, `_ConfiguredAPIKeyMiddleware` enforces `/api/` and `/oauth2/` by default, while preserving source-defined exceptions: `/config`, OAuth login/callback, public trigger webhooks, managed-work-items' `ManagedCaller` path, CORS preflight, MCP's own bearer backend, WebSocket/browser-session policies, and the separately guarded artifact mount. The ordinary Runtime API uses a single configured server key/browser-session authority; there is no per-user principal dimension to exercise as “two principals” on those routes. Managed Work Items role/scope identity tests are distinct evidence and do not prove ordinary API multi-principal isolation. Do not invent two-user semantics for the global-key surface.

## Narrow proof added

Added only `action_server/tests/action_server_tests/test_auth_all_protected_routes_327.py`. It reuses the assembled runtime fixture and route capture/classification helpers, then probes each configured-key method in `protected-api`, `dynamic-action-api`, and `protected-oauth` with both missing and wrong bearer credentials. The default configuration covers 58 methods; shutdown-enabled assembly covers 59, for 117 method identities and 234 requests total. Each request includes an owned synthetic body and returns 403 without invoking the ASGI receive callback, database/storage/dispatch boundaries, or changing the synthetic fixture snapshot. The test also traps `_thread.interrupt_main` as a forbidden boundary, so a shutdown-route authorization regression cannot interrupt pytest. The inventory remains authoritative for the separate public and managed identity categories.

Focused RCC result: `2 passed in 9.19s`; final supervisor receipt reports `PASS`, command exit 0, and `remaining_owned: []`. Targeted formatting and import checks passed: `ruff format --check` and `ruff check --select I` for the new file; their supervisor also reports exit 0 and no remaining owned processes. Final combined logs/receipt: `/workspace/327-probes/auth-all-routes-327-complete.log` and `/workspace/327-probes/auth-all-routes-327-complete-supervisor.json`. Earlier split receipts remain at the paths shown in the preceding audit updates.

## Canonical documentation delta proposed

Target: `docs/skills/repository-operations.md`, under `### Action Server OpenAPI golden snapshots`, immediately after the existing route-inventory paragraph. Proposed text:

> `test_auth_route_inventory.py` is the mounted-route classification contract, while `test_auth_all_protected_routes_327.py` exercises all 58 default and 59 shutdown-enabled configured-key methods in the `protected-api`, `dynamic-action-api`, and `protected-oauth` classes with missing and incorrect bearer credentials. It asserts denial before ASGI request-body receive, database/storage/dispatch boundaries, or fixture state changes; the shutdown-enabled case also traps `interrupt_main`. Keep public OAuth/bootstrap/webhook, managed identity, MCP, browser-session, WebSocket, and artifact mount policies covered by their separate contracts; route classification does not turn these distinct auth models into ordinary API-key routes. The global configured API key does not define independent user principals, so multi-principal isolation requires a separate domain identity contract.

Evidence: current route policy helper and middleware source at this commit; the 58/59-method, 234-request focused test across both assembled configurations; trigger exception/secret tests; managed caller authorization suite. No canonical guide was edited in this isolated lane. The release-matrix multi-principal acceptance row remains open for domain identity-specific evidence; this test closes only the default assembled configured-key route denial matrix.

Upstream disposition: none. No upstream defect was established or investigated.

Documentation improvement:
- Canonical file changed or proposed: proposed exact delta to `actions/docs/skills/repository-operations.md`; not edited in this isolated lane.
- Durable learning captured: route inventory classification and direct per-method early-denial proof are different contracts; the global API key has no per-user principal isolation semantics.
- Evidence: HEAD `207300bf...`, middleware/inventory source, `2 passed in 9.19s`, final supervisor exit 0 with no owned processes.
- Stale or ambiguous guidance removed: none in this isolated lane; propose replacing the prior assertion that classifications alone do not prove a direct negative-auth request to every handler with the new measured 58-method evidence while retaining the distinction for separate auth categories.
- Remaining uncertainty: multi-principal isolation remains a separate acceptance gap for domain-identity surfaces; the global API key itself has no independent-user semantics.
