import ast,hashlib,importlib.util,json,os,pathlib,stat,sys
sys.dont_write_bytecode=True
P=pathlib.Path;D=P('/workspace/engineering/capacity-recovery-batch23-proposal');NAME='a4fa6f1c79c0a18f';BASE=P('/workspace/actions-cloud/robocorp/temp');root=BASE/NAME

def sha(p):
 h=hashlib.sha256()
 with P(p).open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
def b(p):p=P(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
parent=P('/tmp/actions-capacity-recovery-batch19.py');assert b(parent)['bytes']==5244 and sha(parent)=='48fd7e4c79e55b80ceda0b63c1d1da87feeb368cefee265d5c12bad6ad940840';text=parent.read_text();newtext=text.replace("DEST = Path('/dev/shm/actions-completed-scratch-recovery-batch19')","DEST = Path('/dev/shm/actions-completed-scratch-recovery-batch23')").replace("STAGE = Path('/tmp/actions-completed-scratch-recovery-batch19-stage')","STAGE = Path('/tmp/actions-completed-scratch-recovery-batch23-stage')").replace("NAMES = ['c3b676a701cf3ae2']","NAMES = ['a4fa6f1c79c0a18f']")
def norm(s):
 t=ast.parse(s);count=0;cfg=set()
 for node in t.body:
  if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in {'DEST','STAGE','NAMES'}:cfg.add(node.targets[0].id);node.value=ast.Constant('CONFIG_ONLY')
  else:count+=1
 return ast.dump(t,include_attributes=False),count,cfg
assert norm(newtext)==norm(text) and norm(newtext)[1]==16
script=P('/tmp/actions-capacity-recovery-batch23.py');assert script.read_text()==newtext and stat.S_IMODE(script.stat().st_mode)==0o600;assert not P('/dev/shm/actions-completed-scratch-recovery-batch23').exists() and not P('/tmp/actions-completed-scratch-recovery-batch23-stage').exists()
assert root.is_dir() and not root.is_symlink() and (root/'recycle.now').read_text().strip()=='True'
processes=links=gaps=live=0
for proc in P('/proc').iterdir():
 if not proc.name.isdigit():continue
 processes+=1;paths=[proc/'cwd']
 try:paths.extend((proc/'fd').iterdir())
 except OSError:gaps+=1
 for path in paths:
  try:target=os.readlink(path);links+=1
  except OSError:gaps+=1;continue
  if target==str(root) or target.startswith(str(root)+'/'):live+=1
assert live==0
counts={'file':0,'directory':0,'symlink':0,'fifo':0};logical=physical=0;seen=set()
for p in root.rglob('*'):
 s=p.lstat();key=(s.st_dev,s.st_ino)
 if key not in seen:physical+=s.st_blocks*512;seen.add(key)
 if stat.S_ISREG(s.st_mode):counts['file']+=1;logical+=s.st_size
 elif stat.S_ISDIR(s.st_mode):counts['directory']+=1
 elif stat.S_ISLNK(s.st_mode):counts['symlink']+=1
 elif stat.S_ISFIFO(s.st_mode):counts['fifo']+=1
 else:raise AssertionError('UNAPPROVED_TYPE')
root_non_directory_entry_size=logical+sum(p.lstat().st_size for p in root.rglob('*') if stat.S_ISLNK(p.lstat().st_mode));assert root_non_directory_entry_size==24358227
p22=P('/workspace/engineering/capacity-recovery-batch22-proposal/OWNERFINAL-batch22-exact-five-completed-preexecution-proposal.json');assert sha(p22)=='c34b4ef28b2f0c6ae3436f542bc401e3da3bbac9f040739e6020977d5a0e1349';o22=json.loads(p22.read_bytes());adopt=P('/workspace/engineering/root-one-capacity-batch22-adoption.json');assert b(adopt)['bytes']==3539 and sha(adopt)=='2e29b92847f4cc36a5a20a645ee679f2c95e315097c19a74201b84cd9d9c4561';a=json.loads(adopt.read_bytes());assert a['proposal']==b(p22) and a['root_nonconfigAST_exact'];checked=[]
for row in a['verified_bindings']:assert b(row['path'])==row;checked.append(row)
# Bind old accepted40/19 and subsequent ROOT20/21 originals without rerunning prior private stream reviews.
roots=[]
for n,size,digest in [(20,1369,'1d651c9a8d8421d7566c1e1f085136df525a3e783dd5667748960301bc59053a'),(21,969,'2fc2396bdcbcd154c8d3cb11d7caa5e5f236ae407e2d74059143c2623585c485')]:
 p=P(f'/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch{n}.json');assert b(p)['bytes']==size and sha(p)==digest;owner=json.loads(p.read_bytes());assert b(owner['private_inventory']['path'])==owner['private_inventory']
 for row in owner['records']:
  archive=P(row['archive']);assert archive.stat().st_size==row['archive_bytes'] and sha(archive)==row['archive_sha256'] and stat.S_IMODE(archive.stat().st_mode)==0o600 and not P(row['original_namespace']).exists()
 roots.append({'owner':b(p),'private_index':owner['private_inventory'],'ROOT_recorded_archives':len(owner['records']),'independent_stream_scope':'Retain originally pending status here; no new actual validation claim'})
full=P('/workspace/engineering/captured-child-cleanup-current499-independent-SOURCEFULL-review/OWNERFINAL-independent-current499-configured-SOURCEFULL-review.json');assert sha(full)=='403a9a40759b5b8f996d6025b15889e154014af961c9c49ed898cab1687fd5cd'
guard_path=P('/workspace/engineering/captured-child-cleanup-configured-full-proposal/readonly_source_guards_v5.py');spec=importlib.util.spec_from_file_location('capacity23_readonly_retention_guard',guard_path);guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);current=guard.guards();assert current['source_entries']==1422 and current['native_inventory_entries']==1192
native=P('/workspace/engineering/pr310-runner-qualification-owned');inv=json.loads((native/'output/native-artifact-tree-inventory.json').read_bytes());assert {p.relative_to(native/'dist/action-server').as_posix() for p in (native/'dist/action-server').rglob('*')}=={row['path'] for row in inv}
failed=list(BASE.glob('563d*'));assert len(failed)==1 and failed[0].is_dir()
capacity=os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize
r={'schema':'capacity-batch23-owner-preexecution-proposal-v1','decision':'GO_EXACT_SINGLE_COMPLETED_NAMESPACE_SCRIPT_PREPARATION_ONLY_ROOT_RELEASE_REQUIRED','script':b(script),'algorithm_parent':b(parent),'all16_nonconfiguration_AST_exact_parent':True,'only_configuration_changes':['DEST','STAGE','NAMES'],'names_exact_allowlist':[NAME],'destination':'/dev/shm/actions-completed-scratch-recovery-batch23','unused_new_stage':'/tmp/actions-completed-scratch-recovery-batch23-stage','destination_stage_absent':True,'fresh_completed_marker':{'True':True,'sha256':sha(root/'recycle.now')},'fresh_candidate_member_types':counts,'logical_regular_file_bytes':logical,'ROOT_non_directory_file_plus_symlink_entry_bytes':root_non_directory_entry_size,'allocated_unique_entry_blocks_bytes_observation':physical,'accessible_handle_observation':{'processes':processes,'links_read':links,'unobserved_permission_transient_or_FDlists':gaps,'candidate_cwd_FD_observed':live},'source_origin':'UNREPORTED; older/markerTrue/mtime do not establish producer identity','batch22_frozen_proposal':b(p22),'batch22_ROOT_one_adoption':b(adopt),'all_batch22_adoption14_bindings_rehashed':checked,'prior_retention_scope':{'accepted_prior40archives19indices':'Immutable before22 proof rehashed and retained via adopted c34/760c chain; no giant repeat stream or new historical claim','ROOT_recorded_total_before22':'43archives21indices;20/21 original root receipts/index/archives retained, independent streamed review remains separately attributed','ROOT20_21_originals':roots,'batch22_actual':'May be active; no mutable actualindex/log read or future acceptance/count invented'},'current_source_native_retention_readonly':current,'native1192_full_member_set_exact_current':True,'current_cleanup_SOURCEFULL_review':b(full),'failed563d':'EXISTS bounded; not allowlisted/read-as-complete historical baseline/touched','workspace_available_bytes_observation':capacity,'execution_prerequisites':['Root distinct ONE recovery release after current batch22 recovery terminal','Exact script repeats fresh marker/accessible-handle checks before full inventory and after successful archive verification/reinventory before removal','Existingmount private0600gzip+complete0600 index; no copy/install/newnamespaceGC or any other scratch/source/cache/helper/native deletion'],'capacity_gate_subjects':{'source_full_existing_exact_proposal_floor_bytes':1200000000,'native_first_actual_strict_1point2GiB_floor_bytes':1288490189,'target_fresh_bytes':1300000000,'capacity_after_recovery_NOT_PROVEN':'Observe fresh after actual recovery; if below required subject threshold HOLD, no forced launch'},'no_recovery_archive_removal_test_gateway_native_download_source_execution_by_preparer':True,'limits':['Metadata candidate body inventory deferred to root actual exact script','Accessible cwdFD observations omit permission/transient/maps/external users; no universal quiescence','No ACL/xattr/inode/rootmetadata/exact TAR nsmtime or causal source-origin inference','Retained prior SHA bindings do not replace original independent archive stream reviews'],'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md exact existing7d070 preservation paragraph reused unchanged','Exact_delta_or_reuse':o22['Documentation_improvement']['Exact_delta_or_reuse'],'Durable_learning_captured':'Preserve complete archive/index evidence before only named completed expanded removal; handle observations and capacity planning do not provide future source/native gate authority.','Evidence':[b(script),b(parent),b(adopt),b(full)],'Stale_or_ambiguous_guidance_removed':'No ROOT-recorded recovery promoted to independently streamed preservation; separate decimal source-full and strict binary native-cold floor are explicit.','Remaining_uncertainty':'Actual batch23 NOT_RUN and new actual review required; fresh future capacity/handles are unknown; source origin UNREPORTED.'},'retained_initial_metadata_metric_inspector_failure':b(D/'retained-preparation-size-definition-correction.json'),'Upstream_disposition':'none','constructor':b(__file__)}
p=D/'OWNERFINAL-batch23-exact-one-completed-preexecution-proposal.json';p.write_text(json.dumps(r,indent=2)+'\n');p.chmod(0o600);print(json.dumps({'owner':b(p),'script':b(script),'status':'NOT_EXECUTED','logical_regular_file_bytes':logical,'ROOT_non_directory_file_plus_symlink_entry_bytes':root_non_directory_entry_size,'allocated_blocks_observed':physical,'workspace_available_observed':capacity}))
