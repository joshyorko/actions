# Helper and detached fixture repair

Only the allocated two test files changed; production guards are unchanged.

The historical unbound helper SHA c9a99cd5b6dd7320fda2d0a38e4fbeb9a94c0095b119b9da9c66c00ccdd24086 predates commit 1eca22efe6f7201166c15f84a8d0de05aea03aad, which adds JSON-mode model serialization. The repaired byte assertion permits exactly that one line and still verifies the archived remainder. No logger import appears in this helper. Five behavioral cases execute the current helper and verify plain/model-date output, NaN and oversized-output refusal, exclusive creation and private permissions. The detached fake bypasses __init__; setting capability_runner=None restores the real constructor default while preserving its local stop predicate assertions.

Focused prepared-gateway pytest: 25 passed in 0.81s. No PostgreSQL or actual Robot workload. See focused.log/xml and format.log/lint.log. No commit made.

Documentation improvement (exact proposed addition to docs/skills/repository-operations.md):

“When generated execution helper bytes intentionally change, retain an archived-byte assertion for the unchanged remainder and explicitly account for the reviewed transformation. Pair that check with execution tests for serialization and result-file failure boundaries; updating a digest alone does not prove those contracts. Tests that construct a worker through object.__new__ must explicitly provide constructor-default dispatch dependencies, so a fixture omission cannot masquerade as a production cancellation regression.”

Evidence: commit 1eca22ef, test_unbound_helper_archived_bytes, test_unbound_helper_serialization_and_result_boundary, and focused.xml. Stale assumption removed: unbound helper bytes are wholly identical to c7d94ca. Remaining uncertainty: full package verification belongs to root; this lane ran only the allocated focused modules.

Upstream disposition: none. These are local stale test fixtures, not an upstream defect.
