GO for exact-source PostgreSQL v12-to-v13 two-independent-process migration API gate only

All six retained artifact hashes and byte counts match. Test status 0 on PostgreSQL 17.11 linux/amd64, immutable aa90e97 image, source 4e8a/tree1b582, prepared RCC-selected Python3.12.15.

Distinct OS children 20772/20773 map to backend112/115; one simultaneous observation records both blocked by controller98, second also by first112, before release. Both result PIDs match; both exit0/UP_TO_DATE and are reaped.

Frozen assertions establish exact named migration history12/13, single migration13 record/table, empty catalog, full columns/index parity with fresh production bootstrap and unchanged counters/existing table counts.

Owned container95abd086 was independently absent; credential/raw temporary files absent; child cleanup has no errors. Server logs have no ERROR/redundant-BEGIN, but include Alpine locale warning and transient temporary-init-server shutdown FATAL; no zero-warning/FATAL claim.

Canonical guide proposal: A PostgreSQL migration-concurrency receipt must bind two distinct OS child PIDs to two backend PIDs observed simultaneously waiting on the production advisory migration lock before release. Record both child outcomes, exact migration history, bootstrap-equivalent columns/indexes, preserved existing rows/counters, and owned-service/credential/child cleanup. A v12-to-v13 migrate_db receipt proves that migration API boundary only; keep CLI startup, mixed versions, failure recovery, packaged workers, TLS and whole-issue acceptance separate.

Limits: Actual gate ran by Luna; reviewer independently read retained evidence and live cleanup state. First two scratch failures remain immutable and do not count as passing migration proof. No full #84/CLI/failure-recovery acceptance.

Upstream disposition: none.
