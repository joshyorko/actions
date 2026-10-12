from pathlib import Path
import ast,hashlib,json,os,re,stat,subprocess
ROOT=Path('/workspace/engineering');D=Path(__file__).parent;P=ROOT/'pr305-current5306-SOURCEFULL-preexecution';R=ROOT/'pr305';L=ROOT/'pr305-current-a54-source-LIGHT'
H='5306eeb26595da4ce571b99812eb50f047cfc903';T='8418e9ffeeaaf2446771e34b5b4602bab3d357a5';B='a54c982462d1e7ad011d8152bfc299d997503fb3';A='584a7ed0cb7112fe6691103931c007b5cc0be5f3'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def load(p):return json.loads(Path(p).read_text())
def check(row):
 q=bind(row['path']);assert q['sha256']==row['sha256'] and q['bytes']==row['bytes'] and q['mode']==row['mode'];return q
def git(*a):return subprocess.check_output(['git','-C',str(R),*a],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
owner=P/'OWNERFINAL-current5306-managed-configured-SOURCEFULL-preexecution-proposal.json';q=bind(owner);assert(q['bytes'],q['sha256'])==(8597,'fbdaba2989e187ad11547f56ff0107092a479d4592aaa48b9170cc7a2339e553')
proposal=load(owner);cfg=load(P/'frozen-current-source-full-inputs.json');ind=ROOT/'pr305-current5306-independent-LIGHT-preexecution-review/OWNERFINAL-independent-current5306-SOURCE-LIGHT-review.json';q=bind(ind);assert(q['bytes'],q['sha256'])==(16663,'c6ba4df0f15ec59c81d7d643da71457db513fd274064df41ee1ded2f92fa2e96')
assert load(ind)['decision']=='GO_EXACT_CURRENT5306_ORDINARY_A54_SOURCE_LIGHT_ONLY_FULL_PREEXEC_ADOPTION_HOLD_PENDING_NAMED_METADATA_CORRECTION'
assert proposal['source']==cfg['head']==H and proposal['tree']==cfg['tree']==T and cfg['source_root']==str(R)
assert git('show','-s','--format=%H %T %P',H).decode().split()==[H,T,A,B] and git('rev-parse','HEAD').decode().strip()==H and not git('status','--porcelain')
refs=[check(r) for r in proposal['frozen_input_bindings']];assert len(refs)==14
check(cfg['source_LIGHT']);light=load(cfg['source_LIGHT']['path']);lightrefs=[check(r) for r in light['frozen_bindings']];assert len(lightrefs)==38
for row in cfg['implementation_bindings']+cfg['prepared_environment_and_RCC_bindings']:check(row)
rows=load(cfg['source_inventory']);assert len(rows)==1427
for row in rows:
 p=R/row['path'];raw=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['bytes'] and stat.S_IMODE(p.lstat().st_mode)==row['fs_mode']
 for_mode=row['mode'];assert for_mode=='120000' or bool(p.stat().st_mode&0o111)==(for_mode=='100755')
prepared=cfg['prepared30_inputs'];assert len(prepared)==30
for path,digest in prepared.items():assert sha(R/path)==digest
assert len(cfg['concrete_origin_packages'])==5
# Every retained payload, not merely a report hash, is configured for both stages.
retained=cfg['retained_actual_files_and_helpers'];payloadrefs=[check(r) for r in retained];by_path={r['path']:r for r in retained};assert len(retained)==len(by_path)==83
oldproof=load(L/'retained-native-helper-browser-and-V5-proof-postLIGHT.json');v5=load(oldproof['historical_V5_checkpoint']['path']);assert len(v5['raw_receipts_private_do_not_commit'])==18 and len(v5['frozen_posthashes'])==50
for row in v5['raw_receipts_private_do_not_commit']:
 assert row['path'] in by_path and by_path[row['path']]['sha256']==row['sha256'] and by_path[row['path']]['bytes']==row['bytes']
for row in v5['frozen_posthashes']:
 assert row['path'] in by_path and by_path[row['path']]['sha256']==row['sha256']==row['expected_sha256']
for pair in oldproof['frozen_helper_original_and_snapshot_bindings'].values():
 for row in pair.values():assert row['path'] in by_path and by_path[row['path']]['sha256']==row['sha256']
 assert by_path[pair['snapshot']['path']]['mode']=='0o444'
driver=load(oldproof['immutable_proposal']['path'])['driver']
for path in [driver['browser'],driver['node'],driver['frontend_lock']['path']]:assert path in by_path
assert not cfg['historical_original_Git_bodies']
# The immutable native original inventory is separately whole-set checked at both stages.
baseline=load(cfg['original_native_config']);native=baseline['native_original_members'];layout=Path(baseline['native_original_root']);assert len(native)==1192
assert {p.relative_to(layout).as_posix() for p in layout.rglob('*')}=={r['path'] for r in native}
for row in native:
 p=layout/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert not p.is_symlink() and sha(p)==row['content_sha256']
 elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert os.readlink(p)==row['link_target']
launcher=(P/'launch_current_source_full_once.py').read_text();body=(P/'current_source_full_body.py').read_text();guard=(P/'current_source_prepost_guard.py').read_text()
for code in [launcher,body,guard]:ast.parse(code)
expectedargv=['timeout','--signal=TERM','--kill-after=10s','600s',cfg['cached_toolkit_prefix']+'/bin/python',str(P/'current_source_full_body.py')];assert proposal['configured_full_argv']==expectedargv
assert 'timeout=640' in launcher and 'timeout=60' in launcher and 'finally:' in launcher and "owned.mkdir(mode=0o700)" in launcher and 'os.umask(0o077)' in launcher and "log.open('xb')" in launcher
assert "primary_error=type(error).__name__" in launcher and "post_error=type(error).__name__" in launcher and "'full_started':full_started" in launcher and "'one_attempt':'CONSUMED_NO_RETRY'" in launcher
assert "for row in cfg['retained_actual_files_and_helpers']:check(row)" in guard and "for name,digest in cfg['prepared30_inputs'].items()" in guard and "for row in baseline['native_original_members']" in guard and "stage=sys.argv[1];assert stage in ('before','after')" in guard
assert "os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'" in body and "toolkit.poetry('action_server','run','invoke','test-not-integration')" in body
exports={}
for line in Path('/workspace/actions-cloud/activate.sh').read_text().splitlines():
 m=re.fullmatch(r'export (\w+)=(.*)',line)
 if m and m[1]!='PATH':exports[m[1]]=re.sub(r'\$(\w+)',lambda v:exports[v[1]],m[2].strip('"\''))
assert exports==cfg['expected_activation_exports'] and len(exports)==18 and exports['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2' and exports['GOMAXPROCS']=='2'
assert len(cfg['forbidden_actual_operator_exports'])==6 and 'PYTHONOPTIMIZE' in cfg['forbidden_actual_operator_exports']
assert "os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'" in guard
plugin=R/'action_server/.venv/lib/python3.12/site-packages/xdist/plugin.py';plugintext=plugin.read_text();assert 'PYTEST_XDIST_AUTO_NUM_WORKERS' in plugintext and 'return int(env_var)' in plugintext
assert 'environment = os.environ.copy()' in (R/'developer/toolkit.py').read_text() and 'env: dict | None = None' in (R/'action_server/src/actions/server/_build_common/process_call.py').read_text()
owned=P/'one-configured-full-once-owned';assert not owned.exists() and not owned.is_symlink()
release={'schema':1,'status':'ROOT_RELEASE_ONE_SERIALIZED_CONFIGURED_SOURCE_FULL','proposal_sha256':sha(owner),'source':H,'tree':T,'independent_source_and_preexecution_review_GO':True,'serialized_no_other_heavy_or_installer':True};advertised=dict(proposal['root_release_exact_required_schema']);advertised['proposal_sha256']=sha(owner);assert advertised==release
assert cfg['capacity_floor_bytes']==1288490188
assert proposal['execution_bounds']=={'always_post':'finally attempts post guard even on caught preflight/primary failure; OS hard kill cannot guarantee Python finally and remains HOLD','always_post_guard_timeout_seconds':60,'max_normal_parent_envelope_seconds':760,'outer_GNU_timeout_seconds':900,'outer_KILL_grace_seconds':10,'parent_configured_subprocess_timeout_seconds':640,'pre_guard_timeout_seconds':60,'source_GNU_timeout_seconds':600,'source_KILL_grace_seconds':10}
patch=proposal['documentation_improvement']['canonical_guide_delta'];check(patch);assert git('diff',A,H,'--','docs/skills/repository-operations.md','docs/skills/provenance-observability.md')==Path(patch['path']).read_bytes()
newfull=P/'OWNERFINAL-current5306-managed-configured-SOURCEFULL-preexecution-subject-metadata-v2.json';newlight=L/'OWNERFINAL-current5306-ordinary-a54-source-LIGHT-subject-metadata-v2.json';disposition=P/'OWNERFINAL-current5306-metadata-only-subject-correction-disposition-v2.json'
for path,n,digest in [(newfull,11869,'0993125d3ea8c732a7f851e5d3c20df5f71aa1e318bc887c449c1bfd1f9ee623'),(newlight,18366,'896ffb6299cf9e7fca9adacc187115d43057be559226b8cfcd4b99411f9324ee'),(disposition,4163,'ef9e901932051bf0daf0f993f0462ceeb0c69a67f7a12aeaa9f60e68b86d8539')]:
 q=bind(path);assert(q['bytes'],q['sha256'])==(n,digest)
nf=load(newfull);nl=load(newlight);disp=load(disposition);old_light=load(cfg['source_LIGHT']['path'])
copyfull=dict(nf);copyfull.pop('subject_metadata_correction');copyfull['status']=proposal['status'];copyfull['historical_preexecution']=proposal['historical_preexecution'];assert copyfull==proposal
copylight=dict(nl);copylight.pop('subject_metadata_correction');copylight['status']=old_light['status'];assert copylight==old_light
assert nf['status']=='OWNERFINAL_CURRENT5306_SOURCEFULL_PREEXECUTION_READY_FOR_INDEPENDENT_REVIEW_NOT_RUN' and nl['status']=='OWNERFINAL_CURRENT_5306_ORDINARY_A54_SOURCE_LIGHT_GO_FOR_REVIEW_FULL_AND_ACTUAL_HOLD'
assert nf['subject_metadata_correction']['correct_current_tuple']=={'source':H,'target':B,'tree':T}
assert nf['subject_metadata_correction']['execution_contract_unchanged']['launcher_root_release_proposal_sha256']==sha(owner)
for row in nf['subject_metadata_correction']['exact_historical_PR305584_bindings']:check(row)
check(disp['authoring_constructor'])
assert "OWNERFINAL-current5306-managed-configured-SOURCEFULL-preexecution-proposal.json" in launcher and 'subject-metadata-v2' not in launcher
patchproof=load(ind)['Documentation_improvement']['Verified_durable_additional_proposal'];check(patchproof)
space=os.statvfs('/workspace');currentfree=space.f_bavail*space.f_frsize
holds=['ConfiguredSOURCEFULL NOT_RUN; fresh>=1.2GiB strictcapacity and no competing heavy/native/installer slot before ROOT release','Named metadata099312 fixes subject and historical labels; unchanged executable contract still requires originalfbdaba digest in exact seven-key release. Do not substitute namedpacket hash or add keys to launcher strictschema','83payload/1192native/1427source before-after guards are proposals until actual completion; OS hardkill may prevent finally','275production260match8changed7added+5selectors remains nativeUNQUALIFIED; whole99/private/browser/native/provider/backend/release holds','Original contradictory fbdaba/2c277 packets remain immutable history; named metadata successor does not replay gates or upgrade prior584e3 execution']
out={'schema':'actions-independent-current3055306-named-metadata-and-original-full-preexecution/v1','decision':'GO_NAMED_SUBJECT_CORRECTION_AND_STATIC_ORIGINAL_FULL_CONTRACT_CONDITIONAL_ROOT_ADOPTION_FRESH_CAPACITY_SERIALIZATION','named_metadata_FULL':bind(newfull),'named_metadata_LIGHT':bind(newlight),'named_metadata_disposition':bind(disposition),'original_executable_contract':bind(owner),'accepted_SOURCE_LIGHT':bind(ind),'source':{'head':H,'tree':T,'ordered_parents':[A,B],'all1427_current_body_modes_exact':True},'named_correction_review':{'existing_FULL_fields_changed_only':['status','historical_preexecution'],'existing_LIGHT_fields_changed_only':['status'],'all_original_config_scripts_argv_bounds14bindings_and38LIGHTbindings_unchanged':True,'original_fbdaba_and2c277_preserved':True,'actual_current_subject':'PR3055306/a54','exact_original_PR305584_proposal_and_independent_review_rehashed':True,'no_replay_or_execution'},'prepost_coverage':{'explicit_current_payload_paths_and_modes':83,'raw18_and_frozen50_covered':True,'helpers_original_and0444_snapshots_browser_Node_frontend_covered':True,'native_complete_members_modes_hashes_whole_set':1192,'source_bodies_modes':1427,'own_prepared_inputs':30,'five_concrete_origin_checks':5,'read_only_now_and_static_bothstage_iteration':True},'ROOT_execution_proposal':{'cwd':str(R),'managed_steps':proposal['outer_managed_command'],'root_adoption_must_bind_named_metadata099312_and_LIGHT896ff_and_dispositionef9e_and_this_independent_review':True,'launcher_new_release_exact_body':release,'release_proposal_hash_must_be_original_executable_contract_fbdaba':True,'never_substitute_named_metadata099312_hash_in_strictlauncher_release':True,'outer_timeout_seconds':900,'outer_TERM_KILL_grace_seconds':10,'primary_argv':expectedargv,'bounds':proposal['execution_bounds'],'worker_auto_bound':2,'activation18exports_andprimaryPATH19':True,'native_actual_operator_exports_forbidden':5,'PYTHONOPTIMIZE_cleared_and_forbidden':True,'new_output_directory_must_still_be_absent':str(owned),'fresh_minimum_workspace_bytes_conservative':1288490189,'review_observed_workspace_free_bytes':currentfree,'capacity_is_not_root_release':True,'all_outcome_primary_pre_post_errors_and_original_private_log_retained':True,'one_attempt_no_retry':True},'remaining_HOLD':holds,'Documentation_improvement':{'Canonical_files_changed_or_proposed':['docs/skills/repository-operations.md','docs/skills/provenance-observability.md'],'Exact_verified_accepted_import':patch,'Verified_subject_label_consistency_proposal':patchproof,'Durable_learning_captured':'Correct copied execution subject/history labels with a named metadata successor while preserving the original hash-bound executable contract; root adoption names both roles and the strict execution release uses its original contract hash. Explicit83payload before/after guards authenticate artifacts, not merely retention reports.','Evidence':'Exact099312/896ff/ef9e named packets differ only permittedlabel fields plus correction record; original14+38 binding hashes/modes and launcher/config/source intact; root release schema/83payloads/1192native/source1427 code verified','Stale_or_ambiguous_guidance_removed':'PR2821299/c35 labels replaced only in named metadata with actualPR3055306/a54 and original584/2cd287/88f103; original contradictory receipts unchanged and not qualified as correctsubject metadata','Remaining_uncertainty':holds},'Upstream_disposition':'none','no_product_import_tests_source_execution_gate_native_provider_download_install_push_or_merge':True,'review_script':bind(__file__)}
p=D/'OWNERFINAL-independent-current5306-named-managed-SOURCEFULL-preexecution-review.json';p.open('x').write(json.dumps(out,indent=2)+'\n');p.chmod(0o400);print(json.dumps(bind(p)))
