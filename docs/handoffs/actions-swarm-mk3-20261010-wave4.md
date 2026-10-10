# Actions Swarm MK3 — wave 4 convergence checkpoint

This is an additive checkpoint after evidence commit
`e27ef7364b10586886398ab40f2cc1ae68dcb504`. The evidence branch is not an
engineering baseline. All 54 retained contracts, their original bodies, typed
Canvas relationships and historical archives remain unchanged. One contract is
accepted/closed; no new whole-issue completion is claimed here.

The [manifest](../program/evidence/wave4-convergence-20261010T2045Z/manifest.json)
binds 61 copied receipts, command logs and runners (SHA-256
`57996f513ea42141c3ceeb055f502a14e479c6222313e4f34b083e781492bc35`).
PR observations were read at 20:44:36 UTC on 2026-10-10; reconcile them live
before scheduling or merging. Older failed attempts and limitations remain in
the retained evidence.

## Reviewed source checkpoints

- PR306: SAVEPOINT admission bookkeeping repair at
  `1d742149b7341ebc5dd543aa8b7e446f7f9c8b5b`, tree
  `aa2c45671859852b8a003ed61fc50671236385e7`, parent integration
  `4e8a26296608c232ce3dbd1f250ddb709b9459c9`. Independent source/log review GO.
  SQLite authorizer regression and subsequent same-connection recovery pass;
  database suite 61 passed / 12 PostgreSQL skipped. The initial wider run had
  six tool-environment failures; all six affected tests subsequently passed
  after correcting the environment and contained RCC fixture. There was no
  complete wider-suite rerun. Hosted wheel CI hits the known floor-verifier
  mismatch repaired by PR304. PostgreSQL failed-SAVEPOINT acceptance is NOT RUN.
- PR282: exact CLI inventory repair at
  `f74341b03b1e0e554c1b0af8f88cfc0bdce5cdaf`, tree
  `66b295165ff42a123ff5091024eaa3f5b787f8f5`, parent
  `2c6de9797122de0ebf09a75ffeb01073dd75a4ba`. Independent review and focused
  RCC RED/GREEN, lint and type checks pass. Only tests and canonical guidance
  changed. Earlier browser/bundle observations remain bound to the parent;
  production artifact schema, authorization and actual ChatGPT gates remain
  open. Do not merge or expose the production template on this correction.
- PR307: Runtime release-note selection repair at
  `bad6a44752438216c47ebab7fac520e174f9649a`, tree
  `1db860bf248e83aeedf521044633bbd221902282`, stacked on PR304
  `73605934c1c948895410a5abaed6c225a396e038`. Independent source review GO.
  Removes the release-text override so the pinned action selects the exact
  tag H2 from the dedicated changelog. Local 97-pass/generation/lint results
  are owner-reported because original stdout/task files were not retained.
  Native/toolkit/audit CI can run on the temporary base; Runtime package and
  PyPI candidate gates require retargeting to integration after PR304 is
  accepted. Do not merge into the temporary PR304 branch.

## Convergence and ownership

PR304 remains at `73605934`, with 22 successful checks and the macOS development
job queued at this observation. PR292's Windows integration job
`38067347057/114257572296` remains in progress; no cancellation, acceptance or
replacement is inferred. Preserve its accepted native/Go source-equivalent
evidence. The dependency order remains PR292, then PR290 and PR299/PR300.
After PR304 acceptance, refresh dependent floor checks and resolve PR221's
community promotion through reviewed final-union gates.

Core 1.0.3 publication and registry/API verification remain accepted as recorded
in wave 3. Runtime/native 1.0.3 is unpublished. Required Runtime release gates
include actual provider-backed warm execution and the scoped browser security
acceptance, final source/platform checks, immutable publication and downloadable
asset/checksum readback. Owning Homebrew installation/upgrade proof follows
publication. Canvas and private Package metadata inspection are parallel graph
successors, not blanket release prerequisites. Work Items stays 0.4.4.

Dakota ownership was reconciled read-only through target `local` and the stored
Actions CWD: Work Items thread latest turn completed; RCC latest turn interrupted;
both threads notLoaded with no active flags at 20:04 UTC. Neither was resumed
or recreated. Current Cloud work follows those observations; historical names
are not authority to create duplicate coordinators. Devsy remains disabled.

Two source implementation lanes are active: the private RCC inspection repair
and the current-candidate RCC verifier version repair. The former remains HOLD
pending independent review, with actual metadata inspection NOT RUN. Its recovery history remains separate from Runtime source integration;
in-progress review findings are excluded from this public checkpoint. The latter
starts from PR304 and corrects candidate wheel,
Action-result and receipt assumptions that still hardcode Core 1.0.2 despite
current Core 1.0.3 source. Its read-only diagnosis is preserved here; implementation
and actual provider/Runtime execution are not accepted by that diagnosis.

A bounded direct RCC warm diagnostic is awaiting exact-file review. Its selected
staged-consumer fixture includes Python 3.12.15 and Core 1.0.2; another test's
Python-only publication fixture must not be mislabeled as that staged fixture.
No diagnostic success or upstream defect is claimed. The one authorized attempt
has a 180-second cold publication cap and 300-second total cap including cleanup.

Native artifact readback and #153 test-selection reconciliation are ongoing.
The supported artifact connector download URL works where the direct GitHub
signed redirect returned 403; a downloaded small receipt is not proof of inner
binary bytes. Preserve measured candidate identities separately from registry
identities. Broader dependency-ready successor mapping is also read-only and
must use scoped criteria rather than parent-epic closure.

## Documentation and reporting

The source checkpoints improve canonical guidance for failed SAVEPOINT admission,
exact CLI template inventory, and the pinned release action's changelog selection.
This checkpoint also records supported artifact retrieval and retention rules.
Private in-progress review findings stay outside this public evidence copy.
Upstream disposition: none; no confirmed upstream defect report has been filed.
