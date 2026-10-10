# Concrete resource routing history: proposed follow-up

Status: investigation and contract proposal only. No production edits, implementation branch, or claim that PR289 closes this gate. Root selected routing-projection history for design review; implementation remains deferred.

Baseline: published c78288c3a0f07ba1013109c790f8e8b375a852d2, tree 75a108db7d608e1316d59c96918213471409f31a. The existing control worker owns its checkout; unrelated workflow/JUnit/docs edits were untouched. The MCP/model/migration/Core source has no diff from reviewed 6eec6c6493cf029c5bba5d8189834349a26c0f67. Reader SHA256: aeda95a5e5cfd45356138afb1a79e7fc0877976a7f799c61f49dee7adb33d79a.

One scratch regression uses real mounted `/mcp` calls and existing catalog fixtures. `test_resource_routing_history.py` SHA256 d0a9091dc3075b1e9848f9521b78643915457bc8171bf3edaa058b8811a8e43b. Expected baseline result: 1 failed in 0.99s, because all three stale reads invoked different owners. Log `published-head-baseline-red.log` SHA256 dbb07118a6e3352df4698048e66a98439182fea8fe8346f6654de0aa5ae1d07b.

Command (checkout root; no source mutation):

```sh
env PYTHONDONTWRITEBYTECODE=1 TMPDIR=/dev/shm/actions-resource-routing-tmp PYTHONPATH=actions/src:action_server/src:action_server/tests/action_server_tests/mcp:/tmp/work/deployment-values-deps/site-packages /tmp/work/multipackage-runtime-acceptance/venv-primary/bin/python -m pytest -p no:robocorp_log_pytest --basetemp=/dev/shm/actions-resource-routing-confirm --confcutdir=/workspace/work/mcp-resource-routing-review-20261010 -s -q /workspace/work/mcp-resource-routing-review-20261010/test_resource_routing_history.py
```

Observed before → after:

| URI | Prior owner | Later owner |
| --- | --- | --- |
| example://cross/new | old/direct | new/template |
| example://cross-old/item | old/template | new/direct |
| example://acme/item | old/overlap | new/overlap |
| example://control/item | control/direct | control/direct |

The control has a coexisting matching template. Direct lookup wins, as required. Therefore rejecting every historical matching template would incorrectly reject an unchanged valid direct route. Exact namespace reservations omit catalog co-occurrence and historical winners; they cannot recover this information. Runtime matches direct URIs first, then template strings sorted lexically, using anchored placeholder-substitution Python regex. Literal template characters are unescaped: `example://host.test/{item}` also matches `example://hostXtest/one`. Core validation duplicates this local matcher. A simple literal-segment intersection algorithm would change or misrepresent current behavior; no grammar change or general overlap solver is proposed.

## Minimum proposed implementation slice

Persist each distinct admitted resource-routing projection in the existing database: a canonical versioned payload of sorted direct `(URI, package name, action name)` rows and lexically ordered template `(template, package name, action name)` rows. No UUID, code revision, callbacks, auth grants, metadata, or descriptor fingerprint enters the projection. A fixed-size domain-separated SHA256 primary key deduplicates payloads; compare full payload on a digest hit and fail closed on collision/corruption. Do not index arbitrary URI text.

Add one model/table and the next migration after 13. `_ActionRoutes.prepare_actions` already serializes admission with SQLite writer acquisition or PostgreSQL `mcp_catalog_name` table lock. Under that same transaction, after existing complete-candidate validation and exact ownership checks, load/validate prior projections, deduplicate the candidate, check capacity, insert if new, and attach immutable projections to the unpublished private MCP catalog. Failed outer import/reload/commit rolls back the new projection and existing metadata/reservations; publication occurs only after successful admission. All processes must use the same existing admission lock. Concurrent identical candidates insert one projection; distinct candidates serialize. Restart reloads committed history. No-op and metadata-only changes consume no additional projection budget.

At `resources/read`, capture the existing immutable catalog once. Resolve the current winner with the existing direct-first/lexical-template matcher. If unavailable, return the existing unavailable-resource error and never restore an old callback. Otherwise resolve the URI in every retained prior projection with exactly the same precedence. A historical projection that had no winner imposes no restriction. If every historical winner is the current `(package name, action name)`, execute the current callback with current inputs and authorization/filter behavior. If any historical winner differs, return a protocol error before invocation, naming resource rediscovery and the need to choose a non-conflicting URI/pattern. The history never forwards to disabled/deleted owners. Same-owner code/schema/metadata revisions remain permitted; this is capability-pair ownership, not PackageRevision identity.

This runtime check covers previously advertised template expansions even if never read. First-read URI tombstones would be smaller but protect only actual prior reads. Runtime rejection preserves deterministic discovery; it does not prove an entire new template disjoint at admission. A newly admitted pattern may consequently have concrete URIs that return ownership-conflict errors. Existing exact-key admission conflicts still reject the complete update. This distinction requires explicit approval and documentation.

Proposed private capacity defaults for root review: at most 256 distinct projections, 10,000 aggregate route rows across those projections, and 16 MiB aggregate canonical UTF-8 payload bytes. Empty-resource projections need not be persisted because they bind no URI. Before insertion, measure candidate-plus-history against all budgets; at capacity, reject admission with a precise diagnostic and preserve last-good. Never evict, truncate, silently reset, or bypass history. Duplicate projections remain allowed at capacity. If existing persisted history exceeds configured limits or is malformed, fail admission clearly rather than discard protection. These bounds limit retained storage and match count, not the CPU time of arbitrary existing Python regex; inherited matching semantics remain a separate limitation. Values are proposed, not implemented or approved.

Migration starts resource-routing history with the first successful post-upgrade admission. Existing exact-key rows cannot reconstruct old co-occurrence or winner precedence. Unknown pre-upgrade advertisements and unrelated/replaced databases remain outside the guarantee. Persist/validate a matcher policy version; an incompatible future matcher must fail closed until an explicit compatibility migration, rather than reinterpret history silently.

Touchpoints: `_models.py` and current model registry; `migrations/__init__.py` plus new migration; `_api_action_routes.py::prepare_actions/_prepare_actions`; `mcp/setup_mcp_server_v2.py::_McpCatalog/_read_resource` and a shared private winner-resolution helper; focused actual MCP history tests, SQLite/PG transaction/concurrency/migration tests, and canonical guide. No Core matcher change, new service, public API, or descriptor-revision change. Initial scratch regression currently encodes admission-style retention; after policy approval it should accept explicit read-conflict errors while asserting no replacement callback runs and the direct-precedence control still succeeds.

Canonical guide exact proposed addition after the existing cross-kind limit paragraph:

> Historical exact-key rows do not retain which resource routes coexisted or which owner won for a concrete URI. Direct resources take precedence; templates are tested in lexical order using the existing anchored placeholder-substitution matcher, whose literal characters are currently unescaped regex text. Any concrete-URI identity repair must preserve historical winner precedence. Testing every historical matching template can reject unchanged valid direct-resource routing. This remains a distinct gate until admitted routing-history retention and rejection-before-invocation are implemented and independently verified.

Contracts read: cached full #279 repeated-directory synchronization issue and closed #89 deterministic catalog/revision acceptance. This follow-up does not reopen #89 or expand #279 into compiler/workspace semantics. Upstream disposition: none; the reproduced dispatch and duplicated matching implementation are local, and no maintained dependency defect was established. Devsy HOLD. Last measured workspace free 877 MiB; RAM-backed scratch, no installations or heavy generation.
