# RCC materialization capacity plan

## Decision

No current-round view is an approved deletion candidate. The exact repository
guidance says cleanup is serial under exclusive ownership, exact view IDs must be
bound to retained receipts, producers must be stopped, and fresh process/lease
checks must show no use. It also says to retain compiler proof views and that an
RCC dry run is not an atomic lease guarantee. The views under
`a53-claimed/compiler/robocorp` are compiler materializations; the views under
`a59-cold-rcc/acquire/robocorp` belong to the cold acquire proof. Deleting either
family would violate the current retention rule or destroy evidence needed to
reproduce the proof.

The RCC 18.19.3 CLI exposes `holotree delete <partial identity>` and a
`--dryrun` option. The smallest supported operation, if a future candidate is
proven disposable, is one serial call per **full** materialization ID against
its exact owned `ROBOCORP_HOME`, with `--space user` only for entries whose
metadata says `space: user`. Do not use `--unused`, a prefix selector, or a
batch across homes. Any dry run would only confirm RCC's selector/result; it
would not establish lease safety. No delete or dry-run command was issued here.

## Current-round view inventory

All these entries report blueprint `ff6c3fc4b2583116` and RCC `v18.19.3` in
their `.meta.info`. Their RCC journal events identify `controller: rcc.user`,
the exact `.meta` path, and “normal holotree with blueprint” for the suffixed
`9fcd2534` entries. RCC-produced `b00df7dd` `.meta.info` entries have blank
controller/space fields. Those facts do not establish that the trees are
interchangeable, that they were duplicates, or that any lease has expired.

| Owned RCC home | Full identity | Observed time (UTC) | Evidence and binding | Disposition |
|---|---|---:|---|---|
| `a59-cold-rcc/acquire/robocorp` | `23b7c12_5a1fac3_9fcd2534` | 17:33:49 event; `.meta.info` 17:33:51 | Journal says space-used by `rcc.user`, blueprint above; no matching command receipt found | Retain; no command/receipt binding |
| `a59-cold-rcc/acquire/robocorp` | `7b19c17_5a1fac3_9fcd2534` | 17:35:49 event; `.meta.info` 17:35:50 | Journal says space-used by `rcc.user`, blueprint above; no matching command receipt found | Retain; no command/receipt binding |
| `a53-claimed/compiler/robocorp` | `d93c26e_5a1fac3_9fcd2534` | 17:37:27 event; `.meta.info` 17:37:29 | Journal says space-used by `rcc.user`; no matching command receipt found | Retain; compiler proof home |
| `a53-claimed/compiler/robocorp` | `d93c26e_5a1fac3_b00df7dd` | `.meta.info` 17:37:43 | RCC metadata only; controller/space blank; no matching command receipt | Retain; compiler proof home |
| `a53-claimed/compiler/robocorp` | `6de426f_5a1fac3_b00df7dd` | `.meta.info` 17:37:58 | RCC metadata only; controller/space blank; no matching command receipt | Retain; compiler proof home |
| `a53-claimed/compiler/robocorp` | `1a93615_5a1fac3_9fcd2534` | 17:39:18 event; `.meta.info` 17:39:20 | Journal says space-used by `rcc.user`; no matching command receipt found | Retain; compiler proof home |
| `a53-claimed/compiler/robocorp` | `1a93615_5a1fac3_b00df7dd` | `.meta.info` 17:39:35 | RCC metadata only; controller/space blank; no matching command receipt | Retain; compiler proof home |
| `a53-claimed/compiler/robocorp` | `d2e611e_5a1fac3_b00df7dd` | `.meta.info` 17:39:50 | RCC metadata only; controller/space blank; no matching command receipt | Retain; compiler proof home |
| `a53-claimed/compiler/robocorp` | `5b65d1a_5a1fac3_9fcd2534` | 17:41:08 event; `.meta.info` 17:41:10 | Journal says space-used by `rcc.user`; no matching command receipt found | Retain; compiler proof home |
| `a53-claimed/compiler/robocorp` | `5b65d1a_5a1fac3_b00df7dd` | `.meta.info` 17:41:32 | RCC metadata only; controller/space blank; no matching command receipt | Retain; compiler proof home |
| `a53-claimed/compiler/robocorp` | `b831e83_5a1fac3_b00df7dd` | `.meta.info` 17:41:51 | Current generated-journal passing component binds lease10236f0850438bd3e7005f20d96ae8c8 via postgres-object-restore/rcc-execution-receipt.json; controller/space blank | Retain; current execution proof |

The retained cold-execution receipt at
`/workspace/327-probes/a59-cold-rcc/rcc-exec-receipt.json` binds artifact
`sha256:ab46f17f4b1ec8d620a3111ad103eff36f78515df5b4db88d1739f5b1e0a6a24`,
materialization `c2fd1aa_5a1fac3_b00df7dd`, and lease ID
`8842d5a9ccbec8b9a364431135486746`; its command is recorded in
`cold-exec.json`. It does not bind any of the current-round identities above.
The older successful compiler proof in a53 binds `c2fd1aa_5a1fac3_b00df7dd`
and `badcafe_5a1fac3_b00df7dd` through retained proof receipts. Preserve those
as well. Keep the archive (`a7877f…`), artifact (`ab46f…`), original
`badcafe…` view, and acquired cold-proof `c2fd1aa…` view.

The parent task reports that all owned RCC/process users are absent. A local
process listing found no running `/workspace/actions-cloud/bin/rcc` command.
Persistent `.lck` files remain in both holotree directories; their presence or
absence is not a lease oracle. No current-round receipt exposes a lease ID or
proves a fresh per-view lease check, so active lease state for the listed views
is **unknown**, not cleared. RCC `holotree delete --help` confirms that a full
identity can be passed as the selector; this bounded help read did not run a
cleanup operation. RCC's initial help attempt without `ROBOCORP_HOME` reported
that `/home/agent/.robocorp` was read-only; subsequent help calls pointed at
the two existing owned homes and succeeded.

## Capacity and fallback

The parent reports 11.17 GB free against a 10 GiB floor, about 0.4 GB of
headroom. This is not enough evidence to risk removing proof materializations.
Do not count this RCC cleanup plan toward immediate reclamation.

The alternative is to inventory a separately owned **reinstallable, non-proof**
cache and prove its exact receipt/identity, successful reconstruction path,
producer quiescence, and fresh process/lease absence before considering one
serial exact-ID deletion. No such alternative cache was independently
identified in this read. Do not substitute old failed fixture state, a57, or
artifact/catalog/trust/provenance/receipt material. A new cache preparation
would consume capacity and needs its own capacity, import, and target-local
identity proof.

## Canonical documentation delta proposed

File: `actions/docs/skills/repository-operations.md`.

Add one durable sentence to the existing RCC materialization-cleanup paragraph:
“For RCC 18.19.3, the supported targeted form is `rcc holotree delete
<identity> --space <space>`; pass the full `.meta.info` identity, and use
`--dryrun` only to review selector behavior, never as lease proof.” The exact
syntax and flags are supported by the pinned binary's help output; `.meta.info`
identity/space fields are observed in the inspected homes. Keep the existing
exclusive-ownership, receipt, producer, process/lease, and proof-retention
requirements unchanged. This is a proposal for the integration agent; no
canonical guide was edited in this read-only lane.

Upstream disposition: none

Documentation improvement:
- Canonical file changed or proposed: Proposed delta to `actions/docs/skills/repository-operations.md` above.
- Durable learning captured: RCC 18.19.3 accepts a full identity with `holotree delete`; `--dryrun` is selector feedback only, with safety still depending on retained receipt and live lease/process evidence.
- Evidence: Read the canonical guide; read RCC 18.19.3 `holotree delete --help`; inspected `.meta.info` and journal entries in both exact homes; read the retained acquire/cold-execution/compiler proof receipts.
- Stale or ambiguous guidance removed: None; existing guidance remains valid.
- Remaining uncertainty: Current-round IDs lack bound command receipts and lease IDs; dry-run does not close that gap. No candidate is cleared for deletion.

Integration correction: the completed current PostgreSQL/object component binds `b831e83_5a1fac3_b00df7dd` and lease `10236f0850438bd3e7005f20d96ae8c8` in [its retained receipt](postgres-object-restore/rcc-execution-receipt.json). The blanket no-receipt/no-lease statement applies only to other unbound candidates. This passing proof view is retained. No RCC cleanup was authorized or executed by this review.
