import ast,hashlib,json,os,stat,subprocess
from pathlib import Path
R=Path('/workspace/engineering/pr282');O=Path('/workspace/engineering/pr282-current-a54-source-LIGHT');E=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
def git(*a):return subprocess.check_output(['git','-C',str(R),*a],env=E,stderr=subprocess.PIPE)
def entries(rev,paths=()):
 out={}
 for row in git('ls-tree','-rz',rev,'--',*paths).split(b'\0'):
  if row:
   m,n=row.split(b'\t');mode,kind,blob=m.decode().split();out[os.fsdecode(n)]={'mode':mode,'kind':kind,'blob':blob}
 return out
def sha(b):return hashlib.sha256(b).hexdigest()
head,tree,*parents=git('show','-s','--format=%H %T %P','HEAD').decode().split()
assert head=='1299cc4bb6586f467d36ca124faaaaa77362695f' and parents==['c35ee2e279eaefe55b16aecdb80da04c590aff7c','a54c982462d1e7ad011d8152bfc299d997503fb3']
a,b,c=entries(parents[0]),entries(parents[1]),entries(head); assert set(c)==set(a)|set(b)
novel=[p for p in c if c[p]!=a.get(p) and c[p]!=b.get(p)];assert novel==['.gitattributes','.github/workflows/_gen_workflows.py','.github/workflows/actions_runtime_tests.yml','docs/skills/repository-operations.md'];assert tree=='afe2679cc93bf27fa5021c7698ee7ad3ee21a1b9'
fs=[]
for path,row in c.items():
 p=R/path;raw=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes()
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['blob']
 assert row['mode']=='120000' or bool(p.stat().st_mode&0o111)==(row['mode']=='100755')
 fs.append(dict(path=path,**row,sha256=sha(raw),bytes=len(raw),fs_mode=stat.S_IMODE(p.lstat().st_mode)))
assert git('status','--porcelain')==b''
# Attribute producer and selected tests separately, from exact owning verifier inputs.
parsed=ast.parse((R/'action_server/scripts/verify_frozen_catalog_harness.py').read_bytes())
inputpaths=ast.literal_eval(next(n.value for n in parsed.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='INPUT_PATHS' for t in n.targets)))
tests=tuple('action_server/tests/action_server_tests/'+n for n in ['test_cli_mcp_catalog_rollback.py','test_cli_live_reload_multi_package.py','test_cli_successful_generation_drain.py','test_cli_multi_package_sync.py','test_cli_mcp_resource_history.py'])
current,old=entries(head,inputpaths),entries('92498aff',inputpaths)
changed=[p for p in current if p in old and current[p]!=old[p]];added=[p for p in current if p not in old];deleted=[p for p in old if p not in current]
selectors_current,selectors_old=entries(head,tests),entries('92498aff',tests)
selector_changed=[p for p in tests if selectors_current[p]!=selectors_old[p]]
# All original accepted Canvas test bodies/modes and RCC fixture bytes retained.
owned=['action_server/tests/contract_tests/test_source_staging.py','action_server/tests/contract_tests/test_source_read.py','action_server/src/actions/server/deployments/source_read.py','action_server/src/actions/server/deployments/source_staging.py','action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py','action_server/tests/action_server_tests/mcp/test_canvas_query_template.py','action_server/tests/action_server_tests/test_canvas_query_results_fixture.py','action_server/tests/action_server_tests/test_browser_origin_acceptance.py']
for path in owned:assert c[path]==a[path] and git('show',head+':'+path)==git('show',parents[0]+':'+path)
for p in c:
 if p in ['action_server/src/actions/server/_rcc_runtime_adapter.py','action_server/src/actions/server/_rcc.py']:
  assert c[p]==a.get(p),p
inv=O/'private-current-1299-complete-source-body-mode-inventory.json';assert not inv.exists();inv.write_text(json.dumps(fs,sort_keys=True)+'\n');inv.chmod(0o600)
producer={'source':head,'current_production_count':len(current),'old_production_count':len(old),'match':sum(current.get(p)==r for p,r in old.items()),'changed':changed,'added':added,'deleted':deleted,'current':current,'original_native':old,'five_selectors_current':selectors_current,'five_selectors_original':selectors_old,'five_selector_changes':selector_changed,'native_qualification':'UNQUALIFIED'}
p=O/'typed-current-production-and-five-selector-inventory.json';assert not p.exists();p.write_text(json.dumps(producer,indent=2,sort_keys=True)+'\n');p.chmod(0o600)
proof={'source':head,'tree':tree,'ordered_parents':parents,'original_accepted_source':parents[0],'accepted_target':parents[1],'current_leaves':len(c),'application_leaves':len(a),'target_leaves':len(b),'no_deletions':True,'no_novel_non_doc_blobs':True,'automatic_combined_paths':novel,'all_current_Git_to_FS_body_and_modes':len(fs),'original_Canvas3_and_RCC_fixture_whole_bytes_modes_retained':True,'original_RCC_production_body_modes_unchanged':True,'incoming_checkout_filter_delta':'Accepted target .gitattributes trigger union retained; strict Canvas function and workflow step checked separately','production':{k:producer[k] for k in ['current_production_count','old_production_count','match','changed','added','deleted','five_selector_changes','native_qualification']},'source_inventory':{'path':str(inv),'sha256':sha(inv.read_bytes()),'bytes':inv.stat().st_size},'typed_producer_inventory':{'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size},'historical_native_V5_actual':'Original3ec/92498 source/native tuple remains historical; ordinary target union does not transfer qualification.'}
p=O/'committed-current-1299-typed-ordinary-union-source-proof.json';assert not p.exists();p.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');p.chmod(0o600);print(json.dumps({'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size,'head':head,'tree':tree,'leaves':len(c),'production_count':len(current),'native_match':producer['match'],'native_changed':len(changed),'native_added':len(added),'selector_changed':len(selector_changed)}))
