import ast,copy,hashlib,importlib.util,json,subprocess
from pathlib import Path
import yaml
r=Path("/workspace/engineering/runtime-checkout-eol");o=Path("/workspace/engineering/runtime-checkout-eol-source");base="6181b044c75de35386f1ae30e71725398b6a7feb"
def original(p):return subprocess.check_output(["git","show",base+":"+p],cwd=r)
p=".github/workflows/_gen_workflows.py";tree=ast.parse((r/p).read_text());before=ast.parse(original(p));removed=[]
for node in tree.body:
 if isinstance(node,ast.ClassDef) and node.name=="ActionServerTests":
  method=next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name=="on_part")
  candidates=[n for n in method.body if isinstance(n,ast.Expr) and ast.unparse(n)=="parts['on']['pull_request']['paths'].append('.gitattributes')"]
  assert len(candidates)==1;method.body.remove(candidates[0]);removed.append(node.name)
 if isinstance(node,ast.ClassDef) and node.name=="ActionServerPyPiRelease":
  candidates=[n for n in ast.walk(node) if isinstance(n,ast.List) and any(isinstance(e,ast.Constant) and e.value==".gitattributes" for e in n.elts)]
  assert len(candidates)==1;lst=candidates[0];lst.elts=[e for e in lst.elts if not isinstance(e,ast.Constant) or e.value!=".gitattributes"];removed.append(node.name)
assert ast.dump(tree,include_attributes=False)==ast.dump(before,include_attributes=False)
changed=[".github/workflows/actions_runtime_tests.yml",".github/workflows/actions_runtime_pypi_release.yml"]
proof={}
for p in changed:
 old=yaml.safe_load(original(p));new=yaml.safe_load((r/p).read_bytes());assert new["on"]["pull_request"]["paths"].count(".gitattributes")==1
 new["on"]["pull_request"]["paths"].remove(".gitattributes");assert old==new
 newbytes=(r/p).read_bytes();assert newbytes.replace(b"    - .gitattributes\n",b"")==original(p)
 proof[p]={"old":hashlib.sha256(original(p)).hexdigest(),"new":hashlib.sha256(newbytes).hexdigest(),"only_PR_paths_item_changed":True,"all_matrices_jobs_needs_permissions_tag_and_publisher_guards_exact":True}
paths=subprocess.check_output(["git","ls-files",".github"],cwd=r).decode().splitlines();all_yaml=[p for p in paths if p.endswith((".yml",".yaml"))]
for p in all_yaml:
 yaml.safe_load((r/p).read_bytes())
 if p not in changed:assert (r/p).read_bytes()==original(p),p
spec=importlib.util.spec_from_file_location("checkout_generator",r/".github/workflows/_gen_workflows.py");m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
for target in m.TARGETS:assert yaml.safe_load(target.target_file.read_bytes())==target.full
known={x["path"]:x for x in json.loads((o/"original-source-and-design-bindings.json").read_text())["complete_original_leaves"]};allow={".gitattributes", ".github/workflows/_gen_workflows.py",*changed,"docs/skills/repository-operations.md"}
for p,x in known.items():
 if p in allow:continue
 body=original(p);assert body==(r/p).read_bytes(),p;assert bool(int(x["mode"],8)&0o111)==bool((r/p).stat().st_mode&0o111),p
assert subprocess.check_output(["git","diff","--name-only"],cwd=r).decode().splitlines()==sorted(allow)
for p in ["devutils/tests/test_runtime_checkout_bytes.py","devutils/tests/test_runtime_checkout_workflows.py"]:assert (r/p).is_file()
x={"status":"PASS_COMPLETE_ORIGINAL_SOURCE_BYTES_MODES_AND_NARROW_GENERATOR_SCOPE","base":base,"original_typed_leaves":len(known),"unchanged_original_leaves":len(known)-len(allow),"exact_existing_generator_AST_after_only_two_filter_removals":True,"two_owning_classes":removed,"two_generated_outputs":proof,"eight_generated_target_data_matches":len(m.TARGETS),"all_tracked_GitHub_YAML_parsed":len(all_yaml),"other_tracked_YAML_byte_exact":len(all_yaml)-len(changed),"new_tests":["devutils/tests/test_runtime_checkout_bytes.py","devutils/tests/test_runtime_checkout_workflows.py"],"all_Runtime_and_frontend_source_blobs_modes_unchanged":True}
(o/"complete-scope-and-generator-proof.json").write_text(json.dumps(x,indent=2)+"\n");print(json.dumps(x))
