# Contract source ports

These Apache-2.0-attributed snapshots preserve the selected tests from the two
immutable baselines recorded in `work-items/contracts/compatibility-ledger.json`.
They deliberately do not match pytest's `test_*.py` collection pattern. Their
adapted counterparts under `work_items_tests/contract_ports/` are collected and
execute the preserved bodies against `actions-work-items`. The inventory has
123 logical nodes and 153 parametrized cases: 40 implemented, 85 exact
call-phase expected-red, and 28 service-conditional Redis/MongoDB cases. Exact
exception and message ownership is declared in `expected-red-failures.json`;
setup and fixture failures are not intercepted.

The checker without arguments verifies mutable checked-in digests for offline
diagnostics. Its authoritative mode takes explicit Robocorp/custom Git roots,
requires the pinned `HEAD` SHAs, and derives selection, test semantics,
fixtures, exclusions, and public surfaces from those trees. The release
workflow uses authoritative mode. Control Room HTTP, Yorko, and Fizzy
orchestration tests are excluded by the release plan; skipped service cases are
not live-backend evidence.
