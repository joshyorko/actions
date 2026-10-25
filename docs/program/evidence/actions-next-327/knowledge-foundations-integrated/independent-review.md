# Saved Knowledge patch review

Reviewed against recovery commit `332e0bd4a9fb8ee06652c63d7f2c11b3b423150b`.
No repository source or GitHub mutation; no new test execution.

Verified decoded patch hashes:

- Foundation: `31be421afeb5f9261a0c59b9a28f910e10fb2c368fabc5e66137c3828d6bd2b4`.
- Codec/version store: `73d9e2b71e001ee849f19d317982ba5d0b10eee6f813bae62094120067b67878`.

## Review conclusion

No direct authorization bypass was found in this bounded source review. This is
not a security audit or an executable qualification. Apply the foundation patch
once, then codec/version patch; the registration review subset duplicates changes
already in the foundation patch and must not be applied independently afterward.

Definition registration uses common SQL, workspace locking, independent Knowledge
read/manage, exact source read/inspect, retained seal verification and request/audit
replay. `require_revision` is metadata read authority; it does not check provider
availability or source grants and must not be used as an ingestion authorization
shortcut. `require_search_ready` always refuses.

Provider version storage accepts trusted host connection factories and canonical
corpora, with no actor/grant/Run authority. Corpus digest validation establishes
representation integrity, not source issuance. Integration must establish those
authorities before provider access and publish through existing canonical Run
and output services; do not interpret `put` returning a revision as completed
ingestion or authorized search.

## Smallest missing qualification

1. Change the new `foundation` fixture from its hardwired SQLite path to existing
   `database_location`. Its 23 tests currently cannot exercise PostgreSQL merely
   by setting `ACTIONS_INVOICE_TEST_POSTGRES`. Require the owned PG fixture and
   retain separate provider counts, including schema22 migration and old21 refusal.
2. Add a backend-parameterized version-store fixture. The saved test module imports
   and constructs only `DuckDBKnowledgeVersions`; the PostgreSQL class is not
   exercised. Provision explicitly, then test retained read, exact replay, changed
   operation conflict, different revision under the same operation ID, missing
   version, corrupt retained rows and rollback after an inserted document.
3. Use independent PostgreSQL connections for concurrent same-operation and
   conflicting-operation writes. Its explicit table lock is otherwise untested.
   Hold that lock to prove deadline/cancellation refusal and no partial versions,
   documents or operation rows. Include fresh-process reopening.
4. Qualify fresh schema22 creation and migration21-to22 separately. The foundation
   fixture upgrades a historical schema16 and is not a clean-schema test. Retain
   ordinary shared database/migration tests and installed downgrade/restore gates.

No assertion here promotes the saved SQLite/DuckDB receipts to PostgreSQL or
installed proof. Canonical ingestion/publication, authorized search selection,
generated Python consumption and installed lifecycle remain absent from patches.

## Exact canonical guide proposal

After integrating the saved documentation proposals, add this paragraph to
`docs/skills/repository-operations.md` immediately after the provider version-store
paragraph:

> Qualify the common-SQL definition authority and provider version store separately.
> A configured PostgreSQL URL does not exercise a fixture that hardcodes a SQLite
> path, and DuckDB replay tests do not qualify the PostgreSQL store's table lock,
> transaction cancellation or concurrent idempotency. Run the definition matrix
> against both common SQL backends and the version-store matrix against both real
> engines. Definition reads authorize metadata only; corpus validation and provider
> operation receipts supply neither live Knowledge grants nor canonical Run
> publication authority. Require those checks explicitly at the consuming boundary.

Documentation improvement:
- Canonical file proposed: `docs/skills/repository-operations.md`.
- Durable learning: independently qualify metadata authority and provider storage;
  configuration is not exercised-backend evidence; metadata read is not ingestion
  permission.
- Evidence: foundation fixture in decoded patch lines 682 onward; version tests
  import only DuckDB at codec patch line 555; `require_revision` and `require_search_ready`
  at foundation patch lines 558–581; `_Versions` actor-free host API and PG locking.
- Stale or ambiguous guidance removed: avoids interpreting generic replay/rollback
  wording as qualification of an unexecuted PostgreSQL adapter.
- Remaining uncertainty: all new tests above, plus installed/product joins.

Upstream disposition: none. No confirmed upstream defect investigated.
