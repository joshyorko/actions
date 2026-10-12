import ast,hashlib,json,os,stat,subprocess,re,xml.etree.ElementTree as ET
from pathlib import Path
R=Path('/workspace/engineering/runtime-checkout-eol');P=Path('/workspace/engineering/pr312-actual300-refresh');O=Path('/workspace/engineering/pr312-actual300-independent-LIGHT-review')
H='ec70a2928461941c129b1c05332dc441070e0184';A='77ed3de24f33412dff30e4e3c18841c4c09933ac';B='e3c29cde8878307912e55ed09b6436c0f91d06d5';T='47a1e4fceb22fd15eaee1ca380ad6c005abfdde6'
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def verify(x):
 b=bind(x['path']);assert b['bytes']==x['bytes'] and b['sha256']==x['sha256']
 if 'mode' in x:assert oct(stat.S_IMODE(Path(x['path']).stat().st_mode))==x['mode']
 return b
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*a])
def entries(commit):
 result={}
 for line in git('ls-tree','-rz',commit).split(b'\0'):
  if line:
   meta,name=line.split(b'\t',1);mode,kind,blob=meta.decode().split();result[os.fsdecode(name)]=(mode,kind,blob)
 return result
owner=bind(P/'OWNERFINAL-pr312-actual300-refresh-SOURCE-LIGHT-v2.json');assert owner['bytes']==32020 and owner['sha256']=='a55e76b7bc19419e77e505e962a14381e53d7c8a66ad37c270d35986d93f7765'
d=json.loads(Path(owner['path']).read_text());assert [d['head'],d['tree']]==[H,T] and d['ordered_parents']==[A,B]
assert git('show','-s','--format=%H %T %P',H).decode().split()==[H,T,A,B] and not git('status','--porcelain')
cur,old,target=entries(H),entries(A),entries(B);assert (len(cur),len(old),len(target))==(1426,1424,1423)
assert set(cur)==set(old)|set(target)
novel=[p for p,v in cur.items() if v!=old.get(p) and v!=target.get(p)];assert sorted(novel)==['action_server/src/actions/server/_server.py','docs/skills/repository-operations.md']
rows=json.loads(Path(d['complete_typed_proof']['path']).read_text())['source_entries'];assert len(rows)==1426
for row in rows:
 assert cur[row['path']]==(row['mode'],row['kind'],row['blob']);b=git('cat-file','blob',row['blob']);assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
 p=R/row['path'];assert not p.is_symlink() and p.read_bytes()==b and bool(p.stat().st_mode&stat.S_IXUSR)==(row['mode']=='100755')
server='action_server/src/actions/server/_server.py';s=git('show',H+':'+server).decode();normalized=ast.parse(s)
for node in ast.walk(normalized):
 if isinstance(node,ast.ImportFrom) and node.module=='fastapi':node.names=[x for x in node.names if x.name!='BackgroundTasks']
 if isinstance(node,ast.FunctionDef) and node.name=='shutdown':
  assert ast.unparse(node.args)=='background_tasks: BackgroundTasks, timeout: int=-1';node.args.args=node.args.args[1:]
  calls=[x for x in node.body if isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and ast.unparse(x.value.func)=='background_tasks.add_task'];assert len(calls)==1
  assert ast.unparse(calls[0].value.args[0])=='_thread.interrupt_main';calls[0].value=ast.Call(func=ast.Attribute(value=ast.Name(id='_thread',ctx=ast.Load()),attr='interrupt_main',ctx=ast.Load()),args=[],keywords=[])
assert ast.dump(normalized,include_attributes=False)==ast.dump(ast.parse(git('show',B+':'+server)),include_attributes=False)
shutdown='action_server/tests/action_server_tests/test_shutdown_response_order.py';assert cur[shutdown]==old[shutdown]
for p in ['.gitattributes','.github/workflows/_gen_workflows.py','.github/workflows/actions_runtime_tests.yml','.github/workflows/actions_runtime_pypi_release.yml','devutils/tests/test_runtime_checkout_bytes.py','devutils/tests/test_runtime_checkout_workflows.py']:assert cur[p]==old[p]
selected=[p for p in cur if p.startswith('action_server/src/') and p.endswith('.py')]+['action_server/src/actions/server/README.md','action_server/src/actions/server/bin/.gitignore','action_server/src/actions/server/index.html','action_server/src/actions/server/templates/action-templates.yaml','action_server/src/actions/server/vendored_deps/README.md','action_server/frontend/apps/runtime/index.html'];assert len(selected)==208 and len(set(selected))==208
changed=[p for p in selected if p in old and cur[p]!=old[p]];added=[p for p in selected if p not in old];assert changed==[server] and added==['action_server/src/actions/server/run_outputs/transport.py']
before=json.loads(Path(d['before_source']['path']).read_text());assert before['measured_refs']==len(before['preserved_refs'])==212
refs=[verify(x) for x in before['preserved_refs']]+[verify(x) for x in d['private_refs']]+[verify(d['complete_typed_proof']),verify(d['before_source'])]
prep=json.loads((P/'own-Bootstrap-reuse-inputs-and-origins.json').read_text());assert prep['measured_inputs']==len(prep['inputs_exact_prepared_git_bytes_sha256'])==30 and prep['new_Bootstrap_executed'] is False
for name,h in prep['inputs_exact_prepared_git_bytes_sha256'].items():
 assert hashlib.sha256((R/name).read_bytes()).hexdigest()==h and hashlib.sha256(git('show',prep['prepared_source']+':'+name)).hexdigest()==h
for name,row in prep['own5venvs_current_config_and_python'].items():
 assert hashlib.sha256((R/name/'.venv/pyvenv.cfg').read_bytes()).hexdigest()==row['config_sha256'] and str((R/name/'.venv/bin/python').resolve())==row['python_resolved']
assert len(prep['own5actual_prefix_and_source_origin_assertions'])==5
for row in prep['own5actual_prefix_and_source_origin_assertions']:assert Path(row['prefix']).is_relative_to(R) and Path(row['origin']).is_relative_to(R)
node_sets={}
for name,count in [('current-union-scoped-junit.xml',116),('current-EOL-junit.xml',10)]:
 cases=list(ET.parse(P/name).getroot().iter('testcase'));assert len(cases)==count and not any(x.find(k) is not None for x in cases for k in ['skipped','failure','error']);ids=[x.get('classname')+'::'+x.get('name') for x in cases];assert len(set(ids))==count;node_sets[name]=ids
log=(P/'current-union-cached-LIGHT.private.log').read_text();assert '96 passed in 15.41s' in log and '116 passed' in log and '10 passed' in log and 'Success: no issues found in 352 source files' in log and 'GENERATOR8_DEPENDABOT_AND_ALL30_YAML_ROUNDTRIP_PASS' in log
imports=json.loads((P/'canonical-both-parent-import-proof.json').read_text())
for row in imports['imports']:
 verify(row['patch']);diff=git('diff',imports['base'],row['parent'],'--',row['canonical_file']).decode();assert Path(row['patch']['path']).read_text()==diff
 blocks=[];block=[]
 for line in diff.splitlines():
  if line.startswith('+') and not line.startswith('+++'):block.append(line[1:])
  elif block:blocks.append('\n'.join(block));block=[]
 if block:blocks.append('\n'.join(block))
 assert len(blocks)==row['exact_added_blocks_retained'] and all(x in (R/row['canonical_file']).read_text() for x in blocks)
ret=json.loads((P/'post-light-native1192-helper-browser-retained.json').read_text());assert (P/'post-light-native1192-helper-browser-retained.json').read_bytes()==(P/'pre-edit-native1192-helper-browser-retained.json').read_bytes()
for k in ['original_manifest','original_inventory','original_assets_zip','original_frozen_executable','browser','historical_V5_checkpoint','historical_V5_independent_review','immutable_proposal']:verify(ret[k])
for row in ret['frozen_helper_original_and_snapshot_bindings'].values():verify(row['original']);verify(row['snapshot']);assert stat.S_IMODE(Path(row['snapshot']['path']).stat().st_mode)==0o444
assert (P/'post-light-raw18-frozen50-Node-frontend-retained.json').read_bytes()==(P/'pre-edit-raw18-frozen50-Node-frontend-retained.json').read_bytes()
proof={'owner':owner,'source':[H,T,A,B],'complete_typed_parent_union':{'current':1426,'original':1424,'target':1423,'parent_exact':1424,'novel':novel},'whole_target_server_AST_normalized_exact':True,'current_EOLog_selected':208,'preserved212_and_current_bindings':refs,'current_XML_node_sets':node_sets,'both_parent_canonical_imports':imports,'original1192_helper_V5_retained_files_exact':True,'all_source_FS_exec_exact':True,'current_clean':True}
p=O/'complete-independent-current-ec70-LIGHT-proof.private.json';p.write_text(json.dumps(proof,indent=2)+'\n');p.chmod(0o600)
result={'schema':'independent-pr312-current-e3c-SOURCE-LIGHT-v1','decision':'GO_CURRENT_EC70_SOURCE_LIGHT_ONLY_SOURCEFULL_AND_FRESH_HOSTED_ACCEPTANCE_HOLD','head':H,'tree':T,'ordered_parents':[A,B],'actual_target':B,'existing_branch':'fix/runtime-checkout-eol-20261011','source':{'complete_typed_Git_FS_exec_entries':1426,'all_parent_paths_preserved':True,'parent_exact_entries':1424,'automatic_novel_bodies':novel,'whole_target_server_AST_except_original_background_shutdown_exact':True,'all_original10_shutdown_test_bytes':True,'six_original_EOLog_control_files_exact':True,'current_EOLog_selection':{'Python':202,'packaged_text':5,'frontend_HTML':1,'total':208,'old_selected207_historical_only':True,'old_unchanged_bodies':206}},'LIGHT':{'Doctor':'RetainedPASS','prepared_inputs_reused':30,'concrete_owned_venv_config_interpreter_origins':5,'Toolkit_PASS':96,'shutdown_auth_incoming_transport_unique_PASS':116,'current_EOLog_unique_PASS':10,'skipped_failed_errors_in_scoped_XML':0,'configured_lint':'PASS','configured_type_files':352,'generator_roundtrips':8,'all_GitHub_YAML':30,'execution_scope':'Original cached prepared toolkit only; reviewer no test/gateway imports/exec'},'preserved_original_ref_count':212,'original_failure_and_old_full_scope':'Original770WindowsFAIL/ReadError10053 retained unchanged; old77 fullproposal4739 NOTRUN, original770/618 olderfull historical, no currentWindows/native/actual claim','FULL_preexecution':'Separate owner7346 review pending; stale true1424/141 output schema observed despite actual1426/212 guards, successor required before execution admission','proof':bind(p),'owner':owner,'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md and docs/skills/provenance-observability.md exact both-parent accepted guide imports reused','Durable_learning_captured':'ASGI completed response send precedes background interruption, but client delivery/natural exit/cleanup remain independent. Incoming Actor/grant/provider transport and owned ignored RCC preparation maintain their original boundaries. EOL selection derives the current208 inputs rather than carrying old207 counts.','Evidence':imports,'Stale_or_ambiguous_guidance_removed':'No synchronous-shutdown or old-green-Windows claim; preannouncement29929/079d source-input metadata superseded by honest current208 owner32020/a55, no gate rerun or source rewrite','Remaining_uncertainty':'Current sourceFULL and platform client/natural exit/native/release tests remain unobserved; fullpreexec output schema correction remains pending'},'Upstream_disposition':'none'}
f=O/'OWNERFINAL-independent-pr312-current-ec70-SOURCE-LIGHT-review.json';f.write_text(json.dumps(result,indent=2)+'\n');f.chmod(0o444)
assert bind(Path(owner['path']))==owner and not git('status','--porcelain');print(json.dumps(bind(f)))
