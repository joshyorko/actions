The Dakota #134 candidate-wheel harness separates authenticated Action, SQLite, artifact verification, terminal RCC wrapper, and process cleanup evidence. Its Linux supervisor adopts detached descendants, reaps exited children through ECHILD, and fails when unexpected live descendants or incomplete ownership cleanup require intervention. Unsupported platforms fail closed. Wrapper success requires terminal `completed` status and a JSON integer exit code of zero.

The outer CLI now rejects an existing receipt destination before resolving toolchain environment keys or creating supervisor state. It preserves the old receipt byte-for-byte and tells callers to use a fresh path; the worker's `O_EXCL` write remains as a race guard. This is fail-fast for a rejected overwrite, not invalidation of a prior receipt. Historical failed receipts at 67e82ef7, e33987b6, and 7cf11c8b remain unchanged. The latest retained live 7cf receipt records HTTP 403/200, SQLite and artifact cells as passing, and wrapper `failed/-1/child exited non-zero`, so overall acceptance remains FAIL.

Verification for the receipt preflight change:

- RED: the subprocess regression failed because the rejected invocation created `cli-supervisor` state before preserving the prior receipt.
- GREEN: the same test passed after moving refusal to the outer CLI preflight; it asserts nonzero exit, explicit refusal output, byte-identical old receipt, and no supervisor-state directory.
- Focused harness module: 29 passed, 1 live-RCC test skipped.
- Ruff check, Ruff format check, and `git diff --check` passed.

The preceding integration at d9a08395 was separately checked with 28 focused tests, 613 configured Runtime tests/10 skips, package lint/typecheck, and script Ruff. No RCC/provider/Executor run was made for the receipt-preflight change. This draft is a bounded Linux harness checkpoint, not whole #134 or release readiness; production retirement, lease-release ordering, native/frozen acceptance, and remote-provider acceptance remain unproved. Hosted checks are pending, and remote Dakota thread status remains unconfirmed.
