from pathlib import Path,PurePosixPath
import json,hashlib,zipfile,io,csv,base64,stat,ast,subprocess,tomllib,os
D=Path('/workspace/engineering/pr221-current776-linux-consumer-independent-review');BASE=Path('/workspace/engineering/pr221-current776-linux-consumer-preflight');R=Path('/workspace/engineering/pr282')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
def tree(c):return {n.decode():m.decode().split() for row in git('ls-tree','-rz',c).split(b'\0') if row for m,n in [row.split(b'\t',1)]}
p=BASE/'immutable-current776-linux-consumer-preexecution-proposal-v2.json';assert sha(p)=='57a8beb87e5a1c03fae276e4b22d7fc8734d1f42cc3c739ceb989a0d946e73a7' and p.stat().st_size==25752;j=json.loads(p.read_text());refs={}
def walk(x):
 if isinstance(x,dict):
  if {'path','sha256'}<=x.keys() and isinstance(x['path'],str) and x['path'].startswith('/'):
   assert sha(x['path'])==x['sha256'];e=bind(x['path']);assert 'bytes' not in x or e['bytes']==x['bytes'];refs[e['path']]=e
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
walk(j)
assert sha(j['runner']['path'])=='1768d6edebc874f5f76ea77a6a3a49d6effa46e144340b7f49bf6f3da0fcf809';assert sha(j['input_gate']['path'])=='3be2b971a43de3848c5a1aec59eecbeb6ac9dd796a81a6f2e489eab782492d1a'
a=j['actual_integration'];prod=j['producer'];assert git('rev-parse',a['sha']+'^{tree}').decode().strip()==a['tree'];assert git('show','-s','--format=%P',a['sha']).decode().split()==a['ordered_parents']
assert git('rev-parse',prod['synthetic']+'^{tree}').decode().strip()==a['tree']==prod['control_tree'];assert git('show','-s','--format=%P',prod['synthetic']).decode().split()==prod['synthetic_ordered_parents'];assert git('rev-parse',prod['control']+'^{tree}').decode().strip()==a['tree'];assert git('rev-parse',prod['source_candidate']+'^{tree}').decode().strip()==prod['source_tree'];assert git('show','-s','--format=%P',prod['control']).decode().split()==[prod['source_candidate']]
current=tree(a['sha']);source=tree(prod['source_candidate']);manifest=json.loads(Path(j['input_manifest']['path']).read_text());assert manifest['actual_integration']==a
for helper,e in j['unchanged_helper_snapshots_with_Git776_modeblobs'].items():
 assert current[e['git_path']]==e['actual776_mode_blob'];body=git('show',a['sha']+':'+e['git_path']);assert body==Path(e['actual_path']['path']).read_bytes()==Path(e['snapshot']['path']).read_bytes();assert hashlib.sha256(body).hexdigest()==e['snapshot']['sha256'];assert stat.S_IMODE(Path(e['snapshot']['path']).stat().st_mode)==0o600
# Read original artifacts in memory only; no extraction or payload execution.
def members(z):
 infos=z.infolist();assert len({i.filename for i in infos})==len(infos)
 for i in infos:
  n=i.filename;p=PurePosixPath(n);assert n and not n.startswith('/') and '\\' not in n and '\0' not in n and ':' not in n and all(x not in ('.','..') for x in p.parts) and str(p)==n.rstrip('/');assert not stat.S_ISLNK(i.external_attr>>16) and not i.flag_bits&1
 return infos
archive=Path(j['artifact']['original_zip']['path']);wheelpath=Path(j['artifact']['selected_cp312_wheel']['path']);assert stat.S_IMODE(archive.stat().st_mode)==stat.S_IMODE(wheelpath.stat().st_mode)==0o600
with zipfile.ZipFile(archive) as z:
 outer=members(z);expected={r['path']:r for r in manifest['outer_inventory']};assert len(outer)==2 and set(expected)=={i.filename for i in outer}
 for i in outer:
  data=z.read(i);r=expected[i.filename];assert len(data)==r['bytes'] and hashlib.sha256(data).hexdigest()==r['sha256'];assert i.filename!=wheelpath.name or data==wheelpath.read_bytes()
with zipfile.ZipFile(wheelpath) as z:
 infos=members(z);inventory={r['path']:r for r in manifest['original_selected_wheel']['all_member_inventory']};assert len(infos)==241 and set(inventory)=={i.filename for i in infos};payload={i.filename:z.read(i) for i in infos if not i.is_dir()}
 for i in infos:
  b=z.read(i);r=inventory[i.filename];assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'];assert r['kind']==('directory' if i.is_dir() else 'file')
assert len(payload)==215 and sum(i.is_dir() for i in infos)==26 and sum(n.endswith('.py') for n in payload)==196
from email.parser import BytesParser
root='actions_runtime-1.0.3.dist-info';meta=payload[root+'/METADATA'];meta.decode('utf-8');m=BytesParser().parsebytes(meta);assert m.get_all('Name')==['actions-runtime'] and m.get_all('Version')==['1.0.3'];pyproject=tomllib.loads(git('show',prod['source_candidate']+':action_server/pyproject.toml').decode());assert pyproject['tool']['poetry']['name']=='actions-runtime' and pyproject['tool']['poetry']['version']=='1.0.3'
rows=list(csv.reader(io.StringIO(payload[root+'/RECORD'].decode('utf-8'))));assert len(rows)==215 and all(len(r)==3 for r in rows) and len({r[0] for r in rows})==215 and {r[0] for r in rows}==set(payload)
for n,h,size in rows:
 if n==root+'/RECORD':assert h==size==''
 else:assert h=='sha256='+base64.urlsafe_b64encode(hashlib.sha256(payload[n]).digest()).decode().rstrip('=') and int(size)==len(payload[n])
w=BytesParser().parsebytes(payload[root+'/WHEEL']);assert w.get_all('Root-Is-Purelib')==['false'] and all(t.startswith('cp312-cp312-manylinux') for t in w.get_all('Tag'))
tracked=manifest['tracked_member_bindings'];assert len(tracked)==209 and len({e['member'] for e in tracked})==209
for e in tracked:
 assert current[e['source_path']][2]==source[e['source_path']][2]==e['source_blob'];assert git('cat-file','blob',e['source_blob'])==payload[e['member']];assert hashlib.sha256(payload[e['member']]).hexdigest()==e['source_sha256']==e['member_sha256']
oauth=manifest['oauth_member'];assert len(payload[oauth['path']])==287 and hashlib.sha256(payload[oauth['path']]).hexdigest()==oauth['sha256'];node=ast.parse(payload[oauth['path']]);assert len(node.body)==1 and isinstance(node.body[0],ast.Assign);assignment=node.body[0];assert len(assignment.targets)==1 and isinstance(assignment.targets[0],ast.Name) and assignment.targets[0].id=='FILE_CONTENTS';assert ast.literal_eval(assignment.value)=={'actions_config':'','default_user_config':''}
runner=Path(j['runner']['path']).read_text();old=Path(j['preserved_originals']['oldrunner']['path']).read_text();rt=ast.parse(runner);ot=ast.parse(old)
def funcs(t):return {n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
f,g=funcs(rt),funcs(ot)
for name in j['logic_preservation']['exact_original_runner_AST_functions']:assert f[name]==g[name]
def literal(t,name):
 for n in t.body:
  if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id==name for x in n.targets):return ast.literal_eval(n.value)
assert literal(rt,'INVENTORY_CODE')==literal(ot,'INVENTORY_CODE');assert literal(rt,'WHEEL_PYTHON_COUNT')==196
known=j['known_checkout_roots'];assert manifest['known_checkout_roots']==known;wt=subprocess.check_output(['git','-C',str(R),'worktree','list','--porcelain']).decode();actualroots=[line.split(' ',1)[1] for line in wt.splitlines() if line.startswith('worktree ')];assert all(any(Path(x).resolve().is_relative_to(Path(k).resolve()) for k in known) for x in actualroots)
assert not Path(j['planned_ONE_actual_gateway']['attempt_root']).exists();assert j['budgets']['worker_seconds']==595 and j['budgets']['process_including_cleanup_seconds']==600 and j['budgets']['outer_gateway_seconds']==645 and j['budgets']['outer_TERM_KILL_grace_seconds']==10
assert 'deadline = started + 595' in runner and 'min(started + 600, time.monotonic() + 5)' in runner;assert 'ATTEMPT.mkdir(mode=0o700)' in runner and 'assert not ATTEMPT.exists()' in runner and 'tempfile.mkdtemp(prefix="rt103-current776-", dir="/tmp")' in runner and 'temporary.chmod(0o700)' in runner;assert 'capture_output=True' in runner and 'start_new_session=True' in runner
assert '85 passed' in Path(j['servicefree_evidence']['final_focused_GREEN']['log']['path']).read_text();assert j['servicefree_evidence']['final_focused_GREEN']['skipped']==0
patch=Path(j['Documentation improvement']['Exact delta']['path']);assert sha(patch)=='bf95da899763f97c016f76fa4a0cf8878ebba8326d57c11ab1a520b1df597c81'
result={'proposal':bind(p),'runner':bind(j['runner']['path']),'input_gate':bind(j['input_gate']['path']),'input_manifest':bind(j['input_manifest']['path']),'verified_unique_nested_frozen_bindings':len(refs),'nested_hash_bindings':list(refs.values()),'actual_integration':a,'producer_distinct_roles':prod,'original_ZIP_and_selected_wheel_exact_owned0600':True,'outer_members':2,'wheel_members':241,'directories':26,'regular_files_RECORD_rows':215,'RECORD_hash_size_verified':214,'Python_members_derived_current_bytes':196,'tracked_payloads_current_actual776_and_original_d642_equal':209,'METADATA_and_source_pyproject_name_version_equal':True,'generated_OAuth_AST_fixed_empty_strings':'MEASURED_EMPTY_CONTENT_AUTHORITY_HOLD','unchanged_helper_snapshot_Git776_mode_blob_bindings':True,'five_original_runner_function_AST_and_inventory_code_equal':True,'all_known_worktrees_covered_by_fifteen_checkout_roots':True,'known_worktree_count':len(actualroots),'fresh_attempt_path_absent':True,'deadline_scope':'595s worker measured from supervisor start; owned process cleanup uses min(start+600,now+5); outer gateway645s with TERM then10s KILL grace also bounds setup/temporary removal/reporting. 600 is not an independently enforced whole-supervisor wall timeout.','servicefree_controls':'85 PASS/0SKIP final, initial UTF8 metadata RED and earlier draft/static/fixture failure identities retained. No replay by reviewer.','scope':'No actual installed import,pip,Runtime/native/provider/browser/gateway execution or network download by reviewer; Linuxcp312 futureattempt only; fullseven/generatedsourceauthority/content/private/release HOLD','canonical_patch':bind(patch)}
out=D/'independent-frozen-proposal-input-and-safety-proof.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(bind(out),indent=2))
