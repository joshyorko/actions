Canonical target: docs/skills/repository-operations.md, configured logical preparation/execution readiness section.

Exact proposed addition:

Selected bound execution readiness verifies local adapter dependencies before
Task admission. `GeneratedRccExecution._verified_selection` delegates to the
logical port only for capabilities with nonempty immutable requirements. The
port finds their exact retained Deployment bindings and the configured factory
imports only modules needed by those selected operations. It creates no engine,
connection, source-materialization job, secret resolution, grants, Run or Attempt.
This check is not called by factory construction or ordinary startup, and an
unused provider's missing optional dependency cannot reject another selection.

DuckDB sealed scans require the declared Runtime `data-duckdb` extra (currently
DuckDB1.4.1). PostgreSQL CSV scans require psycopg; selected PostgreSQL Parquet
scans additionally require DuckDB because the retained Parquet decoder uses it.
Installing a base Runtime wheel does not imply every optional adapter exists.
Missing or unloadable selected modules return a bounded unavailable error before
Task admission. Successful module import is dependency readiness only, not
connection, credentials, source-byte, privilege or execution qualification. Live
execution authorization and actual engine validation remain unchanged.

Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md.
- Durable learning: selected-provider readiness must include transitive decoder dependencies, without probing all configured providers or moving engine/secret work into startup.
- Evidence: host-final.xml5PASS SQLite/synthetic host-lifecycle state; real TaskHost.require_ready -> verified selection -> TaskService admission path; missing dependency preserves Run/Attempt counts; present dependency admits one Run without Attempt; PostgreSQL CSV ignores missing DuckDB while Parquet requires it. pyproject declares duckdb1.4.1 optional under data-duckdb.
- Stale ambiguity removed: logical port configuration alone is not optional-adapter availability, and a basewheel installation is not DuckDB readiness.
- Remaining uncertainty: module import does not qualify operational engine/credentials/source availability. Root owns installed consumer retry and actual two-provider execution.
