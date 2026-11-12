# Windows logical-context fixture portability

## Diagnosis and bounded change

The reported Windows failures are test portability assumptions, not evidence of
a portable JSON serialization defect. In
`test_logical_preparation.py`, the plain helper's `plain` and `model` cases
assert POSIX `0o600` mode bits even though Windows does not preserve that mode
contract. The bound helper fixture and the logical rows in
`test_generated_result_serialization.py` execute generated code containing
`os.O_NOFOLLOW`; Windows lacks that flag. The generated helper evaluates it
directly, so those logical fixture rows cannot exercise their intended JSON
assertions on Windows.

The test-only change keeps both plain and model JSON value assertions enabled
on every host, and makes only the mode-bit assertion conditional on POSIX. It
skips the private logical-context helper test before `tmp_path` setup on hosts
without POSIX `O_NOFOLLOW`; in the serializer contract matrix, only the
`logical=True` parameter is skipped there. Plain-path success, unsupported
objects, and non-finite JSON rejection remain active for all four serializer
cases. No product code, permission fallback, or security setting changed.

The direct generated logical helper uses `O_NOFOLLOW`, while its caller is the
private logical RCC execution path. The source does not contain an explicit
logical-helper capability guard; therefore this change does not claim generic
Windows logical-context support or add a synthetic direct-helper refusal test.
The existing native Canvas unsupported-platform test is separate evidence and
was not changed. Native Windows execution of these revised tests remains
unverified in this lane.

## Source and test identity

- `rcc_execution.py` SHA-256: `56fc2bfeaad81756dce7a17c1ec031fe4d42c3cc70d80d768070213c650cd610`
- `bootstrap.py` SHA-256: `5f18aef71c68834d99345354c9698786dd256c9a04d5861f6c618927ba69fbc7`
- `test_logical_preparation.py` SHA-256 after edit: `2b9eb9c58bb8026d6c9b318846c3b0c0fcf967f5b63569c176569bb62245c186`
- `test_generated_result_serialization.py` SHA-256 after edit: `6279489349e5320a49d48cdbad0aaa1acbfa09ee981f8191170d8571f06af079`
- Only the two assigned test files were changed by this lane; no production file
  was edited.

## Verification

The focused pinned-RCC command ran both affected files:

```text
pytest tests/action_server_tests/test_logical_preparation.py tests/contract_tests/test_generated_result_serialization.py -q
26 passed in 6.16s
```

Supervisor receipt `/workspace/327-probes/windows-logical-fixtures-327/focused-receipt.json`
reports `PASS`, `remaining_owned: []`, and `adoptees_reaped: []`.

RCC Ruff format check and Ruff import-order check (`ruff check --select I`)
passed after adding the formatter-required blank line. `git diff --check` also
passed. The configured `poetry run black --check ...` attempt could not run
because `black` is not installed in the Action Server Poetry environment; the
attempt is preserved in `format-supervisor.log` and did not modify files.

## Documentation improvement proposal

- Canonical file proposed: `docs/skills/repository-operations.md`, in
  **Generated model outputs and failed installed executions**.
- Durable learning: add the following paragraph after the existing generated
  helper JSON-contract paragraph:

  > The generated plain helper's JSON serialization contract is portable, but
  > its POSIX `0o600` output-mode assertion is meaningful only on POSIX hosts.
  > The private logical-context helper reads its context through
  > `os.O_NOFOLLOW`; tests for that helper and its generated logical-context
  > serialization path require a host exposing `O_NOFOLLOW`. Keep the plain
  > JSON success and rejection cases active on Windows, and skip only the
  > platform-bound logical-context fixtures before creating their temporary
  > state. This test boundary does not establish Windows logical-context
  > execution support.

- Evidence: `rcc_execution.py`'s `_bound_execution_helper` directly references
  `os.O_NOFOLLOW`; the assigned tests reproduce Windows failures when they
  assert POSIX mode bits or run this helper; the revised focused Linux suite
  passes all 26 tests.
- Stale or ambiguous guidance removed: none; proposal only.
- Remaining uncertainty: native Windows behavior has not been rerun in this
  lane, and the product does not explicitly reject direct logical-helper use
  when `O_NOFOLLOW` is absent.

Upstream disposition: none.
