# Exact-source Runtime/browser retest

Both existing dedicated gates passed at clean local source
`123e772ee36c44cfd96ea62a6c599bb4f55c8f1b`, tree
`7d6658bc3f2d536519c8698503f8b379c7b3ed56`, Runtime1.1.0a59:

- `test_canvas_template_candidate_source_runs_through_runtime_and_real_browser`
- `test_canvas_template_runs_through_runtime_and_real_browser`

Prepared RCC18.19.3 gateway result: **2 passed,0 skipped in135.07 seconds**.
The host supervisor passed in144.64 seconds with `remaining_owned: []` and
8 adopted exits reaped. The source checkout remained clean. This is bounded
owned-process cleanup, not universal descendant discovery or cleanup of the
inaccessible old executor's zombies.

The tests retain their source Runtime module-origin/hash, exact4-entry
`python -P -m actions.server` launcher prefix, Core API byte identity, real MCP
calls, actual browser rendering and strict result checks. Chromium151.0.7922.173
was explicitly selected at `/usr/bin/chromium`, SHA256
`2c8d32d29dc6781c35ae196ea83299d507ac88fc339301abe74672feda299779`.
The published-Core browser receipt records Playwright1.62.1 and its frontend
lock hash. Its short browser temp root was removed.

The candidate gate necessarily builds its own Core fixture wheel from the
unchanged, clean Core source in this checkout; SHA256
`7f60329b3fb6c4aefe2137ff1f4a459e1d9ae67299db3eea6493d0a6a6f67142`.
This fixture is separate from the retained Corea8 companion wheel
`42e550a8c207849e0a428fa702827ff2f77d98a00fd63aa0f85a912c0719419f`.
No delivered a57 wheel/constraints or stored a58 artifact was replaced or
silently repinned. The source-bound fixture build is not a byte-identical
reproduction claim for either delivered bundle.

The separate published-Core gate uses the existing exact1.0.3 production
template manifest and measured worker members. Its receipt explicitly limits
that proof: three member hashes do not authenticate the entire wheel or prove
cold registry acquisition. The Runtime here is source, not a frozen installed
a59 Runtime wheel.

Both receipts retain `artifact:null` as a partial result. Neither proves
authorized artifact retrieval, native Canvas/library transitions, actual
ChatGPT rendering, fresh Codex CLI acceptance or invoice E1. No owner-host
gate is relabeled PASS. Original Ubuntu753 remains FAILED; the diagnostic
identified its own stale argv assertion and did not reveal the inaccessible
older artifact's assertion.

Raw receipts and final supervisor are in `browser/`; their source hashes and
the raw log digest are in `origin-manifest.json`. No screenshots were uploaded
to Library. Independent POSIX review found no capability/security regression;
its report is `posix-final-review.md`. Canonical operator/typing/launcher guidance
was updated in the source commit; no additional rule is needed for this retest.
Upstream disposition: none.
