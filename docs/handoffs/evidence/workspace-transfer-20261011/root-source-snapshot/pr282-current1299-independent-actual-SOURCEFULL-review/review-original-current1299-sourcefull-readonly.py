from pathlib import Path
import collections,hashlib,json,os,re,stat,subprocess
D=Path(__file__).parent;ROOT=Path('/workspace/engineering');R=ROOT/'pr282';P=ROOT/'pr282-current1299-SOURCEFULL-preexecution-v2';O=ROOT/'root-pr282-current1299-one-configured-sourcefull';L=ROOT/'pr282-current-a54-source-LIGHT'
H='1299cc4bb6586f467d36ca124faaaaa77362695f';T='afe2679cc93bf27fa5021c7698ee7ad3ee21a1b9';A='c35ee2e279eaefe55b16aecdb80da04c590aff7c';B='a54c982462d1e7ad011d8152bfc299d997503fb3'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def load(p):return json.loads(Path(p).read_text())
def check(row):
 q=bind(row['path']);assert q['sha256']==row['sha256'] and q['bytes']==row['bytes']
 if 'mode' in row:assert q['mode']==row['mode']
 return q
def git(*a):return subprocess.check_output(['git','-C',str(R),*a],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
owner=O/'OWNERFINAL-root-current1299-configured-SOURCEFULL-PASS.json';q=bind(owner);assert(q['bytes'],q['sha256'])==(3467,'e82889eb300600a4d2e6c6367881b4e9b22445b4285b268b935b746956b8b662');actual=load(owner)
assert actual['source']==H and actual['tree']==T and actual['status']=='PASS_CURRENT1299_CONFIGURED_SOURCEFULL'
for k in ['complete_private_census','original_raw_log','original_terminal','preexecution_independent','preexecution_owner','root_outer_terminal','source_LIGHT_independent','source_LIGHT_owner']:check(actual[k])
logpath=Path(actual['original_raw_log']['path']);text=logpath.read_text();lines=text.splitlines();nodes=[];guards=[];summaries=[]
for i,line in enumerate(lines,1):
 m=re.match(r'^\[(gw\d+)\]\s*(?:\[\s*\d+%\])?\s*(PASSED|SKIPPED|FAILED|ERROR)\s+(.+?)\s*$',line)
 if m:nodes.append({'nodeid':m[3],'status':m[2],'worker':m[1]})
 if line.startswith('{'):
  try:
   val=json.loads(line)
   if val.get('stage') in ['before','after']:guards.append(val)
  except ValueError:pass
 if ' passed' in line and '===' in line:summaries.append({'line':i,'text':line})
assert len(nodes)==len({r['nodeid'] for r in nodes})==1361 and collections.Counter(r['status'] for r in nodes)=={'PASSED':1349,'SKIPPED':12}
assert {r['worker'] for r in nodes}=={'gw0','gw1'} and len({r['nodeid'].split('::')[0] for r in nodes})==95
assert nodes==load(actual['complete_private_census']['path'])
assert len(summaries)==1 and '1349 passed, 12 skipped, 16 warnings in 111.49s' in summaries[0]['text']
assert len(guards)==2 and [g['stage'] for g in guards]==['before','after']
for g in guards:assert g['status']=='PASS' and g['source']==H and g['tree']==T and g['source_leaves']==1440 and g['native_original']==1192 and g['five_concrete_origins']==5
assert guards[0]['workspace_available_bytes']>=1288490189
proposal=load(actual['preexecution_owner']['path']);cfg=load(P/'frozen-current-source-full-inputs.json');terminal=load(actual['original_terminal']['path']);outer=load(actual['root_outer_terminal']['path']);release=load(O/'root-one-release.json');command=load(O/'root-one-command.json')
assert release=={'schema':1,'status':'ROOT_RELEASE_ONE_SERIALIZED_CONFIGURED_SOURCE_FULL','proposal_sha256':actual['preexecution_owner']['sha256'],'source':H,'tree':T,'independent_source_and_preexecution_review_GO':True,'serialized_no_other_heavy_or_installer':True}
assert outer['attempts']==1 and outer['root_outer_returncode']==0 and outer['root_release_sha256']==sha(O/'root-one-release.json') and outer['source']==H and outer['tree']==T
assert terminal['source']==H and terminal['tree']==T and terminal['status']=='PASS' and terminal['full_started'] and terminal['primary_returncode']==0 and terminal['primary_error_class'] is None and terminal['post_returncode']==0 and terminal['post_error_class'] is None
assert terminal['records']==actual['records']==[{'stage':'before','returncode':0},{'stage':'configured-full','returncode':0},{'stage':'after-always','returncode':0}]
assert command['source']==H and command['tree']==T and command['proposal_sha256']==actual['preexecution_owner']['sha256'] and command['independent_review_sha256']==actual['preexecution_independent']['sha256'] and command['attempts']==1 and command['serialized_heavy_slot']
cmd=command['command'];assert cmd.startswith('source /workspace/actions-cloud/activate.sh\nunset PYTHONOPTIMIZE\n') and 'export PYTEST_XDIST_AUTO_NUM_WORKERS=2' in cmd and 'timeout --signal=TERM --kill-after=10s 900s' in cmd and str(P/'launch_current_source_full_once.py') in cmd and sha(O/'root-one-release.json') in cmd
assert 'CONFIGURED_RUNTIME_SOURCE_FULL_TWO_WORKERS_NO_INTEGRATION' in text
# Every reference/mode and explicit payload is independently read after original completion.
pre_refs=[check(r) for r in proposal['frozen_input_bindings']];assert len(pre_refs)==14
light=load(actual['source_LIGHT_owner']['path']);lightrefs=[check(r) for r in light['frozen_bindings']];assert len(lightrefs)==45
assert git('show','-s','--format=%H %T %P',H).decode().split()==[H,T,A,B] and git('rev-parse','HEAD').decode().strip()==H and not git('status','--porcelain')
source=load(cfg['source_inventory']);assert len(source)==1440
for row in source:
 p=R/row['path'];body=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes();assert len(body)==row['bytes'] and hashlib.sha256(body).hexdigest()==row['sha256'] and stat.S_IMODE(p.lstat().st_mode)==row['fs_mode']
 assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==row['blob']
 if row['mode']!='120000':assert bool(p.stat().st_mode&0o111)==(row['mode']=='100755')
retained_refs=[check(row) for row in cfg['retained_actual_files_and_helpers']];assert len(retained_refs)==83 and len({r['path'] for r in retained_refs})==83
for path,digest in cfg['prepared30_inputs'].items():assert sha(R/path)==digest
assert len(cfg['prepared30_inputs'])==30 and len(cfg['concrete_origin_packages'])==5
baseline=load(cfg['original_native_config']);layout=Path(baseline['native_original_root']);native=baseline['native_original_members'];assert len(native)==1192 and {p.relative_to(layout).as_posix() for p in layout.rglob('*')}=={r['path'] for r in native}
for row in native:
 p=layout/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert not p.is_symlink() and sha(p)==row['content_sha256']
 elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert os.readlink(p)==row['link_target']
# Qualify permanent source scopes by complete named outcomes, not rollup counts.
module_counts={}
for row in nodes:
 key=row['nodeid'].split('::')[0];module_counts.setdefault(key,collections.Counter())[row['status']]+=1
shutdown=[r for r in nodes if 'test_shutdown_response_order.py::' in r['nodeid']];transport=[r for r in nodes if 'run_outputs/test_transport.py::' in r['nodeid']];assert len(shutdown)==10 and len(transport)==30 and all(r['status']=='PASSED' for r in shutdown+transport)
nodeproof=D/'private-independent-all1361-complete-current-sourcefull-terminal-nodes.json';nodeproof.open('x').write(json.dumps({'source':H,'tree':T,'nodes':nodes,'module_outcomes':{k:dict(v) for k,v in module_counts.items()},'source_only':True},indent=2)+'\n');nodeproof.chmod(0o600)
proof=D/'independent-postactual-source-and-original-payload-preservation-proof.json';proof.open('x').write(json.dumps({'head':H,'tree':T,'1440_source_bodies_GitOIDs_bytes_FS_modes_exact':True,'all14_preexecution_and45_LIGHT_binding_hash_modes_exact':True,'all83_payload_paths_bytes_modes_exact':retained_refs,'all1192_native_members_byte_mode_link_whole_set_exact':True,'own30_inputs_exact':True,'original_completed_before_after_guard_records':guards},indent=2)+'\n');proof.chmod(0o600)
patch=light['documentation_improvement']['exact_imported_accepted_delta'];check(patch);assert git('diff',A,H,'--','docs/skills/repository-operations.md','docs/skills/provenance-observability.md')==Path(patch['path']).read_bytes()
remaining=['Fresh exact1299/a54 fullhostedCI/reviews/policy and normalexistingbranch namedpush verification required before integration','Actualnative/browser/provider/installedconsumer/private/backend/full127/release remain HOLD; source configuredsuite does not admit their runtime gates','Current276producer258match10changed8added+5selectors remains UNQUALIFIED for92498; originalV5 and all old failures keep their identities','Before/after filepreservation is measured; full supervisor/native/process/readers cleanup remains UNKNOWN outside those selected source assertions','Actualaftercapacity1249505280B is below strictfreshfuturefloor1288490189B; this PASS does not release another heavy run','Original historical441/tenUNAVAILABLE and earlierzero-case selectionfailure unchanged; not reconstructed or relabeled']
out={'schema':'actions-independent-current2821299-original-configured-SOURCEFULL/v1','decision':'GO_EXACT_CURRENT1299_CONFIGURED_SOURCEFULL_NORMAL_EXISTING_BRANCH_SOURCE_PUSH_PREREQUISITE_ONLY','owner':bind(owner),'source':{'head':H,'tree':T,'ordered_parents':[A,B],'complete1440_typed_Git_FS_body_and_mode_equal':True},'one_original_execution':{'root_release':bind(O/'root-one-release.json'),'root_command':bind(O/'root-one-command.json'),'root_outer_terminal':actual['root_outer_terminal'],'root_outer_returncode':0,'root_outer_seconds':outer['elapsed_seconds'],'launcher_terminal':actual['original_terminal'],'original_log':actual['original_raw_log'],'primary_pre_post_returncodes':[0,0,0],'primary_error':None,'post_error':None,'original_complete_node_census':actual['complete_private_census'],'independent_node_census':bind(nodeproof),'actual_workers':['gw0','gw1'],'observed_nodes':1361,'unique_nodes':1361,'module_count':95,'PASS':1349,'SKIP':12,'FAIL':0,'ERROR':0,'warnings':16,'pytest_seconds':111.49,'deselected':'UNREPORTED','shutdown_source_PASS':10,'Linux_transport_source_PASS':30,'source_only_not_native_consumer_or_browser':True,'single_attempt_no_replay':True},'fresh_independent_postactual_preservation':bind(proof),'native_process_cleanup_and_internal_readers':'UNKNOWN_NOT_INFERRED_FROM_SUITE_OR_FILE_PRESERVATION','root_owner_independent_actual_review_field_PENDING_preserved':'This named independent successor supplies actualreview; original3467B owner remains unchanged','remaining_HOLD':remaining,'Documentation_improvement':{'Canonical_files_changed_or_proposed':['docs/skills/repository-operations.md','docs/skills/provenance-observability.md'],'Exact_verified_import_reuse':patch,'Durable_learning_captured':'Authenticate the complete whole-line node census, explicit rawpayload before/after fileguards and actualsource tuple separately. Two-worker configuredsource success and exact preservation do not establish native/browser/provider/process cleanup acceptance or release a next run below freshcapacityfloor.','Evidence':'Original347809B/81b977 log,1361completeunique terminalnodes95modules/1349PASS12SKIP16warnings; originalbefore+after PASS1440/1192 and independentfresh83payload/whole1192/source1440; exact8802B guideimport/bothparent lesson proof','Stale_or_ambiguous_guidance_removed':'Warnings measured16 from originalterminal, not guessed15. Full counts are unique wholeparameterized nodeIDs; original ownerPENDING is not rewritten, and originalfailed selection remainshistorical.','Remaining_uncertainty':remaining},'Upstream_disposition':'none','reviewer_no_guard_execution_tests_source_edits_native_provider_browser_download_install_branch_push_ready_merge':True,'review_script':bind(__file__)}
p=D/'OWNERFINAL-independent-current1299-original-configured-SOURCEFULL-review.json';p.open('x').write(json.dumps(out,indent=2)+'\n');p.chmod(0o400);print(json.dumps(bind(p)))
