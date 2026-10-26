# Canonical guide proposal

Propose the following addition to
`actions/docs/skills/repository-operations.md`, immediately after the existing
`qualify_installed_restore_327.py` scope paragraph:

> The offline helper's attachment rebase is limited to `workitems.db` with one
> of its explicitly recognized `work_item_files` layouts. If `workitems.db` is
> absent, the helper returns zero rebases; it does not inspect or rewrite
> Action Server `server.db` RunOutput `object_ref` values. A hash-verified copy
> of `server.db` and a blob directory proves only those copied bytes. Native
> output relocation requires an exact provider/object-reference restore and an
> authorized read through the installed Runtime; do not silently migrate a
> native path or promote a database copy to whole-Runtime restore acceptance.

Evidence: installed a59
`actions/server/_datadir_restore.py` checks only `target / "workitems.db"`,
returns `0` if it is absent, and otherwise validates the table columns for
`work_item_files`. This probe captured and restored the a56 `server.db` plus
five blob bytes (all source and restored SHA-256 values match), observed zero
`run_output` rows and zero attachment rebases, and retained unchanged source
hashes. It ran two fresh installed-a59 store projections but no authorized
Runtime API request. Receipt:
`/workspace/327-probes/a59-recovery-composition/evidence/receipt.json`.

This text is a proposal only; this lane is not authorized to edit the Actions
repository.
