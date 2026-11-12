# Runtime v2 admission integration

Base source 7e0fa8d09be0f152d2aa82bea24fe0bb3209e2dd plus the source changes in this checkpoint. This is source/component qualification, not an installed a40 wheel or rendered projection claim.

Initial collection failed: the prepared Runtime environment retained Core a3 and could not import CanvasSpecV2. The supported RCC/Poetry `action_server install` updated the declared path dependency to Core a5. The original collection error and refresh log are retained.

The corrected five-module gate passed 87 tests, zero failures/errors/skips, using SQLite and a digest-pinned, bounded, owned loopback PostgreSQL fixture. Selected node IDs, commands, source hashes, per-module XML/logs and cleanup status are retained. Cleanup exited zero. Do not sum helper or historical runs as additional unique cases.

Explicit v2 is accepted through Core validation, typed deployment, SQL staging/read/rollback and the MCP tool schema. Default creation and retained v1 canonical bytes/digest behavior remain v1. Generated data projection, rendering and clean installed acceptance remain separate gates.

Upstream disposition: none.

Focused mypy passed four production files using namespace-aware `--explicit-package-bases`. The initial invocation without that flag failed duplicate module naming; both logs are retained.
