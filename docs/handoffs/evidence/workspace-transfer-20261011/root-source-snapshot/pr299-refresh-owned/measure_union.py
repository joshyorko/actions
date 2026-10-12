import hashlib,json,subprocess
from pathlib import Path
root=Path('/workspace/engineering/pr299');own=Path(__file__).resolve().parent
old='9cb61c52fce35201221b55707d73da9e9b0840a6';target='fbde0d3a248c47c9964851355f96575c89a87329'
def git(*a):return subprocess.check_output(['git',*a],cwd=root)
def entries(ref):
 return {row.split(b'\t',1)[1].decode():row.split(b'\t',1)[0].decode() for row in git('ls-tree','-r',ref).splitlines()}
head=git('rev-parse','HEAD').decode().strip();tree=git('rev-parse','HEAD^{tree}').decode().strip();parents=git('show','-s','--format=%P',head).decode().split();assert parents==[old,target]
auto=subprocess.run(['git','merge-tree','--write-tree',old,target],cwd=root,capture_output=True);assert auto.returncode==1;auto_tree=auto.stdout.splitlines()[0].decode();expected=entries(auto_tree);actual=entries(head);guide='docs/skills/repository-operations.md';assert {p:v for p,v in actual.items() if p!=guide}=={p:v for p,v in expected.items() if p!=guide}
base=git('merge-base',old,target).decode().strip();changed=git('diff','--name-only',base,old).decode().splitlines();original=entries(old);preserved=[]
for p in changed:
 if p.startswith('docs/'):continue
 assert actual.get(p)==original.get(p),p
 preserved.append({'path':p,'blob_mode_kind':actual.get(p)})
rows=[]; invroot=root/'docs/program/evidence/runtime-frozen-current-source-20261011'
for file in ['producer-input-inventory.json','selected-test-inventory.json']:
 data=json.loads((invroot/file).read_text());differences=[]
 for p,e in data.items():
  mode,kind,blob=actual[p].split(); observed={'mode':mode,'kind':kind,'blob':blob,'sha256':hashlib.sha256(git('show',head+':'+p)).hexdigest()}
  if observed!=e: differences.append({'path':p,'retained':e,'union':observed,'matches_original299':actual[p]==original.get(p)})
 rows.append({'inventory':file,'entries':len(data),'changed':differences,'matches':len(data)-len(differences)})
r={'original':old,'target':target,'merge':head,'tree':tree,'ordered_parents':parents,'auto_merge_tree_with_guide_conflict':auto_tree,'all_non_guide_entries_match_auto_union':True,'original_changed_nondoc_entries_preserved':preserved,'only_conflict':'canonical guide append; both parent lessons retained','retained_frozen_inventory_comparison':rows,'actual_artifact_carry':'NOT_QUALIFIED; producer differences measured, no artifact/native/provider execution'}
(own/'union-receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'merge':head,'preserved_original_entries':len(preserved),'inventory_comparison':[(x['inventory'],x['matches'],len(x['changed'])) for x in rows]}))
