Proposed addition to docs/skills/repository-operations.md, frozen-source qualification guidance:

Before starting a restored frozen Runtime suite, generate the ignored public OAuth module with the committed scripts/build_oauth2_config.py and bind its hash to the selected wheel. Bootstrap alone may leave this generated input absent even when package imports and version preflight pass. Preserve a missing-input test failure separately from the corrected full-suite result.

For Go wrapper qualification in this saved environment, inspect `go build -x` VCS discovery when a linked Git worktree fails with `error obtaining VCS status`. The supplied Go 1.23.6 selected the outer /workspace Git marker instead of the linked worktree gitfile. Standalone target-local Git metadata at the exact same commit/tree restored the unchanged build test without disabling VCS stamping or altering repository/security settings. Verify source cleanliness and identity again after changing the QA checkout layout.

Evidence: setup-failures.log (2 failures); native-build-diagnostic.log; go-vcs-diagnostic.log; generated-input.json (generated OAuth bytes equal original a52 wheel); setup-corrected.log (2 passed in 61.21s); standalone-clone.log. These observations apply to this saved toolchain/layout, not all Go versions or worktrees.

Stale/ambiguous guidance corrected: Bootstrap + Runtime import/version preflight alone is not complete generated-input readiness; generic worktree advice does not establish Go VCS discovery in this environment.

Remaining uncertainty: full applicable suite still running; installed live cancellation and broader release gates are separate.
Upstream disposition: none. No upstream defect report or external mutation performed.
