# PR301 independent admission review

GO for serialization/CI only at head `c734b9f850ec7b6bea8561b70312aca5c93dd6c1`, integration `e886d26ebaefafa9189a69517f6707691b53662e`, prospective merge `6979048965f33153eff37c34b7c6ee393467f9da`, tree `1b582dd02b367e5216e60796a8da031e520aa12f`. Ordered merge parents are e886/c734. Independent local merge-tree computation matched; diff check passed; eight-file full change reviewed, no production Python source change.

GitHub exact-head checks were 20/20 success and mergeable clean. PR metadata retained stale base f180; live ref, merge parents and executed hosted checkout establish e886. Frontend run 38074235916/job 114277738441 checked out the prospective merge: required bridge 8 passed with zero skips, Runtime suite 31 files/280 tests passed. Later targeted invocations have separate skips. All four adjusted retirement-lock cases passed on Windows, macOS and Linux; production deadline logic unchanged. Backend suite totals: Windows 988 passed/94 skipped, macOS 994/88, Linux 1070/12.

No scoped blocking findings. No local pytest/npm execution, source edits, installs, remote mutations or owned live processes. Renderer, full grammar, authorization, foundry, real ChatGPT and whole-issue acceptance are outside this review. Parent subsequently reported normal merge 4e8a26296608c232ce3dbd1f250ddb709b9459c9; this receipt does not independently read back that merge.

## Documentation improvement

Propose adding immediately after the hosted-validation paragraph under Pull Request Triage in `docs/skills/repository-operations.md`:

> A pull-request metadata response can retain an older `base.sha` after its named target branch advances. Resolve the live target Git ref separately and inspect the prospective merge’s ordered parents and complete tree. Bind carried-forward CI evidence to the checkout actually recorded in job logs; neither the PR payload’s base SHA nor a mergeable flag alone establishes the current tested union.

Evidence is the exact PR payload/live-ref/merge-parent/job-checkout comparison and matching local merge tree. This removes ambiguity about authoritative current base observations. No general GitHub defect or cause is established.

Upstream disposition: none.

Exact commands and bounded observations are recorded in `pr301-review.json`; no full logs retained here.
