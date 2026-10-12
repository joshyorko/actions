import ast, datetime, hashlib, json, os, stat, subprocess
from pathlib import Path
ROOT=Path('/workspace/engineering/pr308-corrected-nine-once2-baseline-preexecution');os.umask(0o077)
def row(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();raw=p.read_bytes();return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'mode':oct(stat.S_IMODE(s.st_mode))}
def put(name,data):
 p=ROOT/name
 if not isinstance(data,str):data=json.dumps(data,sort_keys=True,indent=2)+'\n'
 with p.open('x') as f:f.write(data);f.flush();os.fsync(f.fileno())
 p.chmod(0o400);return row(p)
configpath=ROOT/'frozen-corrected-nine-once2-baseline-execution-config-NOTRUN.json';cfg=json.loads(configpath.read_bytes());configrow=row(configpath)
launcher=ROOT/'run_corrected_nine_once2_baseline.py';tree=ast.parse(launcher.read_bytes());compile(tree,str(launcher),'exec')
assert len([x for x in ast.walk(tree) if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr=='run' and isinstance(x.func.value,ast.Name) and x.func.value.id=='subprocess'])==1
assert not any(isinstance(x,ast.Import) and any(a.name.startswith(('actions','robocorp','pytest')) for a in x.names) for x in ast.walk(tree))
contract=json.loads(Path(cfg['contract']['path']).read_bytes());old=json.loads(Path(cfg['original_contract']['path']).read_bytes())
expected=[a.replace(old['test_source_binding']['path'],cfg['test_source']['path']).replace('root-once-1','root-once-2') for a in old['baseline_argv_after_exact_managed_activation']]
assert contract['baseline_argv_after_exact_managed_activation']==expected and contract['case_map']==old['case_map']
assert cfg['child_baseline_seconds']==120 and cfg['child_kill_after_seconds']==10 and cfg['subprocess_parent_seconds']==135 and cfg['outer_seconds']==450
refs=[]
def collect(v):
 if isinstance(v,dict):
  if all(k in v for k in ('path','bytes','sha256','mode')):refs.append(v)
  else:
   for value in v.values():collect(value)
 elif isinstance(v,list):
  for value in v:collect(value)
collect(cfg);collect(contract)
for r in refs:assert row(r['path'])==r,r['path']
owned=Path(cfg['owned_root']);assert not owned.exists() and not owned.is_symlink()
repo='/workspace/engineering/pr308'
assert subprocess.check_output(['git','-C',repo,'rev-parse','HEAD']).decode().strip()==cfg['source']
assert subprocess.check_output(['git','-C',repo,'rev-parse','HEAD^{tree}']).decode().strip()==cfg['tree']
assert subprocess.check_output(['git','-C',repo,'status','--porcelain=v1'])==b''
assert len(subprocess.check_output(['git','-C',repo,'ls-tree','-rz','HEAD']).split(b'\0'))-1==1440
launcherrow=row(launcher)
rootcontract={'schema':1,'status':'TEMPLATE_ONLY_NOT_AUTHORIZATION_NOT_RUN','required_review_decision':cfg['required_preexecution_decision'],'required_review_fields':{'decision':cfg['required_preexecution_decision'],'launcher_binding':launcherrow,'config_binding':configrow,'contract_binding':cfg['contract']},'root_release_exact_keys':cfg['required_ROOT_release_fields'],'root_release_template_NOT_EXECUTABLE':{'schema':1,'scope':cfg['required_ROOT_release_scope'],'source':cfg['source'],'tree':cfg['tree'],'launcher_binding':launcherrow,'config_binding':configrow,'contract_binding':cfg['contract'],'independent_preexecution_binding':None,'baseline_only':True,'native':'NOT_RUN','mutants':'NOT_RUN'},'ROOT_environment':'Source /workspace/actions-cloud/activate.sh then exact frozen18 expected exports + PATHfirsttwo /workspace/actions-cloud/bin andcachedToolkit c2fd1aa/bin. No inheritedOPT/ADDOPTS/mutant; no source installation/gateway/native.','ROOT_outer_argv_after_activation':['env','-u','PYTHONOPTIMIZE','-u','PYTEST_ADDOPTS','-u','RCC_RELOAD_PRIVATE_MUTANT','timeout','--signal=TERM','--kill-after=10s','450s','/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python',str(launcher),'--release','ROOT_DISTINCT_RELEASE_PATH','--release-sha256','ROOT_DISTINCT_RELEASE_SHA256'],'only_allowed_placeholder_substitution':['ROOT_DISTINCT_RELEASE_PATH','ROOT_DISTINCT_RELEASE_SHA256'],'serialization':'Distinct ROOT review/adoption after no other heavy/native test phase; this packet grants no execution.','final_baseline_gate':'Nine unique exact named cases+reported suite totals9/0/0/0+all eight phase statuses0. Missing malformed JUnit or missingpost is HOLD; originalonce1 not upgraded.','mutants':'NOT_RUN_SEPARATE_EXPLICIT_PHASE_AUTHORIZATION_ONLY_AFTER_GENUINE_BASELINE_PASS'}
rootrow=put('frozen-once2-compatible-independent-review-and-ROOT-release-contract-NOTRUN.json',rootcontract)
proof={'schema':1,'status':'STATIC_PARSED_NOT_EXECUTED','source':cfg['source'],'tree':cfg['tree'],'GitFS_scope':'Read-only HEAD/tree/status/1440leafcount checked now; complete bodies/FSexec/historical1192+237aliases+30+5+temporal2 enforced by unchanged V9 readonly guard before/alwayspost on execution. No guard replay by preparer.','original_case_map':'EXACT','baseline_argv_delta_only':['Corrected test patha577 insteadoldc148','ABSENTonce2 outputs insteadfailedonce1'],'actual_baseline_budget_seconds':120,'actual_kill_after_seconds':10,'parent_subprocess_seconds':135,'outer_seconds':450,'origin_budget_seconds':15,'review_release_admission':'Future distinct review exact launcher/config/contract + ROOT mode600release/source/tree/schema andbaseline_onlyTrue; oldnative release used readonlyguard only.','stdout_stderr_terminal':'Exclusive0600 original capture; stdout/stderr fsynced beforeterminal; directory fsync; owner400 after JUnitadmission.','original_failure':'Read-only all refs retained; no physical deletion/move/overwrite','parent_timeout_limit':'Outer termination may preclude final owner/alwayspost; such missing evidence is HOLD, not cleanupPASS. No universal descendant/reaping claim.','source_config_isolation':'InheritedPYOPT/ADDOPTS/mutant rejected; exact18exports/PATH2/fiveownprefixorigins; freshabsentbasetemp/logger/JUnit/ALL; childnoConftest/n0.','original_reference_count_including_duplicate_roles':len(refs),'all_reference_rows_rehashed':True,'execution':'NOT_RUN','native':'NOT_RUN','mutants':'NOT_RUN'}
proofrow=put('once2-launcher-static-closure-and-original-budget-scope-proof-NOTRUN.json',proof)
canon=Path('/workspace/engineering/pr308-nine-real-private-catalog-lock-source-successor-final-v4-NOTRUN/canonical-reload-control-copy-and-lock-boundaries-proposed.patch')
for p in ('prepare_named_once2_baseline.py','freeze_once2_packet.py'): (ROOT/p).chmod(0o444)
owner={'schema':1,'status':'OWNER_FINAL_CORRECTED_NINE_ONCE2_BASELINE_PREEXECUTION_NOT_RUN','source':cfg['source'],'tree':cfg['tree'],'source_leaves':1440,'launcher_binding':launcherrow,'config_binding':configrow,'contract_binding':cfg['contract'],'source_independent':cfg['source_independent'],'source_owner':cfg['private_source_owner'],'final_source_owner':cfg['final_source_owner'],'compatible_ROOT_release_contract':rootrow,'static_scope_proof':proofrow,'all_bound_original_rows':refs,'constructors':[row(ROOT/'prepare_named_once2_baseline.py'),row(ROOT/'freeze_once2_packet.py')],'namespace':{'path':str(owned),'state':'ABSENT_NOT_CREATED','once1':'PRESERVED_ORIGINAL_FAIL'},'tests':'NOT_RUN','mutants':'NOT_RUN','native':'NOT_RUN','product_source_edits':'NONE','source_adoption':'NONE','ROOTrelease':'NOT_CREATED','required_next':'Independent concrete launcher/config/contract review followed by separate ROOT once baseline release. Do not execute mutants automatically.','documentation_improvement':{'canonical_file_proposed':'docs/skills/repository-operations.md','exact_delta_reused':row(canon),'disposition':'REUSE_ACCEPTED5584_MERGE_REVIEWaa3f_NO_DUPLICATE_OR_COSMETIC_GUIDE_CHILD','durable_learning':'Last-good oracle permits only shallow-copied outercatalog with original nested identities/content frozen; warmup observes token under existingLock and never reacquires getter; originalmissingJUnit timeout remainsFAIL.','evidence':'Original6288diagnosis+realcopy/Locksource; corrected private final864158/source7f5bf/indaa3f; unchanged9names andold5f187/6371budget boundaries.','stale_or_ambiguous_guidance_removed':'No blanket original outer-object identity assumption; baseline PASS does not imply mutant sensitivity/native lifecycle.','remaining_uncertainty':'Corrected nine baseline andsnapshot sensitivity/all9mutants unexecuted; concrete launcher not yet independently accepted; no native reload/drain/provider qualification.'},'upstream_disposition':'none','capture':datetime.datetime.now(datetime.timezone.utc).isoformat()}
ownerrow=put('OWNERFINAL-corrected-nine-once2-baseline-config-contract-launcher-PREEXEC-NOTRUN.json',owner)
print(json.dumps({'owner':ownerrow,'launcher':launcherrow,'config':configrow,'contract':cfg['contract'],'root_contract':rootrow}))
