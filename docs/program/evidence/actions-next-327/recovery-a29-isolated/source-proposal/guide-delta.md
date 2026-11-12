Exact durable addition to docs/skills/work-items.md, bound generic semantic forms:

“Reopening a completed app Run must recompute its authorized terminal output handles through the same projection used by direct execution/status. Run/queue READ+ARTIFACT_READ grants are live checks; permission denial omits handles. Resolve every exact Run/workspace sealed handle before attaching the complete inventory. Malformed/mixed references fail closed rather than returning partial output. Project handles only after selecting the latest associated Run per binding, so historical output inventories are not copied or unnecessarily resolved. A completed-state-only reopen is insufficient browser acceptance: explicitly inspect a retained artifact after a real process restart, while retaining the original failing receipt if applicable.”

Documentation improvement:
- Canonical file proposed:docs/skills/work-items.md; exact paragraph above.
- Durable learning:completion status is not usable reopened artifact state; shared live output projection prevents the frontend from blocking inspection before sending a request.
- Evidence:root’s installed-a28 restart browser failure; test_generic_reopen_artifacts.py red3 then green6 across SQLite/PostgreSQL; exact resolve call, queue-grant revocation and corrupt inventory tests.
- Stale/ambiguous guidance removed:implicit claim that completed-state-only reopening qualifies artifact recovery.
- Remaining uncertainty:root must rerun installed/browser restart with rebuilt candidate; source boundary tests are not installed proof.

Upstream disposition:none. Local projection omission, no dependency issue or external action.
