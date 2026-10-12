from pathlib import Path
import ast,hashlib,json,os,re,stat,subprocess
ROOT=Path('/workspace/engineering');D=Path(__file__).parent;P=ROOT/'pr282-current1299-SOURCEFULL-preexecution-v2';R=ROOT/'pr282';L=ROOT/'pr282-current-a54-source-LIGHT'
H='1299cc4bb6586f467d36ca124faaaaa77362695f';T='afe2679cc93bf27fa5021c7698ee7ad3ee21a1b9';B='a54c982462d1e7ad011d8152bfc299d997503fb3';A='c35ee2e279eaefe55b16aecdb80da04c590aff7c'
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
owner=P/'OWNERFINAL-current1299-managed-configured-SOURCEFULL-preexecution-proposal.json';q=bind(owner);assert(q['bytes'],q['sha256'])==(9181,'038ed3531a697f0ae699590bf6407e9dd37ecebc019231d70b68e53659c0673c')
proposal=load(owner);cfg=load(P/'frozen-current-source-full-inputs.json');ind=ROOT/'pr282-current1299-independent-SOURCE-LIGHT-review/OWNERFINAL-independent-current1299-SOURCE-LIGHT-review.json';q=bind(ind);assert(q['bytes'],q['sha256'])==(18237,'097d279bcaa111caef55f475422c6bca2ba282910869b6c07e054e6e3108b06a')
assert load(ind)['decision']=='GO_EXACT_CURRENT1299_ORDINARY_A54_SOURCE_LIGHT_ONLY_FULL_AND_ACTUAL_HOLD'
assert proposal['source']==cfg['head']==H and proposal['tree']==cfg['tree']==T and cfg['source_root']==str(R)
assert git('show','-s','--format=%H %T %P',H).decode().split()==[H,T,A,B] and git('rev-parse','HEAD').decode().strip()==H and not git('status','--porcelain')
refs=[check(r) for r in proposal['frozen_input_bindings']];assert len(refs)==14
check(cfg['source_LIGHT']);light=load(cfg['source_LIGHT']['path']);lightrefs=[check(r) for r in light['frozen_bindings']];assert len(lightrefs)==45
for row in cfg['implementation_bindings']+cfg['prepared_environment_and_RCC_bindings']:check(row)
rows=load(cfg['source_inventory']);assert len(rows)==1440
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
check(proposal['construction_history']['original_metadata_draft']);assert cfg['capacity_floor_bytes']==1288490188
assert proposal['execution_bounds']=={'always_post':'finally attempts post guard even on caught preflight/primary failure; OS hard kill cannot guarantee Python finally and remains HOLD','always_post_guard_timeout_seconds':60,'max_normal_parent_envelope_seconds':760,'outer_GNU_timeout_seconds':900,'outer_KILL_grace_seconds':10,'parent_configured_subprocess_timeout_seconds':640,'pre_guard_timeout_seconds':60,'source_GNU_timeout_seconds':600,'source_KILL_grace_seconds':10}
patch=proposal['documentation_improvement']['canonical_guide_delta'];check(patch);assert git('diff',A,H,'--','docs/skills/repository-operations.md','docs/skills/provenance-observability.md')==Path(patch['path']).read_bytes()
out={'schema':'actions-independent-current2821299-configured-SOURCEFULL-preexecution/v1','decision':'GO_STATIC_ONE_MANAGED_CONFIGURED_FULL_PROPOSAL_CONDITIONAL_ROOT_RELEASE_FRESH_CAPACITY_SERIALIZED_SLOT','owner':bind(owner),'accepted_SOURCE_LIGHT':bind(ind),'source':{'head':H,'tree':T,'ordered_parents':[A,B],'all1440_FS_bodies_modes_exact':True},'all14_proposal_and45_LIGHT_bindings_hash_size_modes_exact':{'proposal':refs,'LIGHT':lightrefs},'prepost_coverage':{'source_complete_body_and_modes':1440,'prepared_own_inputs':30,'own_concrete_origin_checks':5,'native_original_members_modes_hashes_whole_set':1192,'retained_payload_files_and_modes_explicit':83,'includes_original_raw18':True,'includes_original_frozen50':True,'includes_all_original_and0444snapshot_helpers':True,'includes_browser_Node_frontend_lock':True,'coverage_independently_readonly_verified_now_and_statically_iterated_both_stages':True,'historical_original_Git_body_rows':0},'ROOT_one_command_proposal':{'cwd':str(R),'managed_steps':proposal['outer_managed_command'],'new_distinct_release_body_exact':release,'release_file_sha_argument_required':True,'outer_timeout_seconds':900,'outer_TERM_then_KILL_grace_seconds':10,'primary_argv':expectedargv,'bounds':proposal['execution_bounds'],'new_absent0700_output_directory':str(owned),'private0600_logs_and_terminal_exclusive_no_retry':True,'managed_activation18exports_plus_PATH19':True,'PYTHONOPTIMIZE_cleared_and_forbidden':True,'explicit_auto_workers':2,'native_RRC_operators_forbidden':5,'minimum_workspace_bytes_conservative':1288490189,'fresh_capacity_not_granted_by_past_observation':True,'current_active_RCC_control3_means_NO_EXECUTION_UNTIL_TERMINAL_AND_ROOT_SERIALIZED_RELEASE':True},'original_unannounced_preexecution_metadata_draft_preserved':proposal['construction_history'],'remaining_HOLD':['Full configuredsource NOT_RUN; current RCC control3 owns heavy slot; fresh>=1.2GiB and independent ROOT exactrelease only after terminal','A proposed finally does not prove completed postguard on OS hardkill; retain primary/pre/post errors and UNKNOWN cleanup distinctly','Current276producer258match10changed8added+5selectors stays nativeUNQUALIFIED; source pass does not qualify actualnative/browser/provider/private/backend/full127/release','Original tenUNAVAILABLE records and historicalV5/source/native identities remain unchanged; no record reconstructed or relabeled'],'Documentation_improvement':{'Canonical_file_changed_or_proposed':['docs/skills/repository-operations.md','docs/skills/provenance-observability.md'],'Exact_verified_delta_reuse':patch,'Durable_learning_captured':'The accepted checkout-filter/transport/shutdown/ownfixture lessons remain integrated exactly. Explicit before/after payload byte+mode iteration authenticates raw artifacts, whereas hashing a preservation report alone authenticates only the report. The named proposal now provides that explicit83-file coverage.','Evidence':'Accepted097d SOURCE_LIGHT with1440 union; exact8802B sourceguide import; boundguard3749B/8424 iterates all83payloads and1192native+1440source atbefore/after; managed18exports and installedxdist env2 code authority','Stale_or_ambiguous_guidance_removed':'Original unannounced PR305 historical wording remains retaineddraft; namedV2 correctly cites PR282c35/d5b1/55a621 and current1299. Do not upgrade staticproposal to full execution or inferred cleanup.','Remaining_uncertainty':'Actualfull/output/postguards and fullqualification remain pending; rootowns release'},'Upstream_disposition':'none','reviewer_no_product_import_source_changes_execution_tests_gate_native_provider_download_install_push_or_merge':True,'review_script':bind(__file__)}
p=D/'OWNERFINAL-independent-current1299-managed-SOURCEFULL-preexecution-review.json';p.open('x').write(json.dumps(out,indent=2)+'\n');p.chmod(0o400);print(json.dumps(bind(p)))
