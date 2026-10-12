import ast,difflib,hashlib,json,os,stat,tempfile,types
from pathlib import Path,PureWindowsPath,PurePosixPath
BASE=Path(__file__).resolve().parent
REPO=Path('/workspace/engineering/pr308')
A='action_server/tests/action_server_tests/test_rcc_runtime_adapter.py'
B='action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'
old_a=(REPO/A).read_text();old_b=(REPO/B).read_text()
new_a=old_a.replace('assert calls == [(["/service-free/rcc", "--version"], 900)]','assert calls == [([str(Path("/service-free/rcc")), "--version"], 900)]').replace('assert calls == [("/service-free/rcc", "--version")]','assert calls == [(str(Path("/service-free/rcc")), "--version")]')
node=next(n for n in ast.parse(old_b).body if isinstance(n,ast.FunctionDef) and n.name=='_prepare_owned_rcc_test_package_cache')
function=ast.get_source_segment(old_b,node)
newfunction=function.replace('    import json\n','    import json\n\n    getuid = getattr(os, "getuid", None)\n    getgid = getattr(os, "getgid", None)\n    assert callable(getuid) and callable(getgid), "PACKAGE_CACHE_POSIX_OWNER_FEATURES"\n    owner_uid, owner_gid = getuid(), getgid()\n',1).replace('os.getuid()','owner_uid').replace('os.getgid()','owner_gid')
assert function.count('os.getuid()')==6 and function.count('os.getgid()')==1
new_b=old_b.replace(function,newfunction);assert new_b!=old_b
patch=''.join(difflib.unified_diff(old_a.splitlines(True),new_a.splitlines(True),'a/'+A,'b/'+A))+''.join(difflib.unified_diff(old_b.splitlines(True),new_b.splitlines(True),'a/'+B,'b/'+B))
def put(name,data):
 b=data if isinstance(data,bytes) else data.encode() if isinstance(data,str) else (json.dumps(data,sort_keys=True,indent=2)+'\n').encode()
 p=BASE/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o400)
 with os.fdopen(fd,'wb') as f:f.write(b)
 return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':'0o400'}
patchrow=put('proposed-two-path-assertions-and-cache-owner-features.patch',patch)
results=[]
for kind in (PurePosixPath,PureWindowsPath):
 actual=str(kind('/service-free/rcc'))
 for shape in ('default','injected'):
  measured=([actual,'--version'],900.0) if shape=='default' else (actual,'--version')
  original=(['/service-free/rcc','--version'],900) if shape=='default' else ('/service-free/rcc','--version')
  expected=([str(kind('/service-free/rcc')),'--version'],900) if shape=='default' else (str(kind('/service-free/rcc')),'--version')
  assert measured==expected
  assert (measured==original)==(kind is PurePosixPath)
  results.append({'path_kind':kind.__name__,'shape':shape,'literal_original_equal':measured==original,'proposed_contract_equal':True,'budget_and_argv_tail_unchanged':True})
with tempfile.TemporaryDirectory(prefix='actions-rcc-compatibility-actual-control3-portability-pure-',dir='/dev/shm') as directory:
 root=Path(directory);root.chmod(0o700);client=root/'actions-home';client.mkdir(mode=0o700);case=root/'pytest'/'case';case.mkdir(parents=True,mode=0o700)
 value={'schema':1,'runtime_source_sha':'b'*40,'runtime_source_tree':'c'*40,'label':'control3','binary_sha256':'7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428','state_root':str(root),'package_cache_root':str(client/'pkgs')}
 marker=root/'rcc-package-cache-owner.json';marker.write_text(json.dumps(value));marker.chmod(0o600)
 value['state_marker_sha256']=hashlib.sha256(marker.read_bytes()).hexdigest()
 env={'ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG':json.dumps(value),'RCC_ROLLBACK_CANDIDATE_SHA':'b'*40,'RCC_ROLLBACK_CANDIDATE_TREE':'c'*40,'ACTIONS_HOME':str(client),'ROBOCORP_HOME':str(client)}
 for poison in (None,'missing_uid','noncallable_uid','missing_gid','noncallable_gid'):
  calls=[];proxy=types.SimpleNamespace(environ=env)
  if poison!='missing_uid':proxy.getuid=None if poison=='noncallable_uid' else lambda:calls.append('uid') or os.getuid()
  if poison!='missing_gid':proxy.getgid=None if poison=='noncallable_gid' else lambda:calls.append('gid') or os.getgid()
  ns={'Path':Path,'os':proxy,'stat':stat,'hashlib':hashlib};exec(compile(ast.parse(newfunction),'PRIVATE_CORRECTED_REAL_CACHE_HELPER','exec'),ns)
  before=list(client.iterdir())
  try:r=ns[node.name](case,'v18.19.3',value['binary_sha256'])
  except AssertionError as e:
   assert poison is not None and str(e)=='PACKAGE_CACHE_POSIX_OWNER_FEATURES'
   assert list(client.iterdir())==before and calls==[]
   results.append({'feature_poison':poison,'guard_rejected_before_filesystem_effects':True})
  else:
   assert poison is None and calls==['uid','gid'] and r['cold_first_publication'] is True
   assert stat.S_IMODE((client/'pkgs').stat().st_mode)==0o700
   results.append({'feature_baseline':'actual_helper_FS_PASS','UID_GID_read_once':True,'native':'NOT_RUN'})
control=put('private-pure-path-and-real-cache-helper-feature-controls.json',{'method':'stdlib pure pathlib + actual corrected helper AST in one tiny owned /dev/shm fixture; no Pytest/product imports/native','rows':results,'passed':len(results),'skipped':0,'originalWindowsLiteralRED':2,'fixture_removed_by_owned_TemporaryDirectory':True,'original_47_control_functions':'UNCHANGED_NOT_RERUN'})
proof=put('private-minimal-AST-scope-and-original-source-proof.json',{'source':'8d49d0865ad5ad27b2d4e325ec135212080625e8','originals':[{'path':str(REPO/p),'bytes':len(t.encode()),'sha256':hashlib.sha256(t.encode()).hexdigest()} for p,t in [(A,old_a),(B,old_b)]],'changes':'exacttwo expectedPathstr expressions + sevenUID/GID comparisons reusing one callable-feature-checked snapshot; no existingtestdefinition changed otherwise','all47existingcachecontrols':'wholefileoutsidehelper exact','adapter':'UNCHANGED','product_branch':'UNCHANGED','test_timeouts':'900general/10isolated unchanged','no_fake_Windows_UID':'missing/noncallablefeatures reject; no synthesized ownership'})
canonical='''On Windows, `str(Path("/service-free/rcc"))` renders native separators even when\na fixture starts from a POSIX-looking literal. Compare captured subprocess and\ninjected-runner arguments with the same Path contract; keep version, argument\norder and timeout assertions intact. A Linux-only runtime fixture skip does not\nexclude its helper from Windows type checks. Admit callable UID/GID features\nbefore using POSIX ownership, read the real values once, and fail closed when\nthose features are unavailable; never synthesize Windows ownership values.\n'''
canon=put('canonical-native-path-and-POSIX-feature-proposed.txt',canonical)
owner=put('OWNERFINAL-private-current8d49-Windows-portability-source-PROPOSAL.json',{'schema':'PRIVATE_CURRENT8D49_WINDOWS_PORTABILITY_SOURCE_PROPOSAL','status':'PROPOSAL_ONLY_NO_PRODUCT_ADOPTION','source':'8d49d0865ad5ad27b2d4e325ec135212080625e8','tree':'a80600809d373038ca76e445ba0b7b79bb7eeaa6','evidence':[patchrow,control,proof,canon],'changes':['two expected argument Pathstr expressions','cache helper callable POSIX feature admission and sixUID/oneGID comparisons against single measured values'],'tests':{'pure_rows':len(results),'native_or_package_tests':'NOT_RUN','original47controls':'UNCHANGED_NOT_RERUN','Windows_original':'twoassertionFAILplussevenmypyerrors retained separately'},'full_source_fresh_CI':'REQUIRED_AFTER_ROOTADOPTION','documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; exact seven-line proposed lesson','Durable_learning':'Native Path rendering and static platform API availability are separate fixture contracts','Evidence':'original Windows job114544417671 + purepathmatrix and actualhelperAST ownership-feature poisons','Stale_or_ambiguous_guidance_removed':'POSIX literal expectedarguments; runtimeLinuxskip mistakenforWindowsstaticexclusion','Remaining_uncertainty':'No productionadoption/freshfull/hostedWindows/native qualification'},'upstream_disposition':'none; Actions-owned test portability defects'})
print(json.dumps({'owner':owner,'rows':len(results),'pure_originalWindowsRED':2,'product_mutation':'NONE'}))
