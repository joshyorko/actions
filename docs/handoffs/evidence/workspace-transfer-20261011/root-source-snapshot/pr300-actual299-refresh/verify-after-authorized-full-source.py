from pathlib import Path
import hashlib, json, os, stat, subprocess

R = Path('/workspace/engineering/pr300')
O = Path('/workspace/engineering/pr300-actual299-refresh')
OLD = '3cad4fd6d9fb386451b3b76d7b1103256eec54e5'
TARGET = '6181b044c75de35386f1ae30e71725398b6a7feb'
ORDINARY = 'd4443c49973ddd629838c682111474991e3ea0c2'
def git(*a): return subprocess.check_output(['git','-C',str(R),*a])
def leaves(ref):
    return {p.decode(): h.decode().split() for row in git('ls-tree','-rz',ref).split(b'\0') if row for h,p in [row.split(b'\t',1)]}
head = git('rev-parse','HEAD').decode().strip()
tree = git('rev-parse','HEAD^{tree}').decode().strip()
assert git('show','-s','--format=%P',head).decode().split() == [ORDINARY]
assert git('show','-s','--format=%P',ORDINARY).decode().split() == [OLD,TARGET]
assert git('rev-parse',ORDINARY+'^{tree}').decode().strip() == 'f6b711f1589bcff6b9df73ab889c30503859d90d'
old, target, ordinary, current = map(leaves,(OLD,TARGET,ORDINARY,head))
assert len(current) == len(ordinary) == 1421
assert not set(old)-set(current) and not set(target)-set(current)
guide = 'docs/skills/repository-operations.md'
assert {p for p in current if current[p] != ordinary[p]} == {guide}
rows = {}
for p, (mode,kind,blob) in current.items():
    assert kind == 'blob'
    item = R/p
    if mode == '120000':
        assert item.is_symlink(); b = os.readlink(item).encode()
    else:
        assert stat.S_ISREG(item.lstat().st_mode)
        assert bool(item.stat().st_mode&0o111) == (mode=='100755'),p
        b = item.read_bytes()
    assert b == git('show',head+':'+p),p
    rows[p] = {'mode':mode,'blob':blob,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
transport_paths = ['action_server/src/actions/server/_server.py','action_server/src/actions/server/run_outputs/transport.py','action_server/tests/action_server_tests/run_outputs/test_transport.py','docs/skills/provenance-observability.md']
assert all(current[p] == old[p] for p in transport_paths)
protected = ['action_server/src/actions/server/run_outputs/'+p for p in ['__init__.py','filesystem.py','models.py','service.py','types.py']] + ['action_server/tests/action_server_tests/run_outputs/'+p for p in ['test_concurrency.py','test_filesystem.py','test_migration.py','test_service.py']]
assert len(protected) == 9 and all(current[p] == old[p] == target[p] for p in protected)
assert {p:v for p,v in target.items() if p.startswith('.github/')} == {p:v for p,v in current.items() if p.startswith('.github/')}
native = leaves('92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e')
deps = {f'{p}/{n}' for p in ['actions','action_server','actions-http-helper'] for n in ['pyproject.toml','poetry.lock']}
inputs = sorted(p for p in native if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps)
current_inputs = sorted(p for p in current if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps)
assert len(inputs)==268 and len(current_inputs)==275
changed = [p for p in inputs if current[p]!=native[p]]
added = sorted(set(current_inputs)-set(inputs))
assert len(changed)==8 and len(added)==7
five = sorted(p for p in current if p.endswith(('/test_cli_mcp_catalog_rollback.py','/test_cli_live_reload_multi_package.py','/test_cli_successful_generation_drain.py','/test_cli_multi_package_sync.py','/test_cli_mcp_resource_history.py')))
assert len(five)==5 and all(current[p]==target[p]==native[p] for p in five)
paragraph = ('Verified reuse of package environments does not populate a new checkout\'s\n'
 'ignored Runtime RCC fixture asset. Before tests, bind `get_default_rcc_location()`\n'
 'to the package pin and verify the owned binary\'s digest and mode. A matching\n'
 'already prepared Bootstrap output can be copied with its source and byte identity\n'
 'retained; this is reuse, not a new Bootstrap run or binary build. Do not bypass\n'
 'the fixture, download a substitute, or borrow unrelated generated inputs to\n'
 'clear a missing-asset failure.\n\n')
body = git('show',head+':'+guide).decode();assert body.count(paragraph)==1
assert body.replace(paragraph,'') == git('show',ORDINARY+':'+guide).decode()
assert git('status','--porcelain') == b''
receipt = {'schema':'actions-pr300-actual299-complete-source-union/v1','head':head,'tree':tree,'sole_parent':ORDINARY,'ordinary_merge':{'head':ORDINARY,'tree':'f6b711f1589bcff6b9df73ab889c30503859d90d','ordered_parents':[OLD,TARGET]},'leaf_counts':{'original300':len(old),'actual299':len(target),'union':len(current)},'all_original_paths_and_modes_retained':True,'only_novel_child_path':guide,'all1420_other_leaf_mode_blob_pairs_exact_ordinary':True,'original_four_transport_patch_paths_exact':{p:rows[p] for p in transport_paths},'all_nine_private_foundation_paths_exact_old_and_actual299':{p:rows[p] for p in protected},'whole_GitHub_exact_actual299':True,'all1421_current_files_bytes_and_executable_bits_exact_Git':rows,'all1421_typed_inventory_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'native_producer_comparison':{'historical_source':'92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e','historical_production_count':268,'current_production_count':275,'unchanged_historical_entries':260,'changed_eight':{p:{'old':native[p],'current':current[p]} for p in changed},'added_seven':{p:current[p] for p in added},'all_current275_mode_blob_inputs':{p:current[p] for p in current_inputs},'five_selected_tests_separate':{p:current[p] for p in five},'qualification':'UNQUALIFIED for old92498 native assets;275 production plus5 selected tests are280 combined, not280 production.'},'canonical_exact_novel_paragraph':paragraph,'remaining_HOLD':['No refreshed hostedCI or original/native/installed consumer acceptance','No active-stream grant revocation, HEAD/Range features or production Actor/Canvas/ChatGPT/full private graph/release'], 'upstream_disposition':'none'}
(O/'after-authorized-full-complete-source-proof.json').write_text(json.dumps(receipt,indent=2)+'\n')
(O/'after-authorized-full-canonical-exact-child.patch').write_bytes(git('diff',ORDINARY,head,'--',guide))
print(json.dumps({'head':head,'tree':tree,'leaves':len(current),'native_production':275,'selected_tests':5,'native_status':'UNQUALIFIED','novel_child':'8 guide lines only; all1420 others exact'}))
