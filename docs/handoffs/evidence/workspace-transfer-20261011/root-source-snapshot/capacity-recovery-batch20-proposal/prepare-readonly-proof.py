import ast,hashlib,json,os,pathlib,stat,subprocess,time
from collections import defaultdict
P=pathlib.Path;D=P('/workspace/engineering/capacity-recovery-batch20-proposal');started=time.monotonic();BASE=P('/workspace/actions-cloud/robocorp/temp');NAMES=['6bb7d57b503d838a','9710d7e7a03133a6'];refs=[]
def sha(p):
 h=hashlib.sha256()
 with P(p).open('rb') as f:
  for z in iter(lambda:f.read(1048576),b''):h.update(z)
 return h.hexdigest()
def bind(p):p=P(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def check(r):assert bind(r['path'])=={k:r[k] for k in ('path','bytes','sha256')};refs.append({**bind(r['path']),'current_mode':oct(stat.S_IMODE(P(r['path']).stat().st_mode))});return r
def load(p):return json.loads(P(p).read_bytes())
script=P('/tmp/actions-capacity-recovery-batch20.py');assert sha(script)=='9ce2004405202512c6a6d1f0ca3b0c55bb201a18f548d490b7db82765458c6cc';assert not P('/dev/shm/actions-completed-scratch-recovery-batch20').exists() and not P('/tmp/actions-completed-scratch-recovery-batch20-stage').exists()
# Only a fresh metadata/accessible-handle observation. Full before-removal inventory stays deferred to root execution.
process_count=0;link_count=0;unobserved=0;observed_live=0
for proc in P('/proc').iterdir():
 if not proc.name.isdigit():continue
 process_count+=1;links=[proc/'cwd']
 try:links.extend((proc/'fd').iterdir())
 except (FileNotFoundError,PermissionError,OSError):unobserved+=1
 for link in links:
  try:target=os.readlink(link);link_count+=1
  except (FileNotFoundError,PermissionError,OSError):unobserved+=1;continue
  if any(target==str(BASE/n) or target.startswith(str(BASE/n)+'/') for n in NAMES):observed_live+=1
assert observed_live==0
candidate=[]
for n in NAMES:
 root=BASE/n;assert root.is_dir() and not root.is_symlink() and (root/'recycle.now').read_text().strip()=='True';counts={'file':0,'directory':0,'symlink':0,'fifo':0};total=0
 for p in root.rglob('*'):
  s=p.lstat()
  if stat.S_ISREG(s.st_mode):counts['file']+=1;total+=s.st_size
  elif stat.S_ISDIR(s.st_mode):counts['directory']+=1
  elif stat.S_ISLNK(s.st_mode):counts['symlink']+=1
  elif stat.S_ISFIFO(s.st_mode):counts['fifo']+=1
  else:raise AssertionError('UNAPPROVED_CANDIDATE_TYPE')
 candidate.append({'namespace_allowlist':n,'marker_True':True,'marker_sha256':sha(root/'recycle.now'),'observed_member_types':counts,'logical_regular_file_bytes':total,'full_inventory_content_baseline':'DEFERRED_TO_ROOT_ONE_EXECUTION_NOT_MEASURED_BY_PREPARATION'})
# Rehash the accepted prior archive/index chain without expanding or streaming member payloads.
prior16=load('/workspace/engineering/capacity-recovery-batch16-independent-review/OWNERFINAL-independent-batch16-preservation-review.json');check(prior16['independent_prior_reference_proof']);pr=load(prior16['independent_prior_reference_proof']['path']);summaries=pr['prior15_safe_summary_bindings_exact']+[prior16['owner_safe']]
for n in [17,18]:summaries.append(bind(f'/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch{n}.json'))
archives=0;indices=0
for row in summaries:
 check(row);x=load(row['path']);idx=x.get('private_inventory_binding',x.get('complete_private_inventory'));check(idx);assert stat.S_IMODE(P(idx['path']).stat().st_mode)==0o600;indices+=1
 for ar in x.get('archives',x.get('recovery_records')):
  p=P(ar['archive']);assert not p.is_symlink() and stat.S_IMODE(p.stat().st_mode)==0o600 and p.stat().st_size==ar['archive_bytes'] and sha(p)==ar['archive_sha256'];refs.append({**bind(p),'current_mode':'0o600'});archives+=1
for row in pr['prior_review_bindings_exact']:check(row)
for n in [16,17,18]:
 q=P(f'/workspace/engineering/capacity-recovery-batch{n}-independent-review/OWNERFINAL-independent-batch{n}-preservation-review.json');qr=load(q)
 for key in ['owner_safe','independent_archive_stream_proof','independent_prior_reference_proof','current_Linux_v5_preservation','safe_owner','independent_proof']:
  if key in qr:check(qr[key])
safe=P('/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch19.json');assert sha(safe)=='6b7998bff1c7c0b2ccada06452c6e7eabae4c20c47b5027331f0b16fbda3377a';s=load(safe);check(s['private_complete_inventory']);check(s['archive']);assert stat.S_IMODE(P(s['archive']['path']).stat().st_mode)==0o600;archives+=1;indices+=1;assert archives==40 and indices==19
prior19=P('/workspace/engineering/capacity-recovery-batch19-independent-review/OWNERFINAL-independent-batch19-preservation-review.json');assert sha(prior19)=='808d0fbb4efbcb6207566cc7deed6b11964c6ed3a063ece20b11936d1767a884';refs.extend([bind(safe),bind(prior19)])
check(pr['V5runner_09cdc_exact']);assert pr['V5runner_09cdc_exact']['sha256']=='09cdc6b19f5d3d9cc94fadca23373108868521e0378d33960146b1a8522e88ad';consumer=load(prior16['current_Linux_v5_preservation']['path'])
for key in ['owner','independent_actual','preexecution_owner']:check(consumer[key])
for row in consumer['original_actual_measurement_bindings']+consumer['preexecution_refs']:check(row)
failed=list(BASE.glob('563d*'));assert len(failed)==1 and failed[0].is_dir()
# Entire accepted relocated default-cache416 preservation, pure helper definitions only.
cache_script=P('/workspace/engineering/root-failed300-default-cache-independent-actual-review/verify-readonly-actual.py');tree=ast.parse(cache_script.read_bytes());helpers=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'info','inventory','norm','partition'}];assert len(helpers)==4;ns={'Path':P,'stat':stat,'os':os,'sha':sha,'defaultdict':defaultdict};exec(compile(ast.Module(body=helpers,type_ignores=[]),str(cache_script)+':readonly-functions-only','exec'),ns)
cache_owner=load('/workspace/engineering/root-failed300-default-cache-preservation-actual/OWNERFINAL-root-whole-default-cache-preservation-actual.json');check(cache_owner['private_complete_inventories']);old=load(cache_owner['private_complete_inventories']['path'])['frozen_original'];dest=P(cache_owner['physical_destination']);source=P('/home/agent/.robocorp/pkgs');assert source.is_symlink() and os.readlink(source)==str(dest);current=ns['inventory'](dest);assert ns['norm'](current)==ns['norm'](old) and ns['partition'](current)==ns['partition'](old)==[] and len(current['entries'])==416
# Rehash accepted source guard bindings; do not run any launcher/test/application import while cleanup full is active.
cleanup=load('/workspace/engineering/captured-child-cleanup-configured-full-proposal/OWNERFINAL-cleanup499-managed-activation-configured-full-proposal-v2.json')
for row in cleanup['bindings']:check(row)
light=load('/workspace/engineering/captured-child-cleanup-light-owned/OWNERFINAL-captured-child-cleanup-LIGHT-source-checkpoint-v2.json')
for row in light['bindings']:check(row)
original=load('/workspace/engineering/pr306-original-cleanup-deterministic-control-owned/OWNERFINAL-original-cleanup-deterministic-control-v2.json')
for row in original['bindings']:check(row)
proof=load('/workspace/engineering/captured-child-cleanup-independent-LIGHT-review/complete1422-independent-current-source-body-mode-proof-v2.json');R=P('/workspace/engineering/captured-child-cleanup');assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()==cleanup['head'] and not subprocess.check_output(['git','-C',str(R),'status','--porcelain'])
for row in proof['entries']:
 p=R/row['path'];data=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes();assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'];assert row['mode']=='120000' or bool(p.stat().st_mode&0o111)==(row['mode']=='100755')
native=P('/workspace/engineering/pr310-runner-qualification-owned');inv=load(native/'output/native-artifact-tree-inventory.json');assert len(inv)==1192;assert {p.relative_to(native/'dist/action-server').as_posix() for p in (native/'dist/action-server').rglob('*')}=={r['path'] for r in inv}
for row in inv:
 p=native/'dist/action-server'/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert sha(p)==row['content_sha256']
 elif row['kind']=='symlink':assert os.readlink(p)==row['link_target'] and sha(p)==row['content_sha256']
 else:assert p.is_dir() and not p.is_symlink()
for row in load('/workspace/actions-cloud/receipts/pr305-runner/frozen-helper-bindings.json').values():assert sha(row['snapshot_path'])==row['sha256'] and stat.S_IMODE(P(row['snapshot_path']).stat().st_mode)==0o444
patch=check(pr['canonical7d070_exact_reuse']);paragraph=''.join(l[1:] for l in P(patch['path']).read_text().splitlines(keepends=True) if l.startswith('+') and not l.startswith('+++'));assert paragraph in P('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text()
private={'refs_current_bytes_modes':refs,'canonical':patch,'fresh_candidate_metadata':candidate,'fresh_accessible_handle_observation':{'processes':process_count,'links_read':link_count,'unobserved_permission_transient_links_or_FD_lists':unobserved,'candidate_live_cwd_FD_observed':observed_live},'prior_archives':archives,'prior_indices':indices,'default_cache_entries_exact':416,'native1192_full_exact':True,'cleanup_source1422_ref35_LIGHT67_original31_exact':True,'failed563d_existence_only':True,'script_PREPARED_NOT_EXECUTED':bind(script),'workspace_capacity_observation_bytes':os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize,'existing_shm_capacity_observation_bytes':os.statvfs('/dev/shm').f_bavail*os.statvfs('/dev/shm').f_frsize,'elapsed_seconds':round(time.monotonic()-started,3)}
p=D/'private-readonly-preparation-proof.json';assert not p.exists();p.write_text(json.dumps(private,indent=2)+'\n');p.chmod(0o600);print(json.dumps({'private_proof':bind(p),'status':'PREPARATION_ONLY_NO_ARCHIVE_REMOVAL_EXECUTION','prior_archives':archives,'prior_indices':indices,'candidate_types_counts':[{k:v for k,v in r.items() if k not in {'namespace_allowlist','marker_sha256'}} for r in candidate],'workspace_available_bytes':private['workspace_capacity_observation_bytes']}))
