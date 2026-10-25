# Generic bound-App scratch receipt

Base: fdc38d7090c4ac470171c499e77eab636fd452e6.
Scratch: /workspace/actions-recovery-327/generic-app-draft.
Patch: generic-bound-app.patch; SHA256 ab3767521b2c0f9815774f4865a826b4f00198b25214b0b793dde5b32161753c.
Source hashes: source-identity.json. Shared integration checkout untouched. No branch, commit, push, external mutation, build or RCC launch.
Dependency: sibling generic_work_item_execution.py dispatch registration from model-descriptors.patch a384b919008fb5510d75b5da6704f00c96ab353f65f26d88358dac590aba98e7 was applied in scratch for testing and is intentionally excluded from this patch.

## Evidence

- Source `test_generic_canvas_view.py`: 96 passed, zero skips, 185.05s. SQLite/PostgreSQL common authority × DuckDB/PostgreSQL existing fixture providers. Owned PostgreSQL container actions327-generic-app-pg, bounded memory/CPU/tmpfs and loopback port; stopped after completion. No shared database used.
- Existing MCP facade/AppSession suites: 12 passed in 0.38s.
- Canvas View frontend: 51 passed, one existing conditional round-trip skip in CanvasContractRoundTrip.test.tsx (round-trip environment paths not supplied). New tests all pass. Run from action_server/frontend with `node node_modules/vitest/vitest.mjs run --config apps/canvas-view/vitest.config.ts`.
- TypeScript noEmit and changed-file ESLint passed. Python changed-file Ruff and Isort passed; source Mypy four files passed. Black executable is absent in prepared package environment; no dependency installation attempted.
- `git -C /workspace/actions apply --check --whitespace=error <patch>` passed without mutation.
- Python tests use prepared package interpreter with scratch src/tests overlays, `-o addopts=''`, strict `ACTIONS_REQUIRE_INVOICE_PROVIDERS=1` and owned `ACTIONS_INVOICE_TEST_POSTGRES`. This is source iteration, not installed-consumer evidence.
- Existing review negatives captured corruption, authorization and SQL rollback boundaries. Earlier failing iterations included fixture-argument mistakes, missing owned-Postgres env and incorrect frontend working directory; none are represented as product gate passes.

## Scope and integration

Compose GenericCanvasView around GenericCanvasExecution, which continues to delegate reviewed operations. Ordinary none uses StandaloneActionExecution; optional/producer use generic domain with exact immutable policy. Runner is the existing trusted PinnedGenericRccRunner and prepared profile; request never supplies source, worker identity, credentials or runtime profile. Exact actor/scope/binding/Run FoundryRequest+Audit receipts are transactional with admission and required for every app projection/mutation. Model-created matching-idempotency Runs cannot gain that receipt. Alias binding tests resolve the same snapshot deliberately and still deny cross-binding Run reads/cancellation.

Private generic metadata includes fresh AppSession, eligible binding IDs and bounded recent Run states. Reopen reads at most 256 audit records, reconstructs retained state without launch, and permits explicit continuation only for unlaunched ready state. No complete-history claim. The UI uses official SDK callServerTool; no automatic mount execution or polling. Separate submit/execute preserves Run identity for in-flight status and request cancellation. Cancellation reports requested only. Uncertain launched/expired states remain truthful and cannot silently relaunch. Terminal artifacts require exact sealed Run/workspace inventories, live permission and bounded UTF-8 inspection.

Root must still integrate Runtime composition/version and rebuild bundled frontend/wheel, then prove actual ordinary none RCC, installed official-host form submission/status/cancel/artifact flows, restart/reopen with persistent configured worker identity, screenshots, real second generic app and full regression matrix. Required/consumer app forms with explicit input claim remain unadvertised; their model/domain path is separate. Failure reconciliation remains open: no successful result fabricated or automatic retry. Model none invocation/descriptors remain separate integration work; this patch only adds app none execution. No authenticated ChatGPT proof, no READY FOR DAKOTA claim.

Capture hygiene: sanitize AppSession tokens and synthetic API keys before saving MCP responses/host captures; retain presence/digest and semantic metadata only. None were exported by these passing test logs. Screenshots must exclude host session metadata.

## Documentation improvement

- Canonical file proposed: docs/skills/work-items.md, exact text in guide-delta.md.
- Durable learning: authority association versus spoofable idempotency prefix; split admission/execution; bounded reopen; exact inventory integrity; session capture redaction; proper Canvas Vitest cwd; distinct source/installed qualification.
- Evidence: 96 SQL matrix, 12 MCP facade, 51 frontend passes, source definitions and negative tests.
- Stale/ambiguous guidance: qualify the model-wrapper sentence about unchanged canvas_dispatch; distinguish the separate app composition and its runnable subset.
- Remaining uncertainty: installed/browser/actual none RCC/process restart/consumer-app and reconciliation gates above.

Upstream disposition: none. Findings were local implementation/test-harness issues; no confirmed dependency defect or external issue action.
