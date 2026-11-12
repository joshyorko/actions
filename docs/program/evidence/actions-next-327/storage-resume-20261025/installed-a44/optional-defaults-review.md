# Explicit service selection and signing metadata patch

Deliverable optional-defaults.patch passes git apply --check against current checkout. source-hashes.json records exact base/candidate file bytes. Root must apply after its Runtime suite and retest; NOT part of archived a44. No tracked checkout source changed, commits or pushes.

Files: actions/src/actions/agent/_client.py; new actions/tests/actions_tests/test_agent_client_boundary.py; action_server/src/actions/server/_build_common/signing.py; new action_server/tests/build_system_tests/test_owned_signing_metadata.py.

Agent selection uses explicit ACTIONS_AGENTS_SERVICE_URL first, legacy SEMA4AI_AGENTS_SERVICE_URL only when owned variable absent. Empty or unreachable owned choice fails without legacy fallback. No automatic PID-file lookup; private legacy routines retained without an active constructor path. No new PID configuration feature. Missing configuration fails before probe/file lookup and error names supported inputs. Existing payloads/URL suffixes unchanged.

Windows signing --description-url becomes https://github.com/joshyorko/actions. Credentials, timestamp service and digest flags unchanged. Test intercepts command runner; no tool installation or live signing.

Validation via prepared RCC package gateway: original agent4failed/1passed; isolated candidate5passed. Original signing1failed; isolated candidate1passed. Candidate modules loaded under canonical import names from scratch, retaining actual package dependencies. Configured Ruff format/lint pass. Entire patch applies cleanly with --check. Parent must run integrated tests after apply; isolated passes are not installed-candidate acceptance.

Sequencing disclosure: two new tests were initially written in checkout immediately before parent directed isolation. On parent request they were moved to this directory with bytes preserved; no production source was edited. Concurrent Runtime suite MAY have collected the new signing test before removal; root was notified immediately. Its expected failure would only be the old description URL assertion, with command runner mocked. Checkout status for all four target paths is clean before delivery.

Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md.
- Exact addition after integration: “Agent API helpers require explicit ACTIONS_AGENTS_SERVICE_URL or its legacy SEMA4AI_AGENTS_SERVICE_URL alias. Presence of the owned variable establishes precedence even when empty/unreachable; no automatic Studio PID discovery or fallback follows a failed explicit choice. Windows signing description metadata identifies the owned Actions repository; signing credentials and timestamp policy remain explicit existing configuration.”
- Evidence: no-side-effect/preference/failure boundary cases and mocked signing command test, recorded red/green logs.
- Stale ambiguity removed: old Studio PID paths are compatibility implementation remnants, not implicit endpoint discovery.
- Remaining uncertainty: root integration/full suite and installed candidate gate, potential concurrent test collection noted above; Work Items pinned provenance edge unchanged.

Upstream disposition: none; draft-only, no external mutation or report.
