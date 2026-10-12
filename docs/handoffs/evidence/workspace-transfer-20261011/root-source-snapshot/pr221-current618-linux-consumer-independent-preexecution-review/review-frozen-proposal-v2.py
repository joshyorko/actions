import ast
import base64
import csv
import datetime
from email.parser import BytesParser
import hashlib
import io
import json
from pathlib import Path
import stat
import subprocess
import zipfile

B=Path('/workspace/engineering/pr221-current618-linux-consumer-preflight')
O=Path('/workspace/engineering/pr221-current618-linux-consumer-independent-preexecution-review')
R=Path('/workspace/engineering/pr282')
OLD=Path('/workspace/engineering/pr221-current776-linux-consumer-preflight')
cache={}
def sha(data):return hashlib.sha256(data).hexdigest()
def digest(p):
 p=Path(p);s=p.stat();key=(str(p),s.st_size,s.st_mtime_ns)
 if key not in cache:
  h=hashlib.sha256()
  with p.open('rb') as f:
   for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
  cache[key]=h.hexdigest()
 return cache[key]
def binding(row):
 p=Path(row['path']);assert p.stat().st_size==row['bytes'];assert digest(p)==row['sha256'];return row
def load(p):return json.loads(Path(p).read_bytes())
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*args])
def leaves(ref):
 return {n.decode():m.decode().split() for row in git('ls-tree','-r','-z',ref).split(b'\0') if row for m,n in [row.split(b'\t',1)]}
def functions(p):return {n.name:n for n in ast.parse(Path(p).read_bytes()).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
def adump(n):return ast.dump(n,include_attributes=False)
def assignment(path,name):
 node=next(n for n in ast.parse(Path(path).read_bytes()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets));return node.value

p=B/'immutable-current618-linux-consumer-preexecution-proposal-v3.json'
proposal=binding({'path':str(p),'bytes':31495,'sha256':'41ccd19946c766b97c6c49e72dcb592a38193c56763ae6c806a2d41c52b669e6'})
d=load(p)
assert d['actual_consumer_executed'] is False and d['pip_install_download_publication_executed'] is False
for k in ('runner','input_gate','input_manifest','complete_current202_python_member_manifest','artifact_data_ownerfinal','preparation_failure_diagnostic'):binding(d[k])
assert d['runner']['sha256']=='a7da7760d4b93b1053ca3adef14a7860f61502250962edad130aa4014426e2be'
assert d['input_gate']['sha256']=='7474e6fae0e8d8d8211bfc9376697dcd14546b9c1a4ea5925c4042786720ea25'
assert d['input_manifest']['sha256']=='094853d8b745dcf1f6e9a6e392f84c7b544ef0899f0afbfd0502463b8f48bd3d'
assert len(d['all_private_preexecution_files_and_preserved_originals'])==36
assert len(d['historical776_consumer_and_original84fail1_controls_preserved'])==29
for row in d['all_private_preexecution_files_and_preserved_originals']+d['historical776_consumer_and_original84fail1_controls_preserved']:binding(row)
owner=load(d['artifact_data_ownerfinal']['path']);assert len(owner['evidence'])==24
for row in owner['evidence']:binding(row)
binding(d['original_archive']);binding(d['selected_cp312_wheel'])
m=load(d['input_manifest']['path'])
assert d['producer']==owner['producer']
producer=d['producer'];actual=d['actual_integration']
assert producer['checkout']=='e7666eacf2687f65050b97a88e791f8d0ce4cd20'
assert producer['tree']==actual['tree']=='99ac5309add45af65049546dd3a99f357884cf3b'
assert producer['ordered_parents']==['a70993fafc99a9f94041485542d5a720797ca394',actual['sha']]
for subject,key in [(producer,'checkout'),(actual,'sha')]:
 assert git('rev-parse',subject[key]+'^{tree}').decode().strip()==subject['tree']
 assert git('show','-s','--format=%P',subject[key]).decode().split()==subject['ordered_parents']
assert m['actual_integration']==actual
assert m['producer_tuple']['synthetic']==producer['checkout'] and m['producer_tuple']['run_id']==producer['run_id']
assert m['producer_tuple']['synthetic_ordered_parents']==producer['ordered_parents']
assert m['producer_tuple']['job_id']==114433293243
decoded_logs=0
for row in owner['evidence']:
 if Path(row['path']).name.startswith('job-') and Path(row['path']).suffix=='.log':
  assert producer['checkout'] in Path(row['path']).read_text();decoded_logs+=1
assert decoded_logs==3

def safe_infos(z):
 infos=z.infolist();names=[i.filename for i in infos];assert len(names)==len(set(names))
 for i in infos:
  name=i.filename;parts=Path(name).parts
  assert name and not name.startswith('/') and '\\' not in name and '\x00' not in name and ':' not in name
  assert all(p not in ('.','..') for p in parts)
  assert not stat.S_ISLNK(i.external_attr>>16) and not i.flag_bits&1
 return infos
archive=Path(d['original_archive']['path']);wheel=Path(d['selected_cp312_wheel']['path'])
assert stat.S_IMODE(archive.stat().st_mode)==stat.S_IMODE(wheel.stat().st_mode)==0o600
with zipfile.ZipFile(archive) as outer:
 infos=safe_infos(outer);assert len(infos)==2
 expected={row['path']:row for row in m['outer_inventory']};assert set(expected)=={i.filename for i in infos}
 for i in infos:
  data=outer.read(i);assert len(data)==expected[i.filename]['bytes'] and sha(data)==expected[i.filename]['sha256']
 assert outer.read(wheel.name)==wheel.read_bytes()
with zipfile.ZipFile(wheel) as z:
 infos=safe_infos(z);payload={i.filename:z.read(i) for i in infos if not i.is_dir()}
 expected={row['path']:row for row in m['original_selected_wheel']['all_member_inventory']}
 assert set(expected)=={i.filename for i in infos}
 for i in infos:
  row=expected[i.filename];data=z.read(i)
  assert row['kind']==('directory' if i.is_dir() else 'file') and row['bytes']==len(data) and row['sha256']==sha(data)
 mode_by_member={i.filename:stat.S_IMODE(i.external_attr>>16) for i in infos}
 python_count=sum(name.endswith('.py') for name in payload);dirs=sum(i.is_dir() for i in infos)
 assert len(infos)==248 and len(payload)==221 and dirs==27 and python_count==202
 py_manifest=load(d['complete_current202_python_member_manifest']['path'])
 assert py_manifest['python_member_count']==202 and py_manifest['selected_wheel_sha256']==d['selected_cp312_wheel']['sha256']
 rows={r['member']:r for r in py_manifest['python_member_inventory']};assert set(rows)=={name for name in payload if name.endswith('.py')}
 for name,row in rows.items():assert row['bytes']==len(payload[name]) and row['sha256']==sha(payload[name])
 dist='actions_runtime-1.0.3.dist-info/'
 metadata=BytesParser().parsebytes(payload[dist+'METADATA']);payload[dist+'METADATA'].decode('utf-8')
 assert metadata.get_all('Name')==['actions-runtime'] and metadata.get_all('Version')==['1.0.3']
 wheel_metadata=BytesParser().parsebytes(payload[dist+'WHEEL']);assert wheel_metadata.get_all('Root-Is-Purelib')==['false']
 assert all(tag.startswith('cp312-cp312-manylinux') for tag in wheel_metadata.get_all('Tag'))
 record=list(csv.reader(io.StringIO(payload[dist+'RECORD'].decode('utf-8'))))
 assert len(record)==221 and all(len(row)==3 for row in record) and {row[0] for row in record}==set(payload)
 assert len({row[0] for row in record})==221
 verified=0
 for name,encoded,size in record:
  if name==dist+'RECORD':assert encoded==size==''
  else:
   assert encoded=='sha256='+base64.urlsafe_b64encode(hashlib.sha256(payload[name]).digest()).decode().rstrip('=')
   assert size==str(len(payload[name]));verified+=1
 assert verified==220
 assert sha(payload[dist+'RECORD'])==m['original_selected_wheel']['record_sha256']
 tracked=leaves(actual['sha']);assert len(m['tracked_member_bindings'])==215
 assert len({row['member'] for row in m['tracked_member_bindings']})==215
 for row in m['tracked_member_bindings']:
  meta=tracked[row['source_path']];assert meta[2]==row['source_blob'] and meta[0]==row['source_mode']
  data=git('cat-file','blob',row['source_blob']);assert data==payload[row['member']]
  assert sha(data)==row['source_sha256']==row['member_sha256']
  assert bool(mode_by_member[row['member']]&0o111)==(meta[0]=='100755') and row['executable_bit_equal'] is True
 oauth=ast.parse(payload[m['oauth_member']['path']]);assert len(oauth.body)==1 and isinstance(oauth.body[0],ast.Assign)
 assert ast.literal_eval(oauth.body[0].value)=={'actions_config':'','default_user_config':''}
 assert sha(payload[m['oauth_member']['path']])==m['oauth_member']['sha256']
 assert sha(payload['actions/server/bin/rcc-18.19.3'])=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
 assert len([name for name in payload if name.startswith(dist)])==4

runner=Path(d['runner']['path']);old_runner=OLD/'installed-consumer-runner-v2.py'
new_functions=functions(runner);old_functions=functions(old_runner);assert new_functions.keys()==old_functions.keys()
class Normalize(ast.NodeTransformer):
 def visit_Constant(self,node):
  replacements={'original e766 PR producer; tree equals actual618; selected215 tracked payloads only':'original f5dd PR producer; tree equals actual776; selected209 tracked payloads only','rt103-current618-':'rt103-current776-'}
  if isinstance(node.value,str) and node.value in replacements:node.value=replacements[node.value]
  return node
for name,node in new_functions.items():assert adump(Normalize().visit(node))==adump(old_functions[name]),name
for name in ['CHECKOUT_ROOTS','INVENTORY_CODE','CHECKOUT','GUARD_CHECKOUT']:assert adump(assignment(runner,name))==adump(assignment(old_runner,name))
new_gate=ast.parse(Path(d['input_gate']['path']).read_bytes());old_gate=ast.parse((OLD/'current-input-admission-v2.py').read_bytes())
old_constants=[n for n in ast.walk(old_gate) if isinstance(n,ast.Constant)]
new_constants=[n for n in ast.walk(new_gate) if isinstance(n,ast.Constant)]
assert len(old_constants)==len(new_constants)
diffs=[]
for a,b in zip(old_constants,new_constants):
 if a.value!=b.value:diffs.append([a.value,b.value]);b.value=a.value
assert diffs==[[215,221],[214,220],[209,215],[209,215]]
assert adump(old_gate)==adump(new_gate)
for current,previous in [('test_installed_consumer_runner_v3.py','test_installed_consumer_runner_v2.py')]:
 assert {k:adump(n) for k,n in functions(B/current).items()}=={k:adump(n) for k,n in functions(OLD/previous).items()}
roots=ast.literal_eval(assignment(runner,'INVENTORY_CODE'));assert 'sys_path' in roots and 'actions_http' in roots
assert len(d['known_checkout_roots'])==15 and '/workspace/engineering' in d['known_checkout_roots']
helpers=d['helpers_current_Git618_and_immutable_snapshots_exact']
for name,row in helpers.items():
 binding(row)
 if name!='rcc':
  relative=Path(row['path']).relative_to('/workspace/engineering/pr311' if name=='guard' else R)
  assert sha(git('show',actual['sha']+':'+relative.as_posix()))==row['sha256']
snapshots=[row for row in d['all_private_preexecution_files_and_preserved_originals'] if Path(row['path']).name in {'verify_published_runtime_floor.py','test_active_contracts.py','process.py','publish_verified_runtime.py'}]
assert len(snapshots)==4
for row in snapshots:assert stat.S_IMODE(Path(row['path']).stat().st_mode)==0o444
assert digest(helpers['rcc']['path'])=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
assert d['budgets']['worker_seconds']==595 and d['budgets']['process_including_cleanup_seconds']==600 and d['budgets']['reserved_cleanup_max_seconds']==5
assert d['budgets']['outer_gateway_seconds']==645 and d['budgets']['outer_TERM_KILL_grace_seconds']==10
assert d['planned_ONE_actual_gateway']['argv'][:4]==['timeout','--signal=TERM','--kill-after=10s','645s']
assert d['planned_ONE_actual_gateway']['cwd']==str(R) and not Path(d['planned_ONE_actual_gateway']['attempt_root']).exists()
controls=d['service_free_controls'];binding(controls['predecessor_artifact_count_boundary_RED']);binding(controls['one_current85_GREEN']['log']);binding(controls['final_pins_after_packaging_textonly_correction']['log'])
green=Path(controls['one_current85_GREEN']['log']['path']).read_text();final=Path(controls['final_pins_after_packaging_textonly_correction']['log']['path']).read_text()
assert '85 passed, 2 warnings in 2.86s' in green and 'actual main robot run" was SUCCESS' in green
assert '8 passed, 77 deselected' in final and 'actual main robot run" was SUCCESS' in final
assert 'EXPECTED_RED_OLD_ARTIFACT_LITERAL_RECORD215_REJECTS_NEW221_NO_CONSUMER' in Path(controls['predecessor_artifact_count_boundary_RED']['path']).read_text()
assert any('84 passed' in Path(row['path']).read_text() and '1 failed' in Path(row['path']).read_text() for row in d['historical776_consumer_and_original84fail1_controls_preserved'] if Path(row['path']).suffix=='.log')
binding(d['harness']['complete_prehash']);pre=load(d['harness']['complete_prehash']['path']);assert pre['count']==1433
assert git('rev-parse','HEAD').decode().strip()==d['harness']['head']==pre['head']
assert git('rev-parse','HEAD^{tree}').decode().strip()==d['harness']['tree']==pre['tree']
assert git('status','--porcelain')==b''
current=leaves(d['harness']['head']);assert len(current)==1433
for path,meta in current.items():
 data=(R/path).read_bytes();assert sha(data)==pre['tracked_sha256'][path]
 assert bool((R/path).stat().st_mode&0o111)==pre['tracked_executable_bits'][path]==(meta[0]=='100755')
 assert data==git('cat-file','blob',meta[2])
constructor=load(B/'constructor-and-prewording-receipt-disposition.json')
assert constructor['frozen_proposal_sha256']==proposal['sha256']
for key in ['preserved_prewording_runner','preserved_prewording_manifest']:
 row=constructor[key];assert digest(row['path'])==row['sha256']
canonical=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text()
for row in d['documentation_improvement']['Exact_delta_or_verified_reuse']:
 binding(row['patch']);assert row['exact_added_text'] in canonical
 assert row['exact_added_text'] not in (R/'docs/skills/repository-operations.md').read_text()
hold={'field':'input_manifest.original_archive.id/run/job','observed':{k:m['original_archive'][k] for k in ['id','run','job']},'expected':{'id':11697353355,'run':38126987514,'job':114433293243},'scope':'Current archive path/size/digest is exact; these retained predecessor metadata labels contradict the current original artifact identity. No consumer execution or product failure.'}
assert hold['observed']!=hold['expected']
proof={'status':'HOLD_PREEXECUTION_CURRENT_ARCHIVE_IDENTITY_LABELS','proposal':proposal,'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'remaining_concrete_finding':hold,'verified':{'current_refs':36,'historical_refs':29,'owner_artifact_log_refs':24,'all_direct_size_hashes_exact':True,'builder_logs_exact_checkout':decoded_logs,'synthetic_and_actual_ordered_parents_and_equal_tree_exact':True,'outer_original_archive_members':2,'wheel_python':202,'tracked_source_payloads':215,'wheel_RECORD_files':221,'hash_size_verified_RECORD':220,'wheel_directories':27,'dist_info_regular_files':4,'all248_members_exact_declared_inventory':True,'tracked_body_and_executable_bit_source_exact':True,'generated_OAuth_two_empty_fields':'AUTHORITY_HOLD','generated_RCC_7e588_exact':True,'runner_all9_function_ASTs_equal_predecessor_except_two_fixed_literals':True,'gate_AST_only4_measured_count_literals':diffs,'old15_runner_control_function_AST_exact':True,'known_checkout_roots':15,'future_engineering_guard':True,'INVENTORY_CODE_four_origins_sys_path_exact_predecessor':True,'four_helper_Git618_current_hashes_and_snapshots0444_exact':True,'harness_complete1433_prehashes_current_bytes_exec_Git_clean':True,'one85_control_log_and_final8_binding_log_original_old_count_RED_and84pass1_UTF8_RED_retained':True,'worker595_process600_cleanup5_outer645_TERMkill10_unchanged':True,'fresh_attempt_absent':True},'constructor_history':'Initial derivation/prewording bindings are construction observations only; preserved named before-wording artifacts and final frozen proposal pins are separate. No earlier constructor promoted to final GO.','documentation_improvement':d['documentation_improvement'],'not_performed':['Consumer/native/service/browser/provider execution','Tests/controls/gateway/installer or downloads','Source/index/branch changes','Publication/tag/push/merge'],'upstream_disposition':'none'}
dest=O/'independent-frozen-v3-preexecution-review-HOLD.json';assert not dest.exists();dest.write_text(json.dumps(proof,indent=2)+'\n');dest.chmod(0o444)
print(json.dumps({'path':str(dest),'bytes':dest.stat().st_size,'sha256':digest(dest),'status':proof['status']}))
