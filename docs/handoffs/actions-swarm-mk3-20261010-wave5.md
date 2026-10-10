# Actions Swarm MK3 — wave 5 evidence checkpoint

This additive checkpoint starts from `6e7402857d1bf16a7beeb590e7170987534ad727`.
It records source reviews and bounded acceptance evidence; it is not an
engineering baseline, graph amendment, issue closure, or release approval.
See the linked [additive correction](actions-swarm-mk3-20261010-wave5-correction.md)
for the distinct PR305 Canvas versus PR304 #153 evidence and the independently
recovered nested RCC verification; the original receipts and first checkpoint
remain retained unchanged.
The new evidence directory's manifest
(`wave5-checkpoint-20261010T2109Z/manifest.json`, SHA-256
`abdbeb116c2df53cefb052af74c760fd6915a035e48fc0135d6d8033a3625feb`)
binds the copied text receipts and the preservation check. It intentionally
contains no binaries, credential headers, signed URLs, or private #152 policy
inventory.

## Preserved program record

The graph and ledger were left unchanged. The graph still contains 54 original
contract rows and its issue-body index remains
`1135e3aaf481341d5921bac7ab4ec5d726ffd2e8db0d17eaab90480e020902e8`; one
contract is accepted and 53 remain open. The 16 historical ZIP archives under
`docs/program/evidence/` are byte-identical to the starting commit. Their
individual hashes and the graph/ledger hashes are listed in
`wave5-checkpoint-20261010T2109Z/preservation-check.json`.

## Scoped evidence

- **PR308 candidate verifier:** source `284880ca80bb666de6ef1bd970b493435bb7a8a9`
  (tree `8471f44cc58f2dbe0226fbcf7d89445f440df2f0`, parent
  `73605934c1c948895410a5abaed6c225a396e038`). The repair derives Core and HTTP
  Helper versions from checked-out metadata, checks the versioned wheel filename
  and embedded METADATA, and carries version/hash identity into candidate and
  terminal receipts. Independent source review and corrected-unit readback are
  GO for this source scope. Contract tests: RED 2 failed, then GREEN 2 passed;
  Ruff passed. The first broader attempt was 30 passed / 7 failed / 1 deselected;
  its initial attribution was corrected additively. The corrected canonical RCC
  task run was 37 passed / 1 real-RCC case deselected. No provider/Runtime
  acceptance was run. At the 21:09 UTC readback PR308 remained open with some
  matrix/toolkit checks queued. See the four review/correction receipts and
  retained logs in `wave5-checkpoint-20261010T2109Z/pr308-candidate-verifier/`.
- **PR304 native Work Items artifacts:** run `38081495661` binds PR head
  `73605934c1c948895410a5abaed6c225a396e038` to synthetic merge
  `856c0a47e27dda373d4e44aea2a5a26a1db287d0`, tree
  `a8fe00af1858077273912d0b590f0f7a662c83d5`. Linux, Windows, and macOS
  native jobs completed successfully. The independent review accepts the
  three-OS frozen/Go-wrapper Work Items 0.4.4 subgate, not the whole #208
  contract. Windows' measured Core 1.0.3 candidate wheel hash differs from the
  separately published wheel hash; candidate wheel bytes are absent, so no cause
  or byte identity is inferred. The run seeds a stale reservation and does not
  simulate a process crash. Authorization-denial, missing-support and generic
  HTTP 500 UI cases, and broader manual accessibility/non-Chromium criteria
  remain unverified. The specific #153 Origin/ambient-session test was NOT RUN
  on all three operating systems; #153 and #208 remain open. Owner and
  independent receipts are retained under `pr304-native-artifacts/`.
- **RCC warm attempt 2:** attempt `attempt-20261010T2101Z` is the second and final
  authorized bounded attempt. Pinned RCC cold-published artifact A in 53.8s
  (exit 0; digest `sha256:d78a6bdc62558ab7d8b97df55fb3071eefe1c497bb8afe769490d8e324e86d16`).
  Consumer B's acquire exited 0, but its retained stdout was truncated before
  the exact returned digest and affirmative verification could be parsed; no
  subsequent `env exec` comparison ran. The honest result is
  `PREFLIGHT_OR_RUN_FAILURE`: the record does not prove either successful or
  failed verified acquisition. Cleanup recorded all owned processes/groups
  reaped and no cleanup errors. No retry is authorized, no local-ready/provider
  comparison ran, and no upstream defect is established. Independent result
  review by Sol is pending. See the bounded interpretation and result manifest
  in `rcc-warm-attempt-2/`; the full task receipt and environment values are not
  copied.
- **RCC inspection guide checkpoint:** `2ffcbd5a29795e4cce99f299f5897d0e015a1477`
  (tree `521b583187762ada348bf5e81306ef06bea8dea8`) is a guide-only correction
  of the inherited-variable statement. Its prior focused source/test result
  remains 17 passed, Ruff passed, and Mypy clean for one file. The change only
  clarifies the small retained process-variable allowlist. This is source and
  documentation evidence only: actual RCC inspection, publication, and
  admission were NOT RUN. No private in-progress review details or network values
  are included.
- **Live dependency snapshot:** the exact-head readback at 21:07:45 UTC records
  PR304's macOS development matrix at `Test (integration)` with two sibling OS
  jobs successful, and PR292's Windows development matrix at `Test
  (integration)` with its two sibling OS jobs successful. Both target jobs
  remain in progress; neither is accepted or treated as a blanket prerequisite
  for unrelated work. PR305's retained candidate wheel bytes and METADATA
  identify Core 1.0.3 (SHA-256
  `80f8e0b828ceb92d7cb7412a92f9306a4b0d2960365bf9aee899ad0cd71144f8`); an older
  summary that called it 1.0.2 is stale. The timestamped status receipt is
  `release-ci-refresh-20261010T2107Z.json`.
- **Canvas browser follow-up:** the existing bounded proof receipt records one
  passing pinned Playwright test against the local Runtime bridge and says the
  production host/ChatGPT integration was NOT RUN. A newer runner attempt needs
  a corrected prepared environment; its result is pending and is not represented
  as a new pass in this checkpoint.

## Durable documentation proposal and reporting

No canonical guide was edited in this evidence-only branch. Proposed durable
guidance: bind workflow and matrix status to the exact PR head and retain each
active step as pending; an exit-zero command with truncated output is not a
verified artifact readback; candidate dependency identity requires agreement
between checked-out version, wheel filename, embedded METADATA and measured
bytes. These points are supported by the timestamped run census, RCC acquire
result, and candidate-verifier receipts in this checkpoint.

Upstream disposition: none. No confirmed upstream defect or external report is
identified. All previously open dependencies and acceptance criteria remain
open unless the scoped receipts above explicitly establish a subgate.
