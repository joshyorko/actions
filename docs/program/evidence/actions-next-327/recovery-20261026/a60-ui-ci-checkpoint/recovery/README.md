# a59 recovery composition probe

## Result

The bounded offline SQLite + blob capture and absent-root restore passed. The
capture contains only `server.db` and the five files from `datadir/blobs`; it
does not include logs, lock contents, caches, external profiles, authorization or
HMAC-key files, or an RCC home. The original selected database/blob hashes are
unchanged after the restore, the copied hashes match, and `PRAGMA quick_check`
passed on source and restored databases. The installed a59 `Database` module
performed two safe lifecycle/reference reads in separate fresh Python
processes; the results matched. These are installed store reads, not calls
through a trusted Runtime or MCP/API caller.

The supervisor receipt is [run-supervisor.json](run-supervisor.json); the
qualification and exact member hashes are in
[evidence/receipt.json](evidence/receipt.json). Two bounded read outputs are
[read 1](evidence/installed-a59-readback-1.json) and
[read 2](evidence/installed-a59-readback-2.json). The qualification used the
installed consumer Runtime 1.1.0a59 wheel
`cca5383bd331bfc68227bf5c2749f867cc3d9e7cc7daaeb3f13fbe9125d5960a` at source
`123e772ee36c44cfd96ea62a6c599bb4f55c8f1b`, tree
`7d6658bc3f2d536519c8698503f8b379c7b3ed56`.

The new capture/restore consumed 1,269,760 bytes of measured disk space; free
space remained 11,158,134,784 bytes, above the 10 GiB floor. No Runtime build,
compiler, RCC, PostgreSQL, database migration, Run, Attempt, launch, grant, or
credential was created. The original fixture’s selected DB/blob hash set is
recorded before and after and matches.

## Fixture map

The input is the stopped a56 cancellation fixture, not current a59 data. Its
SQLite `server.db` is 540,672 bytes and has one workspace, one Run, one Run Pin,
one cancelled Attempt, one Run Execution Intent, one 10-minute Run Task receipt,
one Run Admission, one Run access grant, one fenced Work Item, and zero RunOutput
rows. The Run has status `CANCELLED`, the Attempt is `cancelled`, and the Work
Item is `FAILED` with cancellation requested. The Task receipt expires at
`1793022349641` ms UTC; observation at `1793040359724` ms UTC confirms its
stored lifetime elapsed. The API’s actual expired-task refusal was not tested.

OAuth user data, temporary user sessions, user sessions, triggers, and trigger
invocations have zero rows. The fixture has no `server.db` SQLite sidecars and
the recorded lock PID was not running. Five immutable blob files total 57,467
bytes. The fixture has no RunOutput/object reference to use for a native output
restore or terminal artifact read.

## Scope limits and remaining gates

The current a59 helper’s rebase path is for legacy `workitems.db` and its
supported `work_item_files` table. This fixture instead contains native
`server.db`; no legacy attachment table exists, and the helper reported zero
legacy attachment rebases. The bounded file copy therefore says nothing about
relocating native RunOutput references. No new native path migration was added.

The current matrix’s mandatory whole-Runtime gate remains open: coordinated
SQL, object, journal/audit/effect, source and Runtime artifacts; preserved Run
and effect lineage and GC references; clean-host startup/replay; and old-version
fail-closed rollback/downgrade. This probe does not start the installed Runtime
against the alternate root because it has no permitted trusted host caller or
credential source; it does not read the fixture’s protected external profile
or HMAC/auth/session files. It also does not include source/package/compiled
Runtime artifacts, execution caches, external providers, or ordinary CLI
configuration. The fixture belongs to a56, so its a59 model/store reads are not
a current-source or ordinary installed-startup qualification.

The a59 Task service source checks `db_now >= created_ms + ttl_ms` and maps the
expired receipt to bounded `TaskUnavailable`; this is static installed-code
evidence only. No live service refusal was observed. Since the fixture has no
RunOutput rows and the Run is cancelled, terminal artifact availability is
not applicable to this fixture and must not be reported as PASS.

## Canonical guide delta proposal

See [documentation-proposal.md](documentation-proposal.md). No repository file
was changed in this isolated probe.

Upstream disposition: none.

Documentation improvement:
- Canonical file changed or proposed: proposed exact delta to `actions/docs/skills/repository-operations.md`.
- Durable learning captured: the installed offline helper rebases only the recognized legacy `workitems.db` attachment layouts; copying native `server.db` plus blobs does not establish native RunOutput path relocation or whole-Runtime restore.
- Evidence: installed helper source at `_datadir_restore.py` (`database = target / "workitems.db"`, return on absence, then `PRAGMA table_info(work_item_files)`); this probe’s `server.db`, five blobs, zero `run_output` rows, zero legacy attachment rebases, matching restored hashes, and unchanged source hashes.
- Stale or ambiguous guidance removed: none; propose clarifying the helper’s existing scope.
- Remaining uncertainty: ordinary a59 Runtime/API startup, native provider refs, clean-host source/runtime artifacts, expired Task API refusal, and whole coordinated rollback/downgrade remain unqualified.
