# Same-byte inventory binding correction

Review found that 0c2e77a hashed one read, then reopened the mutable wheel path.
A replacement could pair expected digest A with valid inventory B. The original
receipt is evidence of a stable-file observation, NOT same-byte binding under
mutation. That earlier claim is explicitly narrowed here.

The checker now captures one immutable bytes buffer, hashes it, and passes that
same buffer through BytesIO to ZipFile. No reopening occurs. Member-count and
uncompressed-size limits, exact selected digest/version, duplicate and RECORD
checks remain unchanged. No build/workflow/version changes.

The deterministic regression captures valid A then replaces the path with valid
B immediately after read_bytes. Both RECORDs are valid; member bytes differ.
Before: **1 failed, 10 deselected**. After: **11 tests passed**. The receipt now
contains A while the path demonstrably contains B. Red/green JUnit is retained.
This does not lock the source file or prevent its later replacement.

The real retained a38 wheel was requalified with the same explicit outer digest
and version. `candidate-bound-inventory.json.gz` retains all 320 members. A jq
assertion confirms its embedded `actions/server/bin/rcc-18.19.3` still hashes to
`7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428`.
Earlier da928/native/SBOM scope limits remain unchanged. Ruff/Isort checks pass.

Exact canonical-guide delta: hash and parse the same captured artifact bytes or
pinned descriptor; hashing a pathname and reopening it does not bind an inventory
to that digest. Require deterministic valid-A/valid-B replacement controls.
Evidence: red/green JUnit plus real requalification. Removed ambiguity: outer
hash and later path parsing necessarily describe the same bytes. Remaining
uncertainty: resolved SBOM and wider release artifacts. Upstream disposition:
none; local qualifier defect. Rollback reverts this qualifier/test correction only.
