# Generic produced-item app projection — isolated source receipt

Patch: generic-output-app.patch; exact SHA256 and eight file hashes in patch-identity.json. Scratch only, no shared source writes, branches, commits, push, version/bootstrap changes or RCC use.

Dependencies: frozen generic bound-app + none join + descriptor aggregate, then input-app and narrow reopen fix. To integrate cleanly on current a28, apply reopen-artifacts.patch first, then consumer-app-evidence/input-after-reopen.patch (SHA256 fac20f1862f67a22a47405ac628ba8292c5c804b2a6cffc9f4f0b65036cfc442), then this patch. Existing-file baselines are retained for review and applicability checks.

Implemented: explicit app-private output binding and read-only Load produced items panel; exact app association, current scope/policy and live output READ/ARTIFACT_READ; complete producing snapshot/fence/digest/parent validation; published child payload multiset equality; isolated own-child cursor; 20-item pages with bounded UTF-8 previews. Queue scan fails closed above 1000 rows or 1 MiB database text characters. No child adoption, claim, execution, retry or second state authority.

Validation: unsupported-red.log records two expected unsupported-action failures before wiring. sql-qualified.log: 70 passed, 174 deselected, zero skips, 275.77s across SQLite/PostgreSQL; includes producer boundaries, reopen regressions and selected-input smoke. extra-qualified.log: 8 passed, 112 deselected, zero skips, 35.70s; final metadata discovery and extra-child forgery checks. Provider variants deselected are redundant DuckDB/PGlite fixture dimensions, not unavailable SQL providers. frontend-final.log: 63 passed, one pre-existing conditional roundtrip skip. TypeScript, ESLint, Ruff, Isort checks clean; Mypy two source files clean. Completion runner is synthetic; no installed/RCC/browser claim.

Prepared package interpreter and Node dependencies reused without installs. PostgreSQL fixture is an isolated owned tmpfs container; cleanup is recorded separately. No app tokens or credentials are included in this evidence.

Earlier red.log/first.log record a temporary scratch composition indentation error; unsupported-red.log is the actual feature red evidence. Earlier frontend-qualified log contains a fixture type omission fixed before final types.log/eslint.log checks.

Remaining: root integration, version/build, installed official-host/browser and actual producer RCC/output qualification. Large queues intentionally require future bounded server query support rather than relaxing scan bounds. Canonical documentation proposal is guide-delta.md. Upstream disposition: none.

Cleanup: owned actions327-consumer-app-pg container stopped successfully after all source SQL checks; no RCC cache acquired.
