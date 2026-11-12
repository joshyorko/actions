# Canonical guide improvement receipt

Target: `docs/skills/repository-operations.md`, generated execution/lifecycle qualification. Proposed exact insertion (scratch lane; sole integrator owns canonical edit):

> Requirement-bearing generated Actions use one absolute monotonic deadline across eager logical preparation and RCC execution. The runner owns cancellation checks and domain heartbeats; a preparation thread opens its own Database connection and receives an Event, never a callback that reads another thread's SQL connection. The ordinary generic heartbeat renews both the Work Item claim and Run Attempt. A shared LogicalExecution supervisor admits at most four concurrent outstanding preparations, including transferred preparations still in use by RCC. It refuses new preparation once closing starts.
>
> Shutdown must retain every unsettled preparation owner. An unclaimed late result can be released exactly once after its preparation thread joins. A transferred preparation must remain issued until its runner confirms cleanup and explicitly releases it; supervisor close returns false rather than stealing that ownership. TaskHost may confirm a previously unsettled preparation on a later close call, but remains failed and cannot accept new work. Unconfirmed RCC process cleanup remains latched separately. Provider teardown is forbidden while either owner reports incomplete cleanup. These rules do not recover or fabricate a terminal Run.
>
> Zero-requirement execution preserves its existing helper and v1 wire bytes. Logical requirements choose strict v2 journals from the immutable capability, with a safe logicalReads summary in launch and terminal records. The prepared context stays in a private bounded file and is installed only around the Action call through the private Core SDK context API. It is not an input parameter or output artifact. The runner retains the issued publication binding through output staging and atomic publication, then clears it before releasing the preparation. Retained-launch replay refuses to prepare or execute again.
>
> Qualify ownership with deterministic preparation barriers and real SQLite/PostgreSQL fences; qualify the context helper's bounds, digest rejection and context reset separately. Synthetic RCC results can prove the SQL publication join but do not prove native RCC or an installed consumer. Enabling logical Tasks additionally requires v2 Task/read projections and ordinary bootstrap wiring; these are separate gates.

Evidence: new `test_logical_preparation.py` (capacity, late release, transferred ownership, private helper and archived v1 helper hash), `test_logical_runner.py` (thread ownership and dual-fence renewal/abort on both SQL backends), and `test_logical_runner_join.py` (real eager reads and SQL with explicitly synthetic RCC output, shared deadline and guard lifetime). Final command/results and source identity are in receipt.md/source-identity.json. No installed/native RCC claim.

Verified learning: capacity must count issued ownership beyond thread termination; joining a worker alone cannot authorize provider teardown while a transferred preparation remains live. No cosmetic guide or new guide-index entry needed.

Upstream disposition: none. Changes integrate Actions-owned execution, lifetime and SDK handoff. No external report or mutation.
