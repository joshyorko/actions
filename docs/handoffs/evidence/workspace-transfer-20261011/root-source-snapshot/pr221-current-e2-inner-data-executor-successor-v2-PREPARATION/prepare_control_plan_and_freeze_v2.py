import ast,hashlib,json,os,stat
from pathlib import Path
BASE=Path(__file__).resolve().parent
OLD=Path('/workspace/engineering/pr221-current-e2-inner-data-executor-PREPARATION')
def bind(p):
 p=Path(p);s=p.stat();return {'path':str(p),'bytes':s.st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':oct(s.st_mode&0o777)}
def write(p,d):
 b=(json.dumps(d,indent=2,sort_keys=True)+'\n').encode();fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o400)
 with os.fdopen(fd,'wb') as f:f.write(b)
 return bind(p)
cfg=json.loads((OLD/'frozen-executor-inputs.json').read_bytes())
cfg['bindings'] += [bind(OLD/'OWNERFINAL-current-e2-private-inner-data-executor-PREEXECUTION.json'),bind(OLD/'inspect_current_e2_inner_once.py'),bind(OLD/'frozen-executor-inputs.json'),bind(Path('/workspace/engineering/pr221-current-e2-inner-independent-review/OWNERFINAL-independent-current-e2-inner-source-and-executable-PREEXECUTION-HOLD.json'))]
m=write(BASE/'frozen-executor-inputs.json',cfg)
p=BASE/'inspect_current_e2_inner_once_v2.py';s=p.read_text().replace('__MANIFEST_SHA__',m['sha256']);p.write_text(s);p.chmod(0o400);compile(s,str(p),'exec')
t=BASE/'test_actual_inner_boundaries_v2.py';s=t.read_text().replace('__EXECUTOR_SHA__',bind(p)['sha256']);t.write_text(s);t.chmod(0o400);compile(s,str(t),'exec')
proof=write(BASE/'syntax-control-plan-noexecution-proof.json',{'inspector_syntax':'PASS_COMPILE_ONLY','control_syntax':'PASS_COMPILE_ONLY','tests_execution':'NOT_RUN','original_inspection':'NOT_RUN','source':'e2c81adce7858d5a952991ba9a8b7f72e902038a','controls':'FrozenactualfunctionAST against minimal217currentGit source payload baseline; metadata readspies prove caps before payloadreads; no largecap payloadallocations','release_changes':'realunoptimizedguard; regularnonsymlink0600privateROOTrelease guardedbeforeinspection'})
owned='/workspace/engineering/root-current-e2-inner-service-free-controls-v2-once-owned'
args=['/workspace/engineering/pr308/action_server/.venv/bin/python','-m','pytest','-n0','-q',str(t),'--tb=short','--basetemp='+owned+'/basetemp','-o','tmp_path_retention_policy=all','--robocorp-log-output='+owned+'/robot-output','--robocorp-log-max-file-size=10MB','--robocorp-log-max-files=999','--junitxml='+owned+'/junit.xml']
files=[m,bind(p),bind(t),proof,bind('/workspace/actions-cloud/activate.sh'),bind(__file__)]
inputs={'bindings':files,'owned':owned,'argv':args,'activation':{'ACTIONS_CLOUD_ROOT':'/workspace/actions-cloud','ROBOCORP_HOME':'/workspace/actions-cloud/robocorp','XDG_CACHE_HOME':'/workspace/actions-cloud/cache','XDG_CONFIG_HOME':'/workspace/actions-cloud/config','POETRY_CACHE_DIR':'/workspace/actions-cloud/cache/pypoetry','POETRY_CONFIG_DIR':'/workspace/actions-cloud/config/pypoetry','UV_CACHE_DIR':'/workspace/actions-cloud/cache/uv','npm_config_cache':'/workspace/actions-cloud/cache/npm','GOCACHE':'/workspace/actions-cloud/cache/go-build','GOPATH':'/workspace/actions-cloud/cache/go','PLAYWRIGHT_BROWSERS_PATH':'/workspace/actions-cloud/cache/playwright','PYTEST_XDIST_AUTO_NUM_WORKERS':'2','POETRY_NO_INTERACTION':'1','BUILDX_CONFIG':'/workspace/actions-cloud/cache/buildx','ACTIONS_HOME':'/workspace/actions-cloud/actions-home','ROBOTS_HOME':'/workspace/actions-cloud/robots-home','GOMAXPROCS':'2','ACTIONS_RUNTIME_TEST_PYTHON':'/workspace/actions/action_server/.venv/bin/python'}}
c=write(BASE/'frozen-service-free-control-inputs-v2.json',inputs)
launcher='''import hashlib,json,os,stat,subprocess,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
CFG=BASE/'frozen-service-free-control-inputs-v2.json'
CFG_SHA='__CFG_SHA__'
assert not sys.flags.optimize and 'PYTHONOPTIMIZE' not in os.environ and 'PYTEST_ADDOPTS' not in os.environ
raw=CFG.read_bytes();assert hashlib.sha256(raw).hexdigest()==CFG_SHA
cfg=json.loads(raw)
def guards():
 for r in cfg['bindings']:
  p=Path(r['path']);b=p.read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'] and oct(p.stat().st_mode&0o777)==r['mode']
 for k,v in cfg['activation'].items():assert os.environ.get(k)==v
 assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
 assert Path(sys.prefix).resolve()==Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534').resolve()
guards()
out=Path(cfg['owned']);assert not out.exists() and not out.is_symlink();out.mkdir(mode=0o700)
result={'phase':'SERVICE_FREE_REAL_AST_CONTROLS','actual_original_inspection':'NOT_RUN'}
primary=None
try:
 with (out/'stdout.private.log').open('xb') as stdout,(out/'stderr.private.log').open('xb') as stderr:
  os.chmod(out/'stdout.private.log',0o600);os.chmod(out/'stderr.private.log',0o600)
  r=subprocess.run(['timeout','--signal=TERM','--kill-after=10s','120s',*cfg['argv']],cwd=out,env=dict(os.environ),stdout=stdout,stderr=stderr,timeout=131)
  result['returncode']=r.returncode
  if r.returncode:raise RuntimeError('SERVICE_FREE_CONTROL_FAILURE')
except BaseException as exc:
 primary=exc;result['primary_exception_type']=type(exc).__name__
finally:
 try:guards();result['post_bindings']='PASS'
 except BaseException as secondary:
  result['post_bindings']='FAILED'
  if primary is not None:primary.add_note('Controlpostguard also failed: '+type(secondary).__name__)
  else:primary=secondary
 p=out/'original-control-terminal.json';p.write_text(json.dumps(result,sort_keys=True,indent=2)+'\\n');p.chmod(0o600)
if primary is not None:raise primary
'''.replace('__CFG_SHA__',c['sha256'])
l=BASE/'launch_service_free_controls_once_v2.py';l.write_text(launcher);l.chmod(0o400);compile(launcher,str(l),'exec')
owner=write(BASE/'OWNERFINAL-current-e2-inner-successor-v2-service-free-CONTROL-PREEXECUTION.json',{'schema':'OWNERFINAL_CURRENT_E2_INNER_REAL_AST_CONTROL_PREEXECUTION','status':'NOT_EXECUTED_REQUIRES_INDEPENDENT_CONDITIONAL_GO_ROOT_SERIALIZED_RELEASE','executor_binding':bind(p),'manifest_binding':m,'control_binding':bind(t),'launcher_binding':bind(l),'evidence':files+[c,bind(l)],'predecessor':bind(OLD/'OWNERFINAL-current-e2-private-inner-data-executor-PREEXECUTION.json'),'original_HOLD':bind('/workspace/engineering/pr221-current-e2-inner-independent-review/OWNERFINAL-independent-current-e2-inner-source-and-executable-PREEXECUTION-HOLD.json'),'exact_parent_argv':['timeout','--signal=TERM','--kill-after=10s','135s','bash','-c','source /workspace/actions-cloud/activate.sh; exec /workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python '+str(l)],'child_argv':args,'owned_cwd':owned,'fresh_absent_ownedroot':True,'serial':'-n0; no installer/native/browser/network/actualfullinspection','activation':'18literalexports+managedPATH first, cachedtoolkitprefix checked; inheritedPYOPT andADDOPTS refused','absolute_log_outputs':'ownedstdout/stderr/JUnit/robot-output; no shared product ./output','control_scope':['complete minimalcurrent217 source /202Python15nonPython baseline wheel+sdist with metadata RECORDtags scripts and exactlygeneratedwhitelist','independently restored RECORDmissingextra duplicated malformedhashsize self/foreignblank poisons','allZIP headers preflight typesencryptionpathcase duplicates directorysize 64MiB/128MiB/5000 exactedge readspies beforepayload','sdist RCC missingforeign case rootlinks specials64MiBheader gzipCRC/ISIZE','sourcebody/mode differences recordedHOLD','immutable reference member/size/digest/outputcap','actualoptimizer and privateROOTreleaseregular/symlink/type/mode/object guards'],'bounds':{'child_TERM':120,'child_KILL_grace':10,'root_parent_TERM':135,'root_parent_KILL_grace':10,'no_large_cap_payloads':True},'root_release':'Root must announce serialization/capacity clearance and adopt this exact frozenconditionalreviewedargv once; no actualfullinspector release implied','inspector_root_release_future':'Separate v2 executorOWNER proposal after genuinecontrolterminal and independentPREEXECGO, then distinctROOT actualinspection only','documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; existing trusted-source/RECORD/generatedcontent lessons reused; add meaningful optimizer/privateROOTadmission lesson only after control evidence','Durable_learning':'Assert-based inspectors need explicit unoptimized entry and private typed rootrelease before invoking archive validation','Evidence':'reviewb1f40e + realcurrent functions/guards syntax and pending finitecontrols','Stale_or_ambiguous_guidance_removed':'Syntax/AST evidence cannot be called realfunctionboundaryGREEN; original015937HOLD retained','Remaining_uncertainty':'All controls and inspector NOT_RUN; actualgeneratedsource/OAuth/frontend/consumer/release authority HOLD'},'upstream_disposition':'none'})
for r in owner,bind(p),bind(t),bind(l):print(json.dumps(r))
