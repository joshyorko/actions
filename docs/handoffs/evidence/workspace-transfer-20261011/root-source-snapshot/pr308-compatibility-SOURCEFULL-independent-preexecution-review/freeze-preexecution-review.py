import hashlib,json,shutil,subprocess
from pathlib import Path
B=Path('/workspace/engineering/pr308-rcc-compatibility-SOURCEFULL-preexecution');R=Path('/workspace/engineering/pr308');O=Path('/workspace/engineering/pr308-compatibility-SOURCEFULL-independent-preexecution-review')
def bind(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(1048576),b''):h.update(x)
 return {'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}
proposal=B/'OWNERFINAL-reviewed-inputs-current-b614-SOURCEFULL-preexecution-proposal-v2.json';p=json.loads(proposal.read_bytes());readback=O/'safe-independent-frozen-full-launcher-readback.json';proof=json.loads(readback.read_bytes())
assert bind(proposal)['sha256']=='084faca6148648888627bfd7ffd0045d5b518b20ab6f77e5b8882adb404be32e'
assert all(bind(Path(v['path']))==v for v in p['frozen_launcher_input_bindings'])
light=json.loads(Path(p['SOURCE_LIGHT']['path']).read_bytes());assert all(bind(Path(v['path']))==v for v in light['frozen_bindings'])
assert not subprocess.check_output(['git','--no-optional-locks','status','--porcelain'],cwd=R)
refs=[bind(proposal),bind(readback),bind(O/'review-full-launcher-readonly.py'),bind(O/'review-full-launcher-readonly-v2.py'),bind(Path(p['independent_SOURCE_LIGHT_GO']['path'])),bind(Path(p['documentation_improvement']['exact_delta']['path']))]
rootargv=proof['parent_root_adoption_argv'];assert rootargv==['timeout','--signal=TERM','--kill-after=10s','900s',*p['outer_launcher_argv']]
d={
 'schema':'independent-RCC-compatibility-SOURCEFULL-preexecution-review-v1',
 'decision':'GO_CONDITIONAL_PREEXECUTION_ONLY_EXACT_ROOT_OUTER900_ADOPTION_DISTINCT_CAPACITY_AND_SERIALIZATION_RELEASE_REQUIRED',
 'owner_final_proposal':refs[0],
 'immutable_launcher':next(v for v in p['frozen_launcher_input_bindings'] if v['path'].endswith('launch-one-root-reviewed-source-full-v2.py')),
 'source':p['source'],
 'reviewed_root_execution_argv':rootargv,
 'execution_cwd':'/workspace/engineering/pr308',
 'exact_configured_full_argv':p['configured_full_argv'],
 'exact_configured_package_argv':p['configured_package_argv'],
 'configured_package_cwd':p['configured_package_cwd'],
 'adoption_contract':{
  'parent':'Root must wrap the exact original bash argv with reviewed timeout --signal=TERM --kill-after=10s 900s. Original084f bare outer metadata is preserved and does not itself establish a parent bound. No owner/source changes required; root explicitly accepted this separate parent envelope.',
  'budgets':{'parent_TERM_seconds':900,'parent_KILL_grace_seconds':10,'preflight_seconds':120,'full_TERM_seconds':600,'full_KILL_grace_seconds':10,'postconditions_seconds':120,'maximum_component_stage_seconds':850,'parent_margin_seconds':50},
  'authority':'Exactly one source full only after distinct root release; this review is not execution authority. No candidate5/7276, provider/native/browser/consumer/install/hosted control invocation authorized.',
  'capacity':'Root must verify fresh /workspace free>=1200000000 immediately before release; launcher independently rejects below floor before full. Current preparation/independent metadata are not release capacity evidence. Root batch20/21 recovery and clear heavy slot must precede execution.',
  'identity':'Immediately before the root command, rehash exact084f proposal/dd29 launcher/all10 proposal bindings and sourceLIGHT336c/all71 references, exactb614/6fa clean1421 source, activation6478 and managed/own7e588 RCC modes,30 prepared inputs/five configs. Rehash nested installed xdist/toolkit/task source identities in the bound worker proof; launcher dynamically checks five own prefixes/origins before and after.',
  'environment':'Source only exact activation6478; all18 exports plus primary PATHfirst verified before RCC. Root selected binary/provider/real opt-in compatibility flags must be absent. ROOT managed toolkit/RCC3 unchanged. Driver allows only normal declared RCC task/holotree PATH additions while checking cached sys.prefix and managedbin presence, then sets ACTIONS_RUNTIME_TEST_PYTHON to ownpr308 interpreter before unchanged invoke.',
  'outputs':'Require all seven fresh named output paths absent and no other actor using the owned root. Exclusive xb raw log consumes the namespace; one-attempt marker written only after preflight. No retry or overwrite after any failure.',
  'completion':'Overall root parent exit0 plus launcher terminalPASS, full_startedTrue, exact configured full return0 and postconditions return0 are required. Validate observed full counts/worker2 from original log after execution; do not predict or carry an older full count. Parent timeout/failure or absent postcondition/terminal remains HOLD even if a child log contains passing tests.'
 },
 'verified_readonly':{'all10_proposal_and71_sourceLIGHT_bindings_prepost_exact':True,'source_complete1421_and_execbodies_clean':True,'prepared30_inputs_five_config_hashes_exact':True,'activation18_export_values_and_PATH19_exact_source_derived':True,'managed_RCC3_700_and_ignored_own_RCC3_711_sha7e588_exact':True,'worker2':'Actual installed own xdist reads PYTEST_XDIST_AUTO_NUM_WORKERS before CPU fallback; unchanged toolkit copies it and unchanged task uses pytest -n auto. Hash/source excerpts independently match three current files. Actualworker2 remains an execution result to check.', 'dynamic_prepost':'Frozen guard performs five concrete own Poetry interpreter/module-origin calls, all1421 source bodies/execmodes/all71refs/30configs and hash-pinned original1192/helper0444/browser/historicalV5 inventory inspector; no new binaries invoked by those data checks.','sourceLIGHT_preservation':'Original defaults/control c103/D5a and18 guide lines accepted ea79 remain exact; current ordinary parent0a6 retained.','all_execution_outputs_absent_at_review':True},
 'primary_and_secondary_failure_handling':{'private_log':'umask077/exclusive binary raw original stdout+stderr; no payload printed to chat','full_return':'Full configured return remains primary; postcondition exception/return stored separately and cannot convert failure toPASS','preflight_exception':'Primary category and full encoded traceback retained separately; if preflight rejects, marker/full not started','postcondition_exception':'Encoded traceback avoids original binary-stream TypeError; final statusFAIL/HOLD retains primary fields','originals':'ef74 initial proposal/939e old launcher and pure private-log TypeError RED + encoded trace GREEN preserved; named084f/dd29 changed only proposal filename and two logging sites. No actual full or preflight was executed during preparation/review.'},
 'reviewer_construction_history':'Initial independent literal-only shell parser handled ${NAME} but omitted $NAME expansion and failed. Original read-only reviewer script retained; namedv2 adds the equivalent literal expansion and verifies all18 values without sourcing activation. No owner/source/gate bytes changed and no full preflight ran.',
 'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md in immutableb614; exact accepted18-line source patch reused','Exact_delta':refs[5],'additions':18,'removals':0,'Durable_learning':'Default managed pins, exact isolated provenance/descriptor/cache identity and functional qualification remain separate; typed lease/cleanup evidence retains null UNKNOWN. The root adoption additionally separates child task timeout from parent/pre/post envelope without relabeling original metadata.','Evidence':'Accepted SOURCE_LIGHTea79/sourceb614, frozen084f/dd29 code inspection, actual activation/worker/task source hashes, unchanged ef74/TypeError correction and exact root-agreed900 adoption.','Stale_or_ambiguous_guidance_removed':'No source/guide child or cosmetic diary; original bare outer metadata explicitly remains a limitation until reviewed root bound is adopted.','Remaining_uncertainty':'No source full or new binary functional qualification executed; modified5 clean-source equivalence, typed worker release/reaping, full133/134/provider/private/native/platform/OAuth/release remain HOLD.'},
 'Upstream_disposition':'none',
 'evidence':refs,
 'current_readonly_workspace_free_bytes':shutil.disk_usage('/workspace').free,
 'current_execution_status':'NOT_RUN; distinct root capacity/serialization release absent'
}
pout=O/'OWNERFINAL-independent-current-b614-SOURCEFULL-preexecution-review.json'
with pout.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
pout.chmod(0o444);print(json.dumps(bind(pout)))
