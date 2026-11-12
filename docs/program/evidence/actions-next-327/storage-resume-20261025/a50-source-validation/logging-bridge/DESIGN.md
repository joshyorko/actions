# Public Core logging bridge: proposed minimal change

Design only; no source edits or execution. Current Runtime directly imports Core-private logging from `_api_run.py:267`, `_server.py:845`, and selected-child `preload_actions.py:20`. The existing public `actions.server_integration` already owns narrow Core-to-Runtime exports. The private-import contract is correctly failing and must remain unchanged.

Add `get_log_viewer_html` and `log_html` to Core's `actions.server_integration` and `__all__`, reexporting the existing owned implementations (`html as log_html`). This preserves identity, viewer bytes, logging lifecycle, filters and secret redaction; it introduces no second logger. Runtime viewer routes import `get_log_viewer_html` only from that public bridge. The installed Runtime requires new Core a8; root owns the version/dependency/compiler change. Do not provide a Runtime fallback into Core-private modules, including dynamic imports.

Selected child compatibility needs an explicit boundary: Core a6/a7 has the owned logger but does not expose a public HTML bridge. Runtime cannot call that private implementation while simultaneously honoring the import contract. This cannot be solved by an honest import-only fallback. The preload HTML call is used only for optional `X_ACTION_TRACE`; it is not the ordinary Core logging lifecycle.

Recommended compatibility behavior:

1. If `X_ACTION_TRACE` is empty, do not resolve any HTML logger. Existing a6/a7 selected child execution, ordinary logs and redaction remain usable unchanged.
2. If tracing is requested and the public bridge exposes `log_html`, use it. Import the public module normally; import/initialization errors must propagate. Do not catch broad ImportError/AttributeError around the call.
3. For explicitly identified legacy Core distributions that used `robocorp.log`, retain its public `html` path only in that selected child environment. Use an explicit reviewed version eligibility boundary, not broad missing-export fallback. Resolve the actual earliest owned-logger version from source/release evidence before implementing; do not guess a numeric floor.
4. For owned a6/a7 with requested HTML trace but missing public export, fail with a clear compatibility error requiring Core a8 for this optional integration. Do not import upstream logging, suppress the failure, omit requested trace silently, or reach into private Core modules. This narrows only the optional external trace feature; these older environments remain usable when no trace is requested.

If product policy requires HTML trace preservation on a6/a7, a public-bridge backport in a separately versioned Core is necessary. Immutable original a6/a7 bytes cannot acquire a public export. No such backport or mutation is proposed here. Post2/Core6 UI stays immutable.

Tests: Core bridge export identity and exact embedded viewer bytes; Runtime API/static wheel scan unchanged; selected-child matrix with no trace for Core6/7, new public trace success, old legacy public logger success, owned old requested trace explicit failure, new bridge initialization/call error propagation, blocked robocorp imports on new/owned Core, actual decoded Secret/OAuth/context redaction through the same owned logger; neither fallback nor private-import checker weakened. Existing preload compatibility tests should be updated to assert this explicit feature boundary instead of preserving forbidden private imports.

Canonical documentation proposal for provenance-observability: “Runtime consumes Core logging through actions.server_integration. Runtime viewer assets require the matching Core public integration version. Selected child environments may retain older Core for ordinary execution; optional external HTML trace annotations require a public logging bridge, or the explicitly supported legacy public logger. Missing public capability must be reported rather than bypassed through private imports.”

Documentation improvement receipt: proposal grounded in the three current imports and the existing public bridge; no test result claimed. Upstream disposition: local package boundary defect, no external issue or mutation authorized/performed.
