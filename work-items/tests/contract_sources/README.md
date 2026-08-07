# Contract source ports

These Apache-2.0-attributed snapshots preserve the selected tests from the two
immutable baselines recorded in `work-items/contracts/compatibility-ledger.json`.
They deliberately do not match pytest's `test_*.py` collection pattern. Their
adapted counterparts under `work_items_tests/contract_ports/` are collected and
execute the preserved bodies against `actions-work-items`. Every selected test
node is represented by a strict expected-red entry in `ported-tests.json`, and
the ledger suite enforces exact snapshot/port/manifest equality. Control Room
HTTP, Yorko, and Fizzy orchestration tests are excluded by the release plan.
