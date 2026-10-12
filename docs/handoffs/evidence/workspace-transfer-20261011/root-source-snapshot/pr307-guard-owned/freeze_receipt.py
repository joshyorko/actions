import hashlib,json,subprocess
from pathlib import Path
root=Path('/workspace/engineering/pr307');owned=Path(__file__).resolve().parent
head,tree,*parents=subprocess.check_output(['git','log','-1','--format=%H %T %P'],cwd=root,text=True).strip().split()
assert head=='87e412f89b201c697d3e6bd4bd34031cdbd14df3'
assert not subprocess.check_output(['git','status','--porcelain'],cwd=root)
def evidence(path):
 p=Path(path);return {'path':str(p),'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
files=['doctor.log','bootstrap.log','red-behavior.log','final-focused.log','toolkit-test.log','final-configured-gates.log','helper-typecheck.log','controlled-gateway.log','controlled-gateway-receipt.json','refresh-union-receipt.json','preservation-receipt.json','workflow-roundtrip-receipt.json','controlled_gateway.py','outer_invoke_no_yaml.py','workflow_roundtrip.py']
rows={name:evidence(owned/name) for name in files}
gateway=json.loads((owned/'controlled-gateway-receipt.json').read_text());assert gateway['source']['head']==head and gateway['source']['tree']==tree
assert gateway['outer_yaml_forbidden'] and gateway['actual_package_poetry_helper']
assert gateway['package_yaml']['yaml']=='6.0.3'
assert [c['exit_code'] for c in gateway['cases']]==[0,1]
logs=(owned/'final-configured-gates.log').read_text();assert '1173 passed, 13 skipped' in logs and 'Success: no issues found in 335 source files' in logs and '2 files already formatted' in logs
assert '41 passed' in (owned/'final-focused.log').read_text();assert '69 passed' in (owned/'toolkit-test.log').read_text();assert '3 failed' in (owned/'red-behavior.log').read_text()
preservation=json.loads((owned/'preservation-receipt.json').read_text());assert preservation['staged_tree']==tree
source_paths=['action_server/tasks.py','action_server/scripts/build_oauth2_config.py','action_server/tests/build_system_tests/test_oauth2_config_build.py','docs/skills/repository-operations.md']
record={
 'status':'LOCAL_SOURCE_AND_CONTROL_GO; INDEPENDENT_REVIEW_REQUIRED_BEFORE_ROOT_PUSH',
 'source':{'branch':'fix/runtime-release-changelog-selection-20261010','head':head,'tree':tree,'parents':parents,'refresh':json.loads((owned/'refresh-union-receipt.json').read_text()),'files':{p:evidence(root/p) for p in source_paths},'clean':True},
 'guard':{'public_invoke_interface_unchanged':True,'authority':'Sema4AI/oauth-public-configs; existing unpinned authority unchanged','ordered_inputs':['actions-oauth-config.yaml','oauth-config.yaml'],'checked_binary_subprocess':True,'per_input_timeout_seconds':30,'admission':['strict UTF-8','nonblank','safe YAML','root mapping','oauth2Config mapping','providers mapping'],'both_valid_before_same_directory_atomic_replace':True,'original_strings_and_module_format_preserved':True,'previous_module_and_primary_cause_preserved_on_failure':True,'only_owned_temp_cleanup_attempted':True,'cli_diagnostics_exclude_raw_stdout_stderr_and_cause':True,'runtime_poetry_yaml_gateway':gateway['package_yaml'],'empty_provider_mapping':'structurally allowed synthetic fixture; not qualified release content'},
 'validation':{'original_behavior_red':'3 failures: exit17 with empty/error JSON/otherwise-valid body previously overwrote prior module','focused_green':'41 passed: first/second acquisition failures; nonzero with otherwise valid stdout; API error JSON/blank/malformed/wrong shape/invalid UTF8; timeout; temp-write/atomic-replace/cleanup failure; exact raw-byte pair and module rendering; task environment gateway','full_configured_source':'1173 passed / 13 existing skipped / 15 warnings; no source test failure','toolkit':'69 passed','lint':'configured Runtime lint plus explicit helper/test Ruff check and format passed','typecheck':'configured335 files plus explicit helper1 file passed','compile':'helper and existing tasks passed','controlled_gateway':'actual committed Invoke Program -> Runtime Poetry -> helper with outer YAML forbidden; owned fake gh only; baseline pair success; second exit17 preserves prior; private cause withheld; generated module restored','generator':'all8 generated outputs exact; no generator/workflow edits','preservation':preservation},
 'evidence':rows,
 'historical_evidence_preserved':{'original_wheel_sha256':'0f366268f7590e2c0002b8f7e67325810d0d5374775c657b19195c80da48eaaa','original_generated_module_sha256':'f79d95697f1b20691cfff74faa422dc5fa9a13e7fd5d16e98bac3572c6dd7dbe','original_wheel_narrow_consumer_GO_unchanged':True,'no_artifact_rebuild_or_remote_config_acquisition':True,'qualification_attempts':'owned logs1/2/3/5 are proof-harness corrections; attempt4 exposed RCC CONDA_PREFIX selecting outer Poetry environment. All retained; final proof frozen head87e412f8.'},
 'proposal_dispositions':{
  'original_broad_design_2b3095':'DEFERRED: immutable pair/provenance architecture remains dependent on owner authority answer; no manifest/modes/pins/provider cardinality policy implemented',
  'accepted_minimal_boundary_e222695e':'INTEGRATED: adapted to actual helper, finite checked binary acquisition, shape-only admission and atomic pair write',
  'accepted_gateway_bbf66a9c':'INTEGRATED: actual outer-YAML-forbidden controlled proof plus observed RCC activation cleanup; old release-source task remains immutable',
  'accepted_consumer_documentation_4cfc8e79':'INTEGRATED: CLI dry-run/Twine split, PR provenance exclusion, actual checkout identity, selected host wheel and full installed-member complement',
  'accepted_generated_member_followup_b07cfdc9':'INTEGRATED: retained empty generated module remains separate from original narrow installed-wheel GO; no stale unexecuted-consumer claim copied',
  'pr282_hosted_receipt_diagnostics':'PROPOSED_READ_ONLY: existing gates unchanged; stable failure-only predicate categories, safe diagnostics always upload, valid-baseline poison tests; no rerun or source edit in this lane'
 },
 'Documentation improvement':{
  'Canonical file changed or proposed':'Changed docs/skills/repository-operations.md in87e412f8; exact blob and byte digest in source.files',
  'Durable learning captured':'Finite acquisition and shape admission must precede paired atomic generation. Outer Invoke YAML is not assured; Runtime Poetry is the dependency owner and RCC Conda activation can select the wrong interpreter. Dry-run inventory, publication provenance, installed-member identity and generated-content qualification are separate gates. Current task changes do not repair old immutable recovery sources.',
  'Evidence':'RED3/GREEN41, controlled frozen Invoke/Poetry/PyYAML6.0.3 proof, caller-order review9990927d, original retained wheel/generated member and existing publisher/floor source, final configured gates, all8 roundtrip and1404 unchanged blob/mode pairs',
  'Stale or ambiguous guidance removed':'Removed PR generation equivalence claim and implication that dry-run runs Twine; explicitly limits structural empty-provider fixtures and current-helper recovery claims',
  'Remaining uncertainty':'Authoritative supported OAuth pair/revision and provider/release policy remain unidentified; no remote acquisition or actual OAuth/release qualification. Original PR282 Linux admission failed with unknown exact predicate; raw presence remains unknown.'
 },
 'read_only_pr282_diagnostic':evidence('/workspace/engineering/pr282-windows-owned/hosted-linux-admission-diagnostic-proposal.json'),
 'independent_caller_order':evidence('/workspace/engineering/oauth-config-independent-review/existing-caller-order-review.json'),
 'remaining_gates':['acceptance_review independent frozen source/control review','root independent review before normal push','authoritative source pair/release policy before actual OAuth acquisition or qualification'],
 'Upstream disposition':'none: Actions build boundary defect; no established upstream defect or authorized external target'
}
(owned/'successor-receipt.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'head':head,'tree':tree,'receipt':evidence(owned/'successor-receipt.json'),'gateway':rows['controlled-gateway-receipt.json']}))
