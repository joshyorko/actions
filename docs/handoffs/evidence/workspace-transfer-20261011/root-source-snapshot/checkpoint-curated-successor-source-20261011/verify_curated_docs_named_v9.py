import json,hashlib,stat,re,subprocess,difflib
from pathlib import Path
O=Path(__file__).parent;R=Path('/workspace/engineering/campaign-checkpoint');D=R/'docs/program/evidence/wave11/current-engineering-successor-20261011'
def sh(b):return hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
def binding(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=sh(b),mode=oct(stat.S_IMODE(p.stat().st_mode)))
head=git('rev-parse','HEAD').decode().strip();assert head=='62f4e180f6c894777ebc8ed3a729e88d2f6531d6'
tree=git('rev-parse','HEAD^{tree}').decode().strip()
manifest=json.loads((D/'curated-safe-manifest-v7.json').read_bytes());assert manifest['total']==84 and manifest['total_bytes']==683868
privacy_fields=[]
def scan(x,k=''):
 if isinstance(x,dict):
  for a,b in x.items():scan(b,k+'.'+a)
 elif isinstance(x,list):
  for i,b in enumerate(x):scan(b,k+f'[{i}]')
 elif isinstance(x,str):
  assert not any(s in x for s in ('sig=','Bearer ','SharedAccessSignature=','AccountKey=')),k
for row in manifest['rows']:
 p=R/row['proposed_successor_relative_path'];b=p.read_bytes();assert len(b)==row['bytes'] and sh(b)==row['sha256']
 assert stat.S_IMODE(p.stat().st_mode)==0o644 and not p.is_symlink()
 if p.suffix=='.json':scan(json.loads(b))
for p in D.glob('*.json'):json.loads(p.read_bytes())
preserved=[]
for current,original in [('docs/skills/repository-operations.md','original-dirty-repository-operations.md'),('docs/skills/provenance-observability.md','original-dirty-provenance-observability.md'),('docs/program/engineering-handoff.md','original-engineering-handoff.md')]:
 a=(O/original).read_text().splitlines(keepends=True);b=(R/current).read_text().splitlines(keepends=True)
 it=iter(b);assert all(any(x==y for y in it) for x in a),current
 preserved.append(dict(path=current,original=binding(O/original),current=binding(R/current),all_original_lines_in_order=True,only_additions_relative_to_initial_dirty_snapshot=True))
allowed={r['path'] for r in preserved};unchanged=[];delta=[]
for entry in git('ls-tree','-rz','HEAD').split(b'\0'):
 if not entry:continue
 info,name=entry.split(b'\t');mode,typ,oid=info.decode().split();p=R/name.decode()
 assert p.exists() or p.is_symlink(),name
 b=p.readlink().as_posix().encode() if mode=='120000' else p.read_bytes()
 blob=git('cat-file','blob',oid)
 if name.decode() in allowed:delta.append(name.decode())
 else:
  assert b==blob,name
  if mode!='120000':assert bool(p.stat().st_mode&0o111)==(mode=='100755'),name
  unchanged.append(dict(path=name.decode(),git_mode=mode,git_blob=oid,bytes=len(b),sha256=sh(b)))
assert set(delta)==allowed
collector=Path('/workspace/engineering/checkpoint-current-engineering-after299-0938.py')
assert sh(collector.read_bytes())=='0319f50eaa81800c7edf3bc75b80182bbfc5721ba0ef86d45c199e3bc0a6d4d1'
authored=[D/'OPERATOR.md',R/'docs/handoffs/actions-swarm-mk3-20261011-current-engineering-successor.md',R/'docs/program/engineering-handoff.md',R/'docs/skills/repository-operations.md',R/'docs/skills/provenance-observability.md']
linkcount=0;historical_missing_links=[]
original_docs={"docs/skills/repository-operations.md":"original-dirty-repository-operations.md","docs/skills/provenance-observability.md":"original-dirty-provenance-observability.md","docs/program/engineering-handoff.md":"original-engineering-handoff.md"}
for p in authored:
 text=p.read_text()
 for dest in re.findall(r'\]\(([^\s)]+)\)',text):
  if dest.startswith(('http:','https:','#','mailto:')):continue
  q=(p.parent/dest.split('#')[0]).resolve()
  if not q.exists():
   original=original_docs.get(str(p.relative_to(R)))
   assert original and ']('+dest+')' in (O/original).read_text(),(str(p),dest)
   historical_missing_links.append(dict(path=str(p.relative_to(R)),target=dest,scope='EXISTED_IN_ORIGINAL_SNAPSHOT_NOT_CHANGED'))
  else:linkcount+=1
subprocess.run(['git','-C',str(R),'diff','--check'],check=True,capture_output=True)
untracked=[x.decode() for x in git('ls-files','--others','--exclude-standard','-z').split(b'\0') if x]
assert all(x.startswith('docs/program/evidence/wave11/current-engineering-successor-20261011/') or x=='docs/handoffs/actions-swarm-mk3-20261011-current-engineering-successor.md' for x in untracked)
proof=dict(schema=1,status='DOCS_PREPARATION_REVIEW_REQUIRED_NO_COMMIT',head=head,tree=tree,tracked_count=len(unchanged)+len(delta),nonowned_tracked_body_and_Git_mode_exact=len(unchanged),owned_tracked_paths=delta,initial_dirty_work_preservation=preserved,all_copied_originals_exact_count=84,all_copied_originals_exact_bytes=683868,JSON_parse='PASS',signed_URL_or_credential_payload_scan='PASS',referenced_private_payloads_copied=False,authored_local_links_verified=linkcount,historical_missing_links=historical_missing_links,diff_whitespace='PASS',untracked_doc_file_count=len(untracked),collector=binding(collector),old_manifest1180_and_graph='ALL_TRACKED_NONOWNED_EXACT_NO_COLLECTOR_EXECUTION',native_gateway_tests_install_archive_remove_push_commit='NOT_RUN',named_current_target='e2c81adce7858d5a952991ba9a8b7f72e902038a',upstream='NO_NEW_POSTS_EXISTING_AUTHORIZED_COORDINATION_RETAINED')
(O/'private-complete-existing-tracked-body-mode-proof-v9.json').open('x').write(json.dumps(unchanged,indent=2)+'\n')
(O/'safe-current-curated-docs-verification-v9.json').open('x').write(json.dumps(proof,indent=2)+'\n')
print(json.dumps({k:proof[k] for k in ['status','tracked_count','nonowned_tracked_body_and_Git_mode_exact','all_copied_originals_exact_count','all_copied_originals_exact_bytes','authored_local_links_verified','untracked_doc_file_count']}))
