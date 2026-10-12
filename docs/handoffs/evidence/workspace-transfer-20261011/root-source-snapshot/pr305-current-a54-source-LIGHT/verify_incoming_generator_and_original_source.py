import ast,hashlib,json,os,stat,subprocess
from pathlib import Path
import yaml
R=Path('/workspace/engineering/pr305');O=Path('/workspace/engineering/pr305-current-a54-source-LIGHT')
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def sha(b):return hashlib.sha256(b).hexdigest()
old=git('rev-parse','HEAD^1').decode().strip();head=git('rev-parse','HEAD').decode().strip();path='.github/workflows/_gen_workflows.py'
a,b=[ast.parse(git('show',ref+':'+path)) for ref in [old,head]]
class CheckoutFilterOnly(ast.NodeTransformer):
 def visit_ClassDef(self,node):
  if node.name in ['ActionServerTests','ActionServerPyPiRelease']:
   for item in ast.walk(node):
    if isinstance(item,ast.List):item.elts=[e for e in item.elts if not (isinstance(e,ast.Constant) and e.value=='.gitattributes')]
  return node
assert ast.dump(CheckoutFilterOnly().visit(a),include_attributes=False)==ast.dump(CheckoutFilterOnly().visit(b),include_attributes=False)
for path in ['.github/workflows/actions_runtime_tests.yml','.github/workflows/actions_runtime_pypi_release.yml']:
 oldyaml=yaml.safe_load(git('show',old+':'+path));newyaml=yaml.safe_load(git('show',head+':'+path));assert newyaml['on']['pull_request']['paths'].count('.gitattributes')==1;newyaml['on']['pull_request']['paths'].remove('.gitattributes');assert newyaml==oldyaml
primary=Path('/workspace/actions-cloud/bin/rcc');fixture=R/'action_server/src/actions/server/bin/rcc-18.19.3';assert sha(primary.read_bytes())==sha(fixture.read_bytes())=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428';assert stat.S_IMODE(primary.stat().st_mode)==0o700 and stat.S_IMODE(fixture.stat().st_mode)==0o711
owner=Path('/workspace/engineering/pr305-current-e3c-source-LIGHT/OWNERFINAL-current584a-ordinary-e3-source-LIGHT-full-and-actual-HOLD.json');assert sha(owner.read_bytes())=='5835c7c1b57493d784ea39cf0c037253460b04b3b3c9c4fa48fb1db1a887c387';d=json.loads(owner.read_text())
for row in d['frozen_bindings']:
 p=Path(row['path']);assert p.stat().st_size==row['bytes'] and sha(p.read_bytes())==row['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode']
proof=json.loads((O/'committed-current-5306-typed-ordinary-union-source-proof.json').read_text());rows=json.loads(Path(proof['source_inventory']['path']).read_text());assert len(rows)==1427
for row in rows:
 p=R/row['path'];body=os.readlink(p).encode()if row['mode']=='120000'else p.read_bytes();assert sha(body)==row['sha256'] and stat.S_IMODE(p.lstat().st_mode)==row['fs_mode']
assert git('status','--porcelain')==b''
p=O/'post-LIGHT-complete-source-generator-and-original584-preservation.json';assert not p.exists();p.write_text(json.dumps({'status':'PASS','source':head,'tree':proof['tree'],'current_complete_source_leaves':1427,'all_current_source_body_modes_exact':True,'whole_generator_AST_exact_parent584_after_only_two_accepted_checkout_filter_constants_removed':True,'whole_two_generated_YAML_equal_parent584_after_only_checkout_PR_path_removed':True,'all_original584_OWNER_frozen_bindings_unchanged':len(d['frozen_bindings']),'primary_RCC_mode':'0700','own_RCC_fixture_mode':'0711','both_RCC_sha256':sha(primary.read_bytes()),'strict_scope':'PR305 original Canvas fixture/controller semantics remain original accepted bytes; PR28239-predicate gate is separately owned, not an invented PR305 method.'},indent=2)+'\n');p.chmod(0o600);print('POST_LIGHT_SOURCE_GENERATOR_ORIGINAL584=PASS')
