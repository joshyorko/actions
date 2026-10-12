import json,hashlib,stat
from pathlib import Path
O=Path(__file__).parent;R=Path('/workspace/engineering/campaign-checkpoint');D=R/'docs/program/evidence/wave11/current-engineering-successor-20261011'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
items=[('V8_independent_source','/workspace/engineering/rcc-current396925-private-V8-independent-source-review/OWNERFINAL-independent-private-current396925-V8-source-only-review.json','8ac3aed11e1efe07c6859bcf29171c38925b6d8657a8fc2ff17b02db4d78eb2c'),('V8_canonical','/workspace/engineering/rcc-current396925-private-V8-source-only/canonical-current-source-disposal-context-proposed.patch','7629562d370c5e761c4b3d9dab470b2e6ab15a2f9ce643a51a865bc590648313')]
def scan(x):
 if isinstance(x,dict):
  for b in x.values():scan(b)
 elif isinstance(x,list):
  for b in x:scan(b)
 elif isinstance(x,str):assert not any(s in x for s in ['http://','https://','Bearer ','sig='])
preserved=[]
for p in [D/'OPERATOR.md',R/'docs/handoffs/actions-swarm-mk3-20261011-current-engineering-successor.md',R/'docs/skills/repository-operations.md']:
 q=O/('frozen-V2-original-'+p.name);b=p.read_bytes();q.open('xb').write(b);q.chmod(0o600);preserved.append(dict(original_path=str(p),original_bytes=len(b),original_sha256=sha(p),retained_exact_path=str(q)))
m=json.loads((D/'curated-safe-manifest-v6.json').read_bytes())
for g,s,h in items:
 p=Path(s);b=p.read_bytes();assert sha(p)==h
 if p.suffix=='.json':scan(json.loads(b))
 q=D/(g+'--'+p.name);q.open('xb').write(b);q.chmod(0o644)
 m['rows'].append(dict(path=s,bytes=len(b),sha256=h,mode=oct(stat.S_IMODE(p.stat().st_mode)),group=g,content_class='SAFE_INDEPENDENT_SOURCE_OR_ACCEPTED_KNOWLEDGE_ONLY',proposed_successor_relative_path=str(q.relative_to(R)),copied_Git_mode='100644'))
 m['total']+=1;m['additional_exact_rows']+=1;m['total_bytes']+=len(b)
m['status']='CURATED_SAFE_SUCCESSOR_CURRENT_E2_NAMED_V7_BUDGET_ROLE_CORRECTION_REVIEW_REQUIRED_NO_COMMIT'
(D/'curated-safe-manifest-v7.json').open('x').write(json.dumps(m,indent=2)+'\n')
p=D/'OPERATOR.md';s=p.read_text();old='Worker600s/+10s, helper645s, transport660s/+10s, whole parent900s/+10s and\npre/post120s remain.';assert s.count(old)==1
s=s.replace(old,'Owned helper command600s with cleanup10s, Python envelope645s,\ngateway660s/TERM+KILL10s, ROOT outer900s/TERM+KILL10s and pre/post120s remain.')
s=s.replace('curated-safe-manifest-v6.json','curated-safe-manifest-v7.json').replace('manifest V6','manifest V7').replace('82 copied safe bodies / 676,197 bytes','84 copied safe bodies / 683,868 bytes')
s=s.replace('independent review is pending. Actual configuration assembly is HOLD;', 'independent SOURCE_ONLY review is GO. Actual configuration assembly is HOLD;')
s=s.replace('binds RED3 then172 service-free passes; independent source review is pending.', 'binds RED3 then172 service-free passes; its [independent SOURCE_ONLY review](V8_independent_source--OWNERFINAL-independent-private-current396925-V8-source-only-review.json)\nis GO and authorizes no actual configuration or execution.')
p.write_text(s)
p=R/'docs/handoffs/actions-swarm-mk3-20261011-current-engineering-successor.md';s=p.read_text().replace('curated-safe-manifest-v6.json','curated-safe-manifest-v7.json').replace('independent source review and actual configuration assembly remain pending.', 'independent SOURCE_ONLY review is GO while actual configuration assembly remains HOLD.');p.write_text(s)
p=R/'docs/skills/repository-operations.md';s=p.read_text();anchor='equivalence, and a rejected home proves no publication, Action or lease result.\n';assert s.count(anchor)==1
patch=Path(items[1][1]).read_text();paragraph='\n'.join(x[1:] for x in patch.splitlines() if x.startswith('+') and not x.startswith('+++')).strip();assert paragraph not in s
p.write_text(s.replace(anchor,anchor+'\n'+paragraph+'\n'))
(O/'named-V3-budget-role-and-bounded-V8-disposition.json').open('x').write(json.dumps(dict(previous_OWNERFINAL_sha256='dfbce09183900e236f5011c109ed8c2ef8acd6df60897718f86a7cde074da506',previous_original_documents_retained=preserved,change_scope='Exact budget-role labels and two bounded accepted V8 bodies plus five-line/blank canonical knowledge; no budget, code, command, source or actual change.',required_role_labels='Owned helper command600s cleanup10s; Python envelope645s; gateway660s TERM/KILL10s; ROOT outer900s TERM/KILL10s',source_authority='ROOT reviewed actual_transport_v8.py line163 timeout_seconds600',V8_scope='SOURCE_ONLY independent GO; actual config/qualification/release still HOLD',canonical_delta='Exact accepted current-source intentional-disposal context; earlier rawlease preservation paragraph remains, no duplicate entire paragraph.',source_or_test_execution='NOT_RUN'),indent=2)+'\n')
print(json.dumps(dict(rows=m['total'],bytes=m['total_bytes'],commit='NOT_RUN')))
