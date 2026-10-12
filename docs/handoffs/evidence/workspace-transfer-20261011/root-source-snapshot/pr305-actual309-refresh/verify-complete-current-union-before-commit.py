import ast,hashlib,json,os,stat,subprocess
from pathlib import Path
R=Path('/workspace/engineering/pr305');O=Path(__file__).resolve().parent
SOURCE='519a0beb7451cb6e4410f0bee18c826fc493086e';TARGET='a0d258a16095b95b1bf9000cb1201cddfaff4779'
def g(*a):return subprocess.check_output(['git',*a],cwd=R)
def leaves(ref):return {n.decode():m.decode().split() for line in g('ls-tree','-rz',ref).split(b'\0') if line for m,n in [line.split(b'\t',1)]}
expected=(O/'expected-ordinary-merge-tree.txt').read_text().splitlines()[0]
assert g('rev-parse','HEAD').decode().strip()==SOURCE and g('rev-parse','MERGE_HEAD').decode().strip()==TARGET
assert g('write-tree').decode().strip()==expected
old,target,current=map(leaves,(SOURCE,TARGET,expected));assert current.keys()==old.keys()|target.keys()
nonzero=g('ls-files','-u');assert not nonzero
pre=json.loads((O/'before-ordinary-current-a0d-source-and-original-reference-freeze.json').read_bytes())
for v in pre['all_distinct_old_bound_references']:
 p=Path(v['path']);assert p.stat().st_size==v['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==v['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==v['mode']
changed=[p for p in old if old[p]!=current[p]];added=sorted(set(current)-set(old));docs=['docs/skills/repository-operations.md','docs/skills/provenance-observability.md']
assert set(changed)<=set(docs)
assert added==['action_server/tests/action_server_tests/test_auth_route_enforcement.py','action_server/tests/action_server_tests/test_auth_route_inventory.py']
assert all(current[p]==target[p] for p in added)
owned=['action_server/tests/action_server_tests/mcp/test_canvas_runtime_admission.py','action_server/tests/action_server_tests/test_browser_origin_acceptance.py','action_server/tests/action_server_tests/mcp/test_mcp_apps_authoring.py']
assert all(current[p]==old[p] for p in owned)
assert all(current[p]==target[p] for p in current if p.startswith('.github/'))
base=g('merge-base',SOURCE,TARGET).decode().strip()
for doc in docs:
 body=(R/doc).read_text()
 for parent in (SOURCE,TARGET):
  lines=[n[1:] for n in g('diff','--unified=0',base,parent,'--',doc).decode().splitlines() if n.startswith('+') and not n.startswith('+++')]
  assert all(n in body for n in lines if n.strip()),(doc,parent)
entries=[]
for n,(mode,kind,blob) in current.items():
 p=R/n;b=os.readlink(p).encode() if mode=='120000' else p.read_bytes();assert b==g('cat-file','blob',blob)
 assert mode=='120000' or bool(p.stat().st_mode&0o111)==(mode=='100755')
 entries.append({'path':n,'mode':mode,'blob':blob,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
deps={f'{p}/{f}' for p in ('action_server','actions','actions-http-helper') for f in ('pyproject.toml','poetry.lock')}
producer=lambda x:{p:v for p,v in x.items() if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps}
prod=producer(current);assert prod==producer(old)==producer(target)
native=producer(leaves('92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'))
dif=[p for p in native if native[p]!=prod[p]];extra=sorted(set(prod)-set(native))
oldreceipt=json.loads(Path('/workspace/engineering/pr305-actual618-refresh/frozen-source-receipt.json').read_bytes())
five=oldreceipt['five_selected_tests_separate'];assert all(current[p]==v for p,v in five.items())
nine=json.loads(Path(oldreceipt['nine_Rcc_sample_current_target_exact']['path']).read_bytes())
# Whole source parity proves all accepted nine candidate inputs remain equal, without rewriting pins.
result={'status':'COMPLETE_ORDINARY_STAGED_UNION_VERIFIED_BEFORE_COMMIT','ordered_parents':[SOURCE,TARGET],'expected_tree':expected,'complete_count':len(current),'no_deletions':True,'all_complete_entries':entries,'changed_existing_paths':changed,'added_target_auth_paths':added,'all_three_Canvas_original_bodies_modes_AST_unchanged':{p:current[p] for p in owned},'all_github_exact_target':True,'both_parent_canonical_added_lines_retained':docs,'all112_previous_distinct_refs_bytes_modes_unchanged':pre['all_distinct_old_bound_references'],'producer':{'old_count':len(native),'current_count':len(prod),'match_count':len(native)-len(dif),'changed':dif,'added':extra,'all_current_entries':prod,'qualification':'UNQUALIFIED; current source-only union does not transfer old92498 or3ec actualV5 qualification'},'five_selected_tests_separate':five,'old_nine_sample_preserved':oldreceipt['nine_Rcc_sample_current_target_exact'],'upstream_disposition':'none'}
p=O/'complete-staged-ordinary-union-before-commit.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600)
(O/'exact-two-guide-both-parent-import.patch').write_bytes(g('diff','--cached',SOURCE,'--','docs/skills'));(O/'exact-two-guide-both-parent-import.patch').chmod(0o600)
print('PASS complete',len(current),'union, changed',changed,'target additions',added,'producer',len(prod),'; refs112 unchanged')
