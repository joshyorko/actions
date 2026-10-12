import json,hashlib,stat,tarfile,io,os
from pathlib import Path
O=Path(__file__).parent
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def binding(p):
 p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
p=Path('/workspace/engineering/rcc-current-e4ff-control3-actual-independent-review/OWNERFINAL-independent-original-current-e4ff-control3-cache-mode-actual-failure-review.json');owner=json.loads(p.read_text());rows=owner['original_files'];assert len(rows)==8
for r in rows:
 b=binding(r['path']);assert all(b[k]==r[k]for k in ('path','bytes','sha256','mode'))
mp=Path('/workspace/engineering/root-failed-control3-one-byte-preservation-v4/root-exact-historical-failed-member-archive-mapping.json');m=json.loads(mp.read_text());ret=[binding(mp),binding(p)]
for key in ('archive','complete_index','expanded_removal','root_original_terminal'):
 b=binding(m[key]['path']);assert all(b[k]==m[key][k]for k in ('bytes','sha256','mode'));ret.append(b)
matched=None
with tarfile.open(m['archive']['path'],'r|gz')as h:
 for t in h:
  if t.name==m['member']:
   raw=h.extractfile(t).read();assert len(raw)==m['original_binding']['bytes']and hashlib.sha256(raw).hexdigest()==m['original_binding']['sha256']
   assert (t.mode,t.uid,t.gid)==(0o600,m['member_uid'],m['member_gid']);matched={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'mode':t.mode,'uid':t.uid,'gid':t.gid,'status':json.loads(raw)['status']};break
assert matched and matched['status']=='FAIL'
assert not Path(m['original_binding']['path']).exists()
for r in rows:assert binding(r['path'])==r
out={'status':'READONLY_EXACT_EIGHT_FAILED2_AND_ORIGINAL_FAILED1_ALIAS_PRESERVED','original_failed2_owner':binding(p),'eight_original_failed2':rows,'failed1_mapping_and_complete_hash_bindings':ret,'failed1_selected_original_member':matched,'limits':'Selected member stream ends at its match, not a fresh all49132-member or gzipEOF proof; exact whole compressed SHA and original complete index retained. Failed2 eight original records verified, no fresh full failed-cache-tree body audit. No failure upgraded, no restoration/execution.'}
p=O/'private-original-failed2-eight-and-failed1-whole-archive-alias-retention.json';assert not p.exists();p.write_text(json.dumps(out,sort_keys=True,separators=(',',':'))+'\n');p.chmod(0o600)
print(json.dumps({'status':'SUPPLEMENT_PASS','bytes':p.stat().st_size,'sha256':sha(p),'failed2':8,'failed1_status':matched['status']}))
