# Independent review receipt: staged-RCC control f103

Disposition: APPROVE control for hosted execution.

Reviewed immutable control: `f103edc9015128bb5e6d3875208c4077644e8fe4`, tree `e2420f11d98ac92ab1c1918209a893a578cf0ce6`, parent `9cba2438117938e162ffffda885ba1cd45d9ca81`.

Pinned candidate: `2552a8c3419b213825294a51927843b2d61f662e`, tree `af7e419414261525c89db5511c5cbbc6f07981b0`, parent `e886d26ebaefafa9189a69517f6707691b53662e`. GitHub advertised `refs/heads/test/staged-rcc-source-candidate-20261010` at this candidate during review. The old hosted-control branch remained at `c7c18da18f2dfc1134773ea725c7b7de38c14e5c`, which is an ancestor of f103 and is the merged PR #284 branch.

The source candidate changes only the staged consumer test fixture: it registers `get_all_model_classes()`, asserts `McpCatalogName` is present, and asserts the initialized `mcp_catalog_name` table exists. Production source remains identical to integration. Control changes cover the workflow generator and generated YAML, summary/workflow contract tests, and the canonical operations guide.

The summary validator now requires exactly two inventory entries with unique string paths `{action.py, package.yaml}` in both source and staged inventories before constructing digest maps. It separately compares those maps against the corresponding source/staged digest dictionaries. Six regressions reject duplicate, missing, and unexpected paths in both inventories. The existing valid receipt case remains accepted. The exact workflow selector still requires exactly the two named JUnit test identities with 0 failure/error/skip and test process exit 0. Summary admission binds the candidate SHA/tree, loaded Runtime module hashes/origins, staged/source digests, managed worker Python/Core origins, and RCC identity. Hosted RCC execution is NOT RUN by this review.

Validation: see `f103-validation-transcript.txt`; SHA-256 `e2b1c52a572dde67c93b82fd2a7a49bc0d789a7c644acffdf8749b4a5d55c2c1`. It is a transcript assembled from captured tool output, not a redirected raw log. Test runs: 34 developer workflow/summary tests passed; focused valid-plus-duplicate admission tests 3 passed; 25 source-staging contract tests passed; Ruff check, changed-test Ruff format check, and diff check passed.

Documentation improvement: `docs/skills/repository-operations.md` records the exact candidate tuple and that inventory duplicate/missing/unexpected paths fail closed; the guide also explicitly says these synthetic summary tests do not establish the staged RCC consumer, which remains NOT RUN until hosted acceptance passes. No stale claim found. Upstream disposition: none.
