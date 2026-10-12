import hashlib,json,stat
from pathlib import Path
O=Path(__file__).parent
R=Path('/workspace/engineering/campaign-checkpoint')
D=R/'docs/program/evidence/wave11/current-engineering-successor-20261011'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
items=[
('windows282','/workspace/engineering/pr282-original1299-one-Windows-log-acquisition/safe-original-acquisition-receipt.json','608725602ee59e1edeac7b854dc10ab5127bbb2cebab5a5f5fa0b17864c293e1'),
('canvas282repair','/workspace/engineering/pr282-current1299-one-original-Canvas-artifact/OWNERFINAL-root-distinct-current1299-Canvas-artifact-connector-repair-result.json','f7761a118ba6c1d34ba679b0146794b07074cd3ee79e5cc1fc71866ab504d496'),
('pytest38ind','/workspace/engineering/pytest38-vanished-numbered-retention-independent-review/OWNERFINAL-independent-vanished-pytest38-retention-reconciliation-and-source-HOLD-v2.json','2406370ad9a0263d4bdc45c2c246fe314101517cb4c970245edcba02ff9f85c6'),
('pytest38canonical','/workspace/engineering/pytest38-vanished-numbered-retention-independent-review/canonical-isolated-pytest-basetemp-preservation-proposed.md','2158066419dd6fa2ff354ad6480bacef83a685bfafb75b2c1464eb917461b8c8'),
('source308fullind','/workspace/engineering/pr308-current396925-independent-SOURCEFULL-preexecution-review/OWNERFINAL-independent-current396925-managed-isolated-SOURCEFULL-v2-static-preexecution-review-successor.json','575e0a070e3d50e942dec80cba8ca8caa8d1083a19839e14ddd12b2878e979e8'),
('source308fullv2','/workspace/engineering/pr308-native-home-mode-current-a54-SOURCEFULL-preexecution/OWNERFINAL-current396925-managed-configured-SOURCEFULL-preexecution-proposal-v2.json','b9f857ef1305bcd906dd9afe6630a75e913fd2d74a6a6a5d675a535eba0b154c'),
('capacity28prep','/workspace/engineering/capacity-recovery-batch28-proposal-v2/OWNERFINAL-B28-v2-exact34-completed-400MiB-metadata-storage-preservation-PROPOSAL.json','e4ed89f2fab5d0749c6232e45b9969feb34b1cb658b3d9806beb42b0efce6ada'),
('capacity28relocation','/workspace/engineering/capacity-recovery-batch28-proposal-v2/OWNERFINAL-after-B28-v2-one-exact-original-TMP-archive-relocation-PREPARATION.json','4e725dccaa72bd49079444bc0990dc7ff4919ade0ad535a316d2a69080fb8980'),
]
m=json.loads((D/'curated-safe-manifest-v2.json').read_bytes())
def inspect(x,k=''):
 if isinstance(x,dict):
  for a,b in x.items():inspect(b,k+'.'+a)
 elif isinstance(x,list):
  for i,b in enumerate(x):inspect(b,k+f'[{i}]')
 elif isinstance(x,str):
  assert not any(s in x for s in ('https://','http://','Bearer ','sig=')),k
for group,s,digest in items:
 p=Path(s);b=p.read_bytes();assert sha(p)==digest
 if p.suffix=='.json':inspect(json.loads(b))
 q=D/(group+'--'+p.name);q.open('xb').write(b);q.chmod(0o644)
 m['rows'].append(dict(path=s,bytes=len(b),sha256=digest,mode=oct(stat.S_IMODE(p.stat().st_mode)),group=group,content_class='SAFE_OWNER_OR_ACCEPTED_CANONICAL_ONLY_NO_REFERENCED_PAYLOAD_COPY',proposed_successor_relative_path=str(q.relative_to(R)),copied_Git_mode='100644'))
 m['total']+=1;m['additional_exact_rows']+=1;m['total_bytes']+=len(b)
m['status']='CURATED_SAFE_SUCCESSOR_NAMED_V3_REVIEW_REQUIRED_NOT_COMMITTED'
(D/'curated-safe-manifest-v3.json').open('x').write(json.dumps(m,indent=2)+'\n')
ops=R/'docs/skills/repository-operations.md';old=ops.read_text();(O/'pre-v3-repository-operations.md').open('x').write(old)
patch=(Path('/workspace/engineering/pytest38-completed-preservation-private-source')/'canonical-pytest-retention-evidence-root-protection-proposed.patch').read_text()
paragraph='\n'.join(x[1:] for x in patch.splitlines() if x.startswith('+') and not x.startswith('+++'))
assert old.count(paragraph)==1
replacement=Path(items[3][1]).read_text().strip()
ops.write_text(old.replace(paragraph,replacement))
(O/'canonical-retention-v3-disposition.json').open('x').write(json.dumps(dict(status='REFINE_NEWLY_INSERTED_PARAGRAPH_ONLY',original_dirty_preserved=True,old_patch_sha256=sha(Path('/workspace/engineering/pytest38-completed-preservation-private-source/canonical-pytest-retention-evidence-root-protection-proposed.patch')),successor_sha256=items[3][2],evidence=items[2][1],durable_learning='Unique absent per-invocation basetemp; policy all; existing explicit targets removed; policy none increases deletion; observed root loss is not proven process attribution.'),indent=2)+'\n')
for f in [D/'OPERATOR.md',R/'docs/handoffs/actions-swarm-mk3-20261011-current-engineering-successor.md']:
 (O/('pre-v3-'+f.name)).open('xb').write(f.read_bytes())
print(json.dumps(dict(rows=m['total'],body_bytes=m['total_bytes'],new_safe_copies=len(items),commit='NOT_RUN')))
