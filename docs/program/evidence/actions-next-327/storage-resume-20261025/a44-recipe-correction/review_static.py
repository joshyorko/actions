from pathlib import Path
import ast,difflib,hashlib,json,zipfile,re
r=Path('/workspace/recovery327/a44-recipe-correction');b=Path('/workspace/recovery327/actions-327-a44-d0c87a38-installed-candidate.zip');i=json.loads((r/'identity.json').read_text());h=lambda x:hashlib.sha256(x).hexdigest();assert h(b.read_bytes())==i['original_bundle_sha256']
with zipfile.ZipFile(b) as z:
 old=z.read('browser/qualify.py');new=(r/'qualify.py').read_bytes();assert h(old)==i['original_recipe_sha256'] and h(new)==i['corrected_recipe_sha256']
 swaps=[('Prepared a42 official-host','Prepared a44 official-host'),('730f277ce13bd3a123c854c85c1c9fc2c185096c','d0c87a38a937cc339e8e661ac453c7a62ed41fa6'),('fresh a42 v2 app','fresh a44 v2 app')]
 expected=old.decode()
 for a,c in swaps:
  assert expected.count(a)==1;expected=expected.replace(a,c)
 assert expected.encode()==new
 assert ''.join(difflib.unified_diff(old.decode().splitlines(keepends=True),new.decode().splitlines(keepends=True),fromfile='original-bundle/browser/qualify.py',tofile='corrected/browser/qualify.py'))==(r/'recipe.patch').read_text()
 class Normalize(ast.NodeTransformer):
  def visit_Constant(self,node):
   if isinstance(node.value,str):
    for a,c in swaps:node.value=node.value.replace(a,c)
   return node
 tree=ast.parse(new)
 assert ast.dump(Normalize().visit(ast.parse(old)),include_attributes=False)==ast.dump(tree,include_attributes=False)
 config=json.loads(z.read('browser/candidate.example.json'));wheels=json.loads(z.read('wheels.json'))
 assert config['source_sha']==z.read('source-sha.txt').decode().strip()==i['source_sha']
 assert config['wheels']==wheels
 constants={}
 for node in ast.walk(tree):
  if isinstance(node,ast.Assert) and isinstance(node.test,ast.Compare):
   left=node.test.left
   if isinstance(left,ast.Subscript) and isinstance(left.value,ast.Name) and left.value.id=='CONFIG' and isinstance(left.slice,ast.Constant) and len(node.test.comparators)==1 and isinstance(node.test.comparators[0],ast.Constant):
    key=left.slice.value;value=node.test.comparators[0].value
    if key in ['source_sha','runtime_version','core_version']:assert config[key]==value;constants[key]=value
 assert set(constants)=={'source_sha','runtime_version','core_version'}
 for name,digest in wheels.items():assert h(z.read(name))==digest
 sandbox={}
 for name in ['browser/browser-preflight.mjs','browser/browser.mjs']:
  text=z.read(name).decode();sandbox[name]={'chromiumSandbox_true':bool(re.search(r'chromiumSandbox\s*:\s*true',text)),'no_sandbox_flag':'--no-sandbox' in text};assert sandbox[name]['chromiumSandbox_true'] and not sandbox[name]['no_sandbox_flag']
 result={'status':'STATIC_REVIEW_PASS','bundle_sha256':h(b.read_bytes()),'original_recipe_sha256':h(old),'corrected_recipe_sha256':h(new),'exact_replacements':swaps,'patch_exact':True,'ast_only_three_constants_changed':True,'config_assertions':constants,'wheel_hashes_verified':wheels,'sandbox':sandbox,'executed':False}
 (r/'review-evidence.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
