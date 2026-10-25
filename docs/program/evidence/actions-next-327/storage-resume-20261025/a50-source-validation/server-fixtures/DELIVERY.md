# Two confirmed server fixture repairs

Changed only isolated worktree `test_server_async.py` and `test_server/test_server_full_openapi_flag.yml`; root remains sole committer. No production changes.

Async test now uses existing wait_for_non_error_condition(timeout=10) to observe actual RUNNING through the public Run endpoint before cancellation. It tolerates only NOT_RUN while awaiting startup; unexpected terminal/error states fail immediately via pytest.fail. The20-second Sleep cannot satisfy the running-state predicate by naturally completing. Existing cancel response and eventual CANCELLED assertions remain unchanged. Removed the unused request-ID helper/commented wait. This corrects the confirmed0==1 race without changing async production semantics or adding a fixed sleep.

OpenAPI fixture adds only the43reviewed lines for the three assembled managed Work Items routes: schema, capabilities, operations. No route/auth/source change or broad snapshot refresh.

Actual final focused result:2passed,0skipped,1warning,6.94s. Both parent `_server`/`_selftest` and a child Python import are asserted to resolve to the isolated source. The wrapper exports that source-first PYTHONPATH to ActionServerProcess. Initial attempt1passed/1failed exposed child maina49 versus parent isolateda50; its log/XML/tmp remain preserved. This was fixed in the external runner wrapper, not by weakening the fixture version assertion or modifying package metadata. Final test temp is separate tmp02.

Configured Ruff check/format plus isort PASS for the one changed Python file; formatter made no changes. Both ordinary server test fixtures completed shutdown. No PostgreSQL or heavy RCC build/compiler workload started. Source qualification only, not a clean-installed candidate claim.

Artifacts: repair.patch, hashes.json, receipt.json, focused.xml/focused-final.log, format.log and preserved initial-origin-failed.log/xml. Main full suite remains FAILED4299passed197skipped3deselected5failed; these two focused passes do not supersede its complete result or address its other three failures.

Canonical documentation proposal: “An async timeout response confirms admitted background work, not worker startup. Before asserting active cancellation, poll the public lifecycle with a bounded deadline, accept only the expected pre-start state and fail unexpected terminal/error states. Preserve cancellation assertions. For full OpenAPI regression updates, review the exact newly mounted routes and update only that schema delta. Isolated source tests that spawn servers must assert both parent and child import origins; a source-version mismatch is an environment failure, not grounds to relax version checks.”

Upstream disposition: none. Owned fixture repairs; no external mutation.
