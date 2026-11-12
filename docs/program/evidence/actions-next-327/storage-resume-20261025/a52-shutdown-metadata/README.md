# Vanished child metadata during shutdown

The installed a51 cancellation observer trial stopped before calling cancellation. During its cleanup, a child disappeared between process enumeration and `child.name()`, aborting the remaining Runtime shutdown loop. The original failed receipt remains in ../a51-installed-task.

Runtime a52 skips that vanished captured child without reconstructing its numeric PID, logs unexpected metadata errors, continues other children and preserves watcher failures. The legacy signal helper is unchanged; this is not stronger fencing or proof of descendant termination. The earlier failure-lifecycle patch remains on HOLD.

Four deterministic actual-lifespan regressions pass after the initial two failures. Configured Runtime lint/typecheck passes, including 650 source files. Installed a52 shutdown and a fresh complete Runtime suite are still required. No a52 wheel has been built.

The independent clean a51/Core a8 consumer also passes all seven owned truststore tests, including the five previously skipped installed/Linux TLS cases. Windows/macOS remain unverified. Core bytes are unchanged; this does not replace the failed a49 full Runtime receipt.

Canonical guidance in docs/skills/provenance-observability.md records the metadata race, limits of best-effort cleanup, and exact-identity RCC child observation. Upstream disposition: none.
