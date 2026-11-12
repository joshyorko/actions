# Auth and safe-sharing inventory — source checkpoint

Source inspected: `/workspace/actions` HEAD `a4e5b2b66c79da3c083d315cf5865ca70bd4d025`. The machine-readable [routes.json](routes.json) reproduces the exact route-policy identities in `action_server/tests/action_server_tests/test_auth_route_inventory.py`. That test captures the assembled FastAPI routes before server start, fails on unclassified additions/removals, and is parameterized with shutdown disabled and enabled. The policy union has 86 identities (85 when `/api/shutdown/` is absent). This lane inspected source; it did not execute the route-capture test or start a server.

| Mounted surface | Policy identities | Auth/security owner | Existing focused evidence |
|---|---:|---|---|
| Framework docs/OpenAPI | 4 | FastAPI framework | Intentional public framework routes; no app-specific auth negative |
| Browser session | 1 (`GET/POST/DELETE /browser-session`) | `install_browser_sessions`; API key for signin, origin-bound cookie afterward | `test_browser_session.py`: exact-origin, CSRF, wrong bearer, cookie scope/restart, websocket origin, secure-cookie cases |
| MCP | 1 (`/mcp`, GET/HEAD/POST/DELETE) | MCP `APIKeyAuthBackend`, bearer-only | Cookie cannot authenticate MCP; tunnel-origin tests retain bearer auth and temporary host scope |
| Dynamic action dispatch | 1 sample action route | `_ConfiguredAPIKeyMiddleware` plus action endpoint guard | Missing/wrong bearer denied before request body, database, or dispatch in `test_auth_route_enforcement.py` |
| Managed Work Items | 3 schema/capability/operation routes | Managed identity middleware (`ManagedCaller`) and SQL workspace/deployment grants | `test_managed_work_items_runtime.py` and `test_managed_work_items_api.py` cover wrong/missing identity, wrong role/scope, and preventing managed identity from authorizing other Runtime APIs |
| Protected API | 55 policy identities | API-key middleware runs before body read; endpoint dependency accepts configured bearer or authorized browser session | `test_auth_route_enforcement.py` real assembled credential matrix samples secret write, robot catalog/import/run, schedule CRUD, run/artifact, work item and analytics surfaces. These are representative common-guard checks, not a direct negative request to every listed route. Count includes conditional shutdown (54 protected API identities when shutdown is disabled). |
| Protected OAuth | 3 status/logout/reference routes | Same `/oauth2/` middleware boundary | Browser-session tests ensure a cookie cannot authorize mutating OAuth GET handlers; common path-prefix guard applies to remaining protected OAuth paths |
| Public OAuth | 2 login/callback routes | OAuth handlers perform their own input/provider validation | `test_server.py` verifies login/callback are not rejected by API-key middleware |
| Public trigger webhook | 2 methods (`POST/PUT`) | Trigger engine per-trigger secret/method/enabled/rate policy | `test_server.py` covers a public webhook happy path with an empty secret. No missing/wrong nonempty-secret denial test was found. |
| WebSockets | 2 routes | API key/browser session plus exact trusted WebSocket origin | Native ASGI missing/wrong/valid auth matrix; browser-session missing-origin, expiry, logout-close tests |
| Config and UI shell | 11 | `/config` is public bootstrap; UI shell returns static content while data APIs are guarded | Public bootstrap test directly checks `/config` and `/`; the assembled inventory asserts other shell routes |
| Artifact mount | 1 nested mount `/artifacts/{path}` | API key/browser session, immutable run binding and filesystem containment | Assembled GET/HEAD auth checks, private backing-file denial, traversal/symlink and run-scope tests |

## Negative path and safe-sharing evidence

- **Origin / browser session:** `test_browser_session.py` exercises absent, null, evil, wrong-port and path origins; CSRF, invalid bearer, cookie scope across origin/restart, forged host/forwarded headers, missing WebSocket origin, expiry, logout socket close, and no request-body read before auth.
- **MCP origin/auth:** `test_mcp_tunnel_origin_scope.py` asserts exact temporary origin/host allowlisting and release, rejects non-origin tunnel URLs, rejects unlisted hosts, and keeps bearer auth required. `test_pinned_mcp_auth_sdk_contract.py` checks pinned issuer/CIMD URL constraints.
- **Robot SSRF/archive/path:** `test_api_robots.py` rejects private destinations and redirects, unsafe/credentialed URLs, rebinding, proxy environment use (`trust_env=False`), archive parent/ambiguous/case-collision/link/Windows aliases, oversized input/expansion, and partial publication. Network probes use fakes or owned local transport; no live external identity is needed.
- **Filesystem artifact paths:** `test_artifact_storage.py` covers bearer enforcement, duplicate authorization headers, HEAD, run binding, traversal, symlinks, storage-root/ancestor symlinks, and private storage metadata.
- **Secrets:** `test_auth_route_enforcement.py` checks missing/wrong API key on `POST /api/secrets` before state/body access; `test_server_secrets.py` exercises encrypted and unencrypted configured secret transfer. Secret lifecycle correctness does not substitute for route auth coverage.
- **Schedules and trigger admin:** schedule create/update/delete are included as representative common-guard cases. Trigger listing has an unauthenticated 403 assertion in `test_server.py`; the inventory declares every trigger admin route protected, though secret read/rotation lack direct early-denial side-effect tests.

## Acceptance coverage added in this lane

1. Add a local public-webhook contract case using an existing synthetic trigger with a **non-empty** secret. For both allowed methods, missing and wrong secret should return 401 with no invocation/state effect; the matching secret should invoke exactly once. Current server smoke explicitly creates an empty-secret trigger, so it does not exercise this branch.
2. Add direct missing/wrong bearer probes to `GET /api/triggers/{trigger_id}/secret` and `POST /api/triggers/{trigger_id}/regenerate-secret`, spying that the DB/secret-read or rotation boundary is not entered. The common guard is source-wired, but this sensitive effect-specific assertion is absent.

This lane implemented those cases in the isolated test file `action_server/tests/action_server_tests/test_trigger_secret_boundary_327.py`. The focused RCC run passed **10 tests in 2.95s**. For rejected signatures, the test preserves the existing audit contract: a `REJECTED` invocation row is stored, while accepted invocation, work-item dispatch, trigger count, and last-triggered timestamp remain unchanged. The valid-signature control dispatches once through a patched local work-item boundary. Missing/wrong bearer probes for secret read and rotation assert rejection before DB access or secret generation.

## Canonical guidance delta proposed

Target `docs/skills/repository-operations.md`, under `### Action Server OpenAPI golden snapshots` (currently lines 2161–2175), extending its existing statement that assembled auth regressions must include the public webhook exception:

> Keep `test_auth_route_inventory.py` synchronized with every mounted route and method. Treat its route classification as an inventory contract, not proof that each handler has a direct negative-auth test. For each public exception, retain a local positive and failure-path contract; for sensitive credential read/rotation routes, assert denial before the secret/database boundary is entered.

Evidence: the current inventory classifies 86 assembled identities, while the assembled auth matrix has representative protected API cases; the public webhook smoke uses an empty secret, and trigger secret read/rotation paths have no direct early-denial side-effect case. This isolated lane proposes the delta; it does not edit repository docs.

## Upstream disposition

None. The identified gaps are Actions-owned acceptance coverage; no upstream defect was established or investigated.
