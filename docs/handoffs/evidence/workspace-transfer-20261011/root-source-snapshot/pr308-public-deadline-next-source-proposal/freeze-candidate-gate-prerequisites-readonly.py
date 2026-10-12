import ast,difflib,hashlib,json,os,pathlib,re,subprocess
out=pathlib.Path('/workspace/engineering/pr308-public-deadline-next-source-proposal')
repo='/workspace/actions';ref='4ca431b51b018b947fac6f096ca3cdc21028dd28';v='action_server/scripts/verify_dakota_rcc_acceptance.py';t='action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py';doc='docs/skills/repository-operations.md'
def blob(p): return subprocess.check_output(['git','-C',repo,'show',ref+':'+p])
def sha(b): return hashlib.sha256(b).hexdigest()
def file_ref(p):
 p=pathlib.Path(p); b=p.read_bytes();return {'path':str(p),'size':len(b),'sha256':sha(b)}
def freeze(name,obj):
 p=out/name;assert not p.exists();p.write_bytes((json.dumps(obj,indent=2)+'\n').encode());p.chmod(0o444);return file_ref(p)
def apply_unified(old,patch):
 src=old.splitlines(keepends=True);lines=patch.splitlines(keepends=True);result=[];pos=0;i=2
 while i<len(lines):
  match=re.fullmatch(r'@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@.*\n',lines[i]);assert match,lines[i]
  start=int(match[1])-1;assert start>=pos;result.extend(src[pos:start]);pos=start;i+=1
  while i<len(lines) and not lines[i].startswith('@@ '):
   line=lines[i];assert line[0] in ' +-'
   if line[0] in ' -':assert src[pos]==line[1:];pos+=1
   if line[0] in ' +':result.append(line[1:])
   i+=1
 result.extend(src[pos:]);return ''.join(result)
s=blob(v).decode();test=blob(t).decode();module=ast.parse(test);f=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='test_dakota_local_rcc_action_over_authenticated_http')
assertions=[ast.unparse(n.test) for n in ast.walk(f) if isinstance(n,ast.Assert)]
required=["live_receipt['acceptance_status'] == 'FAIL'",*[f"live_receipt['cells']['{key}'] == 'FAIL'" for key in ['offline_warm_action','offline_warm_artifact_verification','offline_warm_wrapper_exit','zero_requests_during_warm_runtime']]]
assert all(x in assertions for x in required)
constant_nodes={n.targets[0].id:n.value for n in ast.parse(s).body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)}
assert ast.literal_eval(constant_nodes['PROOF_TIMEOUT_SECONDS'])==2400
assert ast.literal_eval(constant_nodes['CLEANUP_GRACE_SECONDS'])==10
assert ast.unparse(constant_nodes['CLI_WATCHDOG_SECONDS'])=='PROOF_TIMEOUT_SECONDS + 6 * CLEANUP_GRACE_SECONDS + 5'
calls=[n for n in ast.walk(f) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='run_owned_process'];assert len(calls)==1
kwargs={k.arg:ast.unparse(k.value) for k in calls[0].keywords}
assert kwargs['timeout_seconds']=='harness.CLI_WATCHDOG_SECONDS + 4 * harness.CLEANUP_GRACE_SECONDS + 5'
assert kwargs['cleanup_grace_seconds']=='harness.CLEANUP_GRACE_SECONDS'
oldguide=blob(doc).decode();oldpatch=(out/'exact-canonical-guard-reuse-scope-proposal.patch').read_text();proposedguide=apply_unified(oldguide,oldpatch)
anchor='The live test remains separately opt-in through `ACTIONS_REAL_RCC_ACCEPTANCE=1`.\n';assert proposedguide.count(anchor)==1
learning=('The retained opt-in candidate-wheel test expects overall `FAIL` and failed\n'
'offline-warm cells. A passing test verifies that negative contract; it does not\n'
'qualify a successful candidate lifecycle. Preserve those assertions during guard\n'
'reuse and qualify a positive candidate proof separately. Its retained parent\n'
'watchdog is 2465 seconds and the test envelope is 2510 seconds with a 10-second\n'
'cleanup grace. A shorter control gateway does not cover that invocation.\n')
newguide=proposedguide.replace(anchor,anchor+learning,1)
canonical=''.join(difflib.unified_diff(oldguide.splitlines(keepends=True),newguide.splitlines(keepends=True),fromfile='a/'+doc,tofile='b/'+doc))
cp=out/'exact-canonical-guard-reuse-scope-proposal-v2.patch';assert not cp.exists();cp.write_text(canonical);cp.chmod(0o444)
oldsource=(out/'exact-narrow-accepted-guard-source-proposal.patch').read_text();start=oldsource.index('--- a/'+doc+'\n');prefix=oldsource[:start]
sp=out/'exact-narrow-accepted-guard-source-proposal-v2.patch';assert not sp.exists();sp.write_text(prefix+canonical);sp.chmod(0o444);assert sp.read_text()[:start]==prefix
stat=os.statvfs('/workspace');available=stat.f_bavail*stat.f_frsize
status=subprocess.check_output(['git','-C','/workspace/engineering/pr308','status','--porcelain=v1']).decode();assert status==''
proof={'status':'READ_ONLY_GATE_PREREQUISITE_QUALIFICATION_NO_TEST_OR_PRODUCT_EXECUTION','source':ref,'source_input_sha256':{v:sha(blob(v)),t:sha(blob(t))},'actual_test_name':f.name,'actual_test_source_lines':[f.lineno,f.end_lineno],'exact_negative_assertions':required,'negative_contract_means_pytest_PASS_is_not_positive_candidate_GO':True,'retained_constants':{'proof_seconds':2400,'cleanup_grace_seconds':10,'CLI_watchdog_seconds':2465,'test_owned_envelope_seconds':2510,'CLI_expression':ast.unparse(constant_nodes['CLI_WATCHDOG_SECONDS']),'test_keyword_expressions':kwargs},'actual_test_and_all_guard_code_controls_unchanged_from_original_proposal':True,'code_test_patch_prefix_sha256':sha(prefix.encode()),'new_source_patch':file_ref(sp),'new_canonical_patch':file_ref(cp),'capacity_snapshot':{'available_bytes':available,'clean_pr308':status=='','scope':'Snapshot only. Recheck before authorized preparation; no capacity permission or artifact/newbuild admission. Stack309 owns reserved broad test slot; no concurrent full suite here.'},'actual_candidate_prerequisites':['Separate root-approved positive success contract, retained primary failure disposition and immutable current source/artifact/platform dependency review. No assertion rewrite or failed-cell waiver in this narrow source lane.','Separate immutable runner qualification with complete enclosing deadline/cleanup envelope for unchanged2465/2510 bounds. Earlier660s control or browser runner is not coverage of this invocation.','Qualified root-coordinated capacity and heavy slot. No provisioning, prewarm/cache reset, blind rerun or implicit native92498 requalification.','Missing private01f/frozen-v6 specification and full134 remain explicit HOLD. Public candidate negative test and threecase compatibility do not recover or replace them.'],'authority':'SOURCE proposal only pending root lane authorization; no actual candidate run/retry authorization.'}
pr=freeze('separate-actual-candidate-gate-prerequisite-proof.json',proof)
proposal=json.loads((out/'bounded-existing-PR308-source-control-proposal.json').read_text())
proposal['supersedes_by_named_successor_only']=file_ref(out/'bounded-existing-PR308-source-control-proposal.json')
proposal['SOURCE_change_commit']['preserve_retained_negative_candidate_test']='Exact opt-in test remains untouched, including aggregate FAIL and four failed warm-cell expectations; scope excludes its actual execution and changing its success contract.'
proposal['separate_actual_candidate_gate']=proof
proposal['source_capacity_and_schedule']='Only root-assigned SOURCE B may begin after design disposition. Stack309 reserves current broad slot; coordinate Bootstrap and one bounded full configured source suite later. Available bytes snapshot is not assurance of sufficient capacity.'
proposal['Documentation_improvement']['Canonical_file_changed_or_proposed']='docs/skills/repository-operations.md; exact v2 patch preserves accepted guard23line lesson and scoped guard/native-profile/control clarification, adds six verified lines distinguishing retained negative candidate contract and2465/2510/10 envelope.'
proposal['Documentation_improvement']['Durable_learning_captured']+=' Retained actual candidate test expects failed warm cells/overallFAIL; pytestPASS cannot be relabeled positivecandidateGO. Actual parent envelope needs separate qualification.'
proposal['Documentation_improvement']['Stale_or_ambiguous_guidance_removed']+=' Disclose that the opt-in live test is a negative contract, and that earlier shorter control runners do not enclose its unchanged actual invocation.'
proposal['Documentation_improvement']['Evidence'].append(pr)
proposal['Documentation_improvement']['exact_patch']=file_ref(cp)
proposal['Documentation_improvement']['Remaining_uncertainty']+=' Positive actualcandidate successcontract/runner/capacity remains unqualified; no new actual requested.'
proposal['exact_SOURCE_patch']=file_ref(sp)
receipt=freeze('bounded-existing-PR308-source-control-proposal-v2.json',proposal)
pathlib.Path(__file__).chmod(0o444)
print(json.dumps({'proposal_v2':receipt,'source_patch_v2':file_ref(sp),'canonical_patch_v2':file_ref(cp),'candidate_prerequisite_proof':pr,'capacity_available_bytes':available,'source_scope':'Design only. Exact guard code/test prefix unchanged. No actual authorization.'},indent=2))
