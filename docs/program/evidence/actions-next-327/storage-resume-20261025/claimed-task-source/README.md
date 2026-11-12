# Claimed consumer Robot Task source integration

Isolated development from 5b9c70e00e5e019a751aec5385591e5a2bbd615e while the a49 full Runtime suite was frozen (now terminal FAILED). Runtime source is separately versioned 1.1.0a50; Final integration also adds the reviewed public logging bridge and requires Core a8. Earlier source tests and Core7 installed plans remain historical; fresh Core8 plans and installed qualification are required. No installed acceptance is claimed.

Strict detached-claimed invocation joins canonical queue inputs, Run admission and Task receipt atomically without an Attempt. Configured host worker identity is enforced, then its worker claims the same Run. Existing synchronous Runs cannot gain Task receipts. Terminal Robot failure is MCP Task completed with isError=true.

The independent-cancel regression first FAILED because Generic authorization borrowed execute authority. The corrected Task-specific path checks Run and queue CANCEL, exact live claim/Attempt fence, mutates SQL only, then validates all retained facts before commit. Corruption or queue failure rolls back both owners. Active cancellation stays working/unconfirmed; child stop is not established.

Combined SQLite selection: 93 passed, 143 deselected (including PostgreSQL cases). Separate no-provider/schema cancellation tests: 2 passed. Configured source+test typecheck: 648 files passed. Independent authority review cleared the final cancellation implementation. Earlier fixture expectation and static failures are preserved; no prior failed receipt is rewritten.

Remaining: PostgreSQL boundary/concurrency selection, exact new installed candidate, public Task create/execute/result/restart and observed live cancellation cleanup. No public release, multi-principal or producer/child Robot proof.

Canonical guide changes integrate the admission/wire/host/cancellation reviews. Reviewer suggestions about retained replay fences and outer process supervision apply to the separately prepared installed qualifier, which remains NOT RUN. Upstream disposition: none.
