import ast,hashlib,json,os,pathlib,stat,subprocess,xml.etree.ElementTree as ET
P=pathlib.Path('/workspace/engineering/completed8d49-five-root-storage-PREPARATION-v4');R=pathlib.Path('/workspace/engineering/completed8d49-five-root-storage-independent-review');owner=P/'OWNERFINAL-five-completed8d49-roots-capped-storage-PREEXECUTION-v4.json';d=json.loads(owner.read_bytes())
def digest(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=pathlib.Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 return dict(path=str(p),bytes=s.st_size,sha256=digest(p),mode=oct(stat.S_IMODE(s.st_mode)))
checked=[]
def check(r):
 assert bind(r['path'])==r
 checked.append(r)
assert bind(owner)==dict(path=str(owner),bytes=22172,sha256='a1333777200edeaf0320f437c946e9df15e2e6ce6a3c61a976838d7b9b088b2e',mode='0o400')
for r in d['private_references']:check(r)
assert len(checked)==50
s=json.loads((P/'private-five-root-input-supplement.json').read_bytes());check(s['base_config_binding']);c=json.loads(pathlib.Path(s['base_config_binding']['path']).read_bytes());c['roots']['original27-log']=c['roots'].pop('robocorp-log');c['selected_snapshots']['original27-log']=c['selected_snapshots'].pop('robocorp-log')
for k,v in s['added_roots'].items():c['roots'][k]=v['path'];c['selected_snapshots'][k]=v['snapshot']
assert c['roots']==d['five_selected_roots'] and len(c['roots'])==len(set(c['roots'].values()))==5
for r in c['completion_bindings']+s['completion_bindings']:check(r)
def defs(path):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(pathlib.Path(path).read_bytes()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
old=defs('/workspace/engineering/completed8d49-four-root-storage-PREPARATION-v2/archive_exact_four_completed_roots_once.py');new=defs(P/'archive_exact_five_completed_roots_once.py');same=[n for n in old if old[n]==new[n]];changed=[n for n in old if old[n]!=new[n]]
assert len(old)==19 and len(same)==17 and changed==['load_config','_completion_admitted']
assert set(new)-set(old)=={'_fifth_completion','_durable_fixed_aliases_before_any_removal'}
a=ast.parse(pathlib.Path('/workspace/engineering/completed8d49-four-root-storage-PREPARATION-v2/archive_exact_four_completed_roots_once.py').read_bytes());b=ast.parse((P/'archive_exact_five_completed_roots_once.py').read_bytes())
loops=lambda t:[ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,ast.For)]
assert loops(a)==loops(b)
def snapshot(root):
 entries={};identities={};groups={};allocated=root.lstat().st_blocks*512
 for p in sorted(root.rglob('*')):
  t=p.lstat();allocated+=t.st_blocks*512;e=dict(mode=stat.S_IMODE(t.st_mode),mtime_ns=t.st_mtime_ns,uid=t.st_uid,gid=t.st_gid);r=str(p.relative_to(root));identities[r]=[t.st_dev,t.st_ino,t.st_nlink]
  if stat.S_ISREG(t.st_mode):e.update(kind='file',bytes=t.st_size,sha256=digest(p));groups.setdefault((t.st_dev,t.st_ino),[]).append(r)
  elif stat.S_ISDIR(t.st_mode):e.update(kind='directory')
  elif stat.S_ISLNK(t.st_mode):e.update(kind='symlink',target=os.readlink(p))
  elif stat.S_ISFIFO(t.st_mode):e.update(kind='fifo')
  else:raise AssertionError('UNARCHIVABLE_TYPE')
  entries[r]=e
 for g in groups.values():assert all(identities[r][2]==len(g) for r in g)
 t=root.lstat();ri={k:getattr(t,'st_'+k) for k in ('uid','gid','mtime_ns','dev','ino','nlink')};ri['mode']=stat.S_IMODE(t.st_mode)
 return dict(root=ri,entries=entries,identities=identities),allocated
measured={};count=allocated=0
for k,p in c['roots'].items():
 root=pathlib.Path(p);assert root.is_dir() and not root.is_symlink();v,n=snapshot(root);assert v=={k:x for k,x in c['selected_snapshots'][k].items() if k in ('root','entries','identities')};count+=len(v['entries']);allocated+=n;measured[k]=dict(members=len(v['entries']),allocated=n,snapshot_equal=True,external_hardlinks=0)
assert count==9035 and allocated==294944768
plan=json.loads((P/'private-fixed-nine-original-row-future-archive-member-plan.json').read_bytes());check(plan['original_inventory_binding']);iv=json.loads(pathlib.Path(plan['original_inventory_binding']['path']).read_bytes());assert len(iv['files'])==18 and len(plan['aliases'])==9
fifth=c['selected_snapshots']['Runtime50-robot-output'];root=pathlib.Path(plan['original_root']);assert root==pathlib.Path(c['roots']['Runtime50-robot-output']);assert plan['expected_root_metadata']==fifth['root']
for x in plan['aliases']:
 row=x['original_row'];assert row in iv['files'];check(row);rel=str(pathlib.Path(row['path']).relative_to(root));assert x['member']==plan['archive_label']+'/'+rel and x['expected_member_metadata']==fifth['entries'][rel]
assert len({x['member'] for x in plan['aliases']})==9
assert not pathlib.Path(plan['mapping_path']).exists()
f=s['fifth_completion'];check(f['terminal']);check(f['outer_terminal']);check(f['candidate']);check(f['junit']);t=json.loads(pathlib.Path(f['terminal']['path']).read_bytes());u=json.loads(pathlib.Path(f['outer_terminal']['path']).read_bytes());assert t['returncode']==u['returncode']==0 and t['post_bindings']=='PASS'
cases=ET.parse(f['junit']['path']).getroot().findall('.//testcase');assert len(cases)==50 and len({(x.get('classname'),x.get('name')) for x in cases})==50 and all(not list(x) for x in cases)
assert '--robocorp-log-output='+str(root) in json.loads(pathlib.Path(f['candidate']['path']).read_bytes())['exact_argv']
q=json.loads(pathlib.Path(s['qualified_current_config_binding']['path']).read_bytes());o=json.loads(pathlib.Path('/workspace/engineering/rcc-compatibility-actual-runner-readonly-preparation/FROZEN-three-version-source-and-artifact-config-v2.json').read_bytes()) if False else None
oldconfig=pathlib.Path('/workspace/engineering/completed8d49-four-root-storage-PREPARATION-v2/OWNERFINAL-readonly-active-a209cc-config-and-all-critical-row-overlap-supplement.json');oc=json.loads(oldconfig.read_bytes());check(oc['original237_config_binding_verified']);o=json.loads(pathlib.Path(oc['original237_config_binding_verified']['path']).read_bytes())
rows=[]
def collect(v):
 if isinstance(v,dict):
  if isinstance(v.get('path'),str) and pathlib.Path(v['path']).is_absolute() and ('sha256'in v or 'bytes'in v):rows.append(pathlib.Path(v['path']))
  for x in v.values():collect(x)
 elif isinstance(v,list):
  for x in v:collect(x)
collect(q);assert len(rows)==304
rows += [pathlib.Path(x['path']) for x in o['bindings']];rows += [pathlib.Path(q['source_root'])/x for x in q['prepared_inputs']];rows += [pathlib.Path(q['native_original_root'])/x['path'] for x in q['native_original_members']];rows += [pathlib.Path(q['source_root'])/x['path'] for x in q['source_body_modes']];assert len(rows)==3203
roots=[pathlib.Path(p) for p in c['roots'].values()]
for p in rows:
 assert all(p!=r and r not in p.parents and p.resolve()!=r.resolve() and r.resolve() not in p.resolve().parents for r in roots)
for name,h in q['prepared_inputs'].items():assert digest(pathlib.Path(q['source_root'])/name)==h
# Original probe evidence and exact captured output classification; no guard replay.
pr=json.loads(pathlib.Path('/workspace/engineering/completed8d49-four-root-storage-PREPARATION-v3/OWNERFINAL-one-corrected-managed-Poetry-durable-capture-readonly-guard-PASS.json').read_bytes())
for row in pr['private_references']:check(row)
assert pr['returncode']==0 and pr['actual_checks']['metadata_stdout_bytes']==2258 and pr['archive']==pr['native']=='NOT_RUN' and pr['original_storage_nested_cause']=='UNKNOWN_UNAVAILABLE_CAPTURE_DISCARDED'
# Check only current source identity and clean status (no write-tree or source execution).
env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'}
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',q['source_root'],*args],env=env)
assert git('rev-parse','HEAD').decode().strip()==d['source_head'];assert git('rev-parse','HEAD^{tree}').decode().strip()==d['source_tree'];assert git('status','--porcelain')==b''
assert len(git('ls-tree','-rz','--full-tree','HEAD').split(b'\0'))-1==1440
for p in ['/workspace/engineering/root-completed8d49-five-root-storage-one-owned-v4','/tmp/actions-completed8d49-five-root-preserved-v4','/tmp/actions-completed8d49-five-root-preservation-stage-v4']:assert not pathlib.Path(p).exists()
# Accessible handle census is explicitly limited; unreadable/raced observations are UNKNOWN.
links=unknown=matches=0
for proc in pathlib.Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 candidates=[proc/'cwd']
 try:candidates+=list((proc/'fd').iterdir())
 except (OSError,PermissionError):unknown+=1
 for link in candidates:
  try:target=os.readlink(link)
  except OSError:unknown+=1;continue
  links+=1
  if any(target==str(r) or target.startswith(str(r)+'/') for r in roots):matches+=1
assert matches==0
proof=dict(schema='INDEPENDENT_FIVE_ROOT_READONLY_STATIC_AND_CURRENT_SNAPSHOT_PROOF',proposal_binding=bind(owner),checked_reference_rows=len(checked),owner_reference_rows=50,exact_original_core_AST=same,changed_adapters=changed,new_definitions=sorted(set(new)-set(old)),removal_loop_AST_exact=True,selected_root_summary=measured,selected_members=count,selected_allocated_bytes=allocated,unchanged_original_inventory_rows=18,fixed_original_row_aliases=9,completion_JUnit_50_unique_PASS=True,active_critical_paths_outside_selected_roots=3203,prepared30_rehashed=True,source=d['source_head'],tree=d['source_tree'],source1440_clean=True,corrected_probe_pass_only=True,handle_observation=dict(accessible_links=links,unreadable_or_raced=unknown,selected_matches=matches,universal_quiescence='UNKNOWN'),operation='NOT_RUN',native='NOT_RUN',fresh_capacity_snapshot={x:os.statvfs(x).f_bavail*os.statvfs(x).f_frsize for x in ['/workspace','/tmp','/dev/shm']})
out=R/'independent-five-root-source-alias-completion-and-current-snapshot-proof.json';out.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');out.chmod(0o400);print(json.dumps(dict(proof_binding=bind(out),verified=True)))
