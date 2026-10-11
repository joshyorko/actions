# CI failure triage (read-only)

The two runs fail for different reasons.

PR310 run 38089058102 (`ec8bea135569d98a3a63ef4f4f07b7dcc87e9f9d`, merge `33c936be57c7d567a5841d93e6fc8b3a07f3457c`) fails `inv typecheck` on Windows, Ubuntu, and macOS. All jobs report the same four Mypy errors, “Unsupported right operand type for in (\"object\")”, in `test_dakota_workitems_native_ui_acceptance.py` at lines 745, 781, 782, and 800. Ancestry confirms this is introduced by PR310: lines 745/782 came in `ec8bea13`; lines 781/800 and the `dict[str, object]` receipt shape came in `1b534c59`, both after base `19380993`. This is not an inherited prior-292 failure. In PR292 run 38098225220, Windows and Ubuntu typecheck steps passed; macOS was still in progress when inspected. PR310 integration, lint, and docs steps passed on all matrix jobs.

PR306 run 38087471281 (`1421fcf85c1b681aef1fe58fe2902f776f208167`, base `19380993febaa71238eaee3026b5c808773283ff`) has one Windows integration failure: the duplicate MCP template test waits for the packaged server's readiness/port detection and reaches `TimeoutError` at `_selftest.py:198` after its 90-second bound. The log records subprocess start and action import shortly before timeout. The test file's Git blob is identical at base and head; the PR delta touches `_database.py`, its database tests, and this guide. Ubuntu/macOS jobs passed. This does not prove an infrastructure fault or a database/SAVEPOINT regression; startup behavior under the database delta remains an uncertainty.

No raw workflow log was retained. Only the bounded excerpts in the JSON receipt are preserved. No jobs were replayed, no repository source or workflow was changed, and no upstream report is warranted.

Documentation improvement:
- Canonical file proposed: `docs/skills/repository-operations.md`
- Durable learning: bind CI attribution to the tested merge SHA and line-level ancestry; record timeout site/bound without labeling it infrastructure or product failure from platform count alone.
- Evidence: exact run/job summaries and `git diff`/`git blame` records in `ci-failure-triage-v1.json`.
- Existing guidance retained: Action Server Mypy includes tests; platform-specific CI jobs execute configured checks.
- Remaining uncertainty: cause of PR306's isolated Windows startup timeout.

Upstream disposition: none.
