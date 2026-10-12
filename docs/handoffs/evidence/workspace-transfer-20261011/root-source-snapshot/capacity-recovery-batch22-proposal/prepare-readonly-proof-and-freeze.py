import ast,hashlib,json,os,pathlib,stat,time
from collections import defaultdict
P=pathlib.Path;D=P('/workspace/engineering/capacity-recovery-batch22-proposal');BASE=P('/workspace/actions-cloud/robocorp/temp');NAMES=['4acee51ce3429595','2c405a41e228d221','c238a9a71300c7d0','e598ad78e01f5cad','b83d4d87cb9a91b0'];start=time.monotonic()
def sha(p):
 h=hashlib.sha256()
 with P(p).open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
def b(p):p=P(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
parent=P('/tmp/actions-capacity-recovery-batch19.py');assert b(parent)['bytes']==5244 and sha(parent)=='48fd7e4c79e55b80ceda0b63c1d1da87feeb368cefee265d5c12bad6ad940840';original=parent.read_text();code=original.replace("DEST = Path('/dev/shm/actions-completed-scratch-recovery-batch19')","DEST = Path('/dev/shm/actions-completed-scratch-recovery-batch22')").replace("STAGE = Path('/tmp/actions-completed-scratch-recovery-batch19-stage')","STAGE = Path('/tmp/actions-completed-scratch-recovery-batch22-stage')").replace("NAMES = ['c3b676a701cf3ae2']",'NAMES = '+repr(NAMES))
def norm(s):
 t=ast.parse(s);n=0;c=set()
 for x in t.body:
  if isinstance(x,ast.Assign) and len(x.targets)==1 and isinstance(x.targets[0],ast.Name) and x.targets[0].id in {'DEST','STAGE','NAMES'}:c.add(x.targets[0].id);x.value=ast.Constant('CONFIG_ONLY')
  else:n+=1
 return ast.dump(t,include_attributes=False),n,c
assert norm(code)==norm(original) and norm(code)[1]==16
script=P('/tmp/actions-capacity-recovery-batch22.py');assert not script.exists();script.write_text(code);script.chmod(0o600);assert not P('/dev/shm/actions-completed-scratch-recovery-batch22').exists() and not P('/tmp/actions-completed-scratch-recovery-batch22-stage').exists()
processes=links=gaps=live=0
for proc in P('/proc').iterdir():
 if not proc.name.isdigit():continue
 processes+=1;paths=[proc/'cwd']
 try:paths.extend((proc/'fd').iterdir())
 except OSError:gaps+=1
 for path in paths:
  try:target=os.readlink(path);links+=1
  except OSError:gaps+=1;continue
  if any(target==str(BASE/n) or target.startswith(str(BASE/n)+'/') for n in NAMES):live+=1
assert live==0
candidates=[]
for n in NAMES:
 root=BASE/n;assert root.is_dir() and not root.is_symlink() and (root/'recycle.now').read_text().strip()=='True';types={'file':0,'directory':0,'symlink':0,'fifo':0};logical=physical=0;seen=set()
 for p in root.rglob('*'):
  s=p.lstat();key=(s.st_dev,s.st_ino)
  if key not in seen:physical+=s.st_blocks*512;seen.add(key)
  if stat.S_ISREG(s.st_mode):types['file']+=1;logical+=s.st_size
  elif stat.S_ISDIR(s.st_mode):types['directory']+=1
  elif stat.S_ISLNK(s.st_mode):types['symlink']+=1
  elif stat.S_ISFIFO(s.st_mode):types['fifo']+=1
  else:raise AssertionError('UNAPPROVED_CANDIDATE_TYPE')
 candidates.append({'allowlisted_namespace':n,'marker_True':True,'marker_sha256':sha(root/'recycle.now'),'observed_member_types':types,'logical_regular_file_bytes':logical,'stat_allocated_unique_entry_blocks_bytes_observation':physical,'full_before_removal_byte_inventory':'DEFERRED_TO_ROOT_ACTUAL_SCRIPT'})
prior=P('/workspace/engineering/capacity-recovery-batch20-proposal/private-readonly-preparation-proof.json');assert sha(prior)=='898ee4e52c68572e45ce3fde0e5633f56d5c133afcf0d46e650e1a84697b779b';proof=json.loads(prior.read_bytes());assert proof['prior_archives']==40 and proof['prior_indices']==19;checks=[]
for row in proof['refs_current_bytes_modes']:
 p=P(row['path']);assert b(p)=={k:row[k] for k in ['path','bytes','sha256']}
 if 'current_mode' in row:assert oct(stat.S_IMODE(p.stat().st_mode))==row['current_mode']
 checks.append(b(p))
new_summaries=[];new_archives=0
for n,expected_bytes,expected_sha in [(20,1369,'1d651c9a8d8421d7566c1e1f085136df525a3e783dd5667748960301bc59053a'),(21,969,'2fc2396bdcbcd154c8d3cb11d7caa5e5f236ae407e2d74059143c2623585c485')]:
 p=P(f'/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch{n}.json');assert b(p)['bytes']==expected_bytes and sha(p)==expected_sha;x=json.loads(p.read_bytes());idx=x['private_inventory'];assert b(idx['path'])==idx and stat.S_IMODE(P(idx['path']).stat().st_mode)==0o600
 for r in x['records']:
  a=P(r['archive']);assert a.stat().st_size==r['archive_bytes'] and sha(a)==r['archive_sha256'] and stat.S_IMODE(a.stat().st_mode)==0o600;assert not P(r['original_namespace']).exists();new_archives+=1
 new_summaries.append({'owner':b(p),'index':idx,'actual_ROOT_recorded_archives':len(x['records']),'independent_actual_stream_validation':'PENDING other designated reviewer, not upgraded by these hashes'})
assert new_archives==3
cache_script=P('/workspace/engineering/root-failed300-default-cache-independent-actual-review/verify-readonly-actual.py');helpers=[x for x in ast.parse(cache_script.read_bytes()).body if isinstance(x,ast.FunctionDef) and x.name in {'info','inventory','norm','partition'}];ns={'Path':P,'stat':stat,'os':os,'sha':sha,'defaultdict':defaultdict};exec(compile(ast.Module(body=helpers,type_ignores=[]),str(cache_script)+':pure-readonly-functions','exec'),ns);cache=json.loads(P('/workspace/engineering/root-failed300-default-cache-preservation-actual/OWNERFINAL-root-whole-default-cache-preservation-actual.json').read_bytes());old=json.loads(P(cache['private_complete_inventories']['path']).read_bytes())['frozen_original'];current=ns['inventory'](P(cache['physical_destination']));assert len(current['entries'])==416 and ns['norm'](current)==ns['norm'](old) and ns['partition'](current)==ns['partition'](old)==[]
failed=list(BASE.glob('563d*'));assert len(failed)==1 and failed[0].is_dir()
full=P('/workspace/engineering/captured-child-cleanup-current499-independent-SOURCEFULL-review/OWNERFINAL-independent-current499-configured-SOURCEFULL-review.json');assert sha(full)=='403a9a40759b5b8f996d6025b15889e154014af961c9c49ed898cab1687fd5cd'
private={'all_prior_ref_checks':checks,'new_ROOT_actual_summary_bindings':new_summaries,'prior40_archives19indices_rehashed_unchanged':True,'current_ROOT_recorded_total43_archives21indices_not_all_ind_actual':True,'default416_recorded_body_metadata_hardlinks_exact':True,'fresh_candidates':candidates,'fresh_handles_observation':{'processes':processes,'links_read':links,'unobserved_permission_transient_or_FD_lists':gaps,'candidate_cwd_FD_observed':live},'script_PREPARED_NOT_EXECUTED':b(script),'canonical_exact_reuse':proof['canonical'],'elapsed_seconds':time.monotonic()-start};privatefile=D/'private-readonly-preparation-proof.json';privatefile.write_text(json.dumps(private,indent=2)+'\n');privatefile.chmod(0o600)
r={'schema':'capacity-batch22-owner-preexecution-proposal-v1','decision':'GO_EXACT_FIVE_COMPLETED_NAMESPACE_SCRIPT_PREPARATION_ONLY_ROOT_ONE_RELEASE_REQUIRED','script':b(script),'algorithm_parent':b(parent),'all16_nonconfiguration_AST_exact':True,'only_configuration_changes':['DEST','STAGE','NAMES'],'names_exact_allowlist':NAMES,'destination':'/dev/shm/actions-completed-scratch-recovery-batch22','unused_new_stage':'/tmp/actions-completed-scratch-recovery-batch22-stage','destination_stage_absent':True,'fresh_candidate_metadata':candidates,'fresh_accessible_handle_observation':private['fresh_handles_observation'],'prior_retention':{'independent_prior40archives19indices_hashsize_modes_unchanged':True,'current_ROOT_recorded_additional3archives2indices_hashsize_modes_exact':new_summaries,'current_ROOT_recorded_total43archives21indices':'independent actual20/21 validation pending; do not relabel from hash retention','default_whole416_body_recorded_metadata_hardlinks_exact':True,'source_guard_refs_original_native1192_helpers0444_and_V5runner09cdc_frozen_refs':'Prior immutable proof and all bound references rehashed; failed563d existence only and excluded'},'private_preparation_proof':b(privatefile),'accepted_cleanup499_current_SOURCEFULL_review':b(full),'execution_prerequisites':['ROOT distinct ONE recovery release; no tests/full/runtime/source execution by preparer','Same script fresh marker/no-observed-handles before complete byte inventory and again after archive verification before removal','Lossless complete gzip resolution/member modeUIDGID/link validation plus exact pre-removal re-inventory and private index written before only expanded namespace removal','No failed563d/current active scratch/othercache/native/helper/source/binary namespace inclusion'],'next_gate_authority':'HOLD until post-recovery fresh capacity>=1.2GiB (1288490189 B), target>=1300000000 B, slot serialization and distinct reviewed root release. Physical block estimate is not a capacity guarantee; if insufficient remain HOLD.','workspace_available_bytes_observation':os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize,'candidate_stat_allocated_bytes_observation_sum':sum(c['stat_allocated_unique_entry_blocks_bytes_observation'] for c in candidates),'no_archive_recovery_removal_source_gate_native_download_execution_performed':True,'source_origin':'UNREPORTED for these namespaces; completion markers/mtime are not producer provenance','limits':['No universal process quiescence/permission/transient/maps/external handle coverage','No retrospective raw original baseline/ACL/xattr/inode/rootmetadata/exact TAR ns-time qualification','Complete before-removal content inventory deferred to root actual; independent actual review by separate designated reader remainsrequired','Do not upgrade ROOT20/21 pending stream reviews merely because archive/index hashes persist'],'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md exact existing7d070 capacity paragraph reused, no cosmetic duplicate','Exact_delta_or_reuse':proof['canonical'],'Durable_learning_captured':'Complete archive/index byte evidence and rechecks precede only named completed expanded namespace removal; new gate authority needs fresh measured capacity and separate source/slot review.','Evidence':[b(script),b(parent),b(privatefile)],'Stale_or_ambiguous_guidance_removed':'Capacity/block estimates, markers, mtime and retained hashes do not become causal producer identities, universal quiescence or independent streamed integrity acceptance.','Remaining_uncertainty':'Recovery NOT_RUN; actual20/21 stream reviews pending elsewhere; future bytes/handles/capacity require fresh checks. Insufficient recovery leaves next gate HOLD.'},'Upstream_disposition':'none','constructor':b(__file__)}
p=D/'OWNERFINAL-batch22-exact-five-completed-preexecution-proposal.json';p.write_text(json.dumps(r,indent=2)+'\n');p.chmod(0o600);print(json.dumps({'owner':b(p),'script':b(script),'status':'NOT_EXECUTED','workspace_available':r['workspace_available_bytes_observation'],'allocated_candidate_blocks_observation':r['candidate_stat_allocated_bytes_observation_sum']}))
