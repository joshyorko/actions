# Claimed Task host readiness boundary

New isolated test file only: action_server/tests/action_server_tests/test_claimed_task_host.py. Actual DetachedTaskHost constructor and readiness methods; host's ready/thread fields are deliberately simulated, and Robot provider preparation is a spy. No worker startup, real RCC or PostgreSQL/service launch. Existing claimed/Generic package+SQLite fixtures supply real retained metadata and authorization.

Final9passed9PostgreSQLdeselected1warning2.60s. The gateway wrapper verifies isolated Generic module origin before pytest and uses isolated source/tests. Configured Ruff check/format+isort passed for this test file only. Initial8pass1fail was an expected-exception mismatch: real non-Robot rejection raises FenceRejected, not the test's initial PermissionError/ValueError tuple. Exact failure log/XML preserved; correction expects precise FenceRejected/message. No production guard changed to pass tests.

Coverage: pure scope works inside SQL without touching DB connection/claimed-service/provider; full readiness refuses SQL before provider selection; exact server-held worker, actor, profile, Deployment, queue policy and host-stop mismatches fail before provider preparation; non-Robot retained metadata is rejected; host stop during provider readiness is caught by the second scope check. This proves boundary ordering, not actual installed worker readiness or execution.

Canonical documentation proposal: “Test claimed Task readiness with the actual host identity checks. Wrong claim owner/profile/Deployment/queue must fail before provider preparation. Pure scope rechecks perform no database/archive/provider I/O and may run inside admission SQL; full readiness must run outside SQL and recheck host scope afterward. Label simulated ready-thread/provider fixtures explicitly; they do not qualify worker startup or real RCC execution.”

Upstream disposition: none. Owned host boundary tests; no external mutation.


Authorized follow-up production narrowing: only the three reported queue None sites were changed to explicit local-name checks raising AccessDenied/TaskHostUnavailable before use. Scoped Ruff check/format/isort PASS. Scoped mypy PASS3files with explicit namespace/package bases, no incremental cache and isolated MYPYPATH (`static-narrowing-final.log`); earlier source-resolution failures remain in static-narrowing-origin-failed.log/static-narrowing.log. No blanket casts or queue guard removal. Root's separate cancellation-only authorization failure is outside this test lane and is not superseded by these results.
