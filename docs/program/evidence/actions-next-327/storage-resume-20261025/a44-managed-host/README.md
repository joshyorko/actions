For the prepared native desktop consumer, use **LOW-CAPACITY.md** first. Version 1 adds the reviewed measured-resource compiler and UI-only flow; existing version 0 host adapter bytes remain unchanged. The strict/full-flow instructions below are retained separately.

# a44 managed-CUA overlay — reviewed preparation, not executed

Use only with the original immutable a44 bundle SHA256 37ab0cf8bf66132c0112e5b65c7528a1092f4665ac7f7d32a022ec2ee77d18b0, source d0c87a38a937cc339e8e661ac453c7a62ed41fa6. Product wheels remain unchanged. Preserve the original ZIP and its defective browser/qualify.py (wrong a42 source assertion). Copy this overlay's browser files into a separate extracted browser working directory alongside the original bundle's package.yaml, generated_actions.py, test_generated.py, canvas-spec.json, host-source-identity.json and host package manifests. The corrected strict qualifier SHA256  is90d2ae610bd521a70785ef3bfb9238aa0719b12a8887c68d6a2d6aa4c5ae0f86; it remains a Playwright recipe and must not be used as the CUA adapter.

Owner approval for fresh disposable key/synthetic permissions in this isolated cloud test has been supplied by the parent. No Dakota/Executor access, publication, live credentials, tunnel, proxy or browser security changes. Importing either qualifier has side effects; use static inspection until ready for its authorized execution.

## Exact source and tools

Official host: https://codeload.github.com/modelcontextprotocol/ext-apps/tar.gz/82221c0c8ce7661efa6771c9d461511b1650495f ; 15,884,360 bytes; SHA256 45bf48731a0fb23de541db12e6c3c7ed35fa52e55c8adbecea0b7cec95187733. Extract examples/basic-host and verify all 16 original source members against browser/host-source-identity.json before adaptation. Retain that original copy.

Node Linux x64: https://nodejs.org/dist/v20.19.3/node-v20.19.3-linux-x64.tar.xz ; SHA256 c210e1a547efad55e93af1e04fb80d2f7131b13872f2de4e9ebdfecb8e06caad, obtained from official https://nodejs.org/dist/v20.19.3/SHASUMS256.txt (retained here). Extract to a task-local directory, put its bin on PATH and verify node --version is v20.19.3.

Copy original browser/host-package.json and host-package-lock.json into a fresh host copy as package.json/package-lock.json. Apply the verified adapter using `python apply-host-adapter.py /absolute/target/basic-host`, then run `npm ci` and `npm run build` from that host. Keep both dist/index.html and dist/sandbox.html. This is official reference host plus a disclosed test transport adapter, not unchanged upstream source. Renderer/bridge/sandbox bytes are preserved; only password connection UI, transport, logging and loopback listeners differ. See patch and exact hashes. Independent static review and TypeScript/Vite build passed; no host launch or UI test occurred in producer.

## Managed flow prerequisites and command

The full generated execution flow requires a target-local RCC 18.19.3 compiler preparation from the exact Core a6 wheel and the bundled package.yaml, its measured Core payload proof and actual prepared receipt. A wheel-only consumer does not supply that execution environment. Never copy producer trust or substitute historical receipt paths/digests.

Fill original browser/candidate.example.json with actual target paths/proofs. Keep exact source and wheel hashes; use the adapted built host. `playwright_package` is ignored by the managed qualifier. The parent's explicit execution authorization allows execution_authorized=true. Before invocation, both 127.0.0.1 ports8080/8081 must be free. The full qualifier retains 5 GiB free reserve,256 MiB fixture cap and12 MiB log cap. These guards are not lowered. Reported 4.9 GiB maximum free is insufficient; use an adequate existing writable volume/environment. Public host preparation sampled 201,228,288 allocated bytes; consumer 193,896,448 bytes; target compiler lane cap 2 GiB, full browser peak unmeasured. Conservative fresh plan 8.75 GiB initial free preserves 5 GiB reserve; strict Playwright install would require additional space. These are planning caps, not measured full-run peaks.

```sh
ACTIONS_V2_CANDIDATE=/absolute/target/candidate.json /absolute/target/consumer/bin/python -I -B /absolute/target/browser/managed-qualify.py
```

Managed qualifier SHA256 daf2bf86108b71d27068d282d58224f7b1ef726191e5b3c65a07094edae260ed. It verifies exact installed and adapted host inputs, starts Runtime on 127.0.0.1, creates the approved disposable key and synthetic grants through the existing supported owner CLI, authors/activates the generated report, runs independent protocol controls, and starts the adapted host on 127.0.0.1:8080/8081. It does not launch or configure a browser. It prints token-free READY metadata and writes evidence/managed-ready.json, including application ID, private key path and operator completion path. It waits at most 30 minutes. Treat failures as failures; do not re-run an uncertain existing fixture.

## Operator UI steps and evidence

1. Open ready.host_url in the existing approved managed browser. Paste the disposable key from ready.key_file into the password field and Connect. The field clears. Do not place the key in URL/tool JSON/logs/screenshots. Browser credentials remain only in memory.
2. Select canvas_get and call with the JSON from ready.arguments_file. Verify the Generated report form mounts. Save a PNG of the app region as evidence/managed-mounted.png.
3. Enter Report text `alpha beta`, Generate report. Verify Word counts 2, Processing log `Processed alpha beta`, Report details and visible chart. Save managed-first-result.png.
4. Submit `gamma delta epsilon`. Verify prior result clears and new count 3/details/log appear. Save managed-resubmitted.png. Select Inspect report artifact; verify authorized JSON details.name matches. Save managed-authorized-artifact.png.
5. Through supported window sizing, verify a narrow layout and save managed-narrow.png. If unavailable, report that gate incomplete; do not substitute another full-size screenshot.
6. Submit `fail`. Verify Execution report failed and prior chart/data clear. Save managed-failed-cleared.png. Capture app regions only; inspect screenshots for tokens before sharing.
7. After genuine UI observations, create ready.completion_file with the completion-example.json shape. PNG paths are relative to the evidence directory. The script validates files and 3new backend Runs, then performs authorized artifact/terminal checks, restart/stale-session/rollback/revoked-read checks. It stops owned Runtime/host and disposes of its key even on failure. Cleanup 8mocked failure-path tests passed.

Success is BACKEND_PASS_UI_REVIEW_PENDING, with operator evidence retained for parent visual review. It does NOT attest Chromium sandbox configuration or actual ChatGPT. Parent supplies final visual acceptance; no automatic strict-browser PASS is produced. A manual basic-host-only launch can be separately scoped by the parent, but is not this full generated execution gate or an exemption from these guards.

Canonical original source recipe: joshyorko/actions commit 6234f13ecf449b8df68092a10792ed2760393867, docs/program/evidence/actions-next-327/storage-resume-20261025/browser-handoff/README.md. Its a42 identity is historical.

Upstream disposition: none. Local reviewed test adaptation, no external mutation.

## Target-local compiler phase (included in version 1)

Run before the managed qualifier, using the installed a44 consumer and a new compiler root:

```sh
/absolute/target/a44/consumer/bin/python -I /absolute/overlay/compiler/prepare-compiler.py --candidate-base /absolute/target/a44 --compiler-root /absolute/target/fresh-compiler-a6
```

The scripts use the already bundled, hash-verified RCC 18.19.3, publish only into that new root, verify all 87 Core payload files and logical-context isolation through the newly materialized interpreter, and write target-config-fragment.json with the exact compiler_* candidate fields. Retain newly generated local trust there; do not import producer trust. The 2 GiB lane cap and 5 GiB free reserve remain enforced. See compiler/README.md. The portable phase was statically reviewed, not executed in this handoff. UPSTREAM-LICENSE retains attribution for the adapted official host.

Repository evidence stores the exact adapter patch as `adapter.patch.base64` to preserve unified-diff blank context lines without violating staged whitespace checks. Decode with `base64 -d adapter.patch.base64 > adapter.patch` before checking its manifest hash. The Library overlay contains the original patch unchanged.
