import ast,datetime,difflib,hashlib,json,os,stat,subprocess
from pathlib import Path
B=Path(__file__).resolve().parent;R=Path('/workspace/engineering/pr307');O=Path('/workspace/engineering/pr307-current9760-token-light-once5-namespace-base-PREEXECUTION-NOTRUN');DI=Path('/workspace/engineering/pr307-current9760-once5-ACTUALFAIL-independent-review')
SOURCE='9760d5ec44876558c4941c4c3190abc8d92d14a1';TREE='0d33ebaac258e069ef7045a29b4a3904740f6307';ATTEMPT='/workspace/engineering/pr307-current9760-token-light-once6-owned';RELEASE=str(B/'root-one-TOKEN-LIGHT-once6-release.json');STALE='/workspace/engineering/pr307-currentc97e-token-light-once2-owned'
def row(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(s.st_mode))}
def exact(r):assert row(r['path'])==r;return Path(r['path']).read_bytes()
def put(n,v):
 p=B/n
 with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 p.chmod(0o400);return row(p)
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
assert git('rev-parse','HEAD').decode().strip()==SOURCE and git('rev-parse','HEAD^{tree}').decode().strip()==TREE and not git('status','--porcelain')
oldowner=row(O/'OWNERFINAL-current9760-private-once5-single-Devutils-Mypy-base-SOURCE-and-PREEXEC-NOTRUN.json');old=json.loads(exact(oldowner));cfg=json.loads(exact(old['config']));proof=json.loads(exact(old['sourceproof']));assert len(cfg['bindings'])==225
for r in cfg['bindings']:exact(r)
diag=row(DI/'OWNERFINAL-independent-original-current9760-once5-ACTUALFAIL-and-all-active-probe-address-proposal.json');assert diag['sha256']=='cae5ac59074f656c297bb8aa6ea9808d67b63a10f40e376148c188aeeeee45e2';d=json.loads(exact(diag));assert d['source_preservation']['ROOT_external_before_alwayspost_exact_row_count']==233 and d['source_preservation']['current_consumed_bindings']==225 and d['source_preservation']['retained_originals']==212
for r in proof['all_git_FS_body_and_exec_mode_exact']:
 p=R/r['path'];s=p.lstat();b=os.readlink(p).encode() if r['mode']=='120000' else p.read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'];assert bool(s.st_mode&0o111)==(r['mode']=='100755') if r['mode']!='120000' else stat.S_ISLNK(s.st_mode)
assert len(proof['all_git_FS_body_and_exec_mode_exact'])==1442
for r in proof['prepared30_current_source_inputs']:
 b=(R/r['path']).read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
assert len(proof['prepared30_current_source_inputs'])==30
for r in proof['five_existing_venvs_config_only']:exact(r['pyvenv_config'])
originals=[oldowner,old['config'],old['launcher'],old['sourceproof'],old['ROOT_contract'],diag]+d['original_evidence_bindings']+d['source_preservation']['guard_bindings']
# These six rows start a present-body baseline only; they do not establish pre-once5 historical preservation.
newly_observed_origin_baseline=d['additional_consumed_output_address_audit']['six_current_old_namespace_report_bindings'];originals+=newly_observed_origin_baseline
for p in sorted(O.iterdir()):
 if p.is_file():originals.append(row(p))
for r in originals:exact(r)
newproof=dict(proof);newproof['status']='CURRENT9760_PRIVATE_ONCE6_ACTIVE_OUTPUT_ADDRESS_PREPARATION_SOURCE_UNCHANGED';newproof['retained_original_evidence']=proof['retained_original_evidence']+originals;newproof['original_sourceproof']=old['sourceproof'];newproof['prior_ACTUAL_once5']=d['original_completed_censuses'];newproof['original_once5_scope']={'ROOT_external':233,'child':225,'historical_bound_rows':212};newproof['original_six_origin_report_scope']='UNKNOWN pre-once5 body baseline; newly observed six hashes protect current bytes going forward only';newproof['actual_GATE_child']='NOT_RUN';newproof['new_source_application_delta']='NONE'
sourceproof=put('current9760-unchanged1442-current30-ownfive-original-once5-and-output-baselines.json',newproof)
newcfg=dict(cfg);newcfg['source_proof']=sourceproof
for key,count in [('generator_probe_code',3),('origin_probe_code',1)]:
 assert cfg[key].count(STALE)==count
 newcfg[key]=cfg[key].replace(STALE,ATTEMPT)
 assert newcfg[key].replace(ATTEMPT,STALE)==cfg[key];ast.parse(newcfg[key])
allrows=[sourceproof if r==cfg['source_proof'] else r for r in cfg['bindings']]+originals;seen={}
for r in allrows:
 if r['path'] in seen:assert seen[r['path']]==r
 seen[r['path']]=r
newcfg['bindings']=list(seen.values());config=put('immutable-one-TOKEN-LIGHT-once6-inputs.json',newcfg)
script=exact(old['launcher']).decode();replacements=[('immutable-one-TOKEN-LIGHT-once5-inputs.json','immutable-one-TOKEN-LIGHT-once6-inputs.json'),(old['config']['sha256'],config['sha256']),('/workspace/engineering/pr307-current9760-token-light-once5-owned',ATTEMPT),('RELEASE_ONE_CURRENT9760_TOKEN_LIGHT_ONCE5_ONLY','RELEASE_ONE_CURRENT9760_TOKEN_LIGHT_ONCE6_ONLY'),('GO_CURRENT9760_TOKEN_LIGHT_ONCE5_GATEWAY_PREEXECUTION','GO_CURRENT9760_TOKEN_LIGHT_ONCE6_GATEWAY_PREEXECUTION'),('PASSED_CURRENT9760_TOKEN_LIGHT_ONCE5_ONLY','PASSED_CURRENT9760_TOKEN_LIGHT_ONCE6_ONLY')]
text=script
for a,b in replacements:assert a in text;text=text.replace(a,b)
reverse=text
for a,b in reversed(replacements):reverse=reverse.replace(b,a)
assert reverse==script;ast.parse(text)
lp=B/'launch_one_owned_token_light_once6_current_probe_outputs.py';lp.write_text(text);lp.chmod(0o444);launcher=row(lp)
# Extract outer literal paths and the nested YAML Python string without importing or executing a probe.
def path_literals(code):
 t=ast.parse(code);out=[]
 for n in ast.walk(t):
  if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='Path' and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str):out.append(n.args[0].value)
 return out
outer=path_literals(newcfg['generator_probe_code']);assert outer==[ATTEMPT+'/generated-eight-and-Github30/generated',ATTEMPT+'/generated-eight-and-Github30/eight-outputs.json']
t=ast.parse(newcfg['generator_probe_code']);nested=next(n.value for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets))
def literal_concat(n):
 if isinstance(n,ast.Constant) and isinstance(n.value,str):return n.value
 if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Add):return literal_concat(n.left)+literal_concat(n.right)
 if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='repr' and len(n.args)==1:
  inner=n.args[0];assert isinstance(inner,ast.Call) and isinstance(inner.func,ast.Name) and inner.func.id=='str' and len(inner.args)==1 and isinstance(inner.args[0],ast.Name) and inner.args[0].id=='root';return repr(str(R))
 raise AssertionError('UNKNOWN_NESTED_EXECUTABLE_STRING_FORM')
nested_code=literal_concat(nested);nested_paths=path_literals(nested_code);assert nested_paths==[str(R),ATTEMPT+'/generated-eight-and-Github30/thirty-YAML.json']
orig=path_literals(newcfg['origin_probe_code']);assert orig==[ATTEMPT+'/own-five-origins']
expected=[ATTEMPT+'/generated-eight-and-Github30/generated',ATTEMPT+'/generated-eight-and-Github30/eight-outputs.json',ATTEMPT+'/generated-eight-and-Github30/thirty-YAML.json',ATTEMPT+'/own-five-origins']
for p in expected:assert not Path(p).exists() and not Path(p).is_symlink()
assert not Path(ATTEMPT).exists() and not Path(ATTEMPT).is_symlink() and not Path(RELEASE).exists()
# Historical input rows remain byte-for-byte. Current code destinations alone retarget.
old_historical_paths=[r['path'] for r in cfg['bindings']];new_paths=[r['path'] for r in newcfg['bindings']];assert all(p in new_paths for p in old_historical_paths if p!=cfg['source_proof']['path'])
assert cfg['controlled_runner']==newcfg['controlled_runner'] and cfg['forbidden_generated_outputs']==newcfg['forbidden_generated_outputs'] and cfg['protected_repository']==newcfg['protected_repository']
# All consumed config keys are classified. Path fields here are read-only; two executable fields contain four active outputs.
lt=ast.parse(text);keys=sorted({n.slice.value for n in ast.walk(lt) if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name) and n.value.id=='cfg' and isinstance(n.slice,ast.Constant) and isinstance(n.slice.value,str)})
assert set(keys)=={'bindings','controlled_runner','forbidden_generated_outputs','generator_probe_code','light_workspace_floor_bytes','managed_activation_expected','origin_probe_code','protected_repository','source_proof'}
addresses=put('all-consumed-current-executable-output-and-historical-input-address-closure-NOTRUN.json',{'schema':1,'status':'STATIC_AST_AND_NESTED_STRING_OUTPUT_ADDRESS_CLOSURE_NOTEXECUTED','consumed_config_keys':keys,'generator_outer_outputs':outer,'generator_nested_YAML_paths':nested_paths,'origin_active_output_base':orig[0],'origin_expected_fresh_reports':[orig[0]+'/'+p+'.json' for p in ['actions','actions-http-helper','devutils','work-items','action_server','all-five']],'all_four_active_bases':'CURRENT_UNIQUE_ONCE6_ABSENT','parent_creation':'Unchanged run_phase creates ATTEMPT/name mode0700 before gateway command. generated phase parent exists before owned generatedchild mkdir; own-five phase directory exists before package reports. No mkdir/backfill under old once2.','controlled_Invoke':'Unchanged receives currentATTEMPT/controlled-invoke positionalargument; /pr307-guard-owned/outer_invoke_no_yaml.py is read-only input, not output.','historical_input_paths':'Every original225 binding/path untouched; oldcode/config files immutable. Only the new sourceproof path replaces live proof; oldproof remains separately frozen/bound.','six_old_origin_report_scope':'Pre-once5 baselineUNKNOWN; current observed hashes exact now and protect futureoriginals only. No retrospective unmodified-history claim.','generator_scope':'No generator/YAML/Invoke execution; original sourceworkflownotmismatch since mkdir failed beforegenerator exec.','four_probe_literal_inverse_AST_text':'EXACT oldgenerator/origin code after only currentoutput-root replacements','upstream_disposition':'none'})
oldcontract=json.loads(exact(old['ROOT_contract']));contract=dict(oldcontract);contract.update({'status':'NOT_EXECUTABLE_DISTINCT_ROOT_AND_REAL_INDEPENDENT_PREEXEC_REQUIRED','config':config,'launcher':launcher,'attempt_root':ATTEMPT,'root_release_path':RELEASE,'root_release_required':'regular nonsymlink0600 owningUIDGID/hash+source/tree/config/launcher/realreview; RELEASE_ONE_CURRENT9760_TOKEN_LIGHT_ONCE6_ONLY','independent_review_required':{'decision':'GO_CURRENT9760_TOKEN_LIGHT_ONCE6_GATEWAY_PREEXECUTION','source':SOURCE,'tree':TREE,'config_sha256':config['sha256'],'launcher_sha256':launcher['sha256']},'ROOT_exact_argv':['timeout','--signal=TERM','--kill-after=10s','900s','bash','-c','source /workspace/actions-cloud/activate.sh && exec /workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python '+launcher['path']+' "$@"','pr307-token-light',RELEASE,'ROOT_AUTH_SHA256_FROM_ANNOUNCED_TYPED_RELEASE','OWNER_ANNOUNCED_INDEPENDENT_REVIEW_PATH','OWNER_ANNOUNCED_INDEPENDENT_REVIEW_SHA256'],'once5_actual':'OriginalFAIL FileNotFoundError beforegenerator exec; staticPASS withDevMypy7 preserved, InvokeNOTRUN','once6_actual':'NOT_RUN','four_current_code_output_bases':expected})
rootcontract=put('strict-current9760-once6-ROOT-release-and-bound-command-contract-NOTRUN.json',contract)
canonical=row(DI/'canonical-executable-probe-output-address-and-historical-guard-scope-proposed.txt')
proofrow=put('exact-once6-config-four-output-literals-and-launcher-address-only-delta-NOTRUN.json',{'schema':1,'source':SOURCE,'tree':TREE,'source1442_current30_ownfive':'EXACT_UNCHANGED','old_child225_ROOT233_history212':'Preserved originalonce5 actual scopes; futureonce6counts separatelyderived','code_changes':{'generator_probe_code':3,'origin_probe_code':1},'all_other_config_fields_except_proof_and_appended_historicalbindings':'EXACT','all_other_launcher_commands_predicates_AND_MYPYPATH':'EXACT inverse wholetext after only6declaredfreshmetadata literals','launcher_literal_changes':replacements,'new_child_bindings':len(newcfg['bindings']),'address_proof':addresses,'old_origin_baseline_unknown':'Explicit; sixnewlyobservedrows not proof originalpriorbytes unchanged','source_commits_env_native':'NONE','once6':'NOT_RUN','documentation':canonical,'upstream_disposition':'none'})
patch=B/'exact-private-once5-to-once6-two-probe-output-root-source-delta.patch';patch.write_text(''.join(difflib.unified_diff(json.dumps({k:cfg[k] for k in ['generator_probe_code','origin_probe_code']},indent=2).splitlines(True),json.dumps({k:newcfg[k] for k in ['generator_probe_code','origin_probe_code']},indent=2).splitlines(True),fromfile='frozen-once5-active-probe-code.json',tofile='proposed-once6-active-probe-code.json')));patch.chmod(0o400)
allrefs=[row(p) for p in sorted(B.iterdir()) if p.is_file()]
owner=put('OWNERFINAL-current9760-private-once6-four-active-output-address-SOURCE-and-PREEXEC-NOTRUN.json',{'schema':1,'status':'OWNER_FINAL_PRIVATE_ONCE6_FOUR_ACTIVE_OUTPUT_ADDRESS_SOURCE_AND_PREEXEC_NOTRUN','source':SOURCE,'tree':TREE,'source_clean':True,'source_count':1442,'application_source_ref_commit_environment_delta':'NONE','sourceproof':sourceproof,'config':config,'launcher':launcher,'ROOT_contract':rootcontract,'address_closure_proof':addresses,'static_scope_proof':proofrow,'source_delta':row(patch),'bindings':allrefs,'original_once5_failure':diag,'original_scopes':{'ROOT_external':233,'child':225,'historical':212},'new_child_binding_count':len(newcfg['bindings']),'exact_scope':'Only currentgenerator3 plusorigin1 executableoutput literals and launcherfresh6 metadataaddresses. No historicalinputpath/globalreplace/gate/budget/flags/MYPYPATH/source changes.','current_once6':'NOT_RUN_NO_ROOT_RELEASE_CREATED','required_next':'IndependentSOURCE+PREEXEC thenROOTdistinctfreshserializedONE; no automaticallyretryoldattempt','documentation':{'canonical_file_proposed':'docs/skills/repository-operations.md','exact_delta_reused':canonical,'evidence':'Actualoriginalonce5mkdir failurebeforegenerator + nestedconfigs activeaddressaudit; priorPREEXEC embeddedaddressmiss retained; newallconsumedkeys/twoASTstrings/nestedYAMLoutput/currentphaseparentproof','stale_ambiguity':'OuterCONFIG/launcherretarget notcompleteembeddedoutputclosure; historicalreadonly addresses differfrom activeoutputs; guardPASS limited to actualboundrows and original6reportbaselineUNKNOWN','remaining_uncertainty':'Generator8/YAML30/controlledInvoke/currentfull/native/OAuthauthority/release NOTRUN/HOLD; sixoriginpriorbaselineUNKNOWN. No factualclaim beyond frozenrows.','upstream_disposition':'none'},'capture':datetime.datetime.now(datetime.timezone.utc).isoformat()})
for r in newcfg['bindings']+allrefs:exact(r)
assert not git('status','--porcelain')
print(json.dumps(owner))
