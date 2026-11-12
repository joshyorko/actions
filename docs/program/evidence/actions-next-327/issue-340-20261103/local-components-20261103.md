# Issue 340 local component checkpoint, 2026-11-03

The release PR remains at `642c6d3f62c2d271d33459553ef560a10f283f1f`. The
integration branch was last pushed at `888482c12ccbdd183909f44c4ba588dfcd3a19d1`.
The later local product commits through `204656834d15c442985c90933890a87d6819e768`
are preserved in Library `libfile_80243ce193e08191985204435c77c2de`, version 4.
The Git bundle is 34,013 bytes, SHA-256
`1039e1ebe17340ca1314abba99f3e39b0c963c3c9773e43b949feecec17e28c4`,
and requires the pushed `888482c` commit. A subsequent push failed with GitHub's
`Invalid username or token`; it did not update the remote. No credential or
security changes were made.

## Focused evidence

- Existing generic and Task source regressions after explicit model-publication
  fixture updates: 60 passed, 111 skipped. The earlier run failed 32 existing
  positive fixtures because they lacked the now-required publication selection;
  those failures are not relabeled. SQLite is exercised; skips include PostgreSQL.
- Headless discovery and paging: 23 passed, 12 PostgreSQL skips. MCP protocol
  component tests: 13 passed; discovery wiring tests: 2 passed, 2 skipped.
  These do not prove installed transport or native host startup. The bounded
  scan still has coarse hidden-inventory timing and overflow considerations.
- Canvas alternative-plan regression: the new negative failed before the fix;
  the corrected selection suite passed 15 cases with 30 skips. The default
  Canvas plan remains the published plan.
- Managed Work Items facade: 9 focused tests passed for exact queue and operation
  filtering and projections. It is not wired to native startup: live publication
  and authorization must be checked in the mutation transaction under the shared
  workspace lock. Facade preflight alone does not establish revocation safety.
- The typed internal child Run client contract passed 14 focused Core tests. It
  has no Runtime transport, durable lineage, host delegation, or installed
  Action-to-Robot proof. A pending cancellation is not a terminal cancellation.

Tests used the prepared RCC task environment with a host supervisor and capacity
floor; raw logs are executor-local at `/tmp/actions340-*`. The historical a60
installed Data Run receipt is separately recorded in `a60-installed-data.md`
and applies to `642c6d3f`, not these local commits. The green a60 CI runs apply
only to their recorded source. None of these component results establishes full
#327/#328/#340 acceptance or authorizes publication.

Remaining required work includes real installed RCC verticals, source-current
SQLite and PostgreSQL parity, auth/flag/restart/idempotency and Canvas/MCP gates,
full current-source CI, and the actual owner ChatGPT host test. The prior denied
PostgreSQL role/grant setup remains stopped; the protected-home access denial
also remains an environment restriction. No release, merge, or deployment was
performed by this checkpoint.
