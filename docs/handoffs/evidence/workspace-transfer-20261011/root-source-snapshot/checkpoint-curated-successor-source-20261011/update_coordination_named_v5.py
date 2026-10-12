import json,hashlib,stat
from pathlib import Path
O=Path(__file__).parent;R=Path('/workspace/engineering/campaign-checkpoint');D=R/'docs/program/evidence/wave11/current-engineering-successor-20261011'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
items=[('V8_source_pending','/workspace/engineering/rcc-current396925-private-V8-source-only/OWNERFINAL-private-current396925-V8-minimal-mode-and-source-context-SOURCE_ONLY-v2.json','db4d3729943cd7c71ada8e1b0430bf61886a5ad8522ff076a8cf525e63e9dd06'),('existing_coordination','/workspace/engineering/after282-current-engineering-body-preservation/OWNERFINAL-after282-existing-engineering-body-preservation.json','c174687676f2fd1d9f4473148e0f8cdffeee9dc079449e849676680112452bc8'),('existing_graph','/workspace/engineering/after282-current-engineering-body-preservation/OWNERFINAL-named-exact-101-prior-prefix-and-graph-suffix-preservation.json','229d2f9dc8a451569bc7fd7b903d3809d524e89e5c0ac317f6c9a286c0a1907a'),('aggregate_connector_PREP','/workspace/engineering/pr221-currenta54-connector-original-aggregate-acquisition-successor-preparation/OWNERFINAL-metadata-only-currenta54-one-connector-aggregate-acquisition-successor-preparation.json','c3ad79fc74fb8a07477d142d6685d841bd5a26848cf446b6cbf69dd892897b27')]
def scan(x):
 if isinstance(x,dict):
  for b in x.values():scan(b)
 elif isinstance(x,list):
  for b in x:scan(b)
 elif isinstance(x,str):assert not any(s in x for s in ['http://','https://','Bearer ','sig='])
m=json.loads((D/'curated-safe-manifest-v4.json').read_bytes())
for g,s,h in items:
 p=Path(s);b=p.read_bytes();assert sha(p)==h;scan(json.loads(b));q=D/(g+'--'+p.name);q.open('xb').write(b);q.chmod(0o644)
 m['rows'].append(dict(path=s,bytes=len(b),sha256=h,mode=oct(stat.S_IMODE(p.stat().st_mode)),group=g,content_class='SAFE_SCOPE_AND_PROVENANCE_METADATA_NO_REFERENCED_PAYLOAD_COPY',proposed_successor_relative_path=str(q.relative_to(R)),copied_Git_mode='100644'))
 m['total']+=1;m['additional_exact_rows']+=1;m['total_bytes']+=len(b)
m['status']='CURATED_SAFE_SUCCESSOR_CURRENT_E2_NAMED_V5_REVIEW_REQUIRED_NO_COMMIT'
(D/'curated-safe-manifest-v5.json').open('x').write(json.dumps(m,indent=2)+'\n')
p=D/'OPERATOR.md';s=p.read_text();(O/'pre-v5-OPERATOR.md').open('x').write(s)
s=s.replace('current safe manifest V4](curated-safe-manifest-v4.json)','current safe manifest V5](curated-safe-manifest-v5.json)').replace('named manifest V4](curated-safe-manifest-v4.json)','named manifest V5](curated-safe-manifest-v5.json)').replace('76 copied safe bodies / 631,497 bytes','80 copied safe bodies / 663,108 bytes')
s=s.replace('Private V8 has 172 service-free PASS announced, but its source packet is pending; no configuration or native attempt is frozen/admitted.', 'Private V8 source-only V2 is frozen with original RED3 and 172 PASS / 0 FAIL / 0 ERROR / 0 SKIP; independent review is pending. Actual configuration assembly is HOLD; no native attempt is admitted.')
s=s.replace('The announced 172 service-free V8 passes do not establish a\nfrozen runner or native result.', 'The [frozen private V8 source-only V2 owner](V8_source_pending--OWNERFINAL-private-current396925-V8-minimal-mode-and-source-context-SOURCE_ONLY-v2.json)\nbinds RED3 then172 service-free passes; independent source review is pending.\nIts source template is frozen, but actual config assembly remains HOLD and no\nnative result is established.')
s=s.replace('a named connector-client successor may be necessary after the\nseparate tiny-Canvas CLI Forbidden observation.', 'a [named metadata-only connector preparation](aggregate_connector_PREP--OWNERFINAL-metadata-only-currenta54-one-connector-aggregate-acquisition-successor-preparation.json)\nnow exists, without executor or acquisition. The older aggregate Git CLI\npreparation was NOT_RUN, not a failed acquisition. The separate tiny-Canvas\nCLI Forbidden observation belongs to another artifact.')
s=s.replace('The original 54-contract graph remains unchanged:', 'The [named existing coordination preservation](existing_coordination--OWNERFINAL-after282-existing-engineering-body-preservation.json)\nand [exact101 prefix/graph clarification](existing_graph--OWNERFINAL-named-exact-101-prior-prefix-and-graph-suffix-preservation.json)\nbind the existing engineering body updates to actuale2: all earlier221 body bytes\nare retained, while101 retains its exact prefix and 28,075-byte graph suffix\n(SHA256 `d6aa504c67bb72508006751c65d0d575d2e108a1ae3f677034723ee8101843b7`)\ninside the new wrapper; the old101 body is not contiguous. No raw issue body was\ncopied or graph regenerated here. The original 54-contract graph remains unchanged:')
p.write_text(s)
p=R/'docs/handoffs/actions-swarm-mk3-20261011-current-engineering-successor.md';s=p.read_text().replace('curated-safe-manifest-v4.json','curated-safe-manifest-v5.json').replace('Private V8 has only 172 service-free controls announced; its source packet and\nactual configuration remain pending.', 'Private V8 source-only V2 is frozen with RED3 then172 service-free passes;\nindependent source review and actual configuration assembly remain pending.');p.write_text(s)
print(json.dumps(dict(rows=m['total'],bytes=m['total_bytes'],commit='NOT_RUN')))
