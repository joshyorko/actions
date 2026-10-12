import ast,hashlib,json,subprocess
from pathlib import Path
r=Path('/workspace/engineering/pr309');o=Path('/workspace/engineering/pr309-actual618-refresh');old='5130638dc68161c3cfc1a437bacf0467d7cecb42';target='6181b044c75de35386f1ae30e71725398b6a7feb';original='9475a30fbe8645fd0c6b9c2746182f7a78631059'
def g(*a):return subprocess.check_output(['git','-C',str(r),*a])
def leaves(ref):return {n.decode():m.decode().split() for row in g('ls-tree','-rz',ref).split(b'\0') if row for m,n in [row.split(b'\t',1)]}
a,b,native,orig=map(leaves,(old,target,'92498aff',original));stage=g('ls-files','-sz').split(b'\0');assert all(x.split(b'\t')[0].split()[-1]==b'0' for x in stage if x);c={name.decode():[meta.decode().split()[0],'blob',meta.decode().split()[1]] for x in stage if x for meta,name in [x.split(b'\t',1)]}
assert a.keys()|b.keys()==c.keys();novel={p for p in c if c[p] not in (a.get(p),b.get(p))};assert novel<={'docs/skills/repository-operations.md'}
for p,row in c.items():assert (r/p).read_bytes()==g('cat-file','blob',row[2]);assert bool((r/p).stat().st_mode&0o111)==(row[0]=='100755')
owned=['action_server/tests/action_server_tests/test_auth_route_enforcement.py','action_server/tests/action_server_tests/test_auth_route_inventory.py'];assert all(c[p]==a[p]==orig[p] for p in owned)
assert len((r/owned[0]).read_text().splitlines())==608
assert all(c[p]==b[p] for p in c if p.startswith('.github/'))
deps={f'{p}/{f}' for p in ('action_server','actions','actions-http-helper') for f in ('pyproject.toml','poetry.lock')};inputs=lambda d:sorted(p for p in d if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps);ni,ci=inputs(native),inputs(c);changed=[p for p in ni if c[p]!=native[p]];added=sorted(set(ci)-set(ni));assert len(ni)==268 and len(ci)==274 and len(changed)==7 and len(added)==6
assert all(c[p]==b[p] for p in ci)
five=sorted(p for p in c if p.endswith(('/test_cli_mcp_catalog_rollback.py','/test_cli_live_reload_multi_package.py','/test_cli_successful_generation_drain.py','/test_cli_multi_package_sync.py','/test_cli_mcp_resource_history.py')));assert len(five)==5 and all(c[p]==a[p]==b[p]==native[p] for p in five)
base=g('merge-base',old,target).decode().strip();docs=['docs/skills/repository-operations.md','docs/skills/provenance-observability.md']
for doc in docs:
 current=(r/doc).read_text()
 for parent in (old,target):
  addedlines=[l[1:] for l in g('diff','--unified=0',base,parent,'--',doc).decode().splitlines() if l.startswith('+') and not l.startswith('+++')];assert all(l in current for l in addedlines if l.strip()),(doc,parent)
(o/'exact-both-parent-canonical-import.patch').write_bytes(g('diff',old,'--','docs/skills'))
prior=Path('/workspace/engineering/pr309-issue152-request-enforcement-successor/immutable-request-enforcement-source-checkpoint.json');assert hashlib.sha256(prior.read_bytes()).hexdigest()=='130bb73051b73d060c84ea55a47a36cad7fb99d1aa3bfd60de6ac79669fddf82';x=json.loads(prior.read_text());refs=x['evidence_references'];assert len(refs)==39
for row in refs:
 assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
proof={'ordered_parents':[old,target],'complete_parent_leaf_counts':[len(a),len(b)],'current_leaf_count':len(c),'typed_union':c,'only_novel_combined_path':sorted(novel),'all_current_nondoc_modes_bytes_selected_parent_exact':True,'auth608_and_census_entire_original_mode_blob_bytes_exact9475':{p:c[p] for p in owned},'whole_github_exact_actual618':True,'complete_producer':{'old':268,'current':274,'matching':261,'changed':changed,'added':added,'current_all_entries_exact_actual618':True,'typed_inventory':{p:c[p] for p in ci}},'five_selected_separate':{p:c[p] for p in five},'native_current_qualification':'UNQUALIFIED; complete inventory differs, no exclusions or oldactual carry','both_parent_canonical_accepted_added_lines_retained':docs,'retained_original39refs':refs,'original_mutation_proof':'Three actual9475 synthetic owned-bypass/write/leak REDs retained, not replayed or relabelled; prior209-production parity historical, target274 measured separately','before_commit_current_sha256':{p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in c}}
(o/'ordinary-union-and-original-auth-retention-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print('Complete',len(c),'union;608auth/census/39refs exact;274producer/5selectors separate; guide retained')
