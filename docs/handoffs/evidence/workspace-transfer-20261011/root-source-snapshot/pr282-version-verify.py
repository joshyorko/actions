import ast, hashlib, json, subprocess
from pathlib import Path
import yaml
R=Path('/workspace/engineering/pr282'); BASE='811c826addf662c3a7de23d27c5f1014ecd3c6a3'; BOOT='71f60ee8b931cb968866db5a8f45ba2056d18ed8'
G='.github/workflows/_gen_workflows.py'; W='.github/workflows/actions_runtime_tests.yml'; T='developer/tests/test_canvas_published_workflow.py'; D='docs/skills/repository-operations.md'
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def old(p,s=BASE):return git('show',s+':'+p)
def sha(b):return hashlib.sha256(b).hexdigest()
def tree(s):return {l.split('\t')[1]:l.split('\t')[0] for l in git('ls-tree','-r',s).decode().splitlines()}
old_yaml=yaml.safe_load(old(W)); new_yaml=yaml.safe_load((R/W).read_bytes())
name='Verify Canvas published-Core Runtime and browser acceptance'
def step(v):return next(s for s in v['jobs']['build']['steps'] if s['name']==name)
a,b=step(old_yaml)['run'],step(new_yaml)['run']; la=next(l for l in a.splitlines() if l.startswith('browser_version=')); lb=next(l for l in b.splitlines() if l.startswith('browser_version='))
assert a==b.replace(lb,la);step(new_yaml)['run']=step(old_yaml)['run'];assert old_yaml==new_yaml
old_validator=a.split("<<'PY'\n",1)[1].rsplit('\nPY',1)[0];new_validator=b.split("<<'PY'\n",1)[1].rsplit('\nPY',1)[0];assert old_validator==new_validator
oldgen=ast.parse(old(G));newgen=ast.parse((R/G).read_bytes())
rawnew='          '+lb;rawold='          '+la
class Normalize(ast.NodeTransformer):
 hits=0
 def visit_Constant(self,n):
  if isinstance(n.value,str) and rawnew in n.value:
   self.hits+=1;n.value=n.value.replace(rawnew,rawold)
  return n
x=Normalize();x.visit(newgen);assert x.hits==1;assert ast.dump(oldgen)==ast.dump(newgen)
outputs=['actions_runtime_tests.yml','actions_runtime_rcc_provider_rollback.yml','actions_runtime_frozen_catalog_rollback.yml','actions_core_tests.yml','http_helper_tests.yml','actions_runtime_pypi_release.yml','actions_runtime_binary_release.yml','actions_runtime_recovery.yml']
unchanged={p:sha((R/'.github/workflows'/p).read_bytes()) for p in outputs[1:]};assert all((R/'.github/workflows'/p).read_bytes()==old('.github/workflows/'+p) for p in outputs[1:])
assert (R/'.github/dependabot.yml').read_bytes()==old('.github/dependabot.yml')
changed=git('diff','--name-only',BASE).decode().splitlines();assert sorted(changed)==sorted([G,W,T,D])
entries=tree(BASE)
bootstrap_inputs=[p for p in entries if p.endswith(('pyproject.toml','poetry.lock')) or p=='tasks.py' or p=='developer/toolkit.py' or (p.startswith('developer/') and '/' not in p.removeprefix('developer/') and p.endswith('.yaml')) or p.startswith('devutils/bin/develop.')]
assert all(old(p,BOOT)==(R/p).read_bytes() for p in bootstrap_inputs)
bootstrap=Path('/workspace/actions-cloud/receipts/pr282-writer/bootstrap.log'); assert 'SUCCESS' in bootstrap.read_text()
source_receipt=Path('/workspace/actions-cloud/receipts/pr282-writer/source-checkpoint-receipt.json');assert json.loads(source_receipt.read_text())['source']['commit']==BOOT
helper='action_server/tests/action_server_tests/mcp/test_canvas_query_template.py';h=sha((R/helper).read_bytes());assert h=='edc7ccfb85bd20bc89775f73ee45039bcf4c501fe6dae9a5ebd81a80e16eda4e';assert (R/helper).read_bytes()==old(helper)
shared=Path('/workspace/actions-cloud/receipts/pr305-runner/frozen-helpers/test_canvas_query_template.py');assert sha(shared.read_bytes())==h
result={'base':BASE,'tracked_changed_paths':changed,'generator_AST_only_one_expected_version_measurement_change':True,'full_generated_YAML_policy_only_expected_measurement_change':True,'validator_and_failure_diagnostics_byte_equal':True,'validator_sha256':sha(new_validator.encode()),'all39_predicates_unchanged':True,'seven_other_outputs_byte_equal':unchanged,'dependabot_byte_equal':True,'all_other_tracked_leaves_preserved_by_diff':len(entries)-4,'helper_sha256':h,'shared305_frozen_helper_sha256':h,'bootstrap_reuse':{'source':BOOT,'source_receipt':str(source_receipt),'source_receipt_sha256':sha(source_receipt.read_bytes()),'log':str(bootstrap),'log_sha256':sha(bootstrap.read_bytes()),'inputs_count':len(bootstrap_inputs),'input_paths':bootstrap_inputs,'all_input_bytes_equal':True},'expected_preflight':lb,'no_native_or_browser_gate_execution':True}
Path('/workspace/engineering/pr282-version-source-proof.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,indent=2))
