# Claimed Robot Task readiness correction

Predecessor a50 source `72c8a13e90a4e5bfb6e0ea24e818f7589e75c96b` built and passed installed payload verification. Core8 compiler preparation passed all three phases, verified 87 payload / 82 Python members, and proved isolated context. The six-file SQLite/PostgreSQL regression passed 240 tests with no skips; source fingerprints and exact PostgreSQL cleanup passed. Committed-source contracts passed 49 tests. These results do not establish installed Task acceptance.

Actual a50 installed Task qualification FAILED before creating any Run, Attempt or Task receipt. All three Runtime processes stopped gracefully; outer cleanup had no errors or descendants. The outer ExceptionGroup lacked leaf diagnostics. Independent source analysis and an actual-runner RED regression exposed claimed readiness calling standalone-only eligibility. Preserve the original a50 failure.

The a51 fix adds distinct consumer/claim readiness through the actual PinnedRobotRunner. It preserves standalone none-mode rejection, no outputs, declaration/policy agreement, current activation, authorization and host scope. Actual-runner regression: 15 passed / 15 PostgreSQL deselected; prior RED: one failed / nine passed. Initial configured static checks failed import sorting; the corrected configured lint/typecheck passed 649 files.

Next gate: exact a51 clean build and installed terminal claimed Task success/failure/restart, followed separately by live cancellation. Core8 remains byte-identical: `42e550a8c207849e0a428fa702827ff2f77d98a00fd63aa0f85a912c0719419f`. Same-target prepared artifact `sha256:0a0e5fee81bc3d747aa685d634880e94e344643e942a70733b4280af6d89a8a7` may be reused under exact proof checks. No trust transfer. Full Runtime remains FAILED at a49; complete a51 Runtime qualification is NOT RUN.

The independent Node SDK2 synchronous adapter is prepared, not executed. Its pinned stock SDK rejects Task calls under the required 2026 protocol before transport. Node Task acceptance remains HOLD; Python results cannot supersede it.

Upstream disposition: none; local readiness dispatch defect.
