# A59 installed domain/security evidence

## Scope and gate

This bounded lane adds installed-artifact evidence for two row 22 boundaries in
the original #327/#328 matrix: generated source archive extraction and the
generated worker's environment constructor. The current matrix says row 22
still lacks direct route denials, generated-worker environment qualification,
and transport/auth plus safe-sharing coverage on the final source. Existing
route-auth evidence in `recovery-20261026/auth-boundaries/` and its
`a58-integrity-checkpoint` is not repeated here.

The installed consumer was
`/workspace/327-probes/a59-data-consumer/consumer`. Its readiness receipt binds
source `123e772ee36c44cfd96ea62a6c599bb4f55c8f1b`, tree
`7d6658bc3f2d536519c8698503f8b379c7b3ed56`, and Runtime wheel SHA-256
`cca5383bd331bfc68227bf5c2749f867cc3d9e7cc7daaeb3f13fbe9125d5960a`. The
probe independently checks wheel digest, installed distribution version,
module origin under the selected consumer prefix, and the consumer's source/tree
receipt. No source overlay, dependency install, service, database, or external
network was used.

## Exact proof

The supervised command was:

```text
/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3 /workspace/327-probes/supervise_command.py --receipt /workspace/327-probes/a59-domain-security/final-supervisor.json --log /workspace/327-probes/a59-domain-security/final.log --seconds 120 /workspace/327-probes/a59-data-consumer/consumer/bin/python -I /workspace/327-probes/a59-domain-security/installed_negative_contract.py
```

It exited 0. `final-supervisor.json` records `PASS`, command exit 0, no
remaining owned processes, and no adopted exits. The machine-readable API
assertions are in `installed-negative-contract.json`.

* A fixed ZIP member `../escaped.py` was passed to the installed
  `GeneratedRccExecution._extract_snapshot`. The API raised
  `ValueError("source archive contains an invalid entry")`; its owned
  destination was removed and the would-be escaped file was absent.
* The installed `GeneratedRccExecution._child_environment` was called with a
  synthetic owned work directory and synthetic proxy, account, cloud-secret,
  and model-key environment markers. Its output contained only HOME, PATH,
  ROBOCORP_HOME, ACTIONS_HOME, TMPDIR, LANG, LC_ALL, and RCC_NO_BUILD; none of
  the marker names or values appeared. Its three private worker directories
  were created below the owned work root.

The negative source input is fixed and closed; the proof did not contact any
address. The environment check inspects the constructed environment only. It
did not spawn generated code or RCC and does not prove that files accessible
through ROBOCORP_HOME are secret-isolated from a same-user child, that the
process is a hostile-code sandbox, or that OS credentials, filesystem mounts,
network policy, or live server routing are isolated.

The first supervised attempt failed before the assertion because the harness
had not created the work-root precondition required by `_child_environment`;
the traceback is retained in `supervisor.log` and its receipt in
`supervisor-receipt.json`. After creating the owned parent directory, the
negative contract passed. Pre-run free space was 11,159,523,328 bytes, above
the 10 GiB floor; this lane wrote only small text/JSON evidence files.

## Matrix reconciliation

Row 22 receives a narrow A59 installed-artifact PASS for archive traversal
refusal and ambient-environment filtering. Row 22 remains `partial`: direct
negative requests and side-effect assertions for every sensitive route,
generated-app all-route transport/auth cases, live host configuration, and
safe-sharing acceptance remain open. Rows 17, 18, and 19 are not changed by this
probe. In particular, this does not qualify generated-revision approval/races,
effect retry/reconciliation, scoped-artifact expiry/privacy, replica storage,
or full runtime/host acceptance. Overall campaign status remains NO-GO.

## Canonical documentation improvement proposal

Canonical file: `actions/docs/skills/repository-operations.md`, near the
generated Runtime worker / `GeneratedRccExecution` guidance. Do not edit the
repository from this isolated evidence lane; integration can adopt this exact
delta:

> For installed generated-worker boundary checks, exercise the candidate wheel
> through its fresh consumer and bind the result to wheel hash, source/tree,
> distribution version, and module origin. A fixed parent-traversal ZIP entry
> should raise before an outside file appears and remove the partial owned
> destination. The worker environment constructor emits a closed allowlist and
> must not inherit synthetic proxy/account/secret variables. This constructor
> check does not prove child-process execution, isolation of files reachable
> through ROBOCORP_HOME, hostile-code sandboxing, live server route auth, or
> network policy; qualify those as separate gates.

Evidence: `installed-negative-contract.json`, `final-supervisor.json`, and the
source implementations `action_server/src/actions/server/foundry/rcc_execution.py`
(`_extract_snapshot`, `_child_environment`). Existing portable regressions are
`action_server/tests/contract_tests/test_foundry_rcc_execution.py` (traversal)
and `action_server/tests/contract_tests/test_package_revision_compiler.py`
(`test_prepared_rcc_child_environment_stays_sanitized`). The latter checks the
prepared package-build child environment, not generated-worker execution; the
installed probe exercises the generated worker's separate constructor.

Documentation improvement:
- Canonical file changed or proposed: proposed exact delta above for `docs/skills/repository-operations.md`; no repository file was changed.
- Durable learning captured: installed API proof must bind wheel/source/module identity; the worker environment is a closed constructor allowlist; an owned parent directory is required before its helper creates private subdirectories.
- Evidence: final installed proof, retained supervisor, source APIs, traversal test, and adjacent package-build environment test.
- Stale or ambiguous guidance removed: none; existing evidence was retained and not broadened.
- Remaining uncertainty: no generated child/RCC launch, no assertion about data reachable in ROBOCORP_HOME, and no exhaustive transport/auth or host-level isolation proof.

Upstream disposition: none. No upstream defect was investigated or established.
