from pathlib import Path
import hashlib
import json
import subprocess
import re
import difflib
import yaml

REPO='/workspace/engineering/pr307'
OWNED=Path('/workspace/engineering/pr307-current-hosted-failure-owned')
OUT=Path('/workspace/engineering/pr307-current-hosted-failure-independent-review')
HEAD='87e412f89b201c697d3e6bd4bd34031cdbd14df3'
CONTROL='5c3013a1b02cc1f239c19b9db5f08bbacaafcf6f'
TREE='638b960a3700bbbba3026874efb158fa6e95117f'
TARGET='fbde0d3a248c47c9964851355f96575c89a87329'
def read(n):return json.loads((OWNED/n).read_text())
def binding(p):
 b=p.read_bytes();return {'path':str(p),'size':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def git(*args):return subprocess.check_output(['git','-C',REPO,*args])
pr=read('pr.json');control=read('actual-control.json')
assert pr['head']['sha']==HEAD and pr['merge_commit_sha']==control['sha']==CONTROL
assert control['tree']['sha']==TREE==git('rev-parse',HEAD+'^{tree}').decode().strip()
assert [p['sha']for p in control['parents']]==[TARGET,HEAD]
assert read('actual-base-branch.json')['commit']['sha']==TARGET
checks=read('checks.json');failed=[c for c in checks['check_runs']if c['conclusion']=='failure']
assert len(failed)==7 and all(c['head_sha']==HEAD for c in checks['check_runs'])
metadata=read('failed-job-step-inventory.json');assert len(metadata)==7
rows=[]
for c in sorted(failed,key=lambda x:x['id']):
 j=read(f"job-{c['id']}.json");assert j['head_sha']==HEAD and j['status']=='completed'and j['conclusion']=='failure'
 failures=[s for s in j['steps']if s['conclusion']=='failure'];assert len(failures)==1
 first=failures[0];assert first['name']in ['Build OAuth2 config','Build OAuth2 config (PR)']
 assert all(s['conclusion']in ('success','skipped')for s in j['steps']if s['number']<first['number'])
 p=OWNED/f"job-{c['id']}-original-decoded.log";raw=p.read_bytes();text=raw.decode();safe=[]
 for line in text.splitlines():
  body=re.sub(r'^\d{4}-\d\d-\d\dT[^ ]+ ','',line)
  m=re.fullmatch(r'OAuth2 acquisition failed for actions-oauth-config.yaml \(exit ([0-9]+)\)',body)
  if m:safe.append({'category':'ACQUISITION_FAILED','input':'actions-oauth-config.yaml','gh_exit':int(m[1])})
 assert len(safe)==1 and safe[0]['gh_exit']in (1,4)
 assert f'HEAD is now at {CONTROL[:7]}'in text and CONTROL in text
 assert 'scripts/build_oauth2_config.py'in text
 assert not any('Writing OAuth2 configs to:'in x for x in text.splitlines())
 before=[{'name':s['name'],'conclusion':s['conclusion']}for s in j['steps']if s['number']<first['number']and ('Install project'in s['name']or 'Build frontend'in s['name'])]
 after=[{'name':s['name'],'conclusion':s['conclusion']}for s in j['steps']if s['number']>first['number']and ('Test'in s['name']or 'Build binary'in s['name']or 'Build sdist'in s['name']or 'Build wheels'in s['name'])]
 assert all(x['conclusion']=='skipped'for x in after)
 rows.append({'job':c['id'],'name':c['name'],'run':j['run_id'],'exact_head':HEAD,'actual_checkout_full_sha_in_private_log':True,'first_failed_step':{'name':first['name'],'number':first['number']},'preceding_installs_frontend':before,'subsequent_build_test_not_executed':after,'safe_guard_reason':safe[0],'original_full_job_log_private':binding(p),'authenticated_job_metadata':binding(OWNED/f"job-{c['id']}.json")})
assert sum(r['safe_guard_reason']['gh_exit']==4 for r in rows)==5
assert sum(r['safe_guard_reason']['gh_exit']==1 for r in rows)==2
sourcepaths=['action_server/tasks.py','action_server/scripts/build_oauth2_config.py','action_server/tests/build_system_tests/test_oauth2_config_build.py','.github/workflows/actions_runtime_tests.yml','.github/workflows/actions_runtime_pypi_release.yml','.github/workflows/frontend-build-unauthenticated.yml']
source=[]
for path in sourcepaths:
 raw=git('show',HEAD+':'+path);assert Path(REPO,path).read_bytes()==raw
 source.append({'path':path,'git_blob':git('rev-parse',HEAD+':'+path).decode().strip(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
helper=git('show',HEAD+':action_server/scripts/build_oauth2_config.py').decode()
assert 'except subprocess.CalledProcessError as error:'in helper and 'f"OAuth2 acquisition failed for {file_name} (exit {error.returncode})"'in helper
assert 'check=True,'in helper and 'stderr=subprocess.PIPE,'in helper
assert helper.index('contents = {key: _acquire(file_name) for key, file_name in INPUTS}')<helper.index('os.replace(temporary_path, destination)')
assert helper.index('("actions_config", "actions-oauth-config.yaml")')<helper.index('("default_user_config", "oauth-config.yaml")')
workflows={p:yaml.safe_load(git('show',HEAD+':'+p))for p in sourcepaths if p.startswith('.github/')}
pack=workflows['.github/workflows/actions_runtime_pypi_release.yml']['jobs']
for job in ['build-sdist','build-wheels']:
 step=[s for s in pack[job]['steps']if s['name']=='Build OAuth2 config (PR)'][0];assert 'env'not in step and step['if']=="github.event_name == 'pull_request'"
rt=workflows['.github/workflows/actions_runtime_tests.yml']['jobs']['build']['steps'];rs=[s for s in rt if s['name']=='Build OAuth2 config'][0];assert 'GH_TOKEN'in rs['env']
external=workflows['.github/workflows/frontend-build-unauthenticated.yml']['jobs']['build-external']['steps'];es=[s for s in external if s['name']=='Build OAuth2 config'][0];assert 'GH_TOKEN'in es['env']
prior=Path('/workspace/engineering/pr307-independent-review/frozen-source-control-review.json');assert binding(prior)['sha256']=='48d03bc4256c13ceb6fee1cf81e86bd56e6fd2af2903baf99444d32101693229'
guidepath='docs/skills/repository-operations.md';guide=git('show',HEAD+':'+guidepath).decode()
anchor='CLI failures expose fixed input names and reason categories, never raw acquisition\nstdout, stderr, configuration or credentials.\n';assert guide.count(anchor)==1
delta='''
A hosted failure with `OAuth2 acquisition failed for <fixed input> (exit N)`
identifies checked acquisition failure, not malformed YAML, missing provider
shape or atomic replacement. Stop at that first failed step when classifying
the result: skipped downstream binary/tests are unexecuted, and a cancelled
matrix sibling is not evidence of the same guard failure. The first input must
succeed before the second is requested or either can replace the module.
The numeric exit code alone does not identify authentication, transport or
repository-access cause because acquisition stderr remains private.

Inspect each producer's actual workflow separately: package-release PR config
steps declare no acquisition-token environment, Runtime test steps declare a
secret-backed token, and unsigned binary steps declare the workflow token.
Declarations do not prove actual secret availability or permission. Preserve
the guard and release HOLD until the approved source pair and authorized
acquisition context are established; never infer a stub or bypass from a green
unrelated package/toolkit job or an earlier artifact with empty generated data.
'''
proposed=guide.replace(anchor,anchor+delta,1);patch=OUT/'canonical-hosted-oauth-acquisition-failure-proposed.patch'
patch.write_text(''.join(difflib.unified_diff(guide.splitlines(True),proposed.splitlines(True),fromfile='a/'+guidepath,tofile='b/'+guidepath)))
summary=OUT/'safe-authenticated-first-failure-summary.json'
summary.write_text(json.dumps({'source_head':HEAD,'actual_control':CONTROL,'actual_tree':TREE,'ordered_parents':[TARGET,HEAD],'seven_completed_actual_failed_jobs':rows,'other_observed_statuses':[{'id':c['id'],'name':c['name'],'status':c['status'],'conclusion':c['conclusion']}for c in checks['check_runs']if c['conclusion']in ('cancelled','skipped')or c['status']!='completed'],'fixed_reason_only':True,'no_raw_stderr_env_config_URL_payload':True},indent=2)+'\n')
result={
 'verdict':'GO_SCOPED_FIRST_GUARD_FAILURE_DIAGNOSIS; HOLD_HOSTED307_MERGE_APPROVED_PAIR_ACQUISITION_AND_RELEASE',
 'scope':'bounded read-only original7completedfailedjob logs/step/source admission; no source changes, retry, bypass, stub, provider/repo replacement or publication',
 'exact_tuple':{'source':HEAD,'actual_control':CONTROL,'actual_tree':TREE,'ordered_parents':[TARGET,HEAD],'same_tree_as_original87_source':True},
 'actual_first_failure':'All seven observed completedfailedjobs reached fixed checkedacquisition failure on FIRST actions-oauth-config.yaml: five exit4 Runtime testmatrix/sdist/macOSwheel, two exit1 unsignedUbuntu/Windowsbinary. Preceding projectinstalls andfrontend succeeded; downstream nativebuild/integrationtest paths skipped, not failing runtime tests.',
 'original_failures':rows,'safe_retained_summary':binding(summary),'exact_source_workflow_hashes':source,'accepted_source_gateway_control_review':binding(prior),
 'source_inferred_failclosed_boundary':'CalledProcessError captured withrawstderr private; first_input acquisition aborts dictionary comprehension beforesecond_input/structuralvalidation ofthatbody/pairedmodule replacement. No originalpair atomicreplacement attempted on this failingcall. This source inference is not an independentpostfailure filesystemhash/cleanup observation.',
 'observed_other_context':'Snapshot otherqueued/cancelled/skipped jobs listed safely and separately; no terminalresult or samecause inferred. GreenCore/toolkit/check statuses do notrepair Runtimeacquisition. Snapshot is not fullcurrentCI success.',
 'credential_context_source_only':'Package-releasePR configsteps lackdeclared GH_TOKENenv; RuntimeTests configstep declares secretbackedtoken; unsignedbinary declaresworkflowtoken. No actualvalues/availability/permission or underlyingauth/HTTP/transport cause admitted.',
 'limitations':['Fixedexit4/1 andsanitized CLIreason do not establish underlyingauthentication, network orrepositoryaccess cause; rawghstderr was intentionallycapturedprivate.','No payload acquired/validated here andapprovedpair authoritypending; no newproviderpolicy inferred.','No claim that failednative/integrationtest business behavior was exercised; these downstream paths skipped.','No independentlymeasuredpostfailure generatedmodule/preexistingcontenthash/cleanup result.','Cancelledsiblings/queuedotherjobs not diagnosis-equivalent and this is not completefullCImergeGO.','Guard must remainfailclosed; originalemptyreleasedgeneratedcontent cannot be fallbackauthority.','Private metadata/frozenv6spec-runner/full release gates remainHOLD.'],
 'raw_records':[binding(p)for p in sorted(OWNED.glob('*.json'))],'full_decoded_logs':'PRIVATE outside repository; retainonlysafe summary/independentreview/canonicalpatch, notfullrawlogs',
 'canonical_documentation':{'canonical_file':guidepath,'exact_proposed_delta':binding(patch),'disposition':'PROPOSED additive owningguard failureboundary lesson; sourceguard48d sourceGO preserved withoutclaiminghostedacquisitionGO','durable_learning':'classify actualfirstsafe guardreason, callercredentialdeclarations and downstream unexecutedsteps; do not convertnumericexitcode/siblingcancellation/greenotherpackage to rootcauseorwaiver','evidence':'7authenticated exact87actual5c301/tree638jobsteprecords/privateoriginalhashedlogs/fixedreason/sourcehelper/callerYAML ordering','stale_ambiguity':'allRuntime failurerollup meansruntimebehaviorregression; exitcode establishesauthcause; equalcommandmeanssamecredentials; cancelledsiblingfailedsameguard; configuredsourceGOprovesrealapprovedpair acquisition','remaining_uncertainty':'ownerapprovedpair/revision/authorizedacquisitioncontext and underlyingghfailure; pendingcurrentCI/actualprovider-release acceptance','upstream':'none'},
}
p=OUT/'independent-current-hosted-failure-review.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(binding(p)))
