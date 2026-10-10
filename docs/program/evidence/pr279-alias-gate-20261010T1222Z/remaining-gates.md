# Bounded P0 remaining acceptance gates

Read-only audit against published head `3d077296` / tree `b6ee7d0`, its tested merge
`07864b6ca4ff347af077d8e3c63b498b362a31f2`, and the root-owned test/docs successor.
No implementation or graph changes were made.

Issue #279 itself explicitly scopes repeated-directory startup synchronization,
additive control, and genuinely omitted actions. It explicitly excludes
managed-RCC rollback, generation atomicity, and last-good Runtime behavior from
whole-issue acceptance. The broader user P0 repair also touches those boundaries;
its requirements must not disappear merely because the narrower issue is green.

## Verified gates

- Complete desired-set startup, sequential additive imports, same-name HTTP/MCP
  dispatch and restart, real omission, malformed later-package atomicity, and
  last-good included-source recovery: all four CLI tests explicitly passed in
  hosted Linux and macOS Runtime jobs `114146665363` and `114146665240` of run
  `38029294077`. `inv test-binary` sets the packaged executable override; these
  are actual packaged Runtime/managed-fixture passes.
- Successful watched catalog change and independent-process surface revisions:
  `test_mcp_catalogs_are_fresh_after_action_reload` and
  `test_mcp_catalog_revisions_match_across_independent_runtime_processes` explicitly
  passed in the same two packaged suites. This closes the earlier missing
  successful-refresh/revision execution receipt.
- Actual reload closure compensation for injected nondurable SQLite commit:
  `test_actual_reload_closure_compensates_nondurable_sqlite_commit` passed in the
  nonintegration portions of both jobs. It invokes real routes, process pool and
  SQLite, but injects collected metadata and never executes a worker callback.
- Complete-batch resource URI/template URI/prompt-name rejection with preserved
  DB/source/catalog and executable old callbacks: the new source-subprocess cells
  passed independently in worker and root runs. Their affected baseline fails.
- Current native build/acceptance run `38029294071` passed on Linux, Windows and
  macOS. The release worker's updated `pr273-current-release-readiness-3d077-20261010.md`
  and `pr273-current-native-artifacts/README.md` record byte validation on all three
  platforms. Its updated warm-wrapper receipt reports all four Linux CLI cases
  passing against exact wrapper SHA-256
  `d57b5f9132abcf14d36f96c9eadf96a051c4a05047f8b26807708dec3bb3cb41`.
  The initial clean resolver failure and interrupted disk-floor run remain
  preserved; they do not negate the later warm execution passes.

Exact hosted commands, test names, sanitized excerpts and decoded-log UTF-8 hashes
are in `pr279-hosted-targeted-gates-20261010.json`. Its Linux log hash is
`e0249af4ef41602a2071998cc8b6263542248a3ba5970f4cbdee5c1f3e817719`;
macOS is `7aaf95dfa26ebb93ed358d5bb4a24eabf84f1ed524593341987db0bab2ee9246`.
The hashes identify the connector-decoded log text before excerpt sanitization,
not a GitHub ZIP archive.

## Concrete open gates

1. **Historical tool-alias identity safety is a known failure.** A previously
   advertised generated alias can later become a literal bare name in another
   package and dispatch there. Catalog TTL/revision and deterministic sorting do
   not prevent this; calls have no revision precondition. Existing original-name
   whitelist and server bearer checks did not reveal an internal authorization
   bypass. The user explicitly required a compatibility policy for previously
   discovered tools, so documenting current-catalog-only identity leaves that
   user requirement open. Required acceptance must cover collision arrival and
   removal plus literal-name capture, with restart/historical scope stated. No
   alias registry or new mitigation was implemented in this lane.
2. **Executable failure recovery in a live watched process lacks current-source
   proof.** Successful watched descriptor replacement, restart-based rejection,
   and an injected SQLite compensation closure are different tests. The real-RCC
   `test_current_candidate_failed_reload_keeps_last_good_action_usable` was
   explicitly skipped in both current hosted integration jobs. A historical d8
   receipt reports last-good/last-good/recovered runs and natural exit, but binds
   older changed source and does not record the loaded Core module origin. It
   cannot certify the present broader snapshot/import repair. A bounded actual
   live failure/old-callback/recovery receipt on the final source is still needed
   for that guarantee. Live complete-batch MCP collision rollback is likewise not
   exercised by the new restart-based cells. This is a broader P0 repair gate,
   explicitly outside issue #279's narrow startup criterion.
3. **Finish the remaining exact-head platform/configuration gate.** At the
   06:18 UTC read, Windows Runtime job `114146665360` was still running integration,
   with lint/type/docs pending. Separate native Windows success is useful but
   does not establish the four targeted CLI assertions from that unfinished
   Runtime job. Final accepted test/docs successor must receive its required
   hosted checks; unchanged production file hashes allow older production
   evidence to be identified without claiming the new full tree was tested.

## Documented proof limits, not newly invented blockers

- The new three-key cells intentionally prove unmanaged source subprocesses and
  skip executable overrides. They do not certify frozen/managed-RCC collision
  behavior. Do not claim that boundary; require an additional test only if that
  acceptance claim is made.
- Warm managed execution does not establish a clean resolver or exact published
  Core wheel identity. The release worker preserved the empty-cache network
  failure, and hosted fixture pins are distinct from measured loaded-wheel bytes.
- External mutable `pythonpath` dependencies, arbitrary-length Windows paths,
  Windows ACL isolation, strict-remote provider behavior, safe source-generation
  pruning and complete descendant reaping remain their documented boundaries.
  They are not new #279 startup requirements.
- Runtime release/tag/PyPI/tap publication and #134 whole-issue acceptance remain
  separate, root-owned work.

Documentation improvement proposed for `docs/skills/repository-operations.md`,
after its catalog reload acceptance paragraph:

> Successful watched catalog replacement proves descriptor refresh. It does not
> prove that a failed watched import preserves the previous executable callbacks,
> nor that a SQLite compensation test with injected collected metadata executes
> a worker. Keep successful refresh, complete CLI rejection/restart, and live
> failure/last-good/recovery receipts separate; inspect opt-in skips before using
> a green packaged suite to claim failed-reload acceptance.

This removes the ambiguity between those evidence boundaries without requiring
broader architecture. Evidence is the inspected tests and current hosted PASS/
SKIPPED lines. Alias compatibility and current live failure recovery remain open.

Upstream disposition: none. No independently confirmed dependency defect was found.
