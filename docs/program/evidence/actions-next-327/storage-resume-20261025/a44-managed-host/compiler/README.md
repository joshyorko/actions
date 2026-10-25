# Target-local a44/Core a6 compiler preparation

READY TO RUN; NOT EXECUTED by this lane. Copy this directory alongside the obtainable a44 candidate; no producer homes, trust keys, prepared receipts or RCC artifacts transfer. Only the exact candidate Core wheel is copied into the new compiler root. The script requires the existing installed candidate consumer; it does not install or download RCC.

Candidate base layout: source-sha.txt, consumer/bin/python and wheels/**/actions_core-1.1.0a6-py3-none-any.whl. source-sha.txt must contain d0c87a38a937cc339e8e661ac453c7a62ed41fa6. Both Python scripts must be together. Compiler root must not exist; its parent must already exist.

Exact target command (replace only the three target-local paths):

    /target/a44/consumer/bin/python -I /target/compiler-tools/prepare-compiler.py --candidate-base /target/a44 --compiler-root /target/fresh-compiler-a6

Run directly with the target consumer interpreter. Do not invoke RCC as a wrapper around this command: the script itself invokes the installed bundled RCC and owns its process lifecycle.

Verified constants:
- Core wheel SHA256:718ea63637f096d26c4de5f82ca736eec1358b197d0a63883c063ad205e0860e.
- Bundled installed actions.server/bin/rcc-18.19.3 SHA256:7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428; executable permission required, no chmod. Version output must equal v18.19.3.
- Embedded package.yaml SHA256:f7b4173c11a7eef06cf2ecc526d15a7f069efdd4d465f65cb0fb6258d258b4a8. Generated-v2-report environment pins actions-core1.1.0a6.

Limits:2GiB allocated lane bytes,5GiB consumer free-disk floor (distinct from producer reserve),12MiB combined process stdout/stderr,600s publish and180s proof,30s version check. Cleanup has bounded waits after kernel group stop. Linux subreaper scope is saved/restored; children run in fresh owned sessions and descendants are killed/reaped on success or failure. Fresh HOME/ROBOCORP_HOME/ACTIONS_HOME/TMPDIR and local PIP_FIND_LINKS are used. Only existing proxy/TLS-cert environment settings are retained; authenticated proxy URLs are rejected and credential variables are not copied. Logs redact URL userinfo and authorization headers; command results expose only digests and target paths.

The script runs RCC env publish --provider local into the fresh root, parses exactly one observed specification/artifact result, writes prepared.json through installed PreparedRccEnvironment and verifies its public loader roundtrip. Trust stays in the newly generated root. It then builds an RCC env exec command through installed build_exec_command with --no-build and the new local trust carrier. verify-core.py verifies all 87 installed Core payload members (including 82 Python files and the logging viewer payload), Core version, isolated RCC interpreter, four retired distributions absent, and logical scan context copy/isolation behavior. The execution receipt is checked through installed read_receipt.

On success target-config-fragment.json contains actual target paths, observed specification/artifact digests, exact wheel/RCC/package identities, prepared receipt hash and core proof hash. Publish/proof logs stay in the fresh root; no server, keys/grants, browser or outside consumer configuration is touched. Failure leaves bounded target evidence for inspection; retry with a different fresh root rather than overwriting a prior attempt.

Syntax/AST review only performed here. Proven source workflows were compiler-a6 publish/prepare/core-proof scripts; no new RCC materialization was performed. Target network/dependency availability remains to be demonstrated there. This is a preparation recipe, not an installed/native host acceptance pass.

Canonical documentation proposal (root applies to docs/skills/repository-operations.md):

“Portable compiler handoffs transfer exact candidate wheels and a parameterized target-side preparation recipe, never a producer RCC home, trust carrier or prepared receipt. Verify installed RCC/wheel bytes on the target, publish locally into a fresh owned home with explicit disk/time/log bounds, and derive PreparedRccEnvironment only from observed local publish output. Re-execute a Core payload and isolation proof with --no-build against the new trust carrier before recording target configuration. Keep source-side syntax review distinct from target-side materialization and acceptance.”

Upstream disposition:none. Owned handoff tooling; no confirmed upstream defect, no external mutation or reporting target.

Root review added exact installed Runtime/Core version and Runtime wheel checks. The output fragment now includes the exact compiler_* fields consumed by candidate.json; merge those measured fields into the target candidate configuration. This preparation has still not executed on the target.
