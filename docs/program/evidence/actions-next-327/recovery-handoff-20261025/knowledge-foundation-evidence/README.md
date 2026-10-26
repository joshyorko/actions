# Knowledge foundation review receipt

Scratch-only implementation. Root source was not edited. Full patch applies cleanly
with `git -C /workspace/actions apply --check knowledge-foundation.patch` against
observed root HEAD 595cf5119dbf2f858bcc28109b34de31bdc50f86. Exact existing-file bases
are in base-hashes.json; all deliverable hashes are in SHA256.json.

Apply knowledge-foundation.patch once. knowledge-registration-review.patch is a
review-only subset of its three existing-file changes, NOT an additional patch.
documentation.patch is the exact canonical guide proposal for integration.

## Interface and integration

- KnowledgeRevisionSpec.reference deterministically identifies definition intent.
- KnowledgeRevisionAuthority(db, SqlProviderRegistry) requires the same common DB.
- register_definition(actor, specification, source_provider=exact_ref,
  idempotency_key=key) returns KnowledgeRevisionRef after common transaction,
  workspace lock, live scoped read/manage, source read/inspect, retained evidence,
  immutable metadata and request/audit checks.
- require_revision(actor, reference, permission) reads definition metadata only.
- require_search_ready(actor, reference) always refuses after read authorization.
- SqlFoundryAuthorization.require_knowledge adds distinct knowledge-collection and
  knowledge-revision subjects. Existing grant storage/parser reused, no bootstrap
  owner operations/fingerprint or automatic permissions changed.
- _models.py registers one new model; migration map reserves 22. Historical DDL
  freezes its own class/rules. No publication table, scheduler or second database.

## Verification

Existing prepared Runtime interpreter, explicit scratch overlay, no installation,
RCC, containers, engine execution, trace plugin or root source mutation:

```
cd /workspace/actions-recovery-327/knowledge-foundation-draft/action_server
PYTHONPATH=src:/workspace/actions/action_server/tests /workspace/actions/action_server/.venv/bin/python -m pytest -q -p no:robocorp_log_pytest tests/action_server_tests/test_knowledge_foundation.py --junitxml=/workspace/actions-recovery-327/knowledge-foundation-evidence/final.xml
```

Final 23 passed,0 skipped,0.88s. first 16 passed; expanded second 19 passed/2 failed
because test expected ValueError rather than actual AccessDenied and reused a DB
with incompatible historical model registration. Both test harness issues were
corrected (fresh old-reader connection); third 21 passed and fourth 23 passed.
Original receipts retained. New tests initially collected red missing module.

MYPYPATH=src with mypy --explicit-package-bases --follow-imports=silent
--ignore-missing-imports on five source modules: clean. Ruff check on six changed
source/test modules clean; isort and Ruff formatter applied. These focused static
checks are not a substitute for parent package gates. PostgreSQL and full Runtime
suite not run in this bounded lane. Frozen prior migration implementation fixture
executes its real status check and reports TOO_NEW on migration 22. This proves
status refusal, not an installed downgrade or restore qualification.

## Remaining gates

No codecs, normalized corpus, immutable real provider snapshots, durable ingestion
Run/Task receipt, public operator/authoring wiring, generated search consumption,
paging/export, two-provider installed lifecycle or split-provider service proof.
The v1 sealed source registry admits metadata only and supports at most 16 objects;
definition max_source_files 128 does not widen source admission. No claim that Data
adapters implement Knowledge. Parent owns integration and PostgreSQL qualification.

Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md (documentation.patch).
- Durable learning: distinguish persisted definition intent, exact scoped authority,
  retained raw source admission, and forward-only schema from runnable Knowledge.
- Evidence: 23 SQLite cases; real frozen version 21 status reader; five-module mypy.
- Stale guidance removed: claim that no retained definition/independent authority
  foundation exists; actual provider/ingestion/product gaps remain explicit.
- Remaining uncertainty: PostgreSQL and all ingestion/search/product gates above.

Upstream disposition: none. This is repository-owned foundation work; no new
upstream defect investigation or external mutation.
