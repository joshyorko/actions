# Isolated claimed Robot race tests

Only new isolated test_robot_claimed_races_327.py changed; SHA256 bb41f7b6e2ea2fd68543d5e6135338e6d2b83d343fc59192ed44472ecfcd9fa4. No production/existing-test edits, PG container/connection, Robot execution or environment materialization. Prepared RCC developer gateway ran Python SQLite tests only.

Observed result:4passed,4PostgreSQL parameters deselected in9.59s (second.log/results.xml). First run3passed1failed because test used literal complete instead of canonical Permission.COMPLETE.value; corrected test setup and ensured contender exceptions propagate before runner returns. No production change. Configured Ruff formatter/lint and Isort passed; known anyio assertion-rewrite warning remains.

Cases use independently opened Database connections with Barrier/Event timeouts20s, no sleeps:
- After three synthetic output seals, contender commits queue cancellation before adapter returns; publication rejected, Run/Attempt remain running, all3outputs provisional, item remains cancelled/FAILED.
- Same boundary commits removal of canonical COMPLETE grants; publication rejected with queue still IN_PROGRESS and no final outputs.
- Real queue lease UPDATE occurs, then injected Attempt-renewal failure; independent observer sees original committed pair of leases while writer's update is uncommitted, then both lease deadlines remain unchanged after rollback. Subsequent unmodified heartbeat renews both successfully.
- At queue-finish boundary inside publication transaction (Run already marked PASSED in writer view), cancellation contender is released. Terminal commit remains coherent and contender returns false; item DONE, Attempt succeeded, outputs final. This proves outcome at controlled transaction boundary; it does not measure PostgreSQL lock-wait duration or force CPU scheduling inside the database driver.

Prepared serial PostgreSQL selector: race-review/run-postgresql.py. Root must run only after existing broad PG workload releases capacity, with its existing ACTIONS_INVOICE_TEST_POSTGRES and ACTIONS_REQUIRE_INVOICE_PROVIDERS=1, through the same package gateway. The script selects only postgresql parameters and writes postgresql-results.xml. It does not start a container; fixtures create/drop per-test schemas on the explicitly configured existing database. PG remains NOT RUN here; do not count four deselections as passes.

Documentation improvement:
- Canonical file proposed: docs/skills/work-items.md.
- Exact addition: “Claimed Robot publication tests use independent SQL connections and bounded barriers: committed cancellation/COMPLETE revocation before publication must reject without finalizing outputs, and queue renewal followed by Attempt renewal failure must roll back both leases. A concurrent observer must not see the uncommitted queue extension. Cancellation released at the terminal transaction boundary must not split final Run/Attempt/output and Work Item state. Run the PostgreSQL selector serially against the existing owned database; SQLite outcomes alone do not qualify PostgreSQL lock behavior.”
- Evidence: second.log/results.xml; four deterministic SQLite cases including observer and recovered heartbeat.
- Stale ambiguity removed: injected finish errors alone are not concurrent-reader/rollback evidence; barrier scheduling is not a measured database lock-wait proof.
- Remaining uncertainty: four PG cases, actual installed RCC and public transport gates remain separate.

Upstream disposition: none. Local tests only; draft-only, no external reports.
