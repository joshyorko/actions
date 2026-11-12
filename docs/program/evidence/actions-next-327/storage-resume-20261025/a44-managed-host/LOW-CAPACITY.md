# Ready-to-run bounded managed-browser path

This is the separately reviewed `a44-managed-ui-only-v1` profile requested for the native desktop volume. It does not change or pass the original strict Playwright recipe. The owner has approved disposable local test credentials and synthetic permissions. No extra auth approval is required by this handoff.

If version 0's host adapter is already built, keep it: its four source hashes and protocol behavior are unchanged. Do not reapply the stock-only patch. Copy this version's new browser files into the same separate working browser directory beside the original bundle fixtures. All scripts require the original exact a44 candidate, source d0c87a38a937cc339e8e661ac453c7a62ed41fa6, Core a6 and original wheel hashes.

## Budget basis and admission

Measured on the producer with these actual candidate bytes:

- Fresh RCC publication plus successful all-87-file Core proof: sampled peak 1,935,241,216 bytes.
- Actual installed a44 generated execution, two successes and one deliberate failure, authorized artifacts, restart/rollback/revoked reads: sampled combined compiler/fixture peak 2,953,277,440 bytes; PASS; all six Runtime stops graceful.
- Original official-host preparation sampled 201,228,288 bytes; parent independently reports its already prepared consumer/host/tool footprint at 548 MiB.

The new phase starts AFTER host and consumer preparation. It requires at least 4,563,402,752 free bytes (4.25 GiB) on the compiler filesystem. The compiler retains a 2 GiB allocation cap and 1 GiB free reserve. The managed UI phase requires compiler and fixture on the same filesystem, caps their combined allocation at 3 GiB, retains 1 GiB free, a 256 MiB fixture cap and 12 MiB log cap. The measured combined peak is 267,948,032 bytes below the 3 GiB cap; screenshot files have an additional per-file 5 MiB limit within the fixture cap. Runtime/UI performs exactly three executions rather than repeating three independent client executions first. That independent gate remains separate existing a44 evidence.

The reported rounded 4.678 GB free is compatible only if the actual-byte preflight passes. Guards are mandatory. No unrelated cleanup, filesystem combination assumption or security changes. Measurements are sampled, not a quota or guaranteed worst-case peak. Budget checks run during compiler output polling and on a nominal 0.25-second async UI watchdog; synchronous bounded startup/shutdown phases can delay polling. A violation cancels through bounded cleanup, marks FAIL and preserves sanitized receipts. Compiler publish/proof deadlines are 600/180 seconds; UI operator wait is 30 minutes. SIGTERM cancels the managed coroutine through cleanup. Parent visual review remains required.

## 1. Prepare target-local RCC and Core proof

Use the already installed a44 consumer. Replace only target-local paths; the compiler root MUST NOT exist:

```sh
/target/a44/consumer/bin/python -I /overlay/compiler/prepare-compiler-managed.py --candidate-base /target/a44 --compiler-root /target/fresh-compiler-a6
```

Script SHA256: 6b97c262bc6e807b72959f732586a2aa337d504108900921813310ab60b3e3af.

This uses bundled installed RCC 18.19.3 (SHA256 7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428), copies only the exact candidate Core wheel into that new root, runs `rcc env publish --environment <new package.yaml> --json --provider local`, derives its receipt from actual output, and runs `rcc env exec --no-build` through the installed adapter and NEW local trust. The proof verifies 87 Core payload files, version, isolated interpreter, retired dependencies absent and scan-context isolation. Standard system paths include /usr/sbin and /sbin for RCC's ldconfig discovery; no loader/security check is bypassed. The first producer recipe omitted those paths and failed its environment check; that failed attempt is preserved separately. The corrected full preparation passed.

On success merge the actual fields in `/target/fresh-compiler-a6/target-config-fragment.json` into the target candidate.json. It supplies capacity_profile, source/runtime/Core identities, prepared_receipt, compiler_artifact_digest, compiler_core_wheel_sha256, compiler_core_bytes_verified, compiler_core_receipt and compiler_core_receipt_sha256. Keep the existing actual installed_base, fresh fixture_root, built official_host and node_executable paths. Ignore playwright_package in this variant. Producer measurement receipts are evidence only and MUST NOT be used as target configuration or trust.

## 2. Run managed UI preparation and observation

Both 127.0.0.1:8080 and :8081 must be free. The flow checks these before launch. Use the browser working directory containing original fixtures, the four-file adapter identity and the new script:

```sh
ACTIONS_V2_CANDIDATE=/target/candidate.json /target/a44/consumer/bin/python -I -B /target/browser/managed-qualify-low-capacity.py
```

Script SHA256: e393bdd7ebf65248522a114052d2677e1b975b7444f8bfea35bcfb5d431f6253.

It creates the approved disposable key/grants, authors and activates the exact generated report, starts loopback Runtime and the adapted reference host, and writes/prints token-free `managed-ready.json`. Read the key only from its private file and paste it into the host password input. Follow README.md's six screenshot steps and completion-example.json; the UI must actually execute alpha beta, gamma delta epsilon, then fail. Capture app regions only and inspect screenshots for tokens. No scripted browser launch, sandbox changes, proxy or tunnel occurs.

The three UI Runs are validated against real backend receipts/artifacts. Restart, stale-session, rollback and revoked-read checks remain. Cleanup independently stops owned processes, disposes of the key and writes sanitized receipts. Success is `BACKEND_PASS_UI_REVIEW_PENDING`, never strict sandbox or actual ChatGPT acceptance. The parent reviews actual screenshots before accepting the managed UI gate.

Independent static review and mocked cleanup/watchdog checks passed. This lower-capacity variant itself has not executed on the target; parent execution is the next gate. Original strict scripts and original failed bundle recipe are preserved.

Upstream disposition: none. Resource plan and local test adaptation only.
