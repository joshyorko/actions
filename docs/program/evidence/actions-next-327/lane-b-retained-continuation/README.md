# Retained Knowledge continuation runner

This slice extends the existing installed lifecycle runner with
`retained_ingestion: {invocation_file, terminal_file}` and
`output_http_probes: true` in its private manifest. It first reads the original
Task, requires exact terminal equality and the current public Canvas snapshot,
then replays the exact retained invocation. Missing/expired or changed Tasks
fail before invocation. There is no fallback ingestion and no guessed corpus
handle. The corpus handle is obtained only from the generated ingestion receipt
retrieved through ordinary output HTTP. Subsequent search invocations and
terminals are retained, with canonical invocation digests.

For Knowledge JSON outputs, the optional HTTP probe uses the same configured
installation owner bearer as startup, which must pass both the ordinary outer
key gate and managed authentication. It verifies exact readback, no-store,
nosniff, missing/invalid credentials, a real Canvas-issued AppSession if supplied
by canvas_get, another Workspace, an unknown handle, and rejected Range. Missing
AppSession is explicitly NOT_RUN. The existing public lifecycle then downloads
all search pages and checks exact Task/byte replay after a graceful restart.
No SQL/provider reads or alternate download protocol are introduced.

Prepared private continuation manifest:
`/workspace/lane-b-state/knowledge-a39-continuation-manifest.json`.
Before execution, install the integrator's mounted checkpoint and bind the
manifest's installed_python/prefix, expected_versions and source_checkpoint to
that verified consumer. Keep the existing owned datadir/profile/provider/corpus;
do not build another baseline or substitute a different ingestion Task. The
retained Task has ttlMs=3600000 and createdAt=2026-10-25T14:07:21.735Z; expiry must
remain a failed gate, not trigger silent recreation.

Ready command, after the mounted installation dependency is met, from
`action_server` in the prepared RCC toolchain:

```bash
poetry run python scripts/lane_b_installed_knowledge_lifecycle.py \
  /workspace/lane-b-state/knowledge-a39-continuation-manifest.json
```

Validation command (source/simulated tests, not installed acceptance):

```bash
poetry run pytest -p no:robocorp_log_pytest \
  tests/contract_tests/test_lane_b_installed_lifecycle.py \
  tests/contract_tests/test_lane_b_installed_output_http.py \
  tests/contract_tests/test_lane_b_installed_knowledge.py \
  --junitxml=/workspace/lane-b-state/continuation-final.xml
```

The earlier two-file run passed 27 tests. Final stdout/XML are adjacent. An
initial formatting command named unavailable Black; no installation/fallback was
attempted. Ruff was then pointed at a nonexistent root config once; the corrected
package-local Ruff config and Isort passed. Full package suite and native
non-Linux acceptance were not run for this scripts-only slice.

Installed HTTP/search/paging/restart byte checks remain NOT_RUN pending the
integrator's mounted source checkpoint. Dedicated product export, cancellation,
live grant revocation and real PostgreSQL lifecycle are NOT_RUN; downloading a
complete set of page artifacts does not qualify a dedicated export API. Rollback:
revert this scripts/tests/evidence commit; no production or database changes.

Exact proposed addition to `docs/skills/repository-operations.md`:

> When continuing installed qualification from a retained detached Task, verify
> its current public Task record and exact snapshot/terminal before replaying the
> original idempotent invocation. Missing or expired Task evidence must fail
> explicitly rather than create replacement work. Discover generated corpus
> handles only through authenticated public result artifacts. Qualify ordinary
> output downloads with credentials accepted by both the outer installation gate
> and managed authenticator; Canvas AppSession authority is not a bearer grant.
> Report page artifact download separately from a dedicated export operation.

Evidence: source refusal/control tests, existing HTTP probe tests, and the
retained original invocation/terminal in lane-b-installed-knowledge-a39. This
removes ambiguity around restart replacement and export claims. Remaining
uncertainty is the pending actual installed HTTP run. Upstream disposition: none.
