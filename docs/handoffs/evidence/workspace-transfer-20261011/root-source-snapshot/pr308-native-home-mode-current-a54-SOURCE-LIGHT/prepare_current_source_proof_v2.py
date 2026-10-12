import ast,hashlib,json,os,stat,subprocess
from pathlib import Path
R=Path('/workspace/engineering/pr308');O=Path(__file__).parent
HEAD='396925cb3d6527af1768b7f5333f9653c005fc55';TREE='84f850f0d4e08b21afcd8220413ce94322370acf';PATCH='2058b1b185a79c04b24eaf46a73d278ba4f689e5';TARGET='a54c982462d1e7ad011d8152bfc299d997503fb3';OLD='e4ff080375a8422bb656e52d218f198521dda078';ENV=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
def git(*args):return subprocess.check_output(['git','-C',str(R),*args],env=ENV,stderr=subprocess.PIPE)
def entries(rev,paths=()):
 rows={}
 for raw in git('ls-tree','-rz',rev,'--',*paths).split(b'\0'):
  if raw:
   meta,path=raw.split(b'\t');mode,kind,blob=meta.decode().split();rows[os.fsdecode(path)]={'mode':mode,'kind':kind,'blob':blob}
 return rows
def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(name,value):
 p=O/name;fd=os.open(p,os.O_EXCL|os.O_CREAT|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w') as s:json.dump(value,s,indent=2,sort_keys=True);s.write('\n')
 return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes()),'mode':'0o600'}
assert git('show','-s','--format=%H %T %P','HEAD').decode().split()==[HEAD,TREE,PATCH,TARGET]
assert git('show','-s','--format=%P',PATCH).decode().strip()==OLD
assert not git('status','--porcelain=v1')
a,b,c,old=entries(PATCH),entries(TARGET),entries(HEAD),entries(OLD)
assert set(c)==set(a)|set(b)
novel=[p for p in c if c[p]!=a.get(p) and c[p]!=b.get(p)];assert set(novel)=={'.github/workflows/_gen_workflows.py','docs/skills/repository-operations.md'},novel

# A whole generator blob can combine unchanged top-level definitions from both parents.
def ast_key(n):
 return type(n).__name__+':'+getattr(n,'name',ast.unparse(n).split('\n')[0])
def nodes(rev):
 return {ast_key(n):ast.dump(n,include_attributes=False) for n in ast.parse(git('show',rev+':.github/workflows/_gen_workflows.py')).body}
gena,genb,genc=nodes(PATCH),nodes(TARGET),nodes(HEAD)
assert set(genc)==set(gena)|set(genb)
assert all(value==gena.get(key) or value==genb.get(key) for key,value in genc.items())
genproof={'top_level_nodes':len(genc),'all_nodes_exact_one_parent':True,'all_parent_node_keys_retained':True,'source_only_definitions':[key for key,value in genc.items() if value==gena.get(key) and value!=genb.get(key)],'target_only_definitions':[key for key,value in genc.items() if value==genb.get(key) and value!=gena.get(key)]}

changed=[p for p in a if a[p]!=old.get(p)];assert changed==['action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py','docs/skills/repository-operations.md']
proposed=Path('/workspace/engineering/rcc-current-e4ff-cache-mode-private-v8-proposal/proposed_test_source_staging_rcc_consumer_v2.py').read_bytes()
fixture=changed[0];assert git('show',PATCH+':'+fixture)==proposed and git('show',HEAD+':'+fixture)==proposed
for p in changed:
 assert a[p]['mode']==old[p]['mode']
# The exact accepted public nine-line lesson remains present, without erasing either parent's guide.
lesson=Path('/workspace/engineering/rcc-current-e4ff-control3-mode-source-diagnosis-owned/canonical-native-managed-home-mode-boundary-proposed.md').read_text();guide=(R/changed[1]).read_text();assert guide.count(lesson)==1
# Source and target docs combine; all non-guide blobs are exact one parent.
rows=[]
for name,row in c.items():
 p=R/name;raw=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes()
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['blob'],name
 assert row['mode']=='120000' or bool(p.stat().st_mode&0o111)==(row['mode']=='100755'),name
 rows.append(dict(path=name,**row,sha256=sha(raw),bytes=len(raw),fs_mode=stat.S_IMODE(p.lstat().st_mode)))
assert len(rows)==1426
inventory=write('private-current396925-complete-source-body-mode-inventory.json',rows)
parsed=ast.parse((R/'action_server/scripts/verify_frozen_catalog_harness.py').read_bytes());paths=ast.literal_eval(next(n.value for n in parsed.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='INPUT_PATHS' for t in n.targets)))
tests=tuple('action_server/tests/action_server_tests/'+n for n in ['test_cli_mcp_catalog_rollback.py','test_cli_live_reload_multi_package.py','test_cli_successful_generation_drain.py','test_cli_multi_package_sync.py','test_cli_mcp_resource_history.py'])
producer,original=entries(HEAD,paths),entries('92498aff',paths);selectnew,selectold=entries(HEAD,tests),entries('92498aff',tests)
summary={'current_producer_count':len(producer),'original_producer_count':len(original),'match':sum(producer.get(p)==row for p,row in original.items()),'changed':[p for p in producer if p in original and producer[p]!=original[p]],'added':[p for p in producer if p not in original],'deleted':[p for p in original if p not in producer],'five_selector_changes':[p for p in tests if selectnew[p]!=selectold[p]],'native_qualification':'UNQUALIFIED_CURRENT_SOURCE_NOT_ORIGINAL_BUILD'}
producerbinding=write('typed-current-producer-and-five-selected-inventory.json',dict(summary,current=producer,original=original,selectors_current=selectnew,selectors_original=selectold))
proof={'source':HEAD,'tree':TREE,'parents':[PATCH,TARGET],'current_typed_leaves':len(c),'all_parent_paths_retained':True,'novel_paths':novel,'no_novel_non_doc_blobs_except_exact_generator_AST_parent_union':True,'generator_parent_union':genproof,'patch_parent':OLD,'patch_two_paths_exact':changed,'public_fixture_exact_accepted_proposal':True,'public_nine_line_lesson_present_exact':True,'current_FS_body_and_exec_modes_exact':len(rows),'current_inventory':inventory,'producer_inventory':producerbinding,'producer_scope':summary,'new_native':'NOT_RUN','old_actual_control3_mode_failure':'Unchanged historical failure; public adoption is not native acceptance.'}
write('current396925-typed-parent-union-and-exact-public-patch-proof.json',proof)
print(json.dumps({'head':HEAD,'tree':TREE,'leaves':len(c),'novel':novel,'producer_scope':summary},sort_keys=True))
