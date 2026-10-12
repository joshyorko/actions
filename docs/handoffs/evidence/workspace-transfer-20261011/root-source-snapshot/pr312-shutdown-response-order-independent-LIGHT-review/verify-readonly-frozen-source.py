import ast,hashlib,json,os,stat,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=Path('/workspace/engineering/runtime-checkout-eol');D=Path('/workspace/engineering/pr312-shutdown-response-order-source')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for z in iter(lambda:f.read(1048576),b''):h.update(z)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def check(row):assert bind(row['path'])=={k:row[k] for k in ('path','bytes','sha256')};assert 'mode' not in row or oct(stat.S_IMODE(Path(row['path']).stat().st_mode))==row['mode']
def load(p):return json.loads(Path(p).read_bytes())
owner=D/'OWNERFINAL-pr312-shutdown-response-order-LIGHT-source-checkpoint.json';assert owner.stat().st_size==29872 and sha(owner)=='7812bf4345169e1d52bd0debadb4f5d7c641b44ba079bae139ac125af2bd1f44';r=load(owner)
for row in r['private_refs']:check(row)
assert len(r['private_refs'])==41
for k in ['complete_typed_proof','before_source','before_commit','constructor']:check(r[k])
git=lambda *a:subprocess.check_output(['git',*a],cwd=ROOT)
head='77ed3de24f33412dff30e4e3c18841c4c09933ac';parent='77065131a0aee63d2b1f8621476374bdde3c7b65';tree='943c9b88d5d508a4c59b0461b6220ec86e1a7d62'
assert git('rev-parse','HEAD').decode().strip()==head and git('rev-parse','HEAD^{tree}').decode().strip()==tree and git('show','-s','--format=%P',head).decode().split()==[parent] and not git('status','--porcelain')
assert subprocess.run(['git','merge-base','--is-ancestor','a0d258a16095b95b1bf9000cb1201cddfaff4779',head],cwd=ROOT).returncode==0
assert git('branch','--show-current').decode().strip()=='fix/runtime-checkout-eol-20261011'
def inventory(ref):
 d={}
 for rec in git('ls-tree','-rz',ref).split(b'\0'):
  if rec:meta,n=rec.split(b'\t',1);d[n.decode()]=meta.decode().split()
 return d
old=inventory(parent);cur=inventory(head);assert len(old)==1423 and len(cur)==1424 and set(old)<=set(cur)
changed=[n for n in old if old[n]!=cur[n]];added=sorted(set(cur)-set(old));assert set(changed)=={'action_server/src/actions/server/_server.py','docs/skills/repository-operations.md'} and added==['action_server/tests/action_server_tests/test_shutdown_response_order.py']
for n,(mode,kind,oid) in cur.items():
 p=ROOT/n;data=os.readlink(p).encode() if mode=='120000' else p.read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==oid
 if mode!='120000':assert bool(p.stat().st_mode&0o111)==(mode=='100755')
before=load(r['before_source']['path']);assert before['ref_count']==141 and len(before['distinct_preserved_refs'])==141
for row in before['distinct_preserved_refs']:check(row)
# Only local FastAPI injection and the shutdown interruption scheduling differ.
path='action_server/src/actions/server/_server.py';oldAST=ast.parse(git('show',parent+':'+path));newAST=ast.parse(git('show',head+':'+path));removed_aliases=0;changed_functions=0
for n in ast.walk(newAST):
 if isinstance(n,ast.ImportFrom) and n.module=='fastapi':
  aliases=[a for a in n.names if a.name=='BackgroundTasks'];removed_aliases+=len(aliases);n.names=[a for a in n.names if a.name!='BackgroundTasks']
 if isinstance(n,ast.FunctionDef) and n.name=='shutdown':
  assert isinstance(n.args.args[0].annotation,ast.Name) and n.args.args[0].annotation.id=='BackgroundTasks' and n.args.args[0].arg=='background_tasks';n.args.args=n.args.args[1:]
  call=n.body[-1];assert isinstance(call,ast.Expr) and ast.dump(call.value,include_attributes=False)==ast.dump(ast.parse('background_tasks.add_task(_thread.interrupt_main)',mode='eval').body,include_attributes=False);n.body[-1]=ast.parse('_thread.interrupt_main()').body[0];changed_functions+=1
assert removed_aliases==changed_functions==1 and ast.dump(oldAST,include_attributes=False)==ast.dump(newAST,include_attributes=False)
# Installed response and BackgroundTask semantics are versioned source evidence only.
installed={}
for p in [ROOT/'action_server/.venv/lib/python3.12/site-packages/starlette/responses.py',ROOT/'action_server/.venv/lib/python3.12/site-packages/starlette/background.py']:
 data=p.read_bytes();installed[str(p)]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
responses=(ROOT/'action_server/.venv/lib/python3.12/site-packages/starlette/responses.py').read_text();klass=next(n for n in ast.parse(responses).body if isinstance(n,ast.ClassDef) and n.name=='Response');method=next(n for n in klass.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='__call__');segment=ast.get_source_segment(responses,method);assert segment.index('await send({"type": prefix + "http.response.body"')<segment.index('await self.background()')
# Match original JUnit case outcomes directly, not summary text alone.
junit={}
for name in ['ordering-RED-junit.xml','ordering-GREEN-junit.xml','final-scoped-junit.xml']:
 cases=list(ET.parse(D/name).getroot().iter('testcase'));counts={'PASS':0,'FAIL':0,'ERROR':0,'SKIP':0}
 for c in cases:counts['FAIL' if c.find('failure') is not None else 'ERROR' if c.find('error') is not None else 'SKIP' if c.find('skipped') is not None else 'PASS']+=1
 junit[name]={'cases':len(cases),**counts}
assert junit['ordering-RED-junit.xml']=={'cases':10,'PASS':5,'FAIL':5,'ERROR':0,'SKIP':0} and junit['ordering-GREEN-junit.xml']=={'cases':10,'PASS':10,'FAIL':0,'ERROR':0,'SKIP':0} and junit['final-scoped-junit.xml']=={'cases':86,'PASS':86,'FAIL':0,'ERROR':0,'SKIP':0}
controls=ROOT/added[0];c=ast.parse(controls.read_text());assert 'await asyncio.sleep(0)' in controls.read_text() and 'await asyncio.wait_for(app(scope, receive, send), timeout=2)' in controls.read_text()
assert len([n for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')])==4
for needle in ['status == 200','body == b"null"','body-completed','owned-wrong-key','OwnedSendFailure','timeout=invalid','refuse_native']:assert needle in controls.read_text()
prepared=load(D/'own-Bootstrap-reuse-inputs-and-origins.json');assert len(prepared['inputs_exact_prepared_git_bytes_sha256'])==30
for n,h in prepared['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(ROOT/n)==h
for p,row in prepared['own5venvs_current_config_and_python'].items():assert sha(ROOT/p/'.venv/pyvenv.cfg')==row['config_sha256']
for package,module in [('actions','actions'),('actions-http-helper','actions_http'),('devutils','devutils.invoke_utils'),('work-items','actions.work_items'),('action_server','actions.server._rcc_runtime_adapter')]:
 origin=load(D/('origin-'+package+'.json'));assert str(ROOT/package) in json.dumps(origin)
log=(D/'final-cached-LIGHT.private.log').read_text();assert '86 passed' in log and '350 source files' in log and '314 files already formatted' in log and 'PURE_CACHED_SHUTDOWN_LIGHT_ALL_PASS' in log
patch=Path(r['documentation_improvement']['exact_delta']['path']);check(r['documentation_improvement']['exact_delta']);assert patch.read_bytes()==git('diff',parent,head,'--','docs/skills/repository-operations.md')
canonical=(ROOT/'docs/skills/repository-operations.md').read_text();assert 'ASGI send ordering still requires fresh platform client and' in canonical and 'does not guarantee network delivery' in canonical
proof={'status':'GO_SOURCE_LIGHT_ONLY_NOT_FULL_OR_PLATFORM_ACCEPTANCE','source':{'head':head,'tree':tree,'sole_parent':parent,'branch':'fix/runtime-checkout-eol-20261011','actual_target':'a0d258a16095b95b1bf9000cb1201cddfaff4779','clean':True},'owner':bind(owner),'source_complete1424_Git_FS_body_execmode_exact':True,'all1421_old_other_leaves_exact':True,'all_original141refs_and41current_refs_exact':True,'whole_server_AST_exact_after_only_FastAPI_injection_and_background_task_scheduling_normalization':True,'junit_original_outcomes':junit,'source_limits':'No native/browser/provider/gateway/full tests replayed; fresh client200/naturalrc1/Windows/native-source equivalence and root full execution remain HOLD','installed_Starlette_semantic_source_bindings':installed,'prepared30_and_five_own_origin_receipts_preserved':True,'canonical_exact_accepted_delta':bind(patch),'original_prepytest_setup_failure':'retained; no RED count credited','upstream_disposition':'none'}
f=OUT/'independent-frozen-source-LIGHT-proof.json';assert not f.exists();f.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');f.chmod(0o444);print(json.dumps({'proof':bind(f),'status':proof['status']}))
