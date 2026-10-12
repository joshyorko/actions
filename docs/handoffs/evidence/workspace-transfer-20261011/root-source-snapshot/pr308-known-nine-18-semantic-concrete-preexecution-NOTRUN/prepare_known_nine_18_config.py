import ast,datetime,hashlib,json,os,stat
from pathlib import Path
ROOT=Path('/workspace/engineering/pr308-known-nine-18-semantic-concrete-preexecution-NOTRUN');os.umask(0o077)
def row(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(s.st_mode))}
def put(name,data):
 p=ROOT/name
 if not isinstance(data,str):data=json.dumps(data,indent=2,sort_keys=True)+'\n'
 with p.open('x') as f:f.write(data);f.flush();os.fsync(f.fileno())
 p.chmod(0o400);return row(p)
p=Path('/workspace/engineering/pr308-corrected-nine-semantic-mutant-readonly-command-plan-NOTRUN/OWNERFINAL-known-nine-semantic-mutant-RED-restored-GREEN-exact-command-contract-plan-NOTRUN.json')
assert row(p)['sha256']=='f179092502812f9d3884b077c57f4e4df955c156758dd22709b489e2d8aa6eae'
plan=json.loads(p.read_bytes())
for r in plan['all_original_bindings']:assert row(r['path'])==r
baseline=json.loads(Path(plan['baseline_dependency']['path']).read_bytes());assert baseline['decision']=='GO_ORIGINAL_CURRENT8D49_CORRECTED_NINE_ONCE2_BASELINE_ONLY'
assert baseline['counts']=={'passed':9,'failed':0,'errors':0,'skipped':0}
source=next(r for r in plan['all_original_bindings'] if r['sha256']=='a577d21615877bc19a88ca141e5c8ac7c9779120abf7f86b7a6ec6d2367d5da2')
text=Path(source['path']).read_text();tree=ast.parse(text);names=[n.name for n in tree.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
assert names==[c['exact_test_name'] for c in plan['known_cases']] and len(names)==9
phases=[]
for case in plan['known_cases']:
 pred=case['semantic_RED_predicate'];assert text.splitlines()[pred['source_line']-1].strip()==pred['assertion_source']
 for kind in ('RED','RESTORED_GREEN'):
  old=case['phases'][kind];cmd=list(old['argv']);i=cmd.index('timeout');assert cmd[i+3]=='120s';cmd[i+3]='15s'
  phases.append({'label':case['label'],'kind':kind,'test':case['exact_test_name'],'predicate':pred,'argv':cmd,'cwd':old['cwd'],'parent_seconds':30,'output_parent':old['output_parent'],'stdout':old['stdout'],'stderr':old['stderr'],'junit':old['junit'],'expected_returncode':old['expected_returncode'],'expected_counts':old['expected_counts']})
assert len(phases)==18 and len({q['output_parent'] for q in phases})==18
owned=Path(plan['root_once']);assert not owned.exists() and not owned.is_symlink()
scfgrow=next(r for r in plan['all_original_bindings'] if r['sha256']=='81f52920b50e67619b3bb418a7c1034a2106ec52f4badd71b9d85e29b7376820');scfg=json.loads(Path(scfgrow['path']).read_bytes())
config={'schema':1,'status':'KNOWN_NINE_18_SEMANTIC_RED_FRESH_GREEN_CONCRETE_NOTRUN','source':plan['source'],'tree':plan['tree'],'source_leaves':1440,'plan_binding':row(p),'baseline_dependency':plan['baseline_dependency'],'test_source':source,'root_once':plan['root_once'],'root_release_path':'/workspace/engineering/root-one-known-nine-18-semantic-controls-release.json','activation':scfg['expected_activation_exports'],'path_prefix2':['/workspace/actions-cloud/bin','/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin'],'forbidden_operator_exports':scfg['forbidden_actual_operator_exports'],'guard_argv':plan['before_and_alwayspost_argv'],'guard_parent_seconds':135,'origins':plan['origins'],'origin_parent_seconds':30,'origin_child_seconds':15,'phases':phases,'case_order':names,'original_bindings':plan['all_original_bindings']+[row(p)],'outer_seconds':1200,'outer_kill_grace_seconds':10,'root_parent_seconds':1230,'nominal_python_fallback_sum_seconds':960,'margin_seconds':240,'required_review_status':'INDEPENDENT_KNOWN_NINE_SEMANTIC_RED_GREEN_PREEXECUTION_GO','required_release_scope':'ROOT_DISTINCT_ONE_KNOWN_NINE_18_SEMANTIC_RED_RESTORED_GREEN','raw_log_max_decode_bytes':33554432,'JUnit_max_decode_bytes':8388608,'scope':'SOURCE_ONLY; syntheticworkers; nestedcatalogsnapshot sensitivity NOTRUN; no native/main/provider/reallease/reap/adoption','capture':datetime.datetime.now(datetime.timezone.utc).isoformat()}
print(json.dumps(put('FROZEN-known-nine-18-semantic-15s-config-NOTRUN.json',config)))
