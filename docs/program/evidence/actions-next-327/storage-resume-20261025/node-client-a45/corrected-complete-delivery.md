# Complete independent Node client gate

PASS against installed Runtime 1.1.0a45/Core 1.1.0a7, source e6e8f0130e6a7cfba2142e1382cbdd1f07901d39. Frozen wheel SHA256 values and installed wheel member bytes were verified before server launch. Node 20.19.3, official Client/Core 2.0.0, exact frontend lock and measured SDK entrypoints retained in config/receipt.

Seven checks passed: initialize; tools and annotations; universal Canvas resource MIME and bytes; one synthetic draft creation/idempotent replay/read; unknown application denial; missing bearer denial; wrong bearer denial. Draft used stable key node-327-a45-complete-corrected. SQL audit confirms exactly one canvas.create request, one draft revision, zero active Deployment heads. No activation, execution, Task, browser, PG container or RCC publication was performed.

Cleanup: Node exit 0; server exit -15; graceful Application shutdown complete; no forced kill. Owned server/helper PIDs 49321 and 49322 no longer exist. Supervisor completed. Full evidence: evidence/receipt.json, supervisor.json, client.log, server.log and completion-audit.json.

Original a45 failed client receipt remains FAILED, SHA256 a4e232320f583b70944e4132523de8dcabbbc44a6dde6d14078a5a695955134c. This is a distinct new complete run, not a relabeling of that failure. A supplemental audit initially assumed zero revision rows; corrected audit checks zero active heads because unpublished draft creation legitimately creates a revision.

Scope: independent official Node SDK protocol client, distinct implementation from Python SDK. No official-host UI, browser or ChatGPT readiness claim.

Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md.
- Exact additional delta: “Audit an unpublished Canvas client fixture by its single idempotent canvas.create request and absence of active Deployment heads; a draft itself legitimately creates a Deployment revision. Preserve failed candidate-run receipts separately from subsequent corrected complete runs.”
- Durable learning captured: draft revision storage is distinct from activation; stable idempotency enables exact request counting.
- Evidence: completion-audit.json and source authoring behavior; complete seven-check Node receipt.
- Stale or ambiguous guidance removed: zero revision rows is not the correct no-activation assertion.
- Remaining uncertainty: official-host browser and ChatGPT gates remain separate; no execution qualification from this client probe.

Upstream disposition: none. No external mutation or confirmed upstream defect.
