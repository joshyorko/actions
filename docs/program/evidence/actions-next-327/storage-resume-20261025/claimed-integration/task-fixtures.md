# TaskService retained-result fixture repair

Only authorized test_generated_knowledge.py and test_logical_domain.py changed. Each replaces unbound TaskService._result(SimpleNamespace(...)) with a real TaskService constructed over real DetachedActions(owner.deployments,g.outputs), explicit TaskPolicy and readiness object that raises if dispatch is attempted. No production change, method mocking, validator bypass or permission weakening. Existing corrupt-receipt, issued-authority, cleanup and output-read assertions remain intact. Hashes hashes.json.

Cause: production _result delegates to self._result_payload; partial namespace lacks the real static helper. Red targeted tests both reproduce AttributeError,2failed(red.log). Green affected files SQLite selection:28passed,19PostgreSQL cases deselected in23.40s(green.log/XML). Ruff lint/formatter and isort check pass after local import sorting; diff check clean. No PG or actual Robot/RCC execution; prepared developer gateway only. No commits.

Broad report classification: these fixtures explain generated-knowledge failure plus logical-domain SQLite/PostgreSQL failures (3 of5). Other2 failures are separate test_logical_preparation archived-helper SHA and test_logical_publication_deadline bound fake API mismatch; outside this lane and not fixed/claimed passing. Parent notified.

Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md.
- Exact addition: “Retained Task result tests should construct real TaskService/DetachedActions instances with explicit policy and a readiness guard that rejects dispatch. Calling production methods on SimpleNamespace partial selves breaks when internal delegation changes and can omit inherited validation helpers. Preserve real output resolution and authority assertions; classify such fixture failures separately from actual terminal validation defects.”
- Evidence: two exact AttributeError reproductions followed by28affected-file SQLite passes without production edits.
- Stale ambiguity removed: five broad failures are not all the same partial fake; three are covered here, two remain separate repairs.
- Remaining uncertainty:19PGcases deselected and broad suite not rerun by this lane.

Upstream disposition: none; local test fixtures, draft-only, no external report.
