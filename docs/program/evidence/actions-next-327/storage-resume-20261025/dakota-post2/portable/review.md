# Independent portable recipe review

HOLD: standalone preparation script has no SIGTERM handler. Default SIGTERM bypasses Python finally and can orphan its separately sessioned RCC publish/proof child. The documented direct launch has no outer supervisor. Route SIGTERM/SIGINT into bounded cleanup, ignore repeated termination during cleanup, restore original handlers afterward, or require an existing exact supervisor. Do not claim cleanup on exit until corrected.

Verified source-only identities: manifest2958bd5f331ca12c94eacda8c6210c24216e5e48e577360d52b9bd3f8ddd3304; script ae69ffad388a5eea5fb5261df8bbc9403aa44f94693ad40682d3bb9bf78b9a87; verifier a69b5a9e9e45b87803c89068c17210891040ee92171b6db0b604e06e5adf554d; package f7b4173c11a7eef06cf2ecc526d15a7f069efdd4d465f65cb0fb6258d258b4a8.

No other blocking provenance issue found: exact post2/Core6/WI2/RCC pins, Linux x86_64 CPython3.12 isolated preflight, fresh canonical parent/root, unchanged HOME, full installed payload comparison, local public publish and no-build Core proof, target-local trust, no catalog import or relocation. Public transitives and unproven incidental HOME writes are accurately disclosed. Reviewer did not execute/import recipe or start services/builds.

Canonical proposal for docs/skills/repository-operations.md: “A standalone compiler preparation controller must route termination signals through owned-child cleanup; try/finally alone does not handle default SIGTERM. Ignore repeated termination while cleanup is bounded, restore handlers, and retain failures rather than declaring target readiness.” Durable learning: signal-safe cleanup is distinct from phase timeouts and normal-return finally. Evidence: reviewed direct command and absence of signal handlers. Remaining uncertainty: corrected controller and actual target preparation. Upstream disposition: none; local recipe issue.

Signal re-review: manifest4d6e6b3238a6b9003813030b6d7a2378f868bdb0ac2bbcfc8324c05fdf724259/script70bcb0df8ac2b19067245163c4e368987bcea8c44d29e10440ff6d512a8d46b1 resolves SIGTERM cleanup routing and repeated-signal interruption. Remaining narrow setup gap: DefaultSelector allocation occurs after successful Popen but before try/finally; initialization failure can leave child alive. Move preparation before spawn or guard immediately with nullable selector. No actual compiler executed.

## Final disposition: CLEAR for source handoff

Final manifest SHA256 d85981d41bae25c1a9d46ec3a9b9b73ae9eec6b4188a8b79c61a629ea8fd8e78; script SHA2562c9c537d3e62846e255a5c9ce0c89cfe9890664004311704aa1bfc1d9f0dfaa1. Verified selector/output/streams allocation now precedes Popen, spawn failure closes selector, and successful spawn enters protected try immediately. Both reported cleanup blockers are resolved in these exact bytes. This supersedes earlier HOLD dispositions for source handoff only; original findings remain retained.

No actual compiler/build/services executed by reviewer. Target preparation, dependency resolution, measured capacity and Core proof remain execution gates. Canonical signal-safe controller guidance proposed above remains valid. Upstream disposition: none.
