---
name: verify-run-lifecycle
description: Check the bounded Run/Attempt, claim, Robot launch and cancellation model when changing recovery, fences, journals or stopped-process confirmation; replay counterexamples against Runtime SQL.
---

# Verify the Run lifecycle

Use the installed `create-formal-verification-skill` and `statechart` instructions.
This is one specific bounded proof, not a general verifier or a substitute for
installed RCC execution. Read `source-map.md` before changing the model.

## Scope and sync

Sync commit: `7ce57c1ffc54debc3bcf59d27f46a253bd49ff05`.
One immutable Run/Work Item, two trusted worker identities, and two Attempt/claim
epochs. Run and claim epochs are independent. Explore expiry, takeover, durable
intent, delayed spawn, lost host/result, publication, cancellation and recovery.
Never describe this as exactly-once external effects or a proof of arbitrary
Python/SQL/OS behavior.

## Check

1. Copy `model/RunLifecycle.tla`, its configs and `view.mjs` into a fresh owned
   scratch directory outside the checkout. Use the installed `statechart` skill
   to run each config there and interpret every result. Resolve its tool commands
   from its current SKILL.md, not a copied launcher. Keep one TLC worker, a 512 MiB
   Java heap and the current task CPU/IO limits.
2. `safety.cfg` and `claimed-safety.cfg` must preserve all three invariants.
   `prelaunch-progress.cfg` must preserve standalone recovery progress.
3. `broken-recovery.cfg`, `broken-publication.cfg` and `broken-cancel.cfg` must
   produce their named safety counterexamples. These scratch configurations
   deliberately disable guards; never change Runtime to make them pass.
4. `retained-launch-progress.cfg` and `claimed-progress.cfg` currently expose
   missing progress. Keep those findings; do not weaken the properties or label
   a safe refusal as successful recovery. The claimed progress config assumes a
   genuinely fresh live claim which remains live while dispatch is attempted.
5. Restore the non-mutant config and rerun it after any model change. Preserve
   TLC output, report, counterexample and chart; a missing chart above the skill's
   graph budget does not invalidate the check.

## Runtime replay

After the repository RCC Doctor/Bootstrap gateway, from the prepared
`action_server/` package environment:

```
poetry run pytest -n 0 ../.agents/skills/verify-run-lifecycle/replay_guard_mutation.py
poetry run pytest -n 0 ../.agents/skills/verify-run-lifecycle/replay_prelaunch.py
```

The first replay proves rejection by the correct retained-launch guard and
admission by a one-guard, in-memory mutant, then restores the method. It never
starts an external process. The second requests the desired safe pre-launch
progress and currently fails on SQLite and PostgreSQL. Configure the existing
owned PostgreSQL fixture and require it with `ACTIONS_REQUIRE_INVOICE_PROVIDERS=1`;
missing service skips are not PostgreSQL proof. Never use a live database.

Use the existing installed Action-to-Robot tests for physical execution, cleanup,
restart and cancellation. Reuse credible unchanged evidence; rerun only a new
counterexample or changed implementation/binary.

## Maintenance

Diff every covered source symbol from the sync commit. Keep durable commit and
OS spawn separate, and keep publication/Work Item finish in their actual SQL
transaction. Update the model from code before checking results. Move the sync
commit only after source mapping, baseline checks, mutation sensitivity and
Runtime replay agree. An intended contract change needs its own evidence.
