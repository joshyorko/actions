# Independent static compiler recipe review

Disposition: HOLD pending bounded cleanup correction. No recipe import, RCC execution, materialization, authentication, server, or network action was performed.

Reviewed prepare-compiler.py SHA256 13a47afd9f8c6158433c3e098870e4183a55e377ecde76fcb7bdd9df256f8568 and verify-core.py SHA256 a69b5a9e9e45b87803c89068c17210891040ee92171b6db0b604e06e5adf554d. Both parse successfully. Compared frozen a44/source API definitions and compiler-a6 publish.py/prepare-receipt.py.

Confirmed: frozen source d0c87a38a937cc339e8e661ac453c7a62ed41fa6; actual Runtime wheel SHA256 1502214a6a6319521984d554244aca502659fc919d5a31bac94727d3e534104c; actual Core wheel SHA256 718ea63637f096d26c4de5f82ca736eec1358b197d0a63883c063ad205e0860e contains exactly 87 payload files including 82 Python files. PreparedRccEnvironment/RccBuildIdentity/descriptor/build_exec_command/read_receipt call signatures match frozen source. Output compiler_* keys match managed-qualify.py consumers. Fresh root and isolated candidate interpreter checks, new local trust carrier, no-build proof, bundled RCC identity and declared bounds are present. Parent established isolated candidate identity remains prerequisite: wheel identity plus installed version alone does not independently hash every installed Runtime member.

Blocking correction: run() finally currently executes proc.wait(timeout=10) before descendant cleanup and stream closure. A timeout or psutil failure skips later cleanup, contradicting unconditional descendant cleanup documentation. Independently attempt group stop, bounded direct-child wait, descendant stop/reap, selector/stream close, retaining a failed outcome if any phase fails. Dedicated recipe process ownership makes recursive-child cleanup appropriate here; do not generalize to embedding in a shared process.

Bound enforcement correction: check lane usage and free-disk floor after process completion/cleanup and before publishing success. Current checks run only inside the process polling loop; last writes may occur after its final check. The bounds are sampled, not filesystem quotas; document this accurately.

Nonblocking: sanitization operates on arbitrary read chunks and cannot guarantee redaction across split headers or URL credentials. No credential-bearing inputs are intentionally supplied, and authenticated proxy URLs fail closed; keep logs local and do not describe this sanitizer as a general secret boundary.

Documentation improvement (exact proposed canonical addition): “Compiler preparation runs in a dedicated isolated consumer process. Every cleanup phase must be attempted even when another phase fails; check sampled disk bounds again after child cleanup before emitting success. Static recipe review proves API and artifact wiring only. Target-local publication, no-build payload verification, and GUI acceptance each require separate receipts.”

Upstream disposition: none. Findings concern owned handoff code; no confirmed upstream defect or authorized external reporting target.

## Corrected revision: static review cleared

The earlier HOLD is resolved for prepare-compiler.py SHA256 bd29bcdf6d85a26705a0d26645b53634d9428bc78368763311db8002e48d045c. Payload verifier remains a69b5a9e9e45b87803c89068c17210891040ee92171b6db0b604e06e5adf554d. AST parsing succeeds without importing or executing the recipe.

Group stop, direct-child wait, descendant cleanup, selector close, every stream close, and final budget now have separate attempts. Cleanup errors retain sanitized phase/type labels and fail the run. The final budget follows process cleanup; phase telemetry explicitly labels measured allocation as sampled rather than proof of an unsampled peak. API/identity wiring remains unchanged from the verified frozen-source comparison.

This clears the identified static-review blockers for a bounded target-side trial. It is not a cleanup fault-injection result, materialization pass, or low-capacity acceptance result. The 0.2-second selector timeout is a nominal poll delay, not a guaranteed sampling frequency (directory traversal and I/O add time). Small local receipt/config writes follow the final process budget measurement. Descendant enumeration/termination remains one failure-labelled phase; a failure stops acceptance rather than establishing all children were successfully reaped.

Next exact gate: execute the recipe once in the dedicated consumer process, retain capacity.json plus publish/proof logs, and require all 87 payload comparisons, isolated context behavior, execution receipt, and clean bounded teardown before claiming preparation success. Canonical documentation proposal above remains applicable. Upstream disposition: none.
