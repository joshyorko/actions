import ast
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

B=Path('/workspace/engineering/runtime-checkout-eol-source')
R=Path('/workspace/engineering/runtime-checkout-eol')
O=Path('/workspace/engineering/runtime-checkout-eol-independent-final-source-review')
HEAD='92e6deda5c252a503510c4b6261a86cb51f73cb6'
TREE='8c7362e63c85a930ca2fe962ede9bc3ebb6ffe68'
BASE='6181b044c75de35386f1ae30e71725398b6a7feb'
def sha(body):return hashlib.sha256(body).hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
verified={}
def bind(row):
    p=Path(row['path']);body=p.read_bytes();assert len(body)==row['bytes'] and sha(body)==row['sha256'],str(p)
    verified[str(p)]=row;return row
def refs(value):
    if isinstance(value,dict):
        if {'path','bytes','sha256'}<=value.keys() and str(value['path']).startswith('/'):bind(value)
        for v in value.values():refs(v)
    elif isinstance(value,list):
        for v in value:refs(v)
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*args])
def entries(commit):
    rows={}
    for raw in git('ls-tree','-rz',commit).split(b'\0'):
        if not raw:continue
        meta,path=raw.split(b'\t',1);mode,kind,blob=meta.decode().split();assert kind=='blob';rows[path.decode()]=(mode,blob)
    return rows
def funcs(path):return {n.name:n for n in ast.parse(Path(path).read_bytes()).body if isinstance(n,ast.FunctionDef)}
def dump(n):return ast.dump(n,include_attributes=False)
owner=bind({'path':str(B/'OWNERFINAL-runtime-checkout-eol-SOURCEFINAL.json'),'bytes':22316,'sha256':'b0d51fbc7fb87c88fc0f65af090634cc44c7cfb311e00de7b56472160b074189'})
d=load(owner['path']);refs(d);assert len(d['immutable_evidence_bindings'])==62
light=load(B/'OWNERFINAL-runtime-checkout-eol-LIGHT.json');refs(light);assert len(light['immutable_evidence_bindings'])==41
prefull=load(B/'OWNERFINAL-runtime-checkout-eol-prefull-explicit-worker-bound-v2.json');refs(prefull)
old=load(B/'original-source-and-design-bindings.json');refs(old)
assert git('rev-parse','HEAD').decode().strip()==HEAD and git('rev-parse','HEAD^{tree}').decode().strip()==TREE
assert git('show','-s','--format=%P',HEAD).decode().strip()==BASE and git('status','--porcelain')==b''
previous,current=entries(BASE),entries(HEAD)
assert len(previous)==1419 and len(current)==1421 and set(previous)<=set(current)
changed={name for name in previous if current[name]!=previous[name]}
assert changed==set(d['changed_original_paths']) and len(changed)==5
assert set(current)-set(previous)==set(d['new_permanent_tests']) and len(d['new_permanent_tests'])==2
assert len(previous)-len(changed)==1414
pre=load(B/'committed-source-LIGHT-pre-full.json');assert len(pre['leaves'])==1421
pre_rows={row['path']:row for row in pre['leaves']}
for name,(mode,blob) in current.items():
    body=(R/name).read_bytes();assert body==git('cat-file','blob',blob)
    assert bool((R/name).stat().st_mode&0o111)==(mode=='100755')
    row=pre_rows[name];assert row['mode']==mode and row['git_blob']==blob and row['bytes']==len(body) and row['sha256']==sha(body)
rules=[
 'action_server/src/**/*.py text eol=lf',
 'action_server/frontend/apps/runtime/index.html text eol=lf',
 'action_server/src/actions/server/README.md text eol=lf',
 'action_server/src/actions/server/bin/.gitignore text eol=lf',
 'action_server/src/actions/server/index.html text eol=lf',
 'action_server/src/actions/server/templates/action-templates.yaml text eol=lf',
 'action_server/src/actions/server/vendored_deps/README.md text eol=lf']
attrs=(R/'.gitattributes').read_text();prior_attrs=git('show',BASE+':.gitattributes').decode()
assert attrs==prior_attrs+'\n# Preserve exact Runtime distribution source and HTML scaffold checkout bytes.\n'+'\n'.join(rules)+'\n'
runtime_py=[name for name in current if name.startswith('action_server/src/') and name.endswith('.py')]
selected=runtime_py+[rule.split()[0] for rule in rules[1:]]
assert len(runtime_py)==201 and len(set(selected))==207
for name in selected:assert current[name]==previous[name] and b'\r' not in (R/name).read_bytes()
generator='.github/workflows/_gen_workflows.py'
a=ast.parse((R/generator).read_bytes());b=ast.parse(git('show',BASE+':'+generator))
classes={n.name:n for n in a.body if isinstance(n,ast.ClassDef)}
test_on=next(n for n in classes['ActionServerTests'].body if isinstance(n,ast.FunctionDef) and n.name=='on_part')
appends=[n for n in test_on.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='append' and n.value.args and isinstance(n.value.args[0],ast.Constant) and n.value.args[0].value=='.gitattributes']
assert len(appends)==1;test_on.body.remove(appends[0])
release=next(n for n in classes['ActionServerPyPiRelease'].body if isinstance(n,ast.FunctionDef) and n.name=='on_part')
lists=[n for n in ast.walk(release) if isinstance(n,ast.List) and any(isinstance(x,ast.Constant) and x.value=='.gitattributes' for x in n.elts)]
assert len(lists)==1;lists[0].elts=[x for x in lists[0].elts if not(isinstance(x,ast.Constant) and x.value=='.gitattributes')]
assert dump(a)==dump(b)
for name in ['.github/workflows/actions_runtime_tests.yml','.github/workflows/actions_runtime_pypi_release.yml']:
    text=(R/name).read_text();assert text.count('    - .gitattributes\n')==1
    assert text.replace('    - .gitattributes\n','')==git('show',BASE+':'+name).decode()
github_yaml=[name for name in current if name.startswith('.github/') and name.endswith(('.yml','.yaml'))]
assert len(github_yaml)==30
roundtrip=load(B/'generator-all-eight-roundtrip.json');assert roundtrip['generated_workflows']==8
scope=load(B/'complete-scope-and-generator-proof.json')
assert scope['all_tracked_GitHub_YAML_parsed']==30 and scope['other_tracked_YAML_byte_exact']==28
assert scope['eight_generated_target_data_matches']==8
workflow_controls=funcs(R/'devutils/tests/test_runtime_checkout_workflows.py');old_controls=funcs(B/'initial-filter-controls-before-scope-cleanup.py')
for name,n in workflow_controls.items():assert dump(n)==dump(old_controls[name])
checkout=funcs(R/'devutils/tests/test_runtime_checkout_bytes.py')
helper_source=ast.get_source_segment((R/'devutils/tests/test_runtime_checkout_bytes.py').read_text(),checkout['checkout'])
assert '--no-filters' in helper_source and 'update-index' in helper_source and 'checkout-index' in helper_source
checkout_tree=ast.parse((R/'devutils/tests/test_runtime_checkout_bytes.py').read_bytes())
rules_node=next(n for n in checkout_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='RULES' for t in n.targets))
assert list(ast.literal_eval(rules_node.value))==rules
control_text=(R/'devutils/tests/test_runtime_checkout_bytes.py').read_text()
assert 'for rule in RULES' in control_text and 'with self.assertRaises(AssertionError)' in control_text and 'for setting in (True, False)' in control_text
assert 'GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull' in control_text
red=(B/'checkout-original-policy-RED.log').read_text();green=(B/'checkout-policy-GREEN.log').read_text()
assert '180 additional elements' in red and 'FAILED (failures=2)' in red
assert 'Ran 4 tests' in green and green.rstrip().endswith('OK')
filter_red=(B/'filter-original-policy-RED.log').read_text();assert '6 failed, 88 deselected' in filter_red
assert '10 passed in 5.78s' in (B/'final-owned-scoped-tests-and-static.log').read_text()
assert 'Success: no issues found in 347 source files' in (B/'owned-scoped-and-static.log').read_text()
assert '96 passed' in (B/'Toolkit.log').read_text()
full_log=(B/'full-source-gates.log').read_text();assert '162 passed in 9.74s' in full_log
assert '1219 passed, 13 skipped, 15 warnings in 133.23s' in full_log
assert 'created: 2/2 workers' in full_log and '2 workers [1232 items]' in full_log
assert 'actual main robot run" was SUCCESS' in full_log
terminal=load(B/'full-source-gates-terminal.json');authorization=load(B/'root-one-explicit-two-worker-full-execution-authorization.json');refs(authorization)
assert terminal['returncode']==0 and terminal['full_attempt_count']==1 and terminal['retry'] is False
assert terminal['argv']==authorization['outer_full_argv']==d['full_execution']['exact_argv']
assert authorization['proposal']['sha256']=='7bf6cab2ba416579fd66858e0bb0715622f5f526ee973a4b12cb0eef12a02a5a'
assert authorization['independent_review']['sha256']=='697bfa3f95a6e3d3adbcef1784904c97da743ecb06441ac7782ea42d81210669'
assert authorization['source_head']==HEAD and authorization['source_tree']==TREE
launcher=(B/'full-source-gates-explicit-worker-bound-v2.py').read_text()
assert sha(launcher.encode())=='876adde7c0f82ee428413afc48a6b8d7851937c55f8140facb3f76335b70501d'
assert launcher.index('os.environ["PYTEST_XDIST_AUTO_NUM_WORKERS"] = "2"')<launcher.index('toolkit.poetry(')
post=load(B/'post-full-source-env-and-original-receipt-retention.json')
assert post['head']==HEAD and post['tree']==TREE and post['1421_source_body_exec_mode_hashes_exact'] is True
assert post['created_worker_census']==[['2','2']] and post['worker_item_census']==[['2','1232']]
prep=load(B/'own-Bootstrap-reuse-inputs-and-origins.json')
assert prep['measured_inputs']==len(prep['inputs_exact_prepared_git_bytes_sha256'])==30 and prep['new_Bootstrap_executed'] is False
assert sha(Path(prep['original_bootstrap_log']).read_bytes())==prep['original_bootstrap_log_sha256']
for name,expected in prep['inputs_exact_prepared_git_bytes_sha256'].items():
    assert sha((R/name).read_bytes())==expected==sha(git('show',prep['prepared_source']+':'+name))
assert len(prep['own5venvs_current_config_and_python'])==len(prep['own5actual_prefix_and_source_origin_assertions'])==5
for name,row in prep['own5venvs_current_config_and_python'].items():
    assert sha((R/name/'.venv/pyvenv.cfg').read_bytes())==row['config_sha256']
    assert str((R/name/'.venv/bin/python').resolve())==row['python_resolved']
for row in prep['own5actual_prefix_and_source_origin_assertions']:
    assert Path(row['prefix']).is_relative_to(R) and Path(row['origin']).is_relative_to(R)
    assert Path(row['origin']).is_file() and Path(row['python']).exists()
rcc=R/'action_server/src/actions/server/bin/rcc-18.19.3'
assert sha(rcc.read_bytes())=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428' and stat.S_IMODE(rcc.stat().st_mode)==0o711
native=load(B/'retained-native-helper-browser-and-V5-proof-post-full.json');refs(native)
assert native==load(B/'retained-native-helper-browser-and-V5-proof-root-released-pre.json')
inventory=load(native['original_inventory']['path']);assert len(inventory)==1192
native_root=Path(native['original_frozen_executable']['path']).parent
for row in inventory:
    path=native_root/row['path'];mode=path.lstat().st_mode;assert stat.S_IMODE(mode)==row['mode']
    if row['kind']=='directory':assert path.is_dir()
    elif row['kind']=='symlink':assert path.is_symlink() and os.readlink(path)==row['link_target'];assert sha(path.read_bytes())==row['content_sha256']
    else:assert row['kind']=='file' and path.is_file() and not path.is_symlink();assert sha(path.read_bytes())==row['content_sha256']
for values in native['frozen_helper_original_and_snapshot_bindings'].values():
    assert values['original']['sha256']==values['snapshot']['sha256']
    assert stat.S_IMODE(Path(values['snapshot']['path']).stat().st_mode)==0o444
raw=load(B/'raw18-frozen50-Node-frontend-retained-post-full.json')
assert raw==load(B/'raw18-frozen50-Node-frontend-retained-root-released-pre.json')
consumer=load(native['historical_V5_checkpoint']['path'])
assert len(consumer['raw_receipts_private_do_not_commit'])==18
for row in consumer['raw_receipts_private_do_not_commit']:bind(row)
assert len(consumer['frozen_posthashes'])==50
for row in consumer['frozen_posthashes']:
    assert sha(Path(row['path']).read_bytes())==row['sha256']==row['expected_sha256']
driver=load(native['immutable_proposal']['path'])['driver'];refs(driver)
assert sha(Path(driver['frontend_lock']['path']).read_bytes())==raw['frontend_lock_sha256']
assert sha(Path(driver['node']).read_bytes())==raw['prepared_node_binary_sha256']
assert sha(Path(driver['browser']).read_bytes())==raw['browser_sha256'] and Path(driver['prepared_node_modules']).is_dir()
for path,expected in light['private_v4_principal_frozen_files_unchanged'].items():assert sha(Path(path).read_bytes())==expected
canonical_source=Path('/workspace/engineering/pr221-current618-static-frontend-trace-owned/canonical-checkout-byte-and-generated-content-proposed.patch')
# The exact canonical source path is supplied by its original diagnosis binding.
diagnosis=load(old['bindings'][0]['path'])
def find_ref(value, expected):
    if isinstance(value,dict):
        if value.get('sha256')==expected and 'path' in value:return value
        for v in value.values():
            found=find_ref(v,expected)
            if found:return found
    elif isinstance(value,list):
        for v in value:
            found=find_ref(v,expected)
            if found:return found
    return None
accepted=find_ref(diagnosis,'1306a314811448c8090b4aa2e77340e676bbba397ceb6c7ee0477b908cb9b2bf');assert accepted;bind(accepted)
lines=[x[1:] for x in Path(accepted['path']).read_text().splitlines() if x.startswith('+') and not x.startswith('+++')]
assert len(lines)==16
guide='docs/skills/repository-operations.md';new_guide=(R/guide).read_text();old_guide=git('show',BASE+':'+guide).decode()
block='\n'.join(lines)+'\n';assert new_guide.count(block)==1 and new_guide.replace(block,'')==old_guide
worker_ref=find_ref(prefull,'a113e8c4001305664c781dccc7c5d62a5f0de929df0dc9e09b9c2f41f0d87434');assert worker_ref;bind(worker_ref)
receipt={'schema':'runtime-checkout-eol-independent-final-source-review/v1','status':'GO_SOURCE_ONLY_NORMAL_PUSH_AND_FRESH_HOSTED_WINDOWS_DISTRIBUTION_GATES_REQUIRED',
 'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owner_final':owner,
 'source':{'head':HEAD,'tree':TREE,'sole_parent':BASE,'branch':d['branch'],'clean':True},
 'verified':{'owner_final_refs':62,'original_LIGHT_refs':41,'all_direct_binding_SHA_sizes_exact':True,'unique_direct_bindings':len(verified),
  'complete_Git_FS1421_body_exec_modes_prepost':True,'1414_other_original_mode_blob_pairs_exact':True,'authorized_original_paths':sorted(changed),'new_tests':d['new_permanent_tests'],
  '207_selected_inputs201Python5_nonPython1_frontend_exact_parent':True,'seven_narrow_rules_only':True,
  'generator_wholeAST_exact_after_only_two_PR_filter_additions':True,'two_YAML_exact_one_path_filter_item_other28_unchanged':True,'recorded_gen8_GitHub30_roundtrip':True,
  'real_checkout_RED180_not_historical_Windows178':True,'recorded_two_checkout_settings_GREEN_seven_rule_poisons_and_unrelated_fixtures':True,
  'six_filter_RED_to_final10GREEN_existing_control_AST_exact':True,'Toolkit96_lint_type347':True,
  'root_ONE_explicit_worker_bound_release_and_independent_prefull_identity':True,'full_devutils162PASS0skip_seconds':9.74,'full_Runtime1219PASS13skip15warnings_seconds':133.23,'full_actual_workers':[2,2],'outer_exit':0,'outer_elapsed_seconds':terminal['elapsed_seconds'],
  'own30prepared_inputs5configs5_recorded_actual_origins_Rcc0711_exact':True,
  'native1192_modes_bodies_and_historical_V5_helpers_browser_Node_frontend_raw18_frozen50_retained':True,'old_private_v4_four_bindings_unchanged':True,
  'initial39ecc_worker_bound_HOLD_and_a6f_LIGHT_preparation_failures_retained':True},
 'full_execution':d['full_execution'],'source_scope_limits':d['remaining_holds'],
 'qualification_boundary':'Source checks only. Historical native92498/current3ec consumer preserved as original tuples; unchanged bytes are retention, not new native acceptance. Fresh Windows builder/source checkout/distribution contents, empty OAuth authority and private/platform/provider/native/release gates remain separate.',
 'capacity':'Root-recorded658522112B postfull is not future heavy-gate authorization. Named completed scratch preservation belongs to root; no cleanup by reviewer.',
 'documentation_improvement':{'Canonical_file_changed_or_proposed':guide,'Exact_source_delta':bind(next(x for x in d['immutable_evidence_bindings'] if Path(x['path']).name=='exact-canonical-checkout-and-generated-scope.patch')),
   'Accepted_reuse':[accepted,worker_ref],'Added_source_lines':16,'Durable_learning':'Packaged nonPython and frontend checkout bytes need narrow LF rules and owning CI filters; generated module newlines do not normalize embedded bytes; explicit xdist environment must bind both sequential configured commands.',
   'Evidence':'All207 actual input bodies, real Git two-settings/fault controls, exact2filters, source encoder unchanged, recorded2worker full and original misbound launcher preserved.',
   'Stale_guidance_removed':'No contradictory original paragraph replaced; precise accepted16line lesson inserted. The external worker-bound lesson corrects prior unproved -n auto worker assumption without overwriting original receipts.',
   'Remaining_uncertainty':'Historical checkout/frontend input cause UNKNOWN; synthetic180 differs historical178; new hosted Windows/generated semantics/OAuth/private/native/release unqualified.'},
 'not_performed':['Tests/control/gateway/installer/full suite reruns','Generator execution or YAML regeneration','Downloads/payload imports/native/provider/browser execution','Source/index/ref writes, pushes, new PR or merge','Scratch recovery/removal/restore'],
 'upstream_disposition':'none'}
dest=O/'OWNERFINAL-independent-runtime-checkout-eol-source-review.json';assert not dest.exists();dest.write_text(json.dumps(receipt,indent=2)+'\n');dest.chmod(0o444)
print(json.dumps({'path':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest.read_bytes()),'status':receipt['status']}))
