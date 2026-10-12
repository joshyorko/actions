import hashlib,json,re,stat,subprocess
from collections import Counter
from pathlib import Path
O=Path('/workspace/engineering/pr308-compatibility-current-sourcefull-independent-actual-review');B=Path('/workspace/engineering/pr308-rcc-compatibility-SOURCEFULL-preexecution');P=Path('/workspace/engineering/root-rcc308-one-current-b614-source-full');R=Path('/workspace/engineering/pr308')
def bind(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return {'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}
def emit(n,d):
 p=O/n
 with p.open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
 p.chmod(0o600);return bind(p)
def git(*args):return subprocess.check_output(['git','--no-optional-locks',*args],cwd=R)
owner=P/'OWNERFINAL-root-current-b614-configured-SOURCEFULL.json';a=bind(owner);assert a['bytes']==6277 and a['sha256']=='eb73d4a34acaf77266f6aff75f758fa674e6b48aff968a31bbeca85148319bf8'
d=json.loads(owner.read_bytes());refs=[]
for key in ['actual_full_log','full_terminal','root_parent_terminal','root_release','one_attempt_marker','preexecution_owner','preexecution_independent','SOURCE_LIGHT','SOURCE_LIGHT_independent']:
 row=d[key];assert bind(Path(row['path']))==row;refs.append(row)
assert len(d['launcher_input_bindings10'])==10
for row in d['launcher_input_bindings10']:assert bind(Path(row['path']))==row
light=json.loads(Path(d['SOURCE_LIGHT']['path']).read_bytes());assert len(light['frozen_bindings'])==71
for row in light['frozen_bindings']:assert bind(Path(row['path']))==row
proposal=json.loads(Path(d['preexecution_owner']['path']).read_bytes());ind=json.loads(Path(d['preexecution_independent']['path']).read_bytes());release=json.loads(Path(d['root_release']['path']).read_bytes());parent=json.loads(Path(d['root_parent_terminal']['path']).read_bytes());term=json.loads(Path(d['full_terminal']['path']).read_bytes());mark=json.loads(Path(d['one_attempt_marker']['path']).read_bytes())
assert release['argv']==ind['reviewed_root_execution_argv']==['timeout','--signal=TERM','--kill-after=10s','900s',*proposal['outer_launcher_argv']]
assert release['cwd']==str(R) and release['one_attempt_only'] is True and release['workspace_capacity_observation']>=1200000000
assert parent['returncode']==0 and parent['exception_category'] is None and parent['elapsed_seconds']<900
assert bind(Path(parent['parent_log']['path']))==parent['parent_log'];refs.append(parent['parent_log'])
assert parent['authorization']==d['root_release']
for row in release['frozen_input_bindings']:assert bind(Path(row['path']))==row
assert term['overall_status']=='PASS' and term['full_started'] is True and term['primary_configured_returncode']==term['postcondition_returncode']==0 and term['primary_exception_category'] is None and term['no_automatic_retry'] is True
assert len(term['commands'])==3 and all(x['returncode']==0 for x in term['commands'])
assert term['commands'][1]['argv']==proposal['configured_full_argv'] and term['commands'][1]['seconds']<600 and term['seconds']<850 and term['log']==d['actual_full_log']
assert mark['one_attempt_only'] is True and mark['proposal_sha256']==d['preexecution_owner']['sha256'] and mark['source']==term['source']=={'head':'b614864ba9da55c13662894b6ef3c8515d9fdb25','tree':'6fa4f5c1e9837a0d893868255575b355b3977fae'}
raw=Path(d['actual_full_log']['path']).read_text();rows=[]
for line in raw.splitlines():
 m=re.fullmatch(r'\[gw([0-9]+)\]\s+\[\s*[0-9]+%\]\s+(PASSED|SKIPPED|FAILED|ERROR)\s+(.+?)\s*',line)
 if m:rows.append({'worker':'gw'+m[1],'status':m[2],'node_id':m[3]})
assert len(rows)==len({x['node_id'] for x in rows})==1376 and {x['worker'] for x in rows}=={'gw0','gw1'}
counts=dict(Counter(x['status'] for x in rows));assert counts=={'PASSED':1363,'SKIPPED':13}
assert raw.count('created: 2/2 workers')==raw.count('2 workers [1376 items]')==1
assert re.search(r'1363 passed, 13 skipped, 15 warnings in 132\.62s',raw)
scoped={};wanted={'test_rcc_runtime_adapter.py','test_dakota_rcc_acceptance.py','test_source_staging_rcc_consumer.py'}
for file in sorted(wanted):
 items=[x for x in rows if x['node_id'].split('::')[0].endswith('/'+file)];scoped[file]={'counts':dict(Counter(x['status'] for x in items)),'node_ids':[x['node_id'] for x in items]}
assert scoped['test_rcc_runtime_adapter.py']['counts']=={'PASSED':107,'SKIPPED':1}
assert scoped['test_dakota_rcc_acceptance.py']['counts']=={'PASSED':59}
assert scoped['test_source_staging_rcc_consumer.py']['counts']=={'PASSED':14}
assert sum(x['counts'].get('PASSED',0) for x in scoped.values())==180
reports=[];retentions=[]
for stage in ['before','after']:
 p=B/(stage+'-full-source-prepost.json');report=json.loads(p.read_bytes());reports.append(bind(p))
 assert report['stage']==stage and report['source']==dict(term['source'],clean=True) and report['complete1421_Git_FS_body_execmodes_exact'] is True and report['light71_bindings_exact']==71 and report['prepared30_exact'] is True and report['activation18_exports_and_PATH19_exact'] is True and report['worker_env']=='PYTEST_XDIST_AUTO_NUM_WORKERS=2' and len(report['five_own_concrete_prefix_origins'])==5
 if stage=='before':assert report['fresh_workspace_bytes']>=1200000000
 for origin in report['five_own_concrete_prefix_origins']:assert Path(origin['prefix']).is_relative_to(R) and Path(origin['origin']).is_relative_to(R)
 p=B/(stage+'-full-original-native-helper-browser-V5-readback.json');retentions.append(bind(p));ret=json.loads(p.read_bytes());orig=json.loads(Path(light['retention']['before']['path']).read_bytes());assert ret==orig
 assert stat.S_IMODE(Path(d['actual_full_log']['path']).stat().st_mode)==0o600
assert raw.count('READ_ONLY_ORIGINAL1192_NATIVE_HELPER_BROWSER_V5_RETENTION=PASS')==2
assert git('rev-parse','HEAD').decode().strip()==term['source']['head'] and git('rev-parse','HEAD^{tree}').decode().strip()==term['source']['tree'] and not git('status','--porcelain')
proof=json.loads(Path(light['complete_committed_body_mode_proof']['path']).read_bytes());assert len(proof['complete1421_Git_FS_body_mode_exact'])==1421
for n,row in proof['complete1421_Git_FS_body_mode_exact'].items():
 p=R/n;assert bind(p)['sha256']==row['sha256'] and stat.S_ISREG(p.lstat().st_mode) and bool(p.stat().st_mode&0o111)==(row['mode']=='100755')
prepared=json.loads(Path('/workspace/engineering/pr308-rcc-compatibility-source/own-Bootstrap-reuse-inputs-and-origins.json').read_bytes());assert len(prepared['inputs_exact_prepared_git_bytes_sha256'])==30
for n,h in prepared['inputs_exact_prepared_git_bytes_sha256'].items():assert bind(R/n)['sha256']==h
for pkg,row in prepared['own5venvs_current_config_and_python'].items():assert bind(R/pkg/'.venv/pyvenv.cfg')['sha256']==row['config_sha256']
# Retained RED/static/pin helpers are immutable LIGHT refs, not reconstructed or rerun.
assert all(bind(Path(row['path']))==row for row in light['frozen_bindings']) and all(bind(Path(row['path']))==row for row in d['launcher_input_bindings10'])
private=emit('complete-private-original-full-node-and-scoped-identity-proof.json',{'owner':a,'complete_terminal_nodes':rows,'scoped_current180':scoped,'reports':reports,'native_retention_reports':retentions,'root_original_refs':refs,'all71_and10_prepost_exact':True})
safe=emit('safe-independent-current-b614-full-original-readback.json',{'status':'PASS_ACTUAL_CURRENT_SOURCEFULL_ONLY','owner':a,'source':term['source'],'terminal_nodes':1376,'unique_terminal_nodes':1376,'counts':counts,'warnings':15,'actual_workers':2,'scoped_current_passed':180,'scoped_existing_optin_skipped':1,'scoped_counts_by_file':{k:v['counts'] for k,v in scoped.items()},'pre_post_returncodes':[0,0],'full_returncode':0,'parent_returncode':0,'pytest_seconds':132.62,'full_command_seconds':term['commands'][1]['seconds'],'prefullpost_launcher_seconds':term['seconds'],'root_parent_seconds':parent['elapsed_seconds'],'root_release_workspace_bytes':release['workspace_capacity_observation'],'before_preflight_workspace_bytes':json.loads(Path(reports[0]['path']).read_bytes())['fresh_workspace_bytes'],'after_workspace_bytes':json.loads(Path(reports[1]['path']).read_bytes())['fresh_workspace_bytes'],'source1421_FSexec_clean71and10_30config_five_origins_retention_exact':True,'new_binary_actual':'NOT_RUN','actual_process_cleanup_scope':parent['actual_cleanup'],'private_complete_proof':private})
print(json.dumps(safe))
