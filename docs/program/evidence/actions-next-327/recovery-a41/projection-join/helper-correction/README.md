# Complete terminal projection preimage correction

Apply terminal-preimage-correction.patch AFTER original backend.patch413ca4d4. Root production was not edited. The helper now pins complete Run (including result, inputs and action fields), RunPin, RunAttempt, zero-or-one RunExecutionIntent (absence is pinned too), and every attached RunOutput descriptor. It compares exact scalar SQL preimages after the authorized bounded read. No new grants or scheduler authority.

70 tests passed,35 each SQLite/ownedPostgreSQL. Original48 passing cases retained. Added11 provider-close barrier mutations perbackend cover sourceArtifactDigest/packageRevision/runtimePlanDigest/launch/execution/claim/lineage, inputs, Attemptheartbeat, executionintent and non-result output descriptor. Actual originalhelper RED:20failed,2passed,48deselected;20 failures are DID NOT RAISE. Fixed70passed.

Earlier newtests6/tests7 incorrectly trapped provider.open entering inside a transaction: existing RunOutputService.resolve intentionally acquires provider under its grant lock, then yields the stream outside. Those failures remain retained. Corrected barrier asserts post-read mutation outside SQL. Helper current() rechecks are SQL-only; do not claim existing provider acquisition itself is outside every transaction. This corrects the earlier proposed canonical guide wording. No shared resolver change.

Original tests3 four fixture failures and tests5 original48pass logs/XML now included. Prior failures remain failures. Final configured Ruff/format/isort/mypy passed.

Trusted route still must validate the initial full canonical receipt/selection and supply live SQL-only current binding/grant checks. The helper pins that complete observed state across its read; it does not newly admit or interpret arbitrary terminal receipts.

Upstream disposition:none.
