import hashlib,json,os,pathlib,stat,subprocess
P=pathlib.Path;D=P('/workspace/engineering/capacity-recovery-batch24-proposal');BASE=P('/workspace/actions-cloud/robocorp/temp');NAME='646e9b21fab67902'
def sha(p):
 h=hashlib.sha256()
 with P(p).open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
def b(p):p=P(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def check(r):assert b(r['path'])=={k:r[k] for k in ['path','bytes','sha256']};return b(r['path'])
meta=P(D/'FROZEN-candidate-and-script-metadata-only.json');assert sha(meta)=='e5f5749e9c4006a38318e843c1d002b45ce3797c14bd0ac39f29901431cb414a';m=json.loads(meta.read_bytes());check(m['script']);check(m['algorithm_parent'])
owner=P('/workspace/engineering/root-rcc308-one-current-b614-source-full/OWNERFINAL-root-current-b614-configured-SOURCEFULL.json');assert b(owner)['bytes']==6277 and sha(owner)=='eb73d4a34acaf77266f6aff75f758fa674e6b48aff968a31bbeca85148319bf8';full=json.loads(owner.read_bytes());fullrefs=[]
for key in ['actual_full_log','full_terminal','root_parent_terminal','root_release','one_attempt_marker','preexecution_owner','preexecution_independent','SOURCE_LIGHT','SOURCE_LIGHT_independent']:fullrefs.append(check(full[key]))
for row in full['launcher_input_bindings10']:fullrefs.append(check(row))
Q=P('/workspace/engineering/pr308-rcc-compatibility-SOURCEFULL-preexecution');proofs=[]
for name,size,digest in [('before-full-source-prepost.json',1661,'42ecde2002ccbb7afb8ea2f790efd6a082f4420525243a47b6d3b48d26ccc446'),('after-full-source-prepost.json',1659,'44be1525ef81a2ece7a6aae8f12d8d461c9618f48783ae3361f673fe9399ba4a'),('before-full-original-native-helper-browser-V5-readback.json',4720,'88b95c803cb08c84aede15794eef09521350d6fb617ac2e06081eebb853f4985'),('after-full-original-native-helper-browser-V5-readback.json',4720,'88b95c803cb08c84aede15794eef09521350d6fb617ac2e06081eebb853f4985')]:
 p=Q/name;assert b(p)['bytes']==size and sha(p)==digest;proofs.append(b(p))
light=json.loads(P(full['SOURCE_LIGHT']['path']).read_bytes());assert len(light['frozen_bindings'])==71
for row in light['frozen_bindings']:check(row)
R=P('/workspace/engineering/pr308');assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()==full['source']['head'] and subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD^{tree}'],text=True).strip()==full['source']['tree'] and not subprocess.check_output(['git','-C',str(R),'status','--porcelain'])
proof=json.loads(P(light['complete_committed_body_mode_proof']['path']).read_bytes());entries=proof['complete1421_Git_FS_body_mode_exact'];assert len(entries)==1421
for name,row in entries.items():assert sha(R/name)==row['sha256'] and bool((R/name).stat().st_mode&0o111)==(row['mode']=='100755')
cfg=json.loads((Q/'sourcefull-frozen-inputs.json').read_bytes());prepared=json.loads(P(cfg['prepared']).read_bytes());assert len(prepared['inputs_exact_prepared_git_bytes_sha256'])==30
for name,digest in prepared['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/name)==digest
for name,row in prepared['own5venvs_current_config_and_python'].items():assert sha(R/name/'.venv/pyvenv.cfg')==row['config_sha256']
# Retain original native/browsers/helper1192 inventory by bytes/modes only; never invoke original inspector/application.
ret=json.loads((Q/'after-full-original-native-helper-browser-V5-readback.json').read_bytes());check(ret['original_inventory']);inv=json.loads(P(ret['original_inventory']['path']).read_bytes());layout=P('/workspace/engineering/pr310-runner-qualification-owned/dist/action-server');assert len(inv)==1192 and {p.relative_to(layout).as_posix() for p in layout.rglob('*')}=={row['path'] for row in inv}
for row in inv:
 p=layout/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert sha(p)==row['content_sha256']
 elif row['kind']=='symlink':assert os.readlink(p)==row['link_target'] and sha(p)==row['content_sha256']
 else:assert p.is_dir() and not p.is_symlink()
for group in ret['frozen_helper_original_and_snapshot_bindings'].values():
 for key in ['original','snapshot']:check(group[key])
 assert stat.S_IMODE(P(group['snapshot']['path']).stat().st_mode)==0o444
for key in ['original_manifest','original_assets_zip','original_frozen_executable','browser','historical_V5_checkpoint','historical_V5_independent_review','immutable_proposal']:check(ret[key])
log=P(full['actual_full_log']['path']);namespace_occurrences=log.read_bytes().count(str(BASE/NAME).encode());origin='UNREPORTED' if namespace_occurrences==0 else 'EXACT_RAW_PATH_OBSERVED_ONLY_NO_SOURCE_CAUSE_INFERENCE'
roots=[];archives=0
for n,size,digest in [(22,2690,'e8fd9a9370a10e07d739a9a7b2685e4cfac84699d8e11903ef5b4a7bfdc626b8'),(23,905,'87cbc0fd1ccb7ae1ac562c52d53c035b5b924bf97b6758c3b5626bc3e9ecb91f')]:
 p=P(f'/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch{n}.json');assert b(p)['bytes']==size and sha(p)==digest;s=json.loads(p.read_bytes());check(s['private_inventory'])
 for row in s['records']:
  archive=P(row['archive']);assert archive.stat().st_size==row['archive_bytes'] and sha(archive)==row['archive_sha256'] and stat.S_IMODE(archive.stat().st_mode)==0o600 and not P(row['original_namespace']).exists();archives+=1
 roots.append({'owner':b(p),'private_index':s['private_inventory'],'ROOT_recorded_archives':len(s['records']),'acceptance_scope':'Retained original ROOT counts and pending-at-capture status; this metadata proposal is not independent actual stream validation'})
assert archives==6
prior=P('/workspace/engineering/capacity-recovery-batch23-proposal/OWNERFINAL-batch23-exact-one-completed-preexecution-proposal.json');assert sha(prior)=='aa811248656870b96ee16d19a0dfcad79d92d7771e72c2178147fc8f271e2840';previous=json.loads(prior.read_bytes());failed=list(BASE.glob('563d*'));assert len(failed)==1 and failed[0].is_dir();assert (BASE/NAME/'recycle.now').read_text().strip()=='True';assert not P('/dev/shm/actions-completed-scratch-recovery-batch24').exists() and not P('/tmp/actions-completed-scratch-recovery-batch24-stage').exists()
# Fresh handles again immediately before owner freeze, no process identities or inaccessible content emitted.
procs=links=gaps=live=0
for proc in P('/proc').iterdir():
 if not proc.name.isdigit():continue
 procs+=1;ps=[proc/'cwd']
 try:ps.extend((proc/'fd').iterdir())
 except OSError:gaps+=1
 for p in ps:
  try:t=os.readlink(p);links+=1
  except OSError:gaps+=1;continue
  if t==str(BASE/NAME) or t.startswith(str(BASE/NAME)+'/'):live+=1
assert live==0
r={'schema':'capacity-batch24-owner-preexecution-proposal-v1','decision':'GO_EXACT_SINGLE_COMPLETED_NAMESPACE_SCRIPT_PREPARATION_ONLY_ROOT_ONE_RELEASE_REQUIRED','script':m['script'],'algorithm_parent':m['algorithm_parent'],'all16_nonconfiguration_AST_exact_parent':True,'only_configuration_changes':['DEST','STAGE','NAMES'],'names_exact_allowlist':[NAME],'destination':'/dev/shm/actions-completed-scratch-recovery-batch24','unused_new_stage':'/tmp/actions-completed-scratch-recovery-batch24-stage','destination_stage_absent':True,'fresh_completed_marker_True':True,'candidate_metadata':{'member_types':m['fresh_candidate_member_types'],'logical_regular_file_bytes':m['logical_regular_file_bytes'],'allocated_unique_blocks_observation':m['allocated_unique_entry_blocks_observation_bytes']},'fresh_accessible_handle_observation':{'processes':procs,'links_read':links,'unobserved_permission_transient_FDlists':gaps,'candidate_live_cwdFD_observed':live},'source_origin':origin,'raw_original_full_exact_namespace_path_occurrences':namespace_occurrences,'source_origin_limit':'No timestamp/newest/completion-marker inference; even an exact log path would not itself prove readiness/native cause.','original_ROOT308_SOURCEFULL':b(owner),'ROOT308_current_source':full['source'],'ROOT308_source1421_BODY_Git_execmodes_and71_LIGHT_refs_exact_current':True,'ROOT308_prepared30_own5cfg_exact_and_beforeafter_origin_observations_retained':True,'ROOT308_full_prepost_native1192_helpers0444_original_browser_Node_V5_hashes_retained':True,'original_full_proof_bindings':proofs,'original_full_immediate_bindings':fullrefs,'ROOT_source_full_status_scope':'Original ROOT pass independently reviewed elsewhere; this binds it for preservation only, no new suite/actual/native qualification','prior_retention':{'prior48archives22indices_before23':'Frozen prior40/19+ROOT20/21+ROOT22 chain retained; no giant re-stream or new past handle claims','ROOT22_23_originals':roots,'current_ROOT_recorded_total_before24':'49archives23indices; independent actual scope remains attributable to designated reviews, not this preparation'},'prior_frozen_preparation_chain':b(prior),'failed563d':'EXISTS only and excluded; no deletion or historical content baseline claim','workspace_available_bytes_observation':os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize,'execution_prerequisites':['ROOT distinct ONE recovery release; full source terminal available','Exact script fresh marker/no observed accessible handles before full inventory and again after successful archive resolution/reinventory before removal','Complete private0600gzip/index; named expanded namespace only after every recorded member SHA/size/modeUIDGID/link and full reinventory match','No other namespace/cache/native/helper/source/receipt touched'],'cold_actual_authority':'HOLD until fresh>=1.2GiB1288490189B, slot clear and separate current actual proposal/review/root release; no capacity guarantee','no_archival_removal_source_control_test_gateway_native_download_execution_by_preparer':True,'limits':['Complete candidate before-removal content inventory deferred to root actual script','Observed handle scan is not universal quiescence; permissions/transients/maps/external actors remain unobserved','No ACL/xattr/inode/rootmetadata/exact TAR ns-time or source-origin-by-mtime claim','Preserved ROOT pass/log bindings do not admit new RCC binaries or private/provider/native functional behavior'],'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md exact existing7d070 preservation paragraph reused unchanged','Exact_delta_or_reuse':previous['Documentation_improvement']['Exact_delta_or_reuse'],'Durable_learning_captured':'Complete archive/index evidence and rechecks precede only named completed scratch removal, while producer provenance and actual cold-gate authority remain separate.','Evidence':[m['script'],m['algorithm_parent'],b(owner),*proofs],'Stale_or_ambiguous_guidance_removed':'Do not label the newest completed scratch as source-full producer from mtime or carry a source suite pass into binary/actual acceptance.','Remaining_uncertainty':'Recovery NOT_RUN; actual review by separate reader and fresh cold capacity/slot required; namespace source origin remains bounded/unreported.'},'Upstream_disposition':'none','constructor':b(__file__),'candidate_metadata_constructor':b(meta)}
p=D/'OWNERFINAL-batch24-exact-one-completed-preexecution-proposal.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');p.chmod(0o600);print(json.dumps({'owner':b(p),'script':m['script'],'source_origin':origin,'raw_namespace_path_matches':namespace_occurrences,'status':'NOT_EXECUTED'}))
