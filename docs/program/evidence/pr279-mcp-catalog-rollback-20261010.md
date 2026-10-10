# Complete-batch MCP collision rollback receipt

The three public-decorator CLI/Runtime regressions pass on the repaired source and
fail meaningfully on the affected baseline. This is source acceptance, with no
production edits, graph changes, or publication authority in this lane.

| Run | Exact source binding | Result |
| --- | --- | --- |
| Baseline | `84b8c70a412db9594dfa2a6c5fcb3e8184db019b`, tree `b2d4a1956770a37d714cc43a23a863abf23fa089` | Three failures, 101.91s |
| Worker | Published production base `3d077296d1469b99e9fe50327e98c03a6f0aa58f`, tree `b6ee7d0fb7d5e669c78929da4ca08055866d3353`; test checkpoint `01c5d0b15d037a53bf0542753f9b25a4252f5132` | Three passes, 25.35s |
| Root independent rerun | Same production tree, identical new test, accepted guide delta; resulting local checkpoint `0fc30830fd520ca183f9a765bad9d9cd83ae59e3`, tree `3c26d276323b30ecce50106b7f7a9f2ff5236d29` | Three passes, 27.48s |

The identical new test SHA-256 is
`e9d40db8fde507f3c586ed5a5893e1daa06da27ae3373d2d82b11dd78963733a`.
The JSON companion records exact commands, working directories, installed Core
1.0.2 origin, production file hashes, test and patch hashes, sanitized baseline
excerpts, and observed process/port cleanup.

The cases seed A's tool, direct resource, resource template, and prompt plus B's
sibling tool, and execute all of them over real HTTP/MCP. They then change A's
implementation and metadata, omit B, and introduce C with a duplicate resource
URI, resource-template URI, or prompt name. Each repaired-source case rejects the
complete batch with the expected diagnostic, retains identical ActionPackage and
Action rows, old included source bytes and snapshot-store entries, then restarts
without synchronization. All four catalog responses and their shared revision
remain identical; the old tool, sibling, resource, template, prompt, and HTTP
prompt execute again.

Every baseline case reached candidate admission after successful old catalogs and
callbacks. Per-package synchronization disabled all four A capabilities and B's
sibling before the final catalog was assembled. C alone remained enabled, so the
duplicate disappeared and the candidate server started. The expected-rejection
command timed out after 30 seconds at test line 251. This proves the complete-set
admission defect; it does not show that an individual duplicate-key helper accepts
duplicates. Read-only SQLite facts and relevant server lines are preserved in the
JSON. All six recorded seed/candidate Runtime PIDs were absent, all six loopback
ports refused connections, and no test-path processes remained. No broad kills
were used. This is an observed owned-process cleanup result, not a general
descendant-reaping claim.

| Evidence | SHA-256 |
| --- | --- |
| Baseline pytest log | `80eb5fbb6d040d68d10836fe78f264d3dfa907d4fccf67f5a00b1c41f6952167` |
| Worker pytest log | `11430c8862aa6b5091944945e219bf083086f08bf8e094c578c8fb131c4c0262` |
| Root independent pytest log | `bad4a6043579776dbe8f4414f53d584d74c47e6c7fa30c9f36665d306548238e` |
| Test-only patch | `08371396ef1d5dd388338aab6561b709d8a8f75b9d90fce5140bc2ec058ec11d` |

Only sanitized relevant excerpts are in this durable receipt; no environment dump,
credentials, database files, RCC materializations, or whole job logs are included.
Existing cached RCC handled ordinary local bootstrap/configuration/feedback. No
RCC environment preparation or toolchain changes occurred. The test deliberately
skips the frozen executable override; it does not establish packaged duplicate-key
or failed live-reload behavior. Ruff lint/format, Isort, Mypy for the new test, and
whitespace checks passed.

Documentation improvement:

- Canonical file: `docs/skills/repository-operations.md`; root accepted the exact
  addition from the worker's `documentation-proposal.md` into its local checkpoint.
- Durable learning: complete-catalog validation must precede package replacement
  and omission commits; helper collision checks alone do not prove executable
  last-good preservation.
- Evidence: three baseline failures, three worker passes, three independent root
  passes, exact DB/source/catalog/callback assertions, and bounded cleanup checks.
- Ambiguity removed: CLI all-or-none admission is separate from duplicate-key
  helper correctness, live reload, packaged execution, and stale-alias identity.
- Remaining uncertainty: see `pr279-remaining-gates-20261010.md`; publication and
  final exact-head CI remain root-owned.

Upstream disposition: none. The defect and repair are Actions-local.
