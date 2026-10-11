# Release observation (read-only)

Observed window: 2026-10-11T01:01:25.137076Z to 2026-10-11T01:01:29.842481Z.

Previous readiness receipt: `/workspace/work/actions-mk3-evidence/wave8-release-readiness/readiness.json` (SHA-256 `c125821e49573f888a780ae4942dab69d76fb08fb9ee3f0615ebf6668bd05f19`); its artifact/API digests remain historical and were not redownloaded or retested.

- **pypi_core** `https://pypi.org/pypi/actions-core/json` — 200, observed 2026-10-11T01:01:25.137076Z; response SHA-256 `b63e325cb7e0fb2d0ead0db3d08afff65417dac6445b467c6133e61f35cf9ea6`.
- **pypi_helper** `https://pypi.org/pypi/actions-http-helper/json` — 200, observed 2026-10-11T01:01:25.692892Z; response SHA-256 `9c955a4f4fe3641546da4dd02262dbcd39d505b2508b4a2854f34842bdbea57c`.
- **pypi_runtime** `https://pypi.org/pypi/actions-runtime/json` — 200, observed 2026-10-11T01:01:26.258037Z; response SHA-256 `7d830d6cf750d5cf2b5820cb43f72583047b2b72eab1f2d33ffb4b276c7438ef`.
- **actions_runtime_1_0_3_release** `https://api.github.com/repos/joshyorko/actions/releases/tags/actions-runtime-1.0.3` — 404, observed 2026-10-11T01:01:26.932366Z; response SHA-256 `UNKNOWN`.
- **actions_runtime_1_0_3_tag** `https://api.github.com/repos/joshyorko/actions/git/ref/tags/actions-runtime-1.0.3` — 404, observed 2026-10-11T01:01:27.629610Z; response SHA-256 `UNKNOWN`.
- **actions_latest_release** `https://api.github.com/repos/joshyorko/actions/releases/latest` — 200, observed 2026-10-11T01:01:28.342344Z; response SHA-256 `c8ca6c3f2af614518a269dc1a3feca67b9d5039aa6d4d7944f282ca34e5ce5fb`.
- **homebrew_repo** `https://api.github.com/repos/joshyorko/homebrew-tools` — 200, observed 2026-10-11T01:01:29.134410Z; response SHA-256 `193b8ae13a0e226a6f884c4be8f4712833627621a8779392178b9459d69bbbb3`.
- **homebrew_cask** `https://raw.githubusercontent.com/joshyorko/homebrew-tools/main/Casks/action-server.rb` — 200, observed 2026-10-11T01:01:29.842481Z; response SHA-256 `fbd00170ccbe93d476a168ffc35eba99ced8f0192918b114f308083768c3169f`.

The JSON records exact published file hashes for Core 1.0.3 and Helper 1.0.3 and latest Runtime metadata. Runtime PyPI, native release/tag, and owning Cask are independent observations. Homebrew install/upgrade and ChatGPT validation are NOT RUN.

Documentation proposal: add a concise release checkpoint instruction to inspect current PyPI JSON, native release/tag endpoints, and the actual owning tap Cask; distinguish confirmed 404 from UNKNOWN; preserve prior artifact digests and report registry/native/tap/install gates separately. Existing repository guidance at `docs/skills/repository-operations.md` lines 99–119 already distinguishes candidate and registry bytes; the proposal extends the current endpoint and tap refresh procedure. No guide edit in this lane.

Upstream disposition: none; no confirmed upstream defect.
