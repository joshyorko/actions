# Contract source ports

These Apache-2.0-attributed snapshots preserve the selected tests from the two
immutable baselines recorded in `work-items/contracts/compatibility-ledger.json`.
They deliberately do not match pytest's `test_*.py` collection pattern while
production gaps remain. Every selected test node is represented by a strict
expected-red entry in `ported-tests.json`; implementation tasks replace those
entries with executable adapted tests as each contract closes. Control Room HTTP,
Yorko, and Fizzy orchestration tests are excluded by the release plan.

