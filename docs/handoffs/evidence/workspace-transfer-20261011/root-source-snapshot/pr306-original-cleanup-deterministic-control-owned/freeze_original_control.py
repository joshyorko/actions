import ast
import difflib
import hashlib
import json
import os
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

OUT = Path('/workspace/engineering/pr306-original-cleanup-deterministic-control-owned')
ROOT = Path('/workspace/engineering/pr306')


def bind(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


preflight = json.loads((OUT / 'checked-preflight.json').read_bytes())
assert json.loads((OUT / 'preflight-exit.json').read_bytes())['exit_code'] == 0
assert json.loads((OUT / 'original-control-exit.json').read_bytes())['exit_code'] == 10
source = Path(preflight['source']['path'])
assert bind(source) == preflight['source']
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == preflight['head']
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
suite = ET.parse(OUT / 'original-control-junit.xml').getroot().find('testsuite')
assert {k: int(suite.get(k)) for k in ('tests','failures','errors','skipped')} == {'tests':9,'failures':1,'errors':0,'skipped':0}
cases = list(suite.findall('testcase'))
failed = [c.get('name') for c in cases if c.find('failure') is not None]
assert failed == ['test_asynchronous_child_completion_uses_available_deadline']
rows = [json.loads(p.read_bytes()) for p in sorted(OUT.glob('outcome-*.json'))]
assert len(rows) == 9
async_row = next(r for r in rows if r['scenario'] == 'asynchronous-exit')
assert async_row['clock_end'] == 0.41 and async_row['unused_budget'] == 17.59
assert async_row['child_absent_at'] == 0.75 and async_row['live'] == [200]
assert async_row['wrapper_reaped'] and not async_row['descendant_reap_complete']
assert [r['timeout'] for r in async_row['trace'] if r['event'] == 'psutil_wait'] == [0.2, 0.2]
assert all(r['clock_end'] <= r['deadline'] for r in rows)
assert 'returned non-zero exit status 1' in (OUT/'original-control.private.log').read_text()
assert 'v18.19.3' in (OUT/'original-control.private.log').read_text()
proposal = Path('/workspace/engineering/pr306-current618-fada-startup-diagnostic-original-owned/frozen-readonly-captured-live-child-cleanup-contract-proposal.json')
assert bind(proposal)['sha256'] == '731094016f3a6dd34efa423b5680250a8e72b487ff4438ad76ac96a89cd86044'
guide = ROOT / 'docs/skills/repository-operations.md'
text = guide.read_text()
anchor = 'The bounded process-tree result distinguishes wrapper reaping, observed live\n'
assert text.count(anchor) == 1
lesson = ('A captured-tree cleanup can report an observed live child before its shared\n'
          'deadline is exhausted. A deterministic control of the original function\n'
          'returned after 0.41 seconds following two 0.2-second descendant waits and a\n'
          'quick wrapper reap, while a captured child was modeled absent at 0.75 seconds\n'
          'within the unchanged 18-second tree budget. Keep the reported incomplete\n'
          'result false; wrapper reaping does not establish descendant completion.\n'
          'This control establishes an early-return case, not the cause of a hosted\n'
          'timeout whose surviving identity and remaining cleanup budget were not\n'
          'recorded. Any improvement must retain the same deadline and exclusive\n'
          'Popen wrapper wait ownership, with live, zombie and observation-error\n'
          'states kept distinct.\n\n')
patch = ''.join(difflib.unified_diff(text.splitlines(True), text.replace(anchor, lesson+anchor).splitlines(True),
                 fromfile='a/docs/skills/repository-operations.md', tofile='b/docs/skills/repository-operations.md'))
patch_path = OUT / 'canonical-captured-tree-unused-deadline-proposed.patch'
with patch_path.open('x') as f: f.write(patch)
patch_path.chmod(0o600)
paths = sorted(p for p in OUT.iterdir() if p.is_file() and p.name != 'OWNERFINAL-original-cleanup-deterministic-control.json')
bindings = [bind(p) for p in paths]
bindings += [bind(proposal), bind(source), preflight['previous_reuse_proof'], preflight['original_successful_Bootstrap']]
for item in bindings:
    assert bind(Path(item['path'])) == item
tree = subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip()
result = {
 'schema': 'original-cleanup-private-deterministic-control-v1',
 'decision': 'RED_CONFIRMED_ORIGINAL_CAPTURED_CHILD_EARLY_RETURN_WITH_UNUSED_BUDGET_NO_PRODUCTION_PATCH_AUTHORITY',
 'source': {'prepared_head':preflight['head'],'tree':tree,'body':bind(source),
            'function_AST_sha256':preflight['function_AST_sha256'],
            'original_actual_checkout':'522b7bc6e7e9207dac0c745b49d90907ecdf3080',
            'original_actual_body_exact':True,'worktree_clean_before_and_after':True},
 'environment': {'checked_preflight':bind(OUT/'checked-preflight.json'),
                 'own_concrete_module_origins':5,'prepared_input_count':preflight['input_count'],
                 'RCC_version_in_original_gateway_logs':'v18.19.3','RCC_binary':preflight['RCC_primary'],
                 'no_install':True},
 'execution': {'commands':[
      'source /workspace/actions-cloud/activate.sh; timeout --signal=TERM --kill-after=10s 60s rcc task script -r developer/toolkit.yaml -- python /workspace/engineering/pr306-original-cleanup-deterministic-control-owned/preflight.py',
      'source /workspace/actions-cloud/activate.sh; timeout --signal=TERM --kill-after=10s 60s rcc task script -r developer/toolkit.yaml -- python -c [toolkit.poetry action_server run python -m pytest -q -n 0 --confcutdir=owned-control --junitxml=owned-control/original-control-junit.xml owned-control/test_original_cleanup_control.py]'],
      'exact_pytest_argv': ['run','python','-m','pytest','-q','-n','0','--confcutdir='+str(OUT),'--junitxml='+str(OUT/'original-control-junit.xml'),str(OUT/'test_original_cleanup_control.py')],
      'gateway_exit':10,'nested_pytest_exit':1,'outer_timeout':False,
      'tests':9,'passed':8,'failed':1,'errors':0,'skipped':0,
      'failed_test':failed[0], 'pytest_seconds':float(suite.get('time')),
      'focused_control_executions':1,'real_child_processes_or_network':False,
      'scope':'Canonical gateway processes only; target process tree, wrapper and psutil state are fakes; no actual provider/native Runtime/process-tree launch'},
 'early_return_witness':async_row,
 'control_outcomes':[{k:r[k] for k in ('scenario','clock_end','unused_budget','wrapper_reaped','execution_stopped','descendant_reap_complete','live','zombies','error_count','snapshot_complete')} for r in rows],
 'interpretation':[
      'The actual imported immutable function returns incomplete at 0.41 of18 with captured child live; the model permits absence at0.75 within unchanged deadline.',
      'Child state is a deterministic clock-based model; terminate/kill invocations are recorded, not real OS timing or proof that kill causes hosted absence.',
      'PID-reuse control models an identity-bound old psutil handle raising NoSuchProcess; it does not independently test psutil operating-system PID protection.',
      'Observed false result is correctly fail-closed. Control proves available-budget early return, not an acceptance bypass or universal deadline-completion promise.',
      'RED test also asserts original witness preconditions; a future GREEN regression must preserve desired completion assertion and replace original-only witness assertions with repaired-state observations, not relabel this execution.' ],
 'conditional_minimal_fix_proposal': 'Only after root review/authorization: bounded wait of captured descendant handles using remaining SAME tree deadline after exclusive Popen wrapper reap, then strict original final classification. Never put wrapper in psutil wait or extend18/20/readers reservation; do not waive zombie/live/error/snapshot fields.',
 'remaining_uncertainty':['Hosted cleanup remaining deadline and survivor identity unavailable; original readiness rootcause UNKNOWN; otherfour failure nodes unsampled.','No repaired function, GREEN production test, realprocess, Runtime native/provider or private acceptance execution performed.'],
 'bindings':bindings,
 'Documentation_improvement':{
     'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; exact named patch proposed, not applied',
     'Durable_learning_captured':'Exclusive wrapper reap and short descendant waits can leave unused shared budget; preserve incomplete observation rather than treating wrapper reap as whole-tree success.',
     'Evidence':'Actual original body/AST, nine controlled outcomes, RED1/8PASS and unchanged18-second deadline; proposal73109 and original observed artifact retained.',
     'Stale_or_ambiguous_guidance_removed':'No assumed full deadline use and no transfer of synthetic scheduling to hosted timing/rootcause; existing strict cleanup contract retained.',
     'Remaining_uncertainty':'Hosted remainingbudget/survivor UNKNOWN; production improvement not implemented or tested.'},
 'Upstream_disposition':'none; source behavior belongs to Actions, no upstream defect established'
}
final = OUT/'OWNERFINAL-original-cleanup-deterministic-control.json'
with final.open('x') as stream: json.dump(result,stream,indent=2);stream.write('\n')
final.chmod(0o600)
print(json.dumps({'path':str(final),'bytes':final.stat().st_size,'sha256':bind(final)['sha256'],'decision':result['decision']}))
