# Deployment canonical values — Slice 1a evidence

Date: 2026-10-10. This records the pure canonical JSON and typed-reference
checkpoint only; it does not amend the accepted source design hash or claim
#129, #130, #82, resolver, database, API, adapter, registry, Package compiler,
or release acceptance.

The authorized design input is `docs/design/deployment-revisions-draft.md` at
SHA-256 `ee847c8eef8ebb55dbc1aea12956b5ab4522f4b61ada190ab0fe573d66e620dd`,
as cited in the scoped #129 Slice 1a approval comment
`https://github.com/joshyorko/actions/issues/129#issuecomment-6094862388`.
The implementation does not edit that frozen design input. It adds pure input
canonicalization and immutable identity/reference types under
`action_server/src/actions/server/deployments/` plus focused tests and vectors.

`rfc8785==0.1.4` was downloaded from the PyPI release URL as
`rfc8785-0.1.4-py3-none-any.whl`; its SHA-256 is
`520d690b448ecf0703691c76e1a34a24ddcd4fc5bc41d589cb7c58ec651bcd48`, matching
the PyPI release JSON and generated Poetry lock. The wheel metadata reports
version 0.1.4 and the Apache License 2.0 classifier, and the wheel includes the
Apache-2.0 license text. Upstream tag `v0.1.4` resolves to commit
`4d9b161f6054301d98d0566e813d020fb019ee10`; both wheel Python source files
match the source files at that tag byte-for-byte:

- `rfc8785/__init__.py`: `fa44927afd547caf7547247078bcf28863d1e69caf116d258c532b3f20ffd154`
- `rfc8785/_impl.py`: `c25bc3a046528482d53bee3487b837f31dd9c05f33e8f13288c7aab320932cec`

The PyPI JSON response supplied artifact digests but no signed provenance or
attestation field. This is artifact-hash and tagged-source correspondence, not a
cryptographic publisher-provenance claim.

The focused test suite exercises exact canonical bytes, rejection cases,
normalized-key collisions, fresh-process determinism, typed immutable refs, and
explicit scope mismatches. It runs without the repository's RCC-dependent
session fixture because this pure-value slice has no RCC, provider, database, or
server behavior.
