import ast,hashlib,json,os,shutil,stat,subprocess,sys
from pathlib import Path
out=Path(__file__).resolve().parent
cfg=json.loads((out/'sourcefull-frozen-inputs.json').read_text());root=Path(cfg['root']);stage=sys.argv[1];assert stage in ('before','after')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
for k,v in cfg['expected_activation_exports'].items():assert os.environ.get(k)==v,k
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
assert sha(cfg['activation']['path'])==cfg['activation']['sha256']
for k in ['ACTIONS_RUNTIME_RCC_TEST_COMPATIBILITY','ACTIONS_REAL_RCC_ARTIFACT_TEST','ACTIONS_RUNTIME_RCC_PROVIDER','ACTIONS_RUNTIME_RCC_BINARY']:assert k not in os.environ,k
assert os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
light=Path(cfg['light']['path']);assert sha(light)==cfg['light']['sha256'] and light.stat().st_size==cfg['light']['bytes'];r=json.loads(light.read_text())
for row in r['frozen_bindings']:assert Path(row['path']).stat().st_size==row['bytes'] and sha(row['path'])==row['sha256'],row['path']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==cfg['head']
assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=root,text=True).strip()==cfg['tree']
assert not subprocess.check_output(['git','status','--porcelain'],cwd=root)
proof=json.loads(Path(r['complete_committed_body_mode_proof']['path']).read_text());assert len(proof['complete1421_Git_FS_body_mode_exact'])==1421
for n,row in proof['complete1421_Git_FS_body_mode_exact'].items():
 assert sha(root/n)==row['sha256'],n
 assert bool((root/n).stat().st_mode&0o111)==(row['mode']=='100755'),n
prepared=json.loads(Path(cfg['prepared']).read_text());assert len(prepared['inputs_exact_prepared_git_bytes_sha256'])==30
for n,h in prepared['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(root/n)==h,n
for n,row in prepared['own5venvs_current_config_and_python'].items():assert sha(root/n/'.venv/pyvenv.cfg')==row['config_sha256'],n
for p,mode in [(root/'action_server/src/actions/server/bin/rcc-18.19.3',0o711),(Path('/workspace/actions-cloud/bin/rcc'),0o700)]:assert sha(p)=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428' and stat.S_IMODE(p.stat().st_mode)==mode
sys.path.insert(0,str(root/'developer'));import toolkit
assert toolkit.REPOSITORY_ROOT==root and toolkit.package_environment(root/'action_server')['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
origins=[];tool=Path(cfg['cached_toolkit_prefix'])
for package,module in [('actions','actions'),('actions-http-helper','actions_http'),('devutils','devutils.invoke_utils'),('work-items','actions.work_items'),('action_server','actions.server._rcc_runtime_adapter')]:
 code='import importlib,json,sys;from pathlib import Path;m=importlib.import_module('+repr(module)+');assert Path(sys.prefix).resolve()==Path('+repr(str(root/package/'.venv'))+').resolve();assert Path(m.__file__).resolve().is_relative_to(Path('+repr(str(root/package/'src'))+').resolve());print(json.dumps({"module":'+repr(module)+',"origin":str(Path(m.__file__).resolve()),"prefix":sys.prefix}))'
 cp=subprocess.run([str(tool/'bin/poetry'),'run','python','-c',code],cwd=root/package,env=toolkit.package_environment(root/package),capture_output=True,text=True,timeout=30,check=True);origins.append(json.loads(cp.stdout))
# Execute only the already reviewed frozen inventory inspector, without native execution.
inspector=Path(cfg['retention_original_inspector']);original=(inspector).read_text();tree=ast.parse(original)
for n in tree.body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='out' for t in n.targets):n.value=ast.Call(func=ast.Name(id='Path',ctx=ast.Load()),args=[ast.Constant(str(out))],keywords=[])
 for node in ast.walk(n):
  if isinstance(node,ast.Constant) and node.value=='before-source-retained-native-helper-browser-and-V5-proof.json':node.value=stage+'-full-original-native-helper-browser-V5-readback.json'
exec(compile(ast.fix_missing_locations(tree),str(inspector),'exec'),{'__name__':'reviewed_inventory_inspection_only'})
space=shutil.disk_usage('/workspace').free
if stage=='before':assert space>=cfg['capacity_floor_bytes']
report={'stage':stage,'source':{'head':cfg['head'],'tree':cfg['tree'],'clean':True},'complete1421_Git_FS_body_execmodes_exact':True,'light71_bindings_exact':len(r['frozen_bindings']),'prepared30_exact':True,'activation18_exports_and_PATH19_exact':True,'worker_env':'PYTEST_XDIST_AUTO_NUM_WORKERS=2','five_own_concrete_prefix_origins':origins,'native1192_helpers0444_browser_Node_frontend_historical_V5_originals':'verified by existing immutable inspector; no actual binary execution','fresh_workspace_bytes':space}
f=out/(stage+'-full-source-prepost.json');assert not f.exists();f.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps({'stage':stage,'status':'PASS','head':cfg['head'],'workspace_bytes':space}))
