# Contract source ports

These Apache-2.0-attributed snapshots preserve the selected tests from the two
immutable baselines recorded in `work-items/contracts/compatibility-ledger.json`.
They deliberately do not match pytest's `test_*.py` collection pattern. Their
adapted counterparts under `work_items_tests/contract_ports/` are collected and
execute the preserved bodies against `actions-work-items`. Every selected node
is classified as implemented or strict expected-red in `ported-tests.json`;
implemented nodes run normally, while each pending node is xfail-owned
independently and constrained to its expected exception class.
`scripts/check_contract_port_provenance.py` checks complete function and file
hashes plus selection, exclusions, and public surfaces. Control Room HTTP,
Yorko, and Fizzy orchestration tests are excluded by the release plan.
