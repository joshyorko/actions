# Remaining issue 340 qualification, 2026-11-03

This is a checkpoint, not a release decision. PR #328 remains at
`642c6d3f62c2d271d33459553ef560a10f283f1f`; source under the separate
integration worktree has not been pushed past `888482c12ccbdd183909f44c4ba588dfcd3a19d1`
because GitHub rejected its configured token. The owner must restore supported
GitHub authentication before a normal checkpoint push can proceed.

| Gate | Proven scope | Next minimum proof |
| --- | --- | --- |
| Headless discovery | Source SQL and MCP component tests, exact references and model filtering; no installed transport proof | Build a separate source-bound Runtime candidate and exercise authenticated native MCP startup with real publication, denial and invocation. |
| Managed Work Items model tools | SQLite guarded direct/list, concurrency, current policy and source startup controls; PostgreSQL skipped | Fresh installed Runtime/Core/Work Items wheelhouse; real model discovery and authorized queue flows, negative/revocation checks and SQLite/PostgreSQL parity. |
| Internal Action→RCC Robot | Typed client, lineage identity migration and standalone delegation value; no host bridge | Persist and validate immutable delegation, atomically admit/replay fenced ordinary child Runs, implement supervised local transport, status/cancel and explicit detach lifecycle; prove with real installed RCC vertical and restart/idempotency controls. |
| Existing campaign | a60 source-specific CI and installed Data Package/Run evidence remain valid at `642c6d3f` | Current-source complete CI and original #327/#328 acceptance matrix, including operator/recovery, platform/distribution, provider/security and real invoice E1. |
| Owner ChatGPT | a57 bundle retained, owner test last known deferred | Owner performs actual ChatGPT Desktop CONNECT + RENDER; browser/source checks are not a substitute. |

PostgreSQL parity and the separate sealed-scan component must use an authorized
fixture; the earlier role/password/grant setup was denied before execution.
Its corrected proposal has unresolved all-path network cleanup and is not
approval-ready. Protected-home denial remains an environment restriction. No
package publication, community merge, or deployment follows from this evidence.

The exploratory child-admission prototype was removed from the product tree
because it assumed a detached parent intent and had no real registry/Run test.
It is retained only as unqualified Library file
`libfile_f3d245e9123c81918501a9ec5e1b44c4` version 0, SHA-256
`de4a3f1055870499b97e0ed81153d4fbf44abaded62b3ec8cf1f6255ae435d4f`.
It must not be treated as host implementation. A real fixture must cover both
synchronous and detached parent Runs, fenced cancellation, policy revocation,
replay conflicts and transaction rollback with a verified RCC Robot registry.

At source `e334b9988d0434e6fd47a04b858616cea1cb7a72`, the existing
`test_claimed_task_service.py::test_old_task_cannot_cancel_new_claim_epoch`
passed its SQLite case and skipped PostgreSQL. It moves the Work Item claim to
a replacement epoch and verifies an old Task cannot cancel or change its
cancellation state. The supervisor reported no remaining owned processes. This
is real SQL state with a synthetic Robot adapter, not a real RCC process or
PostgreSQL parity proof.
