import ast, datetime, hashlib, json, os, stat
from pathlib import Path
ROOT=Path('/workspace/engineering/pr308-corrected-nine-once2-baseline-preexecution');os.umask(0o077)
def row(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();raw=p.read_bytes();return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'mode':oct(stat.S_IMODE(s.st_mode))}
def put(name,data,mode=0o400):
 p=ROOT/name
 if not isinstance(data,(str,bytes)):data=json.dumps(data,indent=2,sort_keys=True)+'\n'
 if isinstance(data,str):data=data.encode()
 with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 p.chmod(mode);return row(p)
def verify(r):assert row(r['path'])==r
oldcontract=Path('/workspace/engineering/pr308-current8d49-nine-real-reload-drain-independent-preexecution-review/frozen-nine-real-source-control-baseline-first-ROOT-command-contract-NOTRUN.json')
old=json.loads(oldcontract.read_bytes());assert row(oldcontract)['sha256']=='5f1874357496fe9c890c1acfec43fa114d51c658bd23ea23578fc3c910c1f287'
ind=Path('/workspace/engineering/pr308-private-corrected-nine-source-independent-review/OWNERFINAL-independent-private-corrected-nine-catalog-lock-SOURCE_ONLY-review.json');v=json.loads(ind.read_bytes());assert row(ind)['sha256']=='aa3f927ef250c86d8b76e02e21f6382f2a894c22b0bba7f285b08c5f60f13da4'
for k in ('owner_binding','source_owner_binding','standalone_binding','original_failure_binding','source_proof','prospective_append_binding'):verify(v[k])
source=Path(v['standalone_binding']['path']);assert row(source)['sha256']=='a577d21615877bc19a88ca141e5c8ac7c9779120abf7f86b7a6ec6d2367d5da2'
names=[n.name for n in ast.parse(source.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')];assert names==[c['test'] for c in old['case_map']] and len(names)==9
owned=Path('/workspace/engineering/pr308-current8d49-nine-real-source-control-root-once-2');assert not owned.exists() and not owned.is_symlink()
argv=[a.replace(old['test_source_binding']['path'],str(source)).replace('root-once-1','root-once-2') for a in old['baseline_argv_after_exact_managed_activation']]
assert argv[10]=='120s' and argv[11]=='/workspace/engineering/pr308/action_server/.venv/bin/python'
assert 'original-junit.xml' in argv[-2] and '--noconftest' in argv and '-n0' in argv
contract=dict(old);contract.update({'status':'CORRECTED_NINE_ONCE2_BASELINE_PREPARATION_NOT_RUN','test_source_binding':row(source),'baseline_argv_after_exact_managed_activation':argv,'sequence':'THIS EXECUTABLE: exactly one corrected no-mutant baseline only. Require nine unique PASS0FAIL0ERROR0SKIP JUnit and before/five-origins/always-post success. All nine mutants and snapshot sensitivity phases require separate explicit review/release after genuine baseline PASS; no automatic loop/retry.','root_namespace':str(owned)+' MUST_BE_ABSENT; exclusive0700 phase/basetemp/absolute logger/JUnit outputs; private0600 fsynced originals before result admission.','scope':'SOURCE-ONLY nine actual SQLite/import/routes/pool algorithm controls with synthetic worker handles; no native MAIN/provider/browser/reaping proof.','original_failed_baseline':v['original_failure_binding'],'corrected_source_independent':row(ind),'corrected_source_owner':v['source_owner_binding'],'corrected_final_owner':v['owner_binding'],'original_unchanged_contract':row(oldcontract),'original_unchanged_launcher':row('/workspace/engineering/root-current8d49-nine-real-baseline-once.py'),'mutants':'NOT_RUN_NOT_AUTHORIZED_BY_THIS_LAUNCHER'})
contractrow=put('frozen-corrected-nine-once2-baseline-only-command-contract-NOTRUN.json',contract)
sourcecfg=Path('/workspace/engineering/pr308-expectedEDF-fresh-gates-preparation/frozen-current8d49-source-LIGHT-inputs-v3.json')
nativecfg=Path('/workspace/engineering/rcc-current8d49-qualified-V9-entry-bootstrap-preparation/FROZEN-current8d49-control3-qualified-V9-entry-config-v2.json')
nativerelease=Path('/workspace/engineering/root-rcc-current8d49-control3-V9-one-release.json')
guard=Path('/workspace/engineering/rcc-current8d49-qualified-V9-entry-bootstrap-preparation/readonly_current_input_guard_v9.py')
config={'schema':1,'status':'PREPARATION_NOT_RUN_REQUIRES_DISTINCT_REAL_INDEPENDENT_PREEXEC_REVIEW_AND_ROOT_RELEASE','source':old['source'],'tree':old['tree'],'source_leaves':1440,'owned_root':str(owned),'contract':contractrow,'source_config':row(sourcecfg),'native_readonly_config':row(nativecfg),'native_readonly_original_release':row(nativerelease),'readonly_guard':row(guard),'source_independent':row(ind),'final_source_owner':v['owner_binding'],'private_source_owner':v['source_owner_binding'],'test_source':row(source),'original_failed_baseline':v['original_failure_binding'],'original_contract':row(oldcontract),'original_launcher':row('/workspace/engineering/root-current8d49-nine-real-baseline-once.py'),'readonly_guard_argv':['timeout','--signal=TERM','--kill-after=10s','120s','/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python',str(guard),'--config',str(nativecfg),'--config-sha256',row(nativecfg)['sha256'],'--release',str(nativerelease),'--release-sha256',row(nativerelease)['sha256'],'--label','control3'],'outer_seconds':450,'outer_kill_after_seconds':10,'child_baseline_seconds':120,'child_kill_after_seconds':10,'subprocess_parent_seconds':135,'origin_timeout_seconds':15,'required_preexecution_decision':'GO_CORRECTED_NINE_ONCE2_BASELINE_PREEXECUTION','required_ROOT_release_scope':'ROOT_DISTINCT_ONE_CORRECTED_NINE_ONCE2_BASELINE_ONLY','required_ROOT_release_fields':['schema','scope','source','tree','launcher_binding','config_binding','contract_binding','independent_preexecution_binding','baseline_only','native','mutants'],'native_MAIN':'NOT_RUN','capacity_floor':'NONE_FOR_THIS_SERVICEFREE_REPLAY; ROOT_SERIALIZATION_REQUIRED','mutants':'NOT_RUN','ROOTrelease':'NOT_CREATED','capture':datetime.datetime.now(datetime.timezone.utc).isoformat()}
assert config['native_readonly_config']['sha256']=='5dc48075c8a2c91042f38a4c4c8941e9eb7f5c0feb82dcc93917cb8ec76c9f25'
assert config['native_readonly_original_release']['sha256']=='a131e30087742764ba6dbdbc2634749924133431de3310b2065ced446b97bf3b'
configrow=put('frozen-corrected-nine-once2-baseline-execution-config-NOTRUN.json',config)
print(json.dumps({'contract':contractrow,'config':configrow,'owned_root':'ABSENT_NOT_CREATED'}))
