# Fixed-path offline scripts: independent review

Reviewed prepare-offline-managed.py and validate-public-cache.py without imports or RCC execution. AST parses passed; adjacent final-script-review-fingerprints.json pins reviewed bytes.

The path-matched recipe correctly requires a fresh exact canonical `/tmp/actions327-a44-offline-v1/compiler` with no symlink ancestors. It verifies archive SHA256 a2e388ba921bda7b4c2b04d7ca0d5bb575644cc1cb578528828a64a9417b9598 and size 77512277 bytes, excludes non-library/catalog archive entries, verifies both compressed catalogs' embedded base paths, and checks their relative entry/link structure. runpy.run_path loads the validator without executing its guarded CLI. Strict import and no-build local publish use owned paths and generate target-local trust; target proof requires exact Core a6 payload82 Python/87 total and isolated execution. No new network/security override or producer trust transfer was introduced.

Capacity uses the specifically approved offline profile: 3 GiB initial, 2 GiB compiler allocation cap, 1 GiB floor. Sampling is explicitly identified as sampled rather than a hard unsampled peak proof. UI capacity remains a separate gate.

Required narrow shipping correction: reject sys.flags.optimize explicitly before any assert-dependent validation. Python -O otherwise strips checks and the prctl calls embedded in assertions. Ordinary python -I invocation remains valid; this finding does not invalidate an ongoing non-optimized experiment. Independent validator CLI should likewise reject optimization, or be documented as callable only through the checked orchestrator.

The exact hash pins this reviewed export. Lexical link checks are not a general proof against every possible adversarial symlink-chain archive; do not advertise this validator as a general untrusted archive sandbox. The target experiment must still confirm actual restore paths and Core proof. The prior cross-base failure remains preserved.

Documentation proposal: “Offline compiler scripts reject optimized Python because assert-based checks and setup must remain active. Fixed-path catalog qualification is specific to the measured archive hash and fresh canonical target root; it is not general archive relocation or sandbox validation.”

Documentation-improvement receipt: exact canonical delta proposed to root, shared docs unchanged. Upstream disposition: no new upstream finding; prior RCC relocation draft remains pending classification/deduplication and external authority. No external mutation.
