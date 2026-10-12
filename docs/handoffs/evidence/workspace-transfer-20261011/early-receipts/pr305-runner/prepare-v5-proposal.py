import pathlib,json,hashlib
r=pathlib.Path('/workspace/actions-cloud/receipts/pr305-runner')
def record(p):
 p=pathlib.Path(p);return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
j=json.loads((r/'immutable-runner-proposal-v4.json').read_text())
assert not pathlib.Path(str(j['one_attempt_root']).removesuffix('-3')+'-4').exists()
j['phase']='FROZEN_V5_SOURCE_AND_SERVICE_FREE_QUALIFICATION_ONLY_ACTUAL_NOT_EXECUTED'
j['runner']=record(r/'canvas-native-public-runner-v5.py');j['controls']=record(r/'test_runner_admission_v5.py')
j['one_attempt_root']=str(j['one_attempt_root']).removesuffix('-3')+'-4'
j['gateway']['exact_argv'][-1]=j['gateway']['exact_argv'][-1].replace('canvas-native-public-runner-v4.py','canvas-native-public-runner-v5.py')
j['supersedes_without_overwrite']={
 'runner':record(r/'canvas-native-public-runner-v4.py'),'controls':record(r/'test_runner_admission_v4.py'),'proposal':record(r/'immutable-runner-proposal-v4.json'),
 'actual_failure':record(r/'actual-v4-failed-checkpoint-scoped.json'),'independent_actual_failure_review':record('/workspace/engineering/pr305-v4-independent-runner-review/independent-actual-v4-failure-review.json'),
 'original_output_trace_inventory':record(r/'actual-v4-original-output-trace.json'), 'earlier_predecessors':j['supersedes_without_overwrite']}
pre=j['preparation'];pre['cause_and_fix']='V4 owned Playwright command returned0, then launch-path assertion failed and fallback overwrote retained command streams with empty AssertionError attributes. Actual V4 report/launch placement UNKNOWN; no reconstruction or acceptance upgrade. Named V5 retains returned CompletedProcess rc/stdout/stderr before guard and only invokes exception-output fallback if no CompletedProcess exists. Strict exact one-case/one-result JSON validates original owned stdout, then measured launch path is required in outerstderr or recognized named-result stderr text/strictbase64 chunks. No source/helper/native/browser/argv changes; only freshsuffix4 and this callback/parser.'
pre['command']='activated RCC task script -r developer/toolkit.yaml -- python -c [toolkit.poetry action_server run ruff format/check namedV5 files; toolkit.poetry action_server run python -m pytest namedV5controlpath -q -n 0; toolkit.poetry action_server run python namedV5runnerpath without execute flag]; cwd pr305; exact arguments retained in corrected2 gateway log.'
pre['log']=record(r/'immutable-runner-v5-final-controls-corrected2.log')
pre['ast_scope_proof']=record(r/'v5-ast-scope-proof.json')
pre['real_collection_evidence']=record(r/'v5-real-collection-controls.json')
pre['result']='75 service-free controls PASS/0skip; Ruffformat/checkPASS; current3ec273+originalnative1192+real locked onecase --list preflightPASS; V5 actual NOTRUN'
pre['warnings']='2317 warnings: repeated robocorp.log Python3.12 deprecated AST access plus4 unknown imported integration markers; no skipped/executed product cases.'
pre['negative_controls']+=['actual returnedCompletedProcess0 then launchguardfailure keeps exact streams and return0 receipt; unchanged argv/cwd/env/timeout', 'same postguardprimary exception survives secondary helperposthash failure; completed streams remain exact', 'actual launchparser exactnamedJSON baseline; outerstderr/text/base64/splitchunks valid; missing/wrongpath/skip/count/name/file/retry/globalerrors/resulterror/malformedstderr/base64/JSON rejected']
pre['prior_failures_preserved'] += [record(r/'immutable-runner-v5-RED.log'),record(r/'immutable-runner-v5-final-controls.log'),record(r/'immutable-runner-v5-final-controls-corrected.log')]
pre['red_green']= {'RED':record(r/'immutable-runner-v5-RED.log'),'RED_result':'2 expected failure actualcopiedV4 callback retention/nestedstderr;56deselected;no productexecution','focused_GREEN':record(r/'immutable-runner-v5-focused-GREEN.log'),'focused_GREEN_result':'18PASS/56deselected before finalprimary-secondary control','full_failure_causes':'FirstRuff E721 exacttype expression corrected with int and notbool; second copiedcontrol output names attempted immutableV4writes ->5PermissionErrors,70PASS. V4bytesunchanged; newcontroloutputs namedV5 only.'}
j['launch_receipt_admission']={'raw_source':'CompletedProcess from unchangedaccepted282 owner, pinned command/cwd/env/results; capture originalstdout/stderr/returncode before guard','report':'unchangedcurrent3ec _assert_canvas_playwright_report validates exactlyone intended passedcase/result/no skips; specfile host-harness.spec.ts, retry integer0 excludingbool, errors[]/noresult.error','channels':'CLIouterstderr or validated named-result.stderr; entries exactsingle textstr or strictbase64 UTF8buffer; adjacentchunksjoined without inserting bytes','path':'unchanged exact <launching> + measuredBROWSER whitespace regex; DEBUGpath only, notlivePID/naturalexit','failure':'missing/malformed/wrongcase/wrongpath fail; primary preserved; completedstreams never overwritten by emptyfallback','locked_reporter_source':record('/workspace/engineering/pr310/action_server/frontend/node_modules/playwright/lib/runner/index.js'),'locked_reporter_source_evidence_lines':{'current_worker_stderr_result_capture':[5360,5377],'JSONresultstderr_serialization':[4147,4162],'text_or_base64_and_JSONstdout':[4190,4202]},'V4_actual_channel_placement':'UNKNOWN because overwritten raw; static driver source only explains possiblechannels, not recovery'}
for ref in j['discovery_preflight']['receipts']: ref.update(record(ref['path'].replace('v4-driver-discovery-','v5-driver-discovery-')))
j['documentation_improvement']={
 'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md exact external follow-up proposed; source3ec unchanged',
 'Durable_learning':'Preserve returned command streams before later receiptassertions; inspect only exact validated named-case JSON capturedstderr or outerstderr for measuredlaunchpath; retain testcase/Runtime/outer evidence separately',
 'Evidence':'V4 frozenfailure213855/independent5fe7; bounded original-output traceaf655; locked reporter code verified; meaningfulRED2/full75GREEN; V5actualNOTRUN',
 'Stale_guidance_removed':'Empty exceptionattributes safely replace completedstreams; DEBUGalways lives inouterstderr; command0/fivetoolRows substitute missingexecutedreport; last-runmarker reconstructs oldreport',
 'Remaining_uncertainty':'V4originalreport/launchbytesunavailable; newactual3ec/native92498 combinedbrowser/public3sample/sharedcache5Run proof pending; fullCore/coldregistry/newer302producer/OAuth/wholeepic unqualified',
 'exact_delta':record(r/'canonical-runner-v5-proposed.patch'),
 'accepted_reviewer_patch_reused':record('/workspace/engineering/pr305-v4-independent-runner-review/canonical-actual-v4-proposed.patch'),
 'preserved_writer_actual_lesson':record(r/'canonical-actual-v4-proposed-delta.md'),
 'preserved_V4_dependency_list_budget_delta':record(r/'canonical-runner-v4-proposed-delta.md'),
 'source_integrated_delta':j['documentation_improvement']['source_integrated_delta']}
j['upstream_disposition']='none';j['actual_consumer_executed']=False;j['attempt_root_created']=False;j['source_mutated_after3ec']=False
p=r/'immutable-runner-proposal-v5.json';assert not p.exists();p.write_text(json.dumps(j,indent=2,sort_keys=True)+'\n')
# Fail closed if any retained reference changed before freeze.
def check(x):
 if isinstance(x,dict):
  if 'path' in x and 'sha256' in x and pathlib.Path(x['path']).is_file():assert record(x['path'])['sha256']==x['sha256'],x['path']
  for v in x.values():check(v)
 elif isinstance(x,list):
  for v in x:check(v)
check(j)
for name in ['canvas-native-public-runner-v5.py','test_runner_admission_v5.py','immutable-runner-proposal-v5.json','canonical-runner-v5-proposed.patch','v5-ast-scope-proof.json']:
 f=r/name;f.chmod(0o444);print(name,record(f)['sha256'])
