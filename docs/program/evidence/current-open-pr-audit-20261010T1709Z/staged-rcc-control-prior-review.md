# Independent review: staged-RCC control successor

## Exact subject

- Control commit: `9cba2438117938e162ffffda885ba1cd45d9ca81`
- Control tree: `9a9af532148c24353539d4258eaaa3c1f0f929da`
- Direct parent / source candidate: `230705a4829d0b0adcf76a706d1806cdd8827133`
- Source candidate tree: `af7e419414261525c89db5511c5cbbc6f07981b0`
- Candidate parent: published integration merge `e886d26ebaefafa9189a69517f6707691b53662e`
- Worktree: `/workspace/work/staged-rcc-current-integration-candidate-20261010`
- Reviewed changed paths: `.github/workflows/_gen_workflows.py`, `.github/workflows/actions_runtime_rcc_provider_rollback.yml`, `developer/tests/test_rcc_provider_rollback_workflow.py`, `docs/skills/repository-operations.md`.

## Review result

**BLOCK: summary validator accepts a duplicate staged-inventory row.** The validator builds `inventory_digests` as a dictionary, which collapses duplicate paths, then compares that map with the two-key digest map. A malformed receipt can therefore contain duplicate `action.py` entries in both source and staged inventories and still satisfy the inventory check.

Independent probe: created the normal synthetic passing receipt using the control suite's `_fixture`, duplicated one identical `action.py` entry in both `source_inventory.entries` and `staged_inventory.entries`, and ran the actual generated summary script. It returned exit code 0 with `admission: {passed: true, issues: []}`. Require exactly two entries with unique paths exactly `{action.py, package.yaml}` before accepting the digest map; add a negative regression case.

## Verified behavior and limitations

- Exact control pins candidate SHA `230705a4829d0b0adcf76a706d1806cdd8827133` and tree `af7e419414261525c89db5511c5cbbc6f07981b0`; source commit/tree are independently present as Git objects.
- Workflow is opt-in on its named push branch and path filter, uses read-only contents permission, separately checks control and candidate identities, and pins RCC v18.19.3 by SHA-256.
- Summary validator requires exactly the two expected JUnit identities, with two tests, no failures/errors/skips, matching suite and testcase counts, and zero test process exit.
- Source receipt commit/tree, runtime module hashes/origins, staged source/staged digests, candidate identity, RCC identity, and managed interpreter/core origins are checked fail-closed.
- Repository-operations guidance correctly says the real staged RCC consumer remains NOT RUN until this exact gate passes; a stale one-case control is not acceptance evidence.
- The actual RCC staged consumer was not run in this review. This review does not establish source-stage acceptance or any whole issue.

## Validation

Exact command:

`/workspace/work/community-resume/admission/action_server/.venv/bin/python -m pytest -p no:cacheprovider --confcutdir=developer/tests --basetemp=/workspace/work/staged-rcc-review-9cba-final-20261010 -q developer/tests/test_rcc_provider_rollback_workflow.py developer/tests/test_rcc_provider_rollback_summary.py`

Result: **28 passed in 31.57s**. Captured output: `/workspace/work/staged-rcc-control-review-pytest.log`.

The pytest HTML plugin generated `output/log.html` in the shared immutable source worktree; it is ignored by Git and no tracked source files changed. The generated HTML file was left in place to avoid deleting or restoring potentially pre-existing ignored data.

Upstream disposition: none. This is a local summary-validator finding.
