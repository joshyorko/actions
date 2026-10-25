# Host managed identity to canonical output transport

This independently allocated production slice adds only
`foundry/run_output_transport.py`, its lane-specific test and this evidence.
It requires existing source contracts at `da928b69` and has no dependency on the
Lane B installed-checker/orchestration scripts.

```python
create_run_output_transport(
    outputs: RunOutputService, authenticate: ManagedAuthenticate
) -> RunOutputTransport
```

The factory accepts the existing canonical output service and ordinary trusted
host callback. Only an authenticated ManagedCaller supplies an Actor. It does
not parse credentials, principal headers, cookies, AppSession tokens or audience
hints; it does not create grants, services, stores or routes. Authentication
exceptions reach the existing transport's unavailable response. Canonical
RunOutputService retains live Run/Package/application grants, Workspace,
final-output seals and retention checks.

## Integration reserved to the sole integrator

Construct the factory beside canonical `outputs` and `managed_authenticate` in
`create_runtime_canvas`; append an optional field to RuntimeCanvas without
changing existing positional fields. In `_server.py`, use that transport for
ordinary enabled Tasks only when no explicit transport was supplied. Reuse the
existing `install_run_output_transport` call and endpoint dependencies. Preserve
explicit invoice `canvas_scope` and externally supplied auth ownership. Never
replace an explicitly scoped/custom transport with the native unscoped factory.
No bootstrap/server/auth/CLI/MCP code is changed in this slice.

The host must supply the ordinary managed authenticator, not an AppSession
resolver. The adapter cannot repair a trusted callback that incorrectly grants
managed identity. No browser-cookie-only authentication is synthesized.

## Verification

Prepared Josh RCC18.19.3 Doctor/Bootstrap/ToolkitTest gateway preceded tests;
package-local Poetry, fresh owned SQLite/file fixtures, optional tracing disabled.

```bash
poetry run pytest -p no:robocorp_log_pytest \
  tests/action_server_tests/test_lane_b_run_output_transport.py \
  tests/action_server_tests/run_outputs/test_transport.py \
  --junitxml=/workspace/lane-b-state/receipts/transport-joined.xml
poetry run invoke typecheck
```

Joined result: **42 passed, zero skipped** (12 new +30 existing transport cases).
The new cases cover valid host identity, missing/invalid/AppSession credentials,
wrong-audience callback type, revoked live grants, cross-Workspace handles,
callback failure redaction and invalid factory configuration. Actual SQLite,
filesystem output bytes and FastAPI transport are exercised; this is source
integration, not installed route acceptance or a PostgreSQL claim. Existing
transport coverage retains origin, scoped authority and reader-cleanup boundaries.
The original missing-module RED collection receipt is retained.

Configured typecheck passed578 files after correcting three optional-loader
typing errors in an earlier lane test; its original failed receipt remains in
the sibling installed-knowledge evidence. Scoped Ruff/format/Isort and whitespace
checks passed. Independent read-only review found no blockers. Full package
tests, host wiring and installed artifact acceptance remain unqualified.

Rollback: remove the new factory/test; no migration or persistent state changes.
The first installed a38 operator diagnostic observed404 on POST to the absent
ordinary output route. This factory alone does not change that result; the
integrator must wire and qualify the host before claiming the seam closed.

## Exact canonical documentation proposal

Target: `docs/skills/repository-operations.md`, following the installed output
qualification guidance. Add:

> The native Run output transport factory adapts only an existing host-verified
> ManagedCaller to its Actor. It neither authenticates AppSession credentials nor
> registers an HTTP route. Keep live grants, Workspace, final-output seals and
> retention checks in the canonical RunOutputService. Host wiring must preserve
> explicitly scoped invoice transports and externally supplied authenticators;
> source adapter tests do not establish ordinary installed download acceptance.

Learning: verified identity adaptation and route installation are separate gates.
Evidence: new factory, new real SQL/HTTP tests, existing transport install boundary.
Ambiguity removed: factory creation versus route mounting/installed acceptance.
Uncertainty: forthcoming generated checkpoint and integrator host wiring.

Upstream disposition: none.

## Independent-review test corrections

The original wrong-audience test used an unknown handle, which could hide removal
of the ManagedCaller guard. The corrected test publishes a real output, proves
the ordinary managed owner reads its exact bytes, then checks the app-audience
callback returns no Actor, HTTP returns the exact unavailable response, and the
provider is never opened. An in-memory test-only factory mutation removing that
guard causes this case to fail. Its expected-failure receipt is retained; no
production source bytes were mutated. Original focused corrected run:12passed.

The dedicated test module now carries the same Linux-only skip as its imported
FilesystemOutputProvider fixture's original modules. Imported fixtures do not
inherit module-level marks. Native non-Linux behavior remains unqualified;
unsupported platforms skip explicitly rather than failing at O_DIRECTORY.

Ordinary HTTP downloads must pass both the installation endpoint gate and the
trusted managed identity callback. The middleware's managed-credential bypass is
limited to `/api/managed-work-items/v1`; it does not cover this output route.
These tests do not authorize arbitrary managed tokens through the outer gate.

Additional exact canonical delta proposed:

> Cross-module pytest fixture imports do not transfer module-level platform marks.
> Tests reusing the Linux filesystem output fixture must declare its Linux skip
> explicitly. For identity-denial tests, use a real otherwise-readable output and
> assert no provider access; an unknown handle can hide a removed identity guard.

Evidence: independent review, published-output positive control and retained
guard-removal mutation failure. Source factory commit5db85b8b remains unchanged.
