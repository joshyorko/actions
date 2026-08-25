# RCC runtime adapter first vertical

- [x] Add strict typed RCC descriptor and JSON publish/acquire identity parser
  in `action_server/src/actions/server/_rcc_runtime_adapter.py`.
- [x] Add RED tests for malformed artifact identities, descriptor authority,
  RCC import commands, worker wrapping, and failed preparation phases.
- [x] Implement the minimal adapter and turn the focused contract suite GREEN.
- [x] Route managed spec-v2 package import/discovery through the exact artifact.
- [x] Route the existing `ProcessHandle` TCP worker through
  `env exec --inherit-streams --receipt-file`, and reap the RCC wrapper after
  cancellation/kill.
- [x] Update RCC source/build lookup to v18.19.2 and verify the release binary.
- [x] Run the gated proof with
  `ACTIONS_REAL_RCC_ARTIFACT_TEST=1 poetry run pytest -q
  tests/action_server_tests/test_rcc_runtime_adapter.py -m real_rcc` and record
  the exact artifact digest, Action result, and receipt.
- [ ] Follow-up: prove source-only reload and generation switch/drain.
- [ ] Follow-up: prove provider-dead warm reuse and `rcc cache serve` A→B.
- [ ] Follow-up: reject corrupt/incompatible artifacts and prove source, wheel,
  and frozen acceptance.
