import hashlib,json,stat
from pathlib import Path
O=Path(__file__).parent;R=Path('/workspace/engineering/campaign-checkpoint');D=R/'docs/program/evidence/wave11/current-engineering-successor-20261011'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
items=[('actual282ind','/workspace/engineering/pr282-actual-e2c81-independent-integration-review/OWNERFINAL-independent-actual-e2c81-PR282-integration-review.json','4c1f82529737c112a6775880486df23b00d457041ea2a899811f762bc4022baf'),('canonical282','/workspace/engineering/pr282-current1299-a54-complete-CI-admission-review/canonical-current-Canvas-consumer-and-parent-readback-proposed.patch','a164f54111f3b75fdc7866ad555423358f56b2c21e71301425cde13b4c313319')]
def scan(x):
 if isinstance(x,dict):
  for b in x.values():scan(b)
 elif isinstance(x,list):
  for b in x:scan(b)
 elif isinstance(x,str):assert not any(s in x for s in ['http://','https://','Bearer ','sig='])
m=json.loads((D/'curated-safe-manifest-v5.json').read_bytes())
for g,s,h in items:
 p=Path(s);b=p.read_bytes();assert sha(p)==h
 if p.suffix=='.json':scan(json.loads(b))
 q=D/(g+'--'+p.name);q.open('xb').write(b);q.chmod(0o644)
 m['rows'].append(dict(path=s,bytes=len(b),sha256=h,mode=oct(stat.S_IMODE(p.stat().st_mode)),group=g,content_class='SAFE_INDEPENDENT_ACTUAL_OR_CANONICAL_ONLY_NO_PAYLOAD_COPY',proposed_successor_relative_path=str(q.relative_to(R)),copied_Git_mode='100644'))
 m['total']+=1;m['additional_exact_rows']+=1;m['total_bytes']+=len(b)
m['status']='CURATED_SAFE_SUCCESSOR_CURRENT_E2_INDEPENDENT_ACTUAL_NAMED_V6_REVIEW_REQUIRED_NO_COMMIT'
(D/'curated-safe-manifest-v6.json').open('x').write(json.dumps(m,indent=2)+'\n')
p=R/'docs/skills/repository-operations.md';s=p.read_text();anchor='after the replacement registry artifact and its installed behavior are verified.\n';assert s.count(anchor)==1
block='''
The production template's exact published-Core 1.0.3 gate requires its own
retained installed-worker and browser receipt after the published dependency
prerequisite is verified. Producer proof alone does not qualify that consumer
gate; name the executed candidate-source or published-dependency path and retain
its corresponding source, module and browser identities.

Preserve an original receipt's parent list, including an empty list. Authenticate
the observed checkout SHA's ordered parents separately from the commit object;
an empty receipt list does not establish a parentless commit or replace that
readback, including for shallow CI checkouts.
'''
p.write_text(s.replace(anchor,anchor+block))
(O/'canonical-current-Canvas-context-adaptation-disposition.json').open('x').write(json.dumps(dict(original_patch_sha256=items[1][2],original_patch_retained=True,context='Existing published-Core contract after private candidate wheel paragraph',stale_original_claim='Exact blocked-until-publication sentence absent from this older owning guide; not invented or removed.',changes='Addition-only contextual adaptation; producer and consumer scopes distinct, original receipt empty parents preserved and authenticated Git parents separate.',original_dirty_lines_preserved=True),indent=2)+'\n')
for p in [D/'OPERATOR.md',R/'docs/handoffs/actions-swarm-mk3-20261011-current-engineering-successor.md']:
 s=p.read_text().replace('curated-safe-manifest-v5.json','curated-safe-manifest-v6.json').replace('manifest V5','manifest V6').replace('80 copied safe bodies / 663,108 bytes','82 copied safe bodies / 676,197 bytes')
 if p.name=='OPERATOR.md':s=s.replace('bind this advance. Other rows imply no further merge.', 'bind this advance. The [independent actuale2 integration review](actual282ind--OWNERFINAL-independent-actual-e2c81-PR282-integration-review.json)\nauthenticates the actual ordered Git parents/tree, all 1,440 typed source/FS\nentries and retained original receipts; an empty receipt parent list remains\nempty and is not used to fill Git provenance. Other rows imply no further merge.')
 p.write_text(s)
print(json.dumps(dict(rows=m['total'],bytes=m['total_bytes'],commit='NOT_RUN')))
