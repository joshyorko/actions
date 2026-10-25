# a43 / Core a6 installed checkpoint

Source ce98de6963bb6d20325db5a3687b14a8e238d7d9, tree 3d67addba27d8671f60e5497e692a28addc37aaa. Runtime1.1.0a43 / Core1.1.0a6 / Work Items0.5.0a2. Exact wheel hashes are in wheels.json. This is a qualification checkpoint, not a release or deployment authorization.

| Acceptance boundary | Status |
| --- | --- |
| Original a41 installed generated execution | FAILED, preserved |
| a43 clean consumer and wheel payloads | PASS; 65 resolved distributions, 334 Runtime /87 Core /26 Work Items payload members; pip check and Runtime RECORD |
| Owned dependency independence | PASS in clean consumer: retired distributions absent; official truststore0.10.4 sole namespace provider, six Python RECORD files verified |
| Installed logging/redaction | PASS: two isolated processes, actual AST events, raw/repr Secret/OAuth/encrypted-context canaries, upstream imports blocked, owned cache reused; post-probe Core payloads unchanged |
| Public generated authoring and execution | PASS: compile/test/activate, actual RCC two successes/one expected failure, authorized artifacts/diagnostics, same-state restart, stale session rejection, rollback/restore and revoked read |
| Protocol security | PASS: missing/wrong bearer403, Host421, Origin403; six graceful server shutdowns |
| Robot public installed execution | FAILED combined gate: genuine RCC success/failure and detached Tasks pass; direct Canvas open fails RCC-only profile guard; restart not reached |
| Official MCP Apps basic-host | BLOCKED: supported Chromium sandbox startup unavailable; browser recipe in ../browser-handoff/README.md; no sandbox override |
| Robot claimed Work Items | OPEN: diagnostic proves naive shared guard reads provider within SQL; interface proposal retained, no guard removed |
| Full Runtime suite | OPEN: original interrupted failures retained; focused corrections pass; full rerun pending |
| Documentation and developer suites | PASS: Core448 /devutils333 /HTTP-helper12; configured Core and Runtime static gates; devutils12-file supplementary type check and11-file Markdown parity |
| API documentation validation | FAILED:13 pre-existing Core style violations, not suppressed |
| Independent real clients / Dakota | OPEN; no local dispatch or publication |

CycloneDX7.5.0 validated SBOM generation and declared-edge reconciliation pass. Strict active-graph comparison remains FAILED with29 explained inactive declaration edges; raw SBOM is not relabeled an active graph. The active selected data-duckdb graph independently matches the locked installed consumer. Initial missing optional producer group failure is retained; installation used declared `devutils sync --with sbom` through the pinned toolkit.

All helper canonical documentation proposals are integrated: repository-operations.md adds installed logging probe requirements, optional SBOM group and typed owned docs guidance; work-items.md records the measured SQL/provider boundary and explicitly leaves claimed Robot unimplemented. Upstream disposition: none.

Corrected direct Canvas selector is reviewed and passes38 SQLite/PostgreSQL regressions without skips. Original forged-profile test used an invalid missing profile and failed its expected-error assertion; corrected fixture uses a valid differently pinned profile. Runtime configured typecheck passes630files. Corrected installed acceptance requires a44, not mutation of a43.
