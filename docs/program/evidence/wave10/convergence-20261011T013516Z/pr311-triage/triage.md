# PR 311 Windows devmode integration failure

Observed 2026-10-11 01:27:06 UTC. This is a read-only one-pass diagnosis of workflow run 38099013706, job 114350853595. The run tested PR head `c888fb4a33fb2f8aa2bc30700d36ff92ccf535ca` merged into base `19380993febaa71238eaee3026b5c808773283ff`; the checkout log and verified merge commit identify merge SHA `07c2091b33e13a4f5a8699355a2b0f8a2f4db740`.

The Windows Python 3.12 devmode job failed only at step 17, “Test (integration).” Ubuntu and macOS devmode jobs passed. The Windows step ended `2 failed, 128 passed, 18 skipped, 1092 deselected in 1603.73s`. The failures were the live multi-package watched-reload recovery test and the resource case of the duplicate-MCP rollback test. Both tracebacks end in `TimeoutError` at `_selftest.py:198`, while waiting for the child server's port future. Their captured startup logs show RCC holotree hash/variables commands beginning, but no terminal RCC/server error. The template and prompt cases of the duplicate-MCP rollback test passed in that same job.

The PR diff from its base changes `test_active_contracts.py` and the repository operations guide. The two failing test files and `_selftest.py` have identical Git blob IDs at the PR head and base. This narrows direct change ownership but does not rule out indirect effects. The cause remains UNKNOWN: the evidence does not distinguish slow bootstrap, readiness behavior, or another cause, and does not establish either product regression or runner infrastructure failure. No rerun was performed.

This one Windows cell does not revise the separately accepted controlled Linux installed-wheel proof for #195. No upstream report is warranted absent a confirmed defect.

## Documentation proposal

The current “Live pull-request base identity” section already requires binding CI evidence to the checkout recorded in job logs. A small additive paragraph could say:

> When diagnosing a red matrix cell, retain the failing step and per-platform/test summary, and bind them to the PR head and merge checkout SHA/base shown in the job log. Compare the relevant test and shared wait/source blobs across merge parents before assigning direct change ownership. A readiness `TimeoutError` identifies the wait that expired, not why the child failed to become ready; leave cause unknown unless the log contains terminal evidence. Do not generalize one platform cell to the whole gate.

This is a proposal only; no repository documentation was edited in this read-only task.
