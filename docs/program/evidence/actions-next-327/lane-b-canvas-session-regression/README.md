# Two-role Canvas session regression

Review found that the continuation runner assigned AppSession metadata to its MCP
ClientSession variable after opening ingestion Canvas. Search then attempted
`dict.call_tool`, raising AttributeError. The previous 45 tests did not execute
this two-role path. This is a runner defect, not a Runtime product defect.

The regression exercises ingestion and search, both with and without AppSession
metadata. It verifies all four calls use the original session and preserves each
role's distinct token when present. Before the rename, both cases failed with
AttributeError; stdout/XML are retained. Renaming the metadata local to
`app_session` fixes the shadowing. No authentication behavior changed.

Commands from prepared package-local Poetry in action_server:

```bash
poetry run pytest -p no:robocorp_log_pytest tests/contract_tests/test_lane_b_installed_lifecycle.py -k canvas_keeps --junitxml=/workspace/lane-b-state/canvas-session-before.xml
poetry run pytest -p no:robocorp_log_pytest tests/contract_tests/test_lane_b_installed_lifecycle.py tests/contract_tests/test_lane_b_installed_output_http.py tests/contract_tests/test_lane_b_installed_knowledge.py --junitxml=/workspace/lane-b-state/canvas-session-after.xml
```

The first command is intentionally preserved as failed regression evidence.
The after run exercises the focused source/simulated suite; it is not installed
acceptance. Installed HTTP remains NOT_RUN pending remote mounted checkpoint.
Rollback: revert this correction (reintroduces the known runner defect).

Exact proposed addition to docs/skills/repository-operations.md:

> Installed acceptance harness tests must exercise the complete multi-role
> discovery sequence. Keep MCP ClientSession and Canvas AppSession metadata in
> separate variables, and assert the same client handles both ingestion and
> search discovery. Artifact-checker and HTTP-probe unit tests alone do not
> qualify orchestration control flow.

Evidence: the retained two-case failure before correction and passing two-role
regression after correction. Removes the implicit assumption that checker tests
cover orchestration. Remaining uncertainty: genuine installed HTTP execution.
Upstream disposition: none.

Published failure stdout/XML have trailing whitespace normalized for the repository gate; original bytes remain in /workspace/lane-b-state/canvas-session-before.log and canvas-session-before.xml.

## Missing metadata after restart

A second review identified stale AppSession reuse when a later canvas_get omitted
metadata. The same two-role regression now repeats discovery with metadata
absent. Before the fix, the previously populated case failed (1 failed, 1 passed,
6 deselected); after popping each role before storing a newly issued token, all
47 focused tests pass. Retained stale-session-before/after stdout/XML use the
same commands above with corresponding receipt names. These tests use synthetic
strings only; no real AppSession token is published. Raw failure files remain
under /workspace/lane-b-state; published trailing whitespace is normalized.

Additional exact canonical-guide delta:

> Clear cached per-role AppSession tokens when refreshed Canvas metadata omits
> them. A post-restart denial probe must use a freshly supplied token, or report
> AppSession NOT_RUN; denial of an obsolete token is not fresh-session evidence.

Evidence: repeated discovery regression and retained before/after receipts.
Remaining uncertainty: installed HTTP execution. Upstream disposition: none.
