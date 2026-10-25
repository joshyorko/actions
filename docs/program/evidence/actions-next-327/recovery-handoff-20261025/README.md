# Sole-integrator fresh-container handoff — owner-directed STOP

Existing campaign only:#327/Canvas71/draftPR328/release/327-invoice-vertical-20261020.
Both helpers stopped and released ownership. Root releases after this checkpoint.
DO NOT resume implementation/push until parent explicitly transfers ownership.
No new campaign, branch, PR, publication/tag/merge, GH Actions spending, external
repo mutation, credentials or tunnel. Protected root OAuth remains untouched.

## What this checkpoint is

Recoverable WORK IN PROGRESS, not a new qualified installed release. Last installed
qualified source is remote f1b11838674494cd6a34d343b97404cbb1537004 / tree
f094faf5d2eabbef0a159a7fabb4983a59a8e56c (local b23df406...). Last evidence checkpoint
before this handoff is d11650c4e73a0776e75e0ce3dcf1e197eca76b97. Local Git history maps
API commits by identical tree, with different metadata/parents; never force it onto
remote. Fresh checkout must follow the remote release branch.

Current implementation adds explicit per-Action bundle compiler/admission/selection,
outer Package revision receipts, and backend.actions authoring. Existing runtime
version remains a37; new authoring declarations require >=a38 deliberately. Therefore
this tree MUST NOT be advertised as an installed a38 candidate until joined tests,
versioning, actual canonical two-Action Runs and installed qualification complete.
Bundle format is still private v1-draft. No Robot implementation was added.

Completed:29bundle boundary tests; six actual RCC compiler phases for two Actions;
26SQLite registry tests;7selection boundary tests;10authoring declaration/orchestration
tests; package typecheck555files. Joined source:98both-SQL bundle/registry/selection,
6authoring,46logical-binding,32logical-receipt cases pass. The logical-domain batch
was INTERRUPTED at diskfloor, no complete capture/PASS. Other remaining modules
were not executed. Preserve failed/initial/interrupted receipts; no full-green claim.

Knowledge drafts are NOT applied. Apply full foundation patch ONCE (not its review
subset); migration22reserved,23SQLitepass, PostgreSQLunverified. Then optional
step2patch:30realDuckDBpass/freshprocessreopen; PostgreSQLclass NEVER RUN. Both are
metadata/codec/store foundations, NOT canonical ingestion/publication/search ready.
Exact patches, SHA manifests, limitations and guide proposals are retained here.

## Next steps after explicit ownership transfer

1. Fetch existing release branch, inspect AGENTS/.agents/skills + canonical guides,
   ledger/owner contract. Verify remote head/tree from parent; preserve new state.
2. Use pinned RCC18.19.3 Doctor -> Bootstrap -> ToolkitTest. No old local path is
   assumed. Recreate task-owned synthetic configuration; never copy protectedOAuth.
3. Inspect pending source and helperpatches; root bundle changes already applied.
   Finish remaining joined tests:logical_domain/logical_runner_join/task_service,
   generated_work_item_execution/generic_execution_port, foundry_authoring,
   foundry_authoring_model_contract, foundry_sql_authoring. Retain completed tests
   by exact source hashes; rerun changed surfaces only when justified.
4. Common PostgreSQL environment ACTIONS_INVOICE_TEST_POSTGRES points only to an
   owned local fixture; ACTIONS_REQUIRE_INVOICE_PROVIDERS=1 makes absence fail.
   Run package-local `poetry run pytest <module> -p no:robocorp_log_pytest -q
   --junitxml=<new-receipt>` through the prepared toolkit. Some logical-domain tests
   start a SECOND owned TLSPostgres container: budget BOTH allocations (~600MiB each
   observed) plus test space and768MiBfloor. Fresh disk headroom is required.
   Custom pytest launcher MUST guard __main__ for multiprocessing spawn.
5. Finish real two-Action canonical/installed execution, then integrate Knowledge
   drafts with strict SQL tests and remaining durable-ingest/search joins. Genuine
   Robot/direct plans, broader Task/WorkItem/effect recovery, full MCPApps/client and
   final artifact/upgrade/downgrade/restore/sharedPG/platform gates remain required.
6. Existing extension tester can independently use extension-handoff/README.md now.
   Schema drift is confirmed;2.20.14 correctly rejects it. Existing extension owner
   is reviewing adaptation with negative tests; do not bypass its check.

## Environment/process and evidence state

Old executor was usable at stop. No helper test processes remain. All owned harness
Postgres fixtures stopped; nested2d5dfff714ba had Running=false/Pid0/ExitCode0 after
captured logs and graceful stop. No active RCC views were deleted. Exact task-owned
inactive trace compression receipts preserve decompressed hashes. Do not spend more
work here on storage cleanup; owner requested a fresh saved Actions environment.

Local-only bulky wheels/source archives/fixture archives/datadirs/screenshots remain
preserved in /workspace/actions-recovery-327. They are NOT assumed present in fresh
container and have no invented download URLs. Existing real synthetic screenshots
are committed at3e58d7fa958bec6cc1a496db29c06c96c569e360 under recovery-a32/ordinary-browser.
Library tools/list HTTP401; no uploadIDs. Authenticated Codex401 remains operatorgate.
Celld326 remains NO-GO: no exact new owner answer was received in this thread.
No Dakota/ChatGPT READY claim. Security incident assessment already in recovery-a28;
never repeat token, rotate live credentials or rewrite shared history.

Known local changes intentionally excluded:generated _static_contents.py and five
old a26/a27 CRLF/stat-only log changes. Their paths/hashes are in local-excluded.json.
All new intended source and scoped drafts are saved in this checkpoint. Private
synthetic auth files/datadirs are not included. Upstream disposition:none; earlier
Pydantic draft remains unsubmitted, no external issue authority.

Exact patches, XML and raw diagnostic logs are stored as `.b64` text to preserve
original bytes while satisfying whitespace checks. Decode with Python base64.b64decode
to the original filename before git apply or reading XML. encoded-evidence.json
records original paths and SHA256; no diagnostic whitespace was silently rewritten.
