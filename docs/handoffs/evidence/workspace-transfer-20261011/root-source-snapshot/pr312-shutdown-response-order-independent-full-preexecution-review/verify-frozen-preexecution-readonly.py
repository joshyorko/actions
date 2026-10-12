import ast,hashlib,json,os,stat,subprocess
from pathlib import Path
D=Path('/workspace/engineering/pr312-shutdown-response-order-configured-full-proposal');OUT=Path(__file__).resolve().parent;ROOT=Path('/workspace/engineering/runtime-checkout-eol')
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def check(r):
 assert bind(r['path'])=={k:r[k] for k in ('path','bytes','sha256')}
 if 'mode' in r:assert oct(stat.S_IMODE(Path(r['path']).stat().st_mode))==r['mode']
def load(p):return json.loads(Path(p).read_bytes())
owner=D/'OWNERFINAL-pr312-current77-managed-activation-configured-full-proposal-v3.json';assert bind(owner)=={'path':str(owner),'bytes':19846,'sha256':'473900aaa9beed01b22cb65bb7c0ba992918ba584c912bc08599e339946315a4'};r=load(owner)
assert len(r['bindings'])==25
for row in r['bindings']:check(row)
check(r['current_LIGHT']);light=load(r['current_LIGHT']['path'])
for row in light['private_refs']:check(row)
pre=load(light['before_source']['path'])
for row in pre['distinct_preserved_refs']:check(row)
assert len(light['private_refs'])==41 and len(pre['distinct_preserved_refs'])==141
assert r['head']=='77ed3de24f33412dff30e4e3c18841c4c09933ac' and r['tree']=='943c9b88d5d508a4c59b0461b6220ec86e1a7d62'
assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==r['head']
assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip()==r['tree']
command=r['command'];argv=command['argv'];assert argv[:4]==['bash','--noprofile','--norc','-c'];assert argv[4]=='set -euo pipefail\nsource "$1"\n"$2" "$3" "$4"\nshift 4\nexec "$@"\n'
assert argv[6]=='/workspace/actions-cloud/activate.sh' and argv[7]=='/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python' and argv[8]==str(D/'managed_activation_preflight_v3.py')
assert argv[10:23]==['env','PYTEST_XDIST_AUTO_NUM_WORKERS=2','timeout','--signal=TERM','--kill-after=10s','600s','/workspace/actions-cloud/bin/rcc','task','script','-r','developer/toolkit.yaml','--','python']
assert argv[23]=='-c';check(command['exact_body']);assert argv[24]==Path(command['exact_body']['path']).read_text()
assert command['TERM_seconds']==600 and command['KILL_grace_seconds']==10 and command['root_parent_subprocess_bound_seconds']==640 and command['attempts']==1 and command['pytest_workers']==2
body=ast.parse(argv[24]);calls=[n for n in ast.walk(body) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='toolkit' and n.func.attr=='poetry']
assert any([ast.literal_eval(x) for x in n.args]==['action_server','run','invoke','test-not-integration'] for n in calls if all(isinstance(x,ast.Constant) for x in n.args))
assert 'os.environ["PYTEST_XDIST_AUTO_NUM_WORKERS"]="2"' in argv[24] and argv[24].index('os.environ["PYTEST_XDIST_AUTO_NUM_WORKERS"]="2"')<argv[24].index('toolkit.poetry("action_server","run","invoke","test-not-integration")')
assert len(r['allowlisted_activation_exports'])==18 and r['activation_export_count_including_PATH']==19 and r['PATH_condition'].startswith('First entry /workspace/actions-cloud/bin')
assert bind('/workspace/actions-cloud/activate.sh')['sha256']=='6478b7b31155b8594e4dbd66f79d8a9e94e63543740d81508af8b635056f646a'
guard=D/'current77_readonly_guards_v3.py';gt=ast.parse(guard.read_text());globals={n.targets[0].id:ast.literal_eval(n.value) for n in gt.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('ROOT','OWNER','EXPECTED_OWNER_SHA','HEAD','TREE','EXPORTS') and isinstance(n.value,(ast.Constant,ast.Dict))}
assert globals['EXPORTS']==r['allowlisted_activation_exports'] and globals['HEAD']==r['head'] and globals['TREE']==r['tree']
assert 'PR312_CURRENT77_SERIALIZED_HEAVY_SLOT' in guard.read_text() and 'root-one-pr312-current77-only' in guard.read_text() and 'available>=1200000000' in guard.read_text()
# Compare v2/v3 only two declared hash-only schema accesses; no execution/gate/body change.
v2=(D/'current77_readonly_guards_v2.py').read_text();v3=guard.read_text();expected=v2.replace('verify(proposal["helper_bindings"])','assert binding(proposal["helper_bindings"]["path"])["sha256"]==proposal["helper_bindings"]["sha256"]').replace('verify(proposal["driver"]["frontend_lock"])','assert binding(proposal["driver"]["frontend_lock"]["path"])["sha256"]==proposal["driver"]["frontend_lock"]["sha256"]')
assert ast.dump(ast.parse(expected),include_attributes=False)==ast.dump(ast.parse(v3),include_attributes=False)
retained=load('/workspace/engineering/pr312-shutdown-response-order-source/post-LIGHT-native1192-helper-browser-retained.json');historical=load(retained['immutable_proposal']['path']);assert 'bytes' not in historical['helper_bindings'] and 'bytes' not in historical['driver']['frontend_lock']
for row in [historical['helper_bindings'],historical['driver']['frontend_lock']]:assert bind(row['path'])['sha256']==row['sha256']
check(retained['historical_V5_checkpoint']);checkpoint=load(retained['historical_V5_checkpoint']['path']);assert len(checkpoint['raw_receipts_private_do_not_commit'])==18 and len(checkpoint['frozen_posthashes'])==50
for row in checkpoint['raw_receipts_private_do_not_commit']:check(row)
# All immutable required data-only verification rows have real size/hash schema.
for key in ('original_manifest','original_inventory','original_assets_zip','original_frozen_executable','browser','historical_V5_checkpoint','historical_V5_independent_review','immutable_proposal'):check(retained[key])
for row in retained['frozen_helper_original_and_snapshot_bindings'].values():check(row['original']);check(row['snapshot'])
reuse=load('/workspace/engineering/pr312-shutdown-response-order-source/own-Bootstrap-reuse-inputs-and-origins.json');assert len(reuse['inputs_exact_prepared_git_bytes_sha256'])==30
for name,h in reuse['inputs_exact_prepared_git_bytes_sha256'].items():assert bind(ROOT/name)['sha256']==h
for name,row in reuse['own5venvs_current_config_and_python'].items():assert bind(ROOT/name/'.venv/pyvenv.cfg')['sha256']==row['config_sha256'] and str((ROOT/name/'.venv/bin/python').resolve())==row['python_resolved']
plugin=ROOT/'action_server/.venv/lib/python3.12/site-packages/xdist/plugin.py';pt=ast.parse(plugin.read_text());fn=next(n for n in pt.body if isinstance(n,ast.FunctionDef) and n.name=='pytest_xdist_auto_num_workers');source=ast.get_source_segment(plugin.read_text(),fn);assert source.index('PYTEST_XDIST_AUTO_NUM_WORKERS')<source.index('psutil') and 'return int(env_var)' in source
nested=[bind(plugin),bind(ROOT/'developer/toolkit.py'),bind(ROOT/'action_server/tasks.py')];task=(ROOT/'action_server/tasks.py').read_text();assert '"auto"' in ast.get_source_segment(task,next(n for n in ast.parse(task).body if isinstance(n,ast.FunctionDef) and n.name=='test_not_integration'))
# Postguard calls same source/reference validator; no test rerun or gate waiver.
assert command['post_argv'][1]==str(D/'post_full_readonly_guards_v3.py')
post=ast.parse((D/'post_full_readonly_guards_v3.py').read_text());assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='source_and_references' for n in ast.walk(post))
check(r['documentation_improvement']['exact_delta'])
proof={'status':'GO_CONDITIONAL_PREEXECUTION_ONLY_ROOT_ENFORCED_PARENT640_AND_FRESH_CAPACITY','owner':bind(owner),'source':{'head':r['head'],'tree':r['tree'],'clean':True},'all25proposal_plus41LIGHT_and141original_refs_exact':True,'source_LIGHT_independent_GO':bind('/workspace/engineering/pr312-shutdown-response-order-independent-LIGHT-review/OWNERFINAL-independent-pr312-shutdown-response-order-SOURCE-LIGHT-review.json'),'v3_only_two_hash_only_schema_corrections':'ExactAST comparison v2; original v1/v2 immutable/NOTEXECUTED','managed_activation19_worker2_and_unchanged_600TERM10_configured_Invoke_body':True,'postguard_same_source_and_refs':True,'nested_installed_worker_source_bindings_root_must_rehash_before_launch':nested,'exact_announced_argv':argv,'required_root_parent_adoption':'Enforce actual parent640 around exact bash command; preserve real primaryrc/log before distinct postguards; run postguards on every outcome. Metadata bound alone is not executed timer proof.','fresh_capacity_and_heavy_slot':'Root must independently recheck>=1200000000bytes and serialized slot after308terminal; review grants no execution','no_execution':'No preflight/launcher/gateway/test/native/browser/provider/import performed by reviewer','canonical_exact_delta':r['documentation_improvement']['exact_delta'],'upstream_disposition':'none'}
f=OUT/'independent-frozen-v3-preexecution-proof.json';assert not f.exists();f.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');f.chmod(0o444);print(json.dumps({'proof':bind(f),'status':proof['status']}))
