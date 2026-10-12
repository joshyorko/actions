import ast,hashlib,json,subprocess
from pathlib import Path
source='d642a3ac24f8da85101538bdfdf59b509fd74bfb';tree='fdf2823ebcdbd938b9047fd452c9fb13eb4be4e4';root=Path.cwd();out=Path('/workspace/engineering/pr302-actual310-control-refresh');read=lambda p:subprocess.check_output(['git','show',source+':'+p],text=True);sha=lambda b:hashlib.sha256(b).hexdigest()
allowed=['.github/workflows/_gen_workflows.py','.github/workflows/actions_runtime_rcc_provider_rollback.yml','developer/tests/test_rcc_provider_rollback_workflow.py'];changed=subprocess.check_output(['git','diff',source,'--name-only'],text=True).splitlines();assert sorted(changed)==sorted(allowed)
p=allowed[0];before=ast.parse(read(p));after=ast.parse((root/p).read_text());find=lambda t:next(n for n in t.body if isinstance(n,ast.ClassDef) and n.name=='ActionServerRccProviderRollback');values={}
for n in find(after).body:
 if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['candidate_sha','candidate_tree']:
  name=n.targets[0].id;values[name]=ast.literal_eval(n.value);n.value=next(x.value for x in find(before).body if isinstance(x,ast.Assign) and isinstance(x.targets[0],ast.Name) and x.targets[0].id==name)
assert values=={'candidate_sha':source,'candidate_tree':tree};assert ast.dump(before)==ast.dump(after)
p=allowed[2];before=ast.parse(read(p));after=ast.parse((root/p).read_text());test_values={}
for n in after.body:
 if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['CANDIDATE_SHA','CANDIDATE_TREE']:
  name=n.targets[0].id;test_values[name]=ast.literal_eval(n.value);n.value=next(x.value for x in before.body if isinstance(x,ast.Assign) and isinstance(x.targets[0],ast.Name) and x.targets[0].id==name)
assert test_values=={'CANDIDATE_SHA':source,'CANDIDATE_TREE':tree};assert ast.dump(before)==ast.dump(after)
p=allowed[1];old=read(p);new=(root/p).read_text();assert new.replace(source,'43a73f2dbc48ba9afcb43a22e98b1e087712cdc8').replace(tree,'e05141d122b7245b626c5d0389cf9b653c8ad300')==old
leaves={}
for entry in subprocess.check_output(['git','ls-tree','-rz',source]).split(b'\0'):
 if entry:
  meta,path=entry.split(b'\t',1);mode,kind,blob=meta.decode().split();leaves[path.decode()]=(mode,kind,blob)
for p,(mode,kind,blob) in leaves.items():
 if p not in allowed:
  assert (root/p).read_bytes()==subprocess.check_output(['git','cat-file','blob',blob]);assert ('100755' if (root/p).stat().st_mode & 0o111 else '100644')==mode
outputs=[p for p in leaves if p.startswith('.github/workflows/') and p.endswith('.yml') and p!=allowed[1]]
# Every unrelated tracked workflow and dependabot was covered above, including7othergeneratoroutputs.
result={'source_Sprime':source,'source_tree':tree,'only_allowed_three_paths_changed':changed,'generator_AST_entiremodule_onlytwo_scalar_pin_changes':True,'workflow_test_AST_entiremodule_onlytwo_scalar_expected_constants':True,'pin_values':values,'test_expected_values':test_values,'generated_workflow_only_replaced_sourceSHA_tree_identity_literals':True,'all_other_tracked_leaf_bodies_modes_equal_Sprime':len(leaves)-len(allowed),'total_leaves':len(leaves),'all_unrelated_workflow_bodies_equal':outputs,'other7_generated_outputs_and_dependabot_equal':True,'package_runtime_Corefloor_profile_publishone_raw_summary_3selectors_RCC_bytes_deadlines_identical':True,'canonical_guide_byte_exact_Sprime':'Source/control/nine-sample/fullproducer/testedmerge lesson alreadyintegrated sourceSprime; no cosmeticduplication','actual_execution':'NONE_NEW','native92498':'UNQUALIFIED_CHANGED_ADAPTER_NO_REBUILD'}
(out/'control-only-source-and-output-proof.json').write_text(json.dumps(result,indent=2)+'\n');print('Only2genpins/2testconstants/YAMLidentities changed; allother1406leaves byte/mode exactSprime; sourcepackage/contracts unchanged')
