from pathlib import Path
import ast,copy,difflib,hashlib,json,os,stat,subprocess,xml.etree.ElementTree as ET
B=Path('/workspace/engineering/pr308-current8d49-persistent-two-path-private-recontext');O=Path('/workspace/engineering/pr308-current8d49-persistent-recontext-independent-review');O.mkdir(mode=0o700,exist_ok=True);R=Path('/workspace/engineering/pr308');env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def exact(r):assert bind(r['path'])==r
owner=B/'OWNERFINAL-private-current8d49-persistent-two-path-recontext-SOURCE_ONLY-and-generated-output-HOLD-v2.json';assert bind(owner)['sha256']=='bd7cdb55f6a3450ec989975561df8dc4c877b4ba308a100e3115033a12c8fd9b';d=json.loads(owner.read_bytes())
for row in d['references']:exact(row)
assert len(d['references'])==26
oldowner=Path('/workspace/engineering/pr308-persistent-fixture-private-source/OWNERFINAL-private-current-b614-persistent-fixture-two-path-source-patch.json');old=json.loads(oldowner.read_bytes());assert bind(oldowner)['sha256']=='adeb06df026599e9a8d6e71976f6130de71ef1f3851a8a7c0b895d8b7e6bb419';exact(old['candidate_file']);exact(old['patch']);assert old['patch']['sha256']=='7964bd4e8cf817d0ed1651dafab823d3d9902d7a714015c26675d7bd444f2c48'
accepted=Path('/workspace/engineering/pr308-persistent-fixture-independent-review/OWNERFINAL-independent-private-b614-persistent-two-path-patch-review.json');assert bind(accepted)['sha256']=='604911a30177ab5e30e097ccaddf7a7451c4585001b9df8c0b815be1f684fed6'
original=ast.parse((B/'original8d49-fixture.py').read_bytes());proposed=ast.parse((B/'private-candidate/action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py').read_bytes());historical=ast.parse(Path(old['candidate_file']['path']).read_bytes())
def definitions(t):return {n.name:n for n in t.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
def norm(n):return ast.dump(n,include_attributes=False)
a,b,h=definitions(original),definitions(proposed),definitions(historical);target='test_staged_package_executes_in_managed_rcc_runtime';assert len(a)-1==23
for k in a:
 if k!=target:assert norm(a[k])==norm(b[k])
assert [norm(n) for n in original.body if isinstance(n,(ast.Import,ast.ImportFrom))]==[norm(n) for n in proposed.body if isinstance(n,(ast.Import,ast.ImportFrom))]
helper=copy.deepcopy(b['_run_staged_package_managed_worker']);assert helper.args.kwonlyargs[0].arg=='persistent' and ast.literal_eval(helper.args.kw_defaults[0]) is False;helper.args.kwonlyargs=[];helper.args.kw_defaults=[];helper.name=target
class Specialize(ast.NodeTransformer):
 def visit_If(self,n):
  if isinstance(n.test,ast.Name) and n.test.id=='persistent':return []
  if isinstance(n.test,ast.UnaryOp) and isinstance(n.test.op,ast.Not) and isinstance(n.test.operand,ast.Name) and n.test.operand.id=='persistent':return [self.visit(x) for x in n.body]
  return self.generic_visit(n)
 def visit_IfExp(self,n):
  return self.visit(n.orelse) if isinstance(n.test,ast.Name) and n.test.id=='persistent' else self.generic_visit(n)
 def visit_Assign(self,n):
  if any(isinstance(x,ast.Attribute) and isinstance(x.value,ast.Name) and x.value.id=='settings' and x.attr=='reuse_processes' for x in n.targets):assert isinstance(n.value,ast.Name) and n.value.id=='persistent';n.value=ast.Constant(False)
  return self.generic_visit(n)
assert norm(Specialize().visit(helper))==norm(a[target])
assert norm(b[target].args)==norm(a[target].args) and [norm(n) for n in b[target].decorator_list]==[norm(n) for n in a[target].decorator_list]
assert b[target].body[-1].value.func.id=='_run_staged_package_managed_worker' and not b[target].body[-1].value.keywords
added=[k for k in b if k not in a];assert len(added)==12
for name in added:
 if name!='_run_staged_package_managed_worker':assert norm(b[name])==norm(h[name])
# Shared helper changes only by importing the current default cache-preparation statement.
oldbody=[norm(n) for n in h['_run_staged_package_managed_worker'].body];newbody=[norm(n) for n in b['_run_staged_package_managed_worker'].body]
changes=[(tag,i,j,k,l) for tag,i,j,k,l in difflib.SequenceMatcher(a=oldbody,b=newbody,autojunk=False).get_opcodes() if tag!='equal'];assert len(changes)==1
assert changes[0][:3]==('insert',11,11) and changes[0][3:]==(11,12)
stmt=b['_run_staged_package_managed_worker'].body[11];assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_prepare_owned_rcc_test_package_cache' for n in ast.walk(stmt));assert norm(stmt) in [norm(n) for n in a[target].body]
# Literal two-file diff recreated in memory equals frozen patch.
patch=''
for rel,oldp,newp in [('action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py',B/'original8d49-fixture.py',B/'private-candidate/action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'),('docs/skills/repository-operations.md',B/'original8d49-repository-operations.md',B/'private-candidate/docs/skills/repository-operations.md')]:
 patch+='diff --git a/'+rel+' b/'+rel+'\n'+''.join(difflib.unified_diff(oldp.read_text().splitlines(keepends=True),newp.read_text().splitlines(keepends=True),fromfile='a/'+rel,tofile='b/'+rel))
assert patch.encode()==Path(d['patch']['path']).read_bytes();assert len(patch.encode())==24118
newguide=(B/'private-candidate/docs/skills/repository-operations.md').read_text();oldguide=(B/'original8d49-repository-operations.md').read_text();assert len(newguide.splitlines())-len(oldguide.splitlines())==8
oldcandidate=Path(old['candidate_guide']['path']).read_text();assert all(line in oldcandidate for line in difflib.ndiff(oldguide.splitlines(),newguide.splitlines()) if False)
newlines=[line[2:] for line in difflib.ndiff(oldguide.splitlines(),newguide.splitlines()) if line.startswith('+ ')];assert len(newlines)==8 and '\n'.join(newlines).strip() in oldcandidate
# Original current24 JUnit and transcripts only, no pytest/static replay.
x=ET.parse(B/'one-private-mock-controls-owned-v2/original-private-controls-junit.xml');cases=x.findall('.//testcase');assert len(cases)==24 and len({(n.get('classname'),n.get('name')) for n in cases})==24 and not x.findall('.//failure') and not x.findall('.//error') and not x.findall('.//skipped')
log=(B/'original-current8d49-private-mock-controls-and-static-v2.private.log').read_text();assert '24 passed, 64 deselected, 683 warnings' in log and 'PRIVATE_MOCK_CONTROLS_AND_CONFIGURED_STATIC_PASS_NO_RCC_GATEWAY_NATIVE' in log
# Exact installed logging-option source and actual omission in pinned private launcher.
plugin=Path(d['generated_output_boundary']['original_plugin_destination_source']['ref']['path']);exact(d['generated_output_boundary']['original_plugin_destination_source']['ref']);pt=ast.parse(plugin.read_bytes());functions={n.name:n for n in pt.body if isinstance(n,ast.FunctionDef)}
options=[n for n in ast.walk(functions['pytest_addoption']) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='addoption' and n.args and isinstance(n.args[0],ast.Constant) and n.args[0].value=='--robocorp-log-output'];assert len(options)==1 and next(k.value.value for k in options[0].keywords if k.arg=='default')=='./output'
configure=ast.get_source_segment(plugin.read_text(),functions['pytest_configure']);assert 'Path(config.getoption("--robocorp-log-output", "./output"))' in configure and '_setup_log_output(' in configure
launcher=(B/'run_current8d49_private_mock_controls_once_v2.py').read_text();assert '--robocorp-log-output' not in launcher and "'-o','tmp_path_retention_policy=all'" in launcher and "'--basetemp='+str(base)" in launcher
# Current tracked/source and fourteen LIGHT refs unchanged while root separateFULL runs.
proof=json.loads((B/'immutable-complete8d49-untouched-and-private-default-contract-proof.json').read_bytes());assert len(proof['entries'])==1440
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*args],env=env)
assert git('rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[d['source']['head'],d['source']['tree']] and not git('status','--porcelain=v1')
for row in proof['entries']:
 body=git('cat-file','blob',row['blob']);p=R/row['path'];assert p.read_bytes()==body and len(body)==row['bytes'] and hashlib.sha256(body).hexdigest()==row['sha256'] and bool(p.stat().st_mode&0o111)==(row['mode']=='100755')
light=json.loads(Path('/workspace/engineering/pr308-expectedEDF-fresh-gates-preparation/OWNERFINAL-current8d49-configured-SOURCE_LIGHT-PASS.json').read_bytes());assert len(light['frozen_bindings'])==14
for row in light['frozen_bindings']:exact(row)
assert not git('status','--porcelain=v1')
result={'schema':1,'status':'PASS_PRIVATE_SOURCE_ONLY_RECONTEXT_ADOPTION_AND_GENERATED_OUTPUT_HOLD','owner_binding':bind(owner),'patch_binding':d['patch'],'references_rehashed':26,'original_accepted_private_owner':bind(oldowner),'original_accepted_private_review':bind(accepted),'current_tracked_Git_FS_mode_rows':1440,'current_LIGHT_refs':14,'original_non_target_definitions_AST':23,'original_import_AST':'EXACT','defaultFalse_whole_AST':'EXACT_CURRENT8D49_ORIGINAL','added_definitions':12,'added_permanent_helper_controls_AST_exact_historical':11,'shared_helper_only_old_to_current_delta':'One current cache-preparation If statement from current original default fixture preserved; all other shared helper statements exact historical','prospective_patch_paths':2,'guide_new_lines':8,'guide_lesson':'Exact accepted persistent eight-line addition','mock_current_unique_cases':24,'deselected':64,'warnings':683,'mock_fail_skip_error':0,'static_transcripts':'Configured Ruff/format/isort/one private Mypy PASS observed','logger_plugin_binding':bind(plugin),'logger_option':'--robocorp-log-output default ./output with configured_path → _setup_log_output','private_command':'Explicitbasetemp/ALL but loggingflagABSENT; toolkit.poetry uses package cwd, so ./output remained shared','original_ignored_outputs':'UNAVAILABLE in both preparing lanes; original SHA metadata survives, other copies UNKNOWN','adoption_actual_baseline':'HOLD3→5→7276first, no private source application or actual reuse','reviewer_operations':'Read-only AST/JUnit/transcripts/source Git and exact refs. No tests/imports/source/gate/native/download/index mutation.'}
p=O/'independent-current8d49-private-persistent-recontext-and-logging-boundary-proof.json'
with p.open('x') as w:json.dump(result,w,sort_keys=True,indent=2);w.write('\n')
p.chmod(0o400);print(json.dumps(bind(p)))
