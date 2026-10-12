import hashlib,json,stat,datetime
from pathlib import Path
OUT=Path(__file__).parent;REPO=Path('/workspace/engineering/campaign-checkpoint');DEST=REPO/'docs/program/evidence/wave11/current-engineering-successor-20261011'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
# Retain the named subject correction as its own body; the original stale label remains historical.
p=Path('/workspace/engineering/pr305-current-a54-source-LIGHT/OWNERFINAL-current5306-ordinary-a54-source-LIGHT-subject-metadata-v2.json');raw=p.read_bytes();assert sha(p)=='896ffb6299cf9e7fca9adacc187115d43057be559226b8cfcd4b99411f9324ee'
dest=DEST/('current305--'+p.name);dest.open('xb').write(raw);dest.chmod(0o644)
m=json.loads((DEST/'curated-safe-manifest.json').read_bytes());m['rows'].append(dict(path=str(p),bytes=len(raw),sha256=sha(p),mode=oct(stat.S_IMODE(p.stat().st_mode)),group='current305',original_declared_status='NAMED_SUBJECT_METADATA_CORRECTION_ONLY',proposed_successor_relative_path=str(dest.relative_to(REPO)),copied_Git_mode='100644'))
m['additional_exact_rows']+=1;m['total']+=1;m['total_bytes']+=len(raw);m['status']='CURATED_SAFE_SUCCESSOR_COPY_WITH_NAMED_CURRENT305_SUBJECT_CLARIFICATION_REVIEW_REQUIRED_NOT_COMMITTED';q=DEST/'curated-safe-manifest-v2.json';q.open('x').write(json.dumps(m,indent=2)+'\n');q.chmod(0o644)
readme='''# Current engineering successor — 2026-10-11

This is a curated documentation checkpoint after `62f4e180`, not a product
baseline, release admission or campaign completion. It retains the prior
1,180-entry manifest and collector unchanged. The [safe manifest](curated-safe-manifest-v2.json)
binds 40 planned summaries/patches plus explicitly announced successors; only
those bodies were copied. Referenced private APIs, logs, configurations,
process/member inventories, archives and native binaries remain outside Git.
Original failed, conditional and stale-label receipts retain their identities.

The named integration target is `a54c982462d1e7ad011d8152bfc299d997503fb3`,
tree `47a1e4fceb22fd15eaee1ca380ad6c005abfdde6`, ordered parents
`e3c29cde8878307912e55ed09b6436c0f91d06d5` and
`ec70a2928461941c129b1c05332dc441070e0184`. Community remains
`a70993fafc99a9f94041485542d5a720797ca394`. PR300 and PR312 have distinct
normal-integration receipts. None of the remaining rows implies another merge.

| Subject | Latest bounded evidence | Required next gate |
|---|---|---|
| PR308 current source `396925cb`, tree `84f850f0d4e08b21afcd8220413ce94322370acf` | Clean 1,426-entry ordinary union, reviewed public native-home permission fix; SOURCE_LIGHT and independent union/source reviews pass. | Fresh SOURCEFULL, independent exact configuration admission and distinct root actual release. |
| RCC actual compatibility | Original b614 control3 capacity/cleanup FAIL retained; later e4ff owned-home mode FAIL retained with source-supported diagnosis. RCC5 and candidate7276 have not executed. | Freeze and review the private V8 configuration, qualify its exact current source, then separately authorize a bounded control3 attempt before either newer version. |
| PR282 local/pushed source `1299cc4b` | SOURCEFULL 1,349 PASS / 12 SKIP, independent source review and normal draft-branch push. Root's 16:37/16:41 snapshot records 25 successful checks. | Exact CI/policy/owned Windows readback and normal-integration review. Browser/native/private/full127 acceptance remains separate. |
| PR305 local source `5306eeb2`, tree `8418e9ffeeaaf2446771e34b5b4602bab3d357a5` | SOURCE_LIGHT; named executable V4 and independent preexecution GO correct the copied inventory subject/path. Original packets remain HOLD. | Distinct root serialized SOURCEFULL release; current full suite and new branch push have not run. |
| PR313 source `12dd` | Scoped SOURCE_LIGHT and corrected bound full-preexecution review retained from their original tuple. | A newer full/CI/integration result needs its own owner and exact source binding; none is inferred here. |
| PR221 at a54 | Metadata-only snapshot records 33 SUCCESS and one expected Work Items tag SKIP. Original aggregate acquisition is prepared only. | Separate exact original-artifact acquisition, source/content inventory and approved OAuth input/content authority; consumers, native and publication remain separate. |
| Capacity B27 | Root original preservation and independent data-only review pass for three exact completed namespaces. 61 prior archives / 27 indices remain retained. | Fresh capacity measurements govern later source/native releases; recovered capacity is not qualification. |
| Pytest38 storage preparation | Synthetic archiver controls: original RED3, index durability RED1, final34 PASS. Final read-only admission finds the original root absent; no archival/removal operation ran. | HOLD: original bodies unavailable, no reconstruction or archival-preservation claim. Responsible retention invocation remains UNKNOWN. |

The installed toolkit Pytest source defaults to retaining three numbered roots
and registers candidate cleanup at exit. With an observed maximum41, root38
is eligible under that default; directory numbers do not identify which
invocation deleted it. The first synthetic control used default root39; later
controls use new explicit owned basetemp directories. Existing failed setup,
controls and admission logs remain private and hash-bound. Protect retained
roots from concurrent retention-triggering tests before preservation.

The original 54-contract graph remains unchanged: 53 retained open contracts
and accepted/closed210. No closure census, ledger regeneration, issue closure,
Runtime1.0.3 publication, tag, registry mutation or release was performed by this
checkpoint. Private01f/frozen-v6, complete134/135, backend/platform/native,
Homebrew cold install/upgrade, ChatGPT and full product contracts remain held.
Published Core/Helper1.0.3 evidence remains its historical scope; Work Items
stays0.4.4. The production/toolkit RCC default stays18.19.3. Released5's dirty-VCS
source-equivalence UNKNOWN is separate from candidate7276's immutable tuple.
Devsy remains disabled; no new infrastructure, Devsy or Dakota execution occurs.

Continue short dependency-ready engineering waves on the existing owners and
branches. Reconcile live refs, ownership, source and capacity before each gate;
a documentation checkpoint neither restarts workers nor authorizes a rerun.
Upstream disposition: none.
'''
p=DEST/'OPERATOR.md';p.open('x').write(readme);p.chmod(0o644)
handoff='''# Actions Swarm MK3 current engineering successor — 2026-10-11

Continue from the [curated current engineering checkpoint](../program/evidence/wave11/current-engineering-successor-20261011/OPERATOR.md)
and its [exact safe-body manifest](../program/evidence/wave11/current-engineering-successor-20261011/curated-safe-manifest-v2.json).
The prior handoffs, original 54-contract graph and 1,180-entry evidence manifest
remain intact. This branch stores operational evidence and is not the product
baseline or a release candidate.

Integration is `a54c982462d1e7ad011d8152bfc299d997503fb3`; community remains
`a70993fafc99a9f94041485542d5a720797ca394`. PR308 current396925 has reviewed
SOURCE_LIGHT, with fresh full source and actual compatibility pending. Original
control3 capacity/cleanup and later home-mode failures remain failures; newer
RCC5/7276 have not executed. PR2821299 has a reviewed full source pass and normal
push; captured CI is green, with policy/Windows/integration admission separate.
PR3055306 has SOURCE_LIGHT and named V4 preexecution GO; full source is NOT_RUN.
PR221a54 artifact acquisition remains preparation only. No registry, native,
consumer or release qualification transfers from an earlier tuple.

Pytest38's inventoried root is now absent. The proposed archiver was never
launched; original bodies are unavailable and retention causation is scoped,
not attributed to a particular invocation. Preserve the failed admission and
use absent, explicitly owned basetemp directories for synthetic controls.

Continue the existing bounded engineering lanes after checking current ownership,
refs and serialized source/native slots. No issue closure, source rebase,
replacement branch, package/tag publication, new infrastructure or Devsy/Dakota
execution follows from this checkpoint. Full private, platform, backend,
Runtime publication and product contracts remain held. Upstream disposition: none.
'''
p=REPO/'docs/handoffs/actions-swarm-mk3-20261011-current-engineering-successor.md';p.open('x').write(handoff);p.chmod(0o644)
p=REPO/'docs/program/engineering-handoff.md';original=p.read_bytes();(OUT/'original-engineering-handoff.md').open('xb').write(original);(OUT/'original-engineering-handoff.md').chmod(0o600)
p.write_bytes(original+b'\n\n## Current engineering successor — 2026-10-11\n\nContinue from the [curated successor](../handoffs/actions-swarm-mk3-20261011-current-engineering-successor.md) and its scoped source, actual and storage dispositions. The earlier snapshots remain historical. This documentation checkpoint preserves the original 54-contract graph and private evidence boundaries; it grants no native attempt, merge, closure, publication or infrastructure action.\n')
print(json.dumps(dict(safe_rows=m['total'],copied_body_bytes=m['total_bytes'],new_documents=2,commit='NOT_RUN')))
