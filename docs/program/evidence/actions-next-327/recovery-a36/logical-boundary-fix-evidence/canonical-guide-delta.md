Canonical target: docs/skills/repository-operations.md, Common Run Task receipt and Bound generated execution receipt sections.

Exact proposed addition:

V2 Task acknowledgement and result retrieval use distinct retention checks. A
terminal creation/replay acknowledgement without a result may validate expired
final-output metadata. Both Task projection and its no-result formatter pass
this private terminal-only mode; it never authorizes pending publication.
Immutable operation identities, lineage, final SQL seals, inventory and canonical
retention timestamps remain checked. A corrupt seal or malformed timestamp is
unavailable even for acknowledgement. Result get, publication and ordinary
validator defaults still enforce current output retention. Do not make Task
acknowledgement depend on retaining readable artifact bytes indefinitely.

The logical invocation binding accepts a trusted `publication_check` callback.
The mixin invokes it inside the existing transaction immediately before canonical
base publication, after domain schema and child-output validation. It returns
None or raises, and may inspect only monotonic time and in-memory cancellation;
it must not query SQL, providers, files or secrets. Durable cancellation remains
the canonical base fence's responsibility. The native runner supplies this
callback explicitly to close the wait/validation interval after its earlier
deadline check. A callback failure rolls back publication and leaves provisional
outputs and Run/queue authority uncompleted. This gate is not a promise that
native SQL operations have hard real-time completion bounds.

Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md.
- Durable learning: no-result Task acknowledgements need closed metadata validation independent of artifact expiry; final in-memory budgets must be checked after domain validation, inside the publication transaction.
- Evidence: red.xml4FAIL reproduced both boundaries; final.xml55PASS/19deselected SQLite-only component regressions; retention-final.xml4PASS adds malformed-expiry metadata refusal. Pure callback tests move deadline/cancellation during schema validation and verify no terminal write.
- Stale ambiguity removed: a pre-transaction deadline check alone does not cover SQL wait/domain validation; strict get expiry need not break durable terminal acknowledgements.
- Remaining uncertainty: root owns PostgreSQL qualification, runner callback integration and installed acceptance; no RCC/container/full-suite evidence in this bounded lane.
