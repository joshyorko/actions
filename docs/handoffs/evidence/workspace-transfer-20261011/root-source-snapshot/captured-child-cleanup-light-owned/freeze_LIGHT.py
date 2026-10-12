import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

OUT=Path('/workspace/engineering/captured-child-cleanup-light-owned')
ROOT=Path('/workspace/engineering/captured-child-cleanup')


def bind(path):
    path=Path(path);h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':h.hexdigest()}


def suites(name):
    root=ET.parse(OUT/name).getroot()
    rows=list(root.iter('testcase'))
    return {'tests':len(rows),'passed':sum(c.find('failure') is None and c.find('error') is None and c.find('skipped') is None for c in rows),
            'failed':sum(c.find('failure') is not None for c in rows),
            'errors':sum(c.find('error') is not None for c in rows),
            'skipped':sum(c.find('skipped') is not None for c in rows),
            'failure_names':[c.get('name') for c in rows if c.find('failure') is not None]}


sourceproof=json.loads((OUT/'LIGHT-immutable-source-and-preservation-proof.json').read_bytes())
assert subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)==b''
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==sourceproof['head']
green=suites('permanent-GREEN-junit.xml');red=suites('permanent-original-RED-successor-junit.xml')
initial=suites('permanent-original-RED-junit.xml');adjacent=suites('adjacent-source-controls-junit.xml')
assert green=={'tests':10,'passed':10,'failed':0,'errors':0,'skipped':0,'failure_names':[]}
assert red['failed']==2 and red['passed']==8 and red['errors']==0
assert initial['errors']==10 and initial['passed']==0 and initial['failed']==0
assert adjacent['passed']==103 and adjacent['skipped']==1 and adjacent['failed']==adjacent['errors']==0
for name in ['doctor','own-inputs-and-origins','prepared-copy-v2','permanent-GREEN','authored-configured-format','full-configured-static','toolkit','generator-roundtrip','adjacent-source-controls','source-preservation-v2']:
    assert json.loads((OUT/(name+'-exit.json')).read_bytes())['exit_code']==0
assert '96 passed' in (OUT/'toolkit.private.log').read_text()
static=(OUT/'full-configured-static.private.log').read_text()
assert 'Success: no issues found in 350 source files' in static
assert all(s in static for s in ['ruff check','ruff format','isort'])
generator=json.loads((OUT/'generator-roundtrip-successor-v2-receipt.json').read_bytes())
assert generator['generated_output_count']==8 and generator['all_tracked_GitHub_YAML_count']==30
original=Path('/workspace/engineering/pr306-original-cleanup-deterministic-control-owned/OWNERFINAL-original-cleanup-deterministic-control-v2.json')
assert bind(original)['sha256']=='ab1d68eded83108fa58c32046f2d2c2b8dfa92972b6fedf7a66a4cb72ab87c22'
for item in json.loads(original.read_bytes())['bindings']:assert bind(item['path'])==item
ind=Path('/workspace/engineering/pr306-original-cleanup-deterministic-independent-review/OWNERFINAL-independent-original-cleanup-deterministic-RED-review.json')
assert bind(ind)['sha256']=='58b007d23144a46522095ba727eeb8ec6cfaaf13dd09bcbbb387222c57f0bfa5'
for path in OUT.iterdir():
    if path.is_file():path.chmod(0o600)
refs=[bind(path) for path in sorted(OUT.iterdir()) if path.is_file()]
refs += [bind(original),bind(ind),bind(Path('/workspace/engineering/pr306-current618-fada-startup-diagnostic-original-owned/frozen-readonly-captured-live-child-cleanup-contract-proposal.json'))]
for name in sourceproof['changed']+sourceproof['added']:refs.append(bind(ROOT/name))
r={'schema':'captured-child-cleanup-light-source-checkpoint-v1',
   'decision':'SOURCE_LIGHT_PASS_STOP_FOR_INDEPENDENT_REVIEW_FULL_AND_PUSH_NOT_AUTHORIZED',
   'branch':'fix/captured-child-cleanup-deadline-20261011','head':sourceproof['head'],'tree':sourceproof['tree'],'ordered_parents':sourceproof['parents'],
   'actual_target':'a0d258a16095b95b1bf9000cb1201cddfaff4779',
   'source_scope':{'changed':sourceproof['changed'],'added':sourceproof['added'],
       'whole_original_module_AST_preserved_after_removing_one_added_wait_block':True,
       'remaining_same_deadline_only':True,'Popen_exclusive_wrapper_reap_unchanged':True,
       'strict_live_zombie_error_snapshot_result_fields_unchanged':True,
       'legacy_Process_stop_startup20_reader2_seconds_unchanged':True,
       'all_original_parent_leaves_and_modes_retained':True,'current_leaf_count':sourceproof['current_leaf_count'],
       'tracked_source_line_delta':'process.py21 insertions; permanent controls220 lines; exact accepted guide12 lines'},
   'implemented_behavior':'After exclusive Popen wrapper reap, inspect identity-bound captured handles; wait only observed live nonzombie handles through remaining SAME deadline, retain wait/inspection errors, then use original strict classification. No fresh child PID lookup or extra signal.',
   'prepared_environment':{'Doctor':'PASS','Bootstrap':'Original successful own pr306 prepared proof plus30 exact inputs; five lossless independent copies on existing exec /dev/shm with literal path-only rebinding; no installer',
      'physical_storage':'/dev/shm/actions-captured-child-cleanup-prepared-envs-20261011',
      'own_checkout_env_links':'Each package .venv resolves to its unique owned physical environment; concrete module files resolve under own checkout source.',
      'all5_original_complete_source_env_inventories_unchanged_after_LIGHT':True,
      'RCC':'v18.19.3; primary/source/copied fixture22,282,402B SHA7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428',
      'existing_autouse_fixture':'Unchanged local RCC configure identity --do-not-track; no mocked/no-op override, no provider/native Runtime invocation'},
   'verification':{'original_private_experiment':'Immutable1expectedFAIL8PASS retained and independent58b GO; no repeat',
      'permanent_initial_setup_failure':initial,'permanent_original_RED_successor':red,'permanent_fixed_GREEN':green,
      'permanent_RED_GREEN_AST_identical_except_formatter_whitespace':True,
      'adjacent_source_controls':adjacent,'adjacent_skip':'Existing ACTIONS_REAL_RCC_ARTIFACT_TEST opt-in absent; actual provider remains unverified',
      'ToolkitTest':{'passed':96},'configured_Ruff_format_Isort':'PASS complete invoke lint',
      'configured_Mypy':{'status':'PASS','source_files':350,'notes':'Three annotation-unchecked notes for untyped permanent-test helper initializer; no type errors.'},
      'generated_workflow_roundtrips':8,'all_tracked_GitHub_YAML_parsed_and_preserved':30,
      'whole_GitHub_bytes_exact_actual_parent':True,'authored_whitespace':'PASS'},
   'native_source_parity':{'producer_inventory_count':sourceproof['current_producer_count'],'original92498_count':268,
      'changed_old_producer_paths':sourceproof['native_changed_original_paths'],'added_producer_paths':sourceproof['native_added_paths'],
      'only_new_delta_from_actual_target':sourceproof['only_new_producer_delta_from_actual_parent'],
      'five_selected_tests_exact_actual_target_and_original92498':True,
      'qualification':'UNQUALIFIED production bytes differ; no old native/control receipt carry, rebuild, repin or execution'},
   'preservation':{'original_private31_bindings_exact':True,'original_failed_constructor_and_1RED8PASS_retained':True,
      'original_Source_f432_in_pr306_unchanged':True,'original_private_helpers_not_rewritten':True,
      'source_proof_draft':'First proof failed a documentation anchoring assertion; namedv2 compares exact patch placement and passed, no product/test/gate changes or evidence rewrite'},
   'scope_limits':['No full suite run or push/PR creation/merge authorized by this checkpoint.','New permanent cleanup harness uses fake OS handles; adjacent legacy source controls use bounded host Python children, and unchanged feedback fixture local RCC identity configuration. No native Runtime/provider/browser/installer/network qualification.',
      'Hosted readiness cause, final survivor identity and original remaining budget UNKNOWN; otherfour failure nodes unsampled.','Public fix improves captured-child remaining-budget use; it does not establish full cleanup coverage, graceful leases, PID discovery/adoption, platform/native or private acceptance.'],
   'full_gate':'HOLD; fresh overlay capacity observation below required1.2GiB; root independent-review plus separate capacity/full release required',
   'capacity_observation_bytes':os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize,
   'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; exact accepted36cc12line lesson applied in commit499a',
      'Durable_learning_captured':'A quick wrapper reap plus short descendant waits can return early with unused shared budget; retain strict incomplete result and exclusive wrapper ownership, and separate controlled proof from unknown hosted cause.',
      'Evidence':'Original imported f432/AST4daa RED and independent58b; permanent unchanged-AST RED2/8 and GREEN10; source insertion uses only remaining same deadline.',
      'Stale_or_ambiguous_guidance_removed':'No assumed whole deadline use; no transfer of synthetic clock schedule to hosted timing or wrapper reap to whole-tree success.',
      'Remaining_uncertainty':'Hosted cause and full/native/platform acceptance still unverified; full source gate held.'},
   'Upstream_disposition':'none; Actions source change, no upstream defect established',
   'bindings':refs}
for item in refs:assert bind(item['path'])==item
p=OUT/'OWNERFINAL-captured-child-cleanup-LIGHT-source-checkpoint.json'
with p.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
p.chmod(0o600)
print(json.dumps(bind(p)))
