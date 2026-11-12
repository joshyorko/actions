# Queue publication counterexample, 2026-11-03

**Invariant:** a model caller authorized for a reviewed input queue must not see
an identifier belonging only to an unpublished output queue.

**Counterexample:** `SQLReviewQueue.finish_fenced` created a child in the
input queue's `_output` queue. The domain ItemView contained the child ID, and
the pre-fix model projection returned it even though only the input QueueRef was
published. This is disclosure of lineage metadata; it does not authorize a
fetch of that child.

**Reproduction:** in a detached worktree at pre-fix source
`95ae3e9873d5478197f1c52b137078f814228efc`, the regression test file was copied
from fix commit `a5da58bc79382dd0c09eafb0f998b0acdb24e2d3`; its SHA-256 was
`66a80679494085fb33089953a8b62e10857dcc63ee894f47e6dd37d17ded115e`.
The single real SQLite/DuckDB reviewed-output test failed because `child_ids`
contained the unpublished child ID: **1 failed, 3 skipped**. The three skips
were unconfigured PostgreSQL provider/control-plane cells. The same test file
and command at exact fixed commit `a5da58bc79382dd0c09eafb0f998b0acdb24e2d3`
passed: **1 passed, 3 skipped**. The command was pinned RCC 18.19.3's task
script gateway running the prepared Action Server Python with
`pytest -p no:cacheprovider .../test_managed_work_items_mcp.py::test_model_projection_omits_unscoped_item_lineage_from_real_sql_service -q -rs`.
The supervisors report no owned processes remaining for both runs.

**Fix:** the model projection omits parent and child IDs because the domain
ItemView does not identify their queues. Domain and REST ItemViews are unchanged.
The isolated before/after logs, supervisor receipts and command scripts are in
Library `libfile_4bce9541e9a88191b40a178105716284` version 0, SHA-256
`6f04b035a7992c0a44a2361821578b4f3615114db57890a467675d1ba0063de6`.

**Limits:** this is source-level SQLite/DuckDB evidence, not PostgreSQL, an
installed Runtime or ChatGPT host result. Neither commit has exact-head hosted
CI. The release branch still points to `642c6d3f`; current-source CI and all
remaining #327/#328/#340 gates remain required.
