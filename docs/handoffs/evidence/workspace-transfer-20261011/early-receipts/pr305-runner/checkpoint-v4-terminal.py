import hashlib,json,pathlib,subprocess,types,sys,xml.etree.ElementTree as ET
root=pathlib.Path('/workspace/actions-cloud/receipts/pr305-runner'); proposal_path=root/'immutable-runner-proposal-v4.json'; proposal=json.loads(proposal_path.read_text()); attempt=pathlib.Path(proposal['one_attempt_root'])
runner_path=root/'canvas-native-public-runner-v4.py'; raw=runner_path.read_bytes(); assert hashlib.sha256(raw).hexdigest()=='da4be9f4f6f01a7079f0ff285fa8339618e663425224a4873f3cf299d6787032'
m=types.ModuleType('pr305_v4_checkpoint');m.__file__=str(runner_path);sys.modules[m.__name__]=m;exec(compile(raw,str(runner_path),'exec'),m.__dict__)
def rec(path):
 p=pathlib.Path(path);return {'path':str(p),'sha256':m.sha(p),'bytes':p.stat().st_size}
refs={}
def visit(obj):
 if isinstance(obj,dict):
  if isinstance(obj.get('path'),str) and isinstance(obj.get('sha256'),str):
   p=pathlib.Path(obj['path'])
   if p.is_file():
    record=rec(p);record['expected_sha256']=obj['sha256'];record['matches']=record['sha256']==record['expected_sha256'];assert record['matches'];refs[str(p)]=record
  for x in obj.values():visit(x)
 elif isinstance(obj,list):
  for x in obj:visit(x)
visit(proposal)
m.verify_helpers();source=m.admit_source();measure=m.load_helper('native_inventory');expected=json.loads((m.NATIVE/'output/native-artifact-tree-inventory.json').read_text());owned=measure.packaged_tree_inventory(attempt/'frozen-runtime');original=measure.packaged_tree_inventory(m.NATIVE/'dist/action-server');assert owned==original==expected
runtime=json.loads((attempt/'runtime-cleanup.json').read_text());m.admit_cleanup(runtime['cleanup']);outer=json.loads((attempt/'outer-cleanup.json').read_text());commands=json.loads((attempt/'command-receipts.json').read_text());tree=ET.parse(attempt/'junit.xml');suites=[x.attrib for x in tree.iter('testsuite')];cases=[{k:v for k,v in x.attrib.items() if k in ('classname','name','time')} for x in tree.iter('testcase')]
sampler=runtime['observer_final_report'];assert sampler['sampler_cancelled'] is True and sampler['sampler_alive'] is False
canonical=root/'canonical-actual-v4-proposed-delta.md';assert not canonical.exists();canonical.write_text('A post-command admission assertion can fail after a zero exit status without carrying stdout or stderr attributes. Retain the returned CompletedProcess streams before admission, and do not replace them with empty exception fallback streams. If the original launch or named-case report bytes are missing, hold that acceptance even when persisted tool Runs and cleanup fields are independently measurable. Command exit status, testcase/report admission, Runtime cleanup, and outer subreaper cleanup remain separate evidence.\n')
raws=[rec(p) for p in sorted(attempt.rglob('*')) if p.is_file() and 'frozen-runtime' not in p.relative_to(attempt).parts]
raws.append(rec(root/'actual-v4-gateway.log'))
checkpoint={
 'status':'failed_HOLD','actual_attempts_this_runner':1,'actual_retry_authorized':False,'gateway_exit_code':10,'worker_exit_code':outer['command_returncode'],
 'runner':rec(runner_path),'proposal':rec(proposal_path),'independent_review':rec('/workspace/engineering/pr305-v4-independent-runner-review/independent-v4-runner-qualification.json'),
 'source':source,'junit':{'suites':suites,'cases':cases,'tests':1,'failures':1,'errors':0,'skipped':0},
 'primary':{'kind':'AssertionError','message':'Actual Playwright launch path not observed','boundary':'external owned_command browser-launch receipt assertion'},
 'playwright':{'command_returncode':commands[2]['returncode'],'report_admitted':False,'launch_path_admitted':False,'returned_streams_retained':False,'limitation':'Frozen catch branch replaced prior command-3 stdout/stderr with empty AssertionError fallback. Zero return code alone does not admit one browser testcase or launch path.'},
 'runtime_cleanup':{'testcase_status':runtime['status'],'strict_measured_fields_passed':True,'cleanup':runtime['cleanup'],'finite_observed_descendants':runtime['finite_observed_descendants'],'sampler_cancelled':sampler['sampler_cancelled'],'sampler_alive':sampler['sampler_alive'],'natural_shutdown_proven':False},
 'outer_cleanup':outer,'native':{'producer':m.PRODUCER,'entries':len(expected),'owned_copy_equals_original':True,'original_equals_immutable_inventory':True,'inventory':rec(m.NATIVE/'output/native-artifact-tree-inventory.json')},
 'postconditions':{'source_clean':not subprocess.check_output(['git','status','--porcelain'],cwd=m.REPO,text=True).strip(),'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=m.REPO,text=True).strip(),'browser_hash':m.sha(m.BROWSER),'browser_matches':m.sha(m.BROWSER)==m.BROWSER_SHA,'helpers_match':True},
 'frozen_posthashes':list(refs.values()),'bounds':proposal['gateway'],'raw_receipts_private_do_not_commit':raws,
 'documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md exact follow-up proposed; source3ec remains unchanged','Durable_learning':'Post-CompletedProcess assertion must preserve returned streams; zero exit/partial tool evidence cannot admit absent browser receipt','Evidence':'V4 command3 return0; frozen catch overwrite; actual1failure0skip; strict Runtime and separate outer receipts','Stale_guidance_removed':'Exception fallback always safely substitutes command output; command0 equals report acceptance','Remaining_uncertainty':'Original command3 JSON/DEBUG bytes unavailable; whole combined acceptance remains HOLD; current actual tool/origin evidence awaits independent read-only review','exact_delta':rec(canonical)},
 'remaining_uncertainty':['No retry authorized','Current source3ec/native92498 actual combined case not qualified','Core three-member samples are not whole wheel/cold registry','No production artifact/OAuth release/full epic admission'], 'upstream_disposition':'none'}
assert checkpoint['postconditions']['source_clean'] and checkpoint['postconditions']['browser_matches']
p=root/'actual-v4-failed-checkpoint.json';assert not p.exists();p.write_text(json.dumps(checkpoint,indent=2,sort_keys=True)+'\n');p.chmod(0o444);canonical.chmod(0o444)
print('checkpoint',m.sha(p));print('canonical',m.sha(canonical));print('raw receipt records',len(raws),'frozen references',len(refs),'native entries',len(expected))
