from pathlib import Path
import os,json,hashlib,stat,ast
O=Path(__file__).parent;PREV=Path('/workspace/engineering/pr308-native-home-mode-current-a54-SOURCE-LIGHT')
def write(n,s):
 p=O/n;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o444)
 with os.fdopen(fd,'w') as f:f.write(s)
light='''import json,os,runpy,subprocess,sys,hashlib
from pathlib import Path
O=Path(__file__).parent;cfg=json.loads((O/'frozen-currentEDF-source-LIGHT-inputs.json').read_text())
assert cfg['execution_enablement']=='ROOT_CURRENT_SOURCE_GATES_ADOPTED_ONCE' and cfg['head'] and cfg['phase']=='LIGHT'
assert not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE') and 'PYTEST_ADDOPTS' not in os.environ
root=Path(cfg['source_root']);out=Path(cfg['owned_evidence_root']);sys.path.insert(0,str(root/'developer'));import toolkit
assert toolkit.REPOSITORY_ROOT==root and Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
parent=Path(cfg['pytest_owned_parent']);meta=parent.lstat();assert parent.parent==Path('/tmp') and parent.is_dir() and not parent.is_symlink() and meta.st_mode&0o777==0o700
assert parent.name.startswith('actions-pr308-currentEDF-LIGHT-once-')
def absent(name):
 p=parent/name;assert not p.exists() and not p.is_symlink(),'EXPLICIT_PYTEST_BASETEMP_MUST_BE_ABSENT';return p
os.environ['ACTIONS_RUNTIME_TEST_PYTHON']=str(root/'action_server/.venv/bin/python')
toolkit.doctor()
base=absent('ToolkitTest')
os.environ['PYTEST_ADDOPTS']='--basetemp='+str(base)+' -o tmp_path_retention_policy=all'
try:toolkit.toolkit_test()
finally:os.environ.pop('PYTEST_ADDOPTS',None)
base=absent('scoped-Runtime')
toolkit.poetry('action_server','run','python','-m','pytest','-n0','-q','tests/action_server_tests/test_rcc_runtime_adapter.py','tests/action_server_tests/test_dakota_rcc_acceptance.py','tests/action_server_tests/test_source_staging_rcc_consumer.py','tests/action_server_tests/run_outputs/test_transport.py','tests/action_server_tests/test_shutdown_response_order.py','-m','not integration_test','--tb=short','--basetemp='+str(base),'-o','tmp_path_retention_policy=all','--junitxml='+str(out/'current-scoped-source-junit.xml'))
toolkit.poetry('action_server','run','invoke','lint')
toolkit.poetry('action_server','run','invoke','typecheck')
paths=subprocess.check_output(['git','ls-files','.github/*.yaml','.github/*.yml'],cwd=root).decode().splitlines();assert len(paths)==cfg['expected_tracked_YAML_count']
before={p:(root/p).read_bytes() for p in paths};namespace=runpy.run_path(str(root/'.github/workflows/_gen_workflows.py'),run_name='__main__')
import yaml
for path,data in before.items():assert (root/path).read_bytes()==data;yaml.load(data,Loader=yaml.BaseLoader)
names=[t.target for t in namespace['TARGETS']];assert len(names)==len(set(names))==8
p=out/'current-generator8-allYAML-roundtrip.json';assert not p.exists();p.write_text(json.dumps({'generated_outputs':names,'generated_count':8,'all_YAML_count':len(paths),'all_YAML_sha256':{k:hashlib.sha256(v).hexdigest() for k,v in before.items()},'source':cfg['head'],'tree':cfg['tree']},indent=2)+'\\n');p.chmod(0o600)
print('CURRENT_EDF_CACHED_SOURCE_LIGHT_COMPLETE_NATIVE_NOT_RUN')
'''
write('currentEDF_cached_source_LIGHT_body.py',light)
launcher='''import hashlib,json,os,stat,subprocess,sys,time,traceback
from pathlib import Path
O=Path(__file__).parent
assert len(sys.argv)==4 and sys.argv[1] in ('LIGHT','FULL')
phase=sys.argv[1];cfg_path=O/('frozen-currentEDF-source-'+phase+'-inputs.json');cfg=json.loads(cfg_path.read_text())
assert cfg['execution_enablement']=='ROOT_CURRENT_SOURCE_GATES_ADOPTED_ONCE' and cfg['head'] and cfg['phase']==phase
assert not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(row):
 p=Path(row['path']);assert p.is_file() and not p.is_symlink() and sha(p)==row['sha256'] and p.stat().st_size==row['bytes'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode']
release_path=Path(sys.argv[2]);assert sha(release_path)==sys.argv[3];release=json.loads(release_path.read_text())
assert release['status']=='ROOT_RELEASE_ONE_SERIALIZED_CURRENT_EDF_SOURCE_'+phase
assert release['proposal_sha256']==sha(O/('OWNERFINAL-currentEDF-'+phase+'-execution-proposal.json'))
assert release['source']==cfg['head'] and release['tree']==cfg['tree']
assert release['serialized_no_other_heavy_or_installer'] is True and release['current_storage_independent_GO'] is True
for row in release['independent_review_bindings']:check(row)
assert len(release['independent_review_bindings'])>=1
for row in cfg['implementation_bindings']+cfg['prepared_environment_and_RCC_bindings']:check(row)
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
for key,value in cfg['expected_activation_exports'].items():assert os.environ.get(key)==value,key
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
assert 'PYTEST_ADDOPTS' not in os.environ,'INHERITED_PYTEST_ADDOPTS_REJECTED'
assert os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize>=cfg['capacity_floor_bytes']
assert os.statvfs('/tmp').f_bavail*os.statvfs('/tmp').f_frsize>=cfg['tmp_capacity_floor_bytes']
parent=Path(cfg['pytest_owned_parent']);assert parent.parent==Path('/tmp') and not parent.exists() and not parent.is_symlink();os.umask(0o077);parent.mkdir(mode=0o700)
if phase=='FULL':
 assert cfg['source_LIGHT'] and cfg['current_source_independent_review'] and cfg['current_full_preexecution_independent_review']
 os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']='2';os.environ['PYTEST_ADDOPTS']=cfg['pytest_addopts'];assert not Path(cfg['pytest_basetemp']).exists()
owned=Path(cfg['owned_evidence_root']);assert not owned.exists() and not owned.is_symlink();owned.mkdir(mode=0o700);log=owned/'original-'+phase+'-source.private.log'
R=Path(cfg['source_root']);guard=[sys.executable,str(O/'currentEDF_readonly_source_and_storage_guard.py'),str(cfg_path)];records=[];primary=None;primary_error=None;post=None;post_error=None;started=False;begin=time.monotonic()
with log.open('xb') as stream:
 try:
  cp=subprocess.run(['timeout','--signal=TERM','--kill-after=10s','120s',*guard,'before'],cwd=R,stdout=stream,stderr=subprocess.STDOUT);records.append({'stage':'before','returncode':cp.returncode})
  if cp.returncode:raise RuntimeError('BEFORE_FAILED_PRIMARY_NOT_STARTED')
  started=True;body=O/('currentEDF_cached_source_LIGHT_body.py' if phase=='LIGHT' else 'currentEDF_configured_full_body.py');budget='480s' if phase=='LIGHT' else '600s'
  argv=['timeout','--signal=TERM','--kill-after=10s',budget,sys.executable,str(body)];cp=subprocess.run(argv,cwd=R,stdout=stream,stderr=subprocess.STDOUT,timeout=500 if phase=='LIGHT' else 640);primary=cp.returncode;records.append({'stage':phase,'argv':argv,'returncode':primary})
 except BaseException as e:primary_error=type(e).__name__;stream.write(traceback.format_exc().encode())
 finally:
  try:
   cp=subprocess.run(['timeout','--signal=TERM','--kill-after=10s','120s',*guard,'after'],cwd=R,stdout=stream,stderr=subprocess.STDOUT);post=cp.returncode;records.append({'stage':'after-always','returncode':post})
  except BaseException as e:post_error=type(e).__name__;stream.write(traceback.format_exc().encode())
status='PASS' if started and primary==0 and not primary_error and post==0 and not post_error else 'FAIL/HOLD'
terminal={'source':cfg['head'],'tree':cfg['tree'],'phase':phase,'status':status,'primary_started':started,'primary':primary,'primary_error':primary_error,'post':post,'post_error':post_error,'records':records,'seconds':time.monotonic()-begin,'log':{'path':str(log),'sha256':sha(log),'bytes':log.stat().st_size},'native':'NOT_RUN','scratch':'PRESERVE_ALL_NO_CLEANUP','attempt':'CONSUMED_NO_AUTOMATIC_RETRY'};p=owned/'original-terminal.json';p.write_text(json.dumps(terminal,indent=2)+'\\n');p.chmod(0o600);print(json.dumps({'status':status,'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}));raise SystemExit(0 if status=='PASS' else 10)
'''
write('launch_currentEDF_source_gate_once.py',launcher)
constructor='''"""Root-supplied accepted binding constructor; no test/RCC/native execution."""
import hashlib,json,os,stat,subprocess,sys
from pathlib import Path
O=Path(__file__).parent;assert len(sys.argv)==2
adopt=Path(sys.argv[1]);receipt=json.loads(adopt.read_text())
assert receipt['status']=='ROOT_ADOPTED_EDF_SOURCE_AND_ACCEPTED_STORAGE_BINDINGS'
cfg=json.loads((O/'expectedEDF-source-gates-UNBOUND-template.json').read_text());R=Path(cfg['source_root'])
assert receipt['source'] and len(receipt['source'])==40 and receipt['tree']==cfg['tree']
def binding(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def check(row):assert binding(row['path'])==row
for group in ['root_source_adoption','accepted_B28_actual_and_independent','accepted_TMP_relocation_actual_and_independent']:
 assert receipt[group] and type(receipt[group]) is list
 for row in receipt[group]:check(row)
 cfg[group if group!='root_source_adoption' else 'root_current_source_adoption']=receipt[group]
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[receipt['source'],receipt['tree']]
assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain'])
raw=subprocess.check_output(['git','-C',str(R),'ls-tree','-r','-z',receipt['source']]);rows=[]
for item in raw.split(b'\\0'):
 if not item:continue
 info,path=item.split(b'\\t',1);mode,kind,obj=info.decode().split();p=R/path.decode();b=os.readlink(p).encode() if mode=='120000' else p.read_bytes();committed=subprocess.check_output(['git','-C',str(R),'cat-file','blob',obj]);assert b==committed
 rows.append({'path':path.decode(),'mode':mode,'object':obj,'sha256':hashlib.sha256(b).hexdigest(),'fs_mode':stat.S_IMODE(p.lstat().st_mode)})
assert len(rows)==1440
p=O/'private-currentEDF-source-body-mode-inventory.json';assert not p.exists();p.write_text(json.dumps(rows,indent=2)+'\\n');p.chmod(0o400)
cfg.update(head=receipt['source'],source_inventory=str(p),execution_enablement='ROOT_CURRENT_SOURCE_GATES_ADOPTED_ONCE',phase='LIGHT',pytest_owned_parent=receipt['pytest_LIGHT_owned_parent'],owned_evidence_root=receipt['LIGHT_owned_evidence_root'])
cfg['expected_tracked_YAML_count']=len(subprocess.check_output(['git','-C',str(R),'ls-files','.github/*.yaml','.github/*.yml']).decode().splitlines())
cfg['implementation_bindings']=[binding(O/x) for x in ['currentEDF_readonly_source_and_storage_guard.py','currentEDF_cached_source_LIGHT_body.py','launch_currentEDF_source_gate_once.py','currentEDF_configured_full_body.py']]+[binding(p)]
final=O/'frozen-currentEDF-source-LIGHT-inputs.json';assert not final.exists();final.write_text(json.dumps(cfg,indent=2,sort_keys=True)+'\\n');final.chmod(0o400)
print(json.dumps({'status':'SOURCE_LIGHT_CONFIG_CONSTRUCTED_FOR_REVIEW_ONLY','config':binding(final),'source':cfg['head'],'tree':cfg['tree'],'source_count':len(rows),'native':'NOT_RUN','root_execution_release':'SEPARATELY_REQUIRED'}))
'''
write('construct_currentEDF_LIGHT_after_root_adoption.py',constructor)
for p in O.glob('*.py'):ast.parse(p.read_text())
print('PREPARATION_PYTHON_AST_PARSED_NO_GATE_OR_CONSTRUCTOR_EXECUTION')
