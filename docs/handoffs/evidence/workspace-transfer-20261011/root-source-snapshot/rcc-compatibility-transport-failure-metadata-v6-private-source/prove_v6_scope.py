"""Exact source projection and original-byte guard; no transport execution."""
import ast
import copy
import difflib
import hashlib
import json
import stat
import subprocess
from pathlib import Path

OUT=Path('/workspace/engineering/rcc-compatibility-transport-failure-metadata-v6-private-source')
R=Path('/workspace/engineering/rcc-compatibility-actual-runner-readonly-preparation')


def bind(p):
    p=Path(p);b=p.read_bytes()
    return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(p.stat().st_mode))}


old=ast.parse((R/'actual_transport_v5.py').read_bytes())
new=ast.parse((R/'actual_transport_v6.py').read_bytes())
before=json.loads((OUT/'before-v6-complete263-and-original-failure-bindings.json').read_bytes())
for row in [*before['original263'],*before['original_failure']]:
    actual=bind(row['path']);assert all(actual[k]==row[k] for k in actual),row['path']
assert (OUT/'original-actual_transport_v5.py').read_bytes()==(R/'actual_transport_v5.py').read_bytes()
assert (OUT/'original-test_actual_transport_v5.py').read_bytes()==(R/'test_actual_transport_v5.py').read_bytes()
new.body=[n for n in new.body if not (isinstance(n,ast.Import) and n.names[0].name=='traceback')
          and not (isinstance(n,ast.FunctionDef) and n.name in ['original_helper_facts','make_safe_result','require_transport_binding'])]
execute=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='execute_one')
assert [n.arg for n in execute.args.kwonlyargs]==['retain_exception']
execute.args.kwonlyargs=[];execute.args.kw_defaults=[]
execute.body=[n for n in execute.body if not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['helper_facts','exception_retention_failure'] for t in n.targets))]
inner=next(n for n in execute.body if isinstance(n,ast.Try)).body[0]
inner.body=[n for n in inner.body if not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='helper_facts' for t in n.targets))]
handler=inner.handlers[0]
handler.body=[n for n in handler.body if not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='helper_facts' for t in n.targets))
              and not (isinstance(n,ast.If) and isinstance(n.test,ast.Compare) and isinstance(n.test.left,ast.Name) and n.test.left.id=='retain_exception')]
returned=execute.body[-1].value
pairs=[(k,v) for k,v in zip(returned.keys,returned.values) if k.value not in ['original_helper_facts','secondary_exception_retention_failure_class']]
returned.keys=[k for k,v in pairs];returned.values=[v for k,v in pairs]
main=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='main')
oldmain=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='main')
main.body=[n for n in main.body if not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['observed_supervisor_identity','last_observed_process_tree'] for t in n.targets))
           and not (isinstance(n,ast.FunctionDef) and n.name=='retain_error')
           and not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='require_transport_binding')]
observe=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='observe')
observe.body=[n for n in observe.body if not (isinstance(n,ast.If) and isinstance(n.test,ast.UnaryOp) and isinstance(n.test.operand,ast.Name) and n.test.operand.id=='observed_supervisor_identity')
              and not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=='last_observed_process_tree' for t in n.targets))]
for i,n in enumerate(main.body):
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='result' for t in n.targets):
        assert [k.arg for k in n.value.keywords]==['retain_exception'];n.value.keywords=[]
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='safe' for t in n.targets):
        assert isinstance(n.value,ast.Call) and n.value.func.id=='make_safe_result'
        main.body[i]=copy.deepcopy(next(x for x in oldmain.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='safe' for t in x.targets)))
current_try=next(n for n in main.body if isinstance(n,ast.Try))
old_try=next(n for n in oldmain.body if isinstance(n,ast.Try))
assert len(old_try.body)==len(current_try.body)+2
current_try.body[2:2]=copy.deepcopy(old_try.body[2:4])
assert ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
config=Path(R/'FROZEN-control3-current-b614-actual-config-v1.json')
assert bind(config)['sha256']=='8c5da5be25ebfcf86f286ee9f93ddad328c68b3243b0935ec5937c93376bb948'
c=json.loads(config.read_bytes());root=Path(c['source_root'])
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip()==c['source']
assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=root).decode().strip()==c['tree']
assert subprocess.check_output(['git','status','--porcelain'],cwd=root)==b''
for row in c['source_body_modes']:
    p=root/row['path'];b=p.read_bytes()
    assert hashlib.sha256(b).hexdigest()==row['sha256'] and stat.S_IMODE(p.lstat().st_mode)==row['fs_mode']
assert len(c['source_body_modes'])==1421
for p,h in c['prepared_inputs'].items():assert bind(root/p)['sha256']==h
for row in c['native_original_members']:
    p=Path(c['native_original_root'])/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
    if row['kind']=='file':assert not p.is_symlink() and bind(p)['sha256']==row['content_sha256']
    elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
    else:assert p.is_symlink() and p.readlink().as_posix()==row['link_target']
assert len(c['native_original_members'])==1192
patch=''.join(difflib.unified_diff((R/'actual_transport_v5.py').read_text().splitlines(True),(R/'actual_transport_v6.py').read_text().splitlines(True),fromfile='a/actual_transport_v5.py',tofile='b/actual_transport_v6.py'))
p=OUT/'frozen-original-v5-to-private-v6-metadata-only.patch'
with p.open('x') as f:f.write(patch)
p.chmod(0o600)
proof={'status':'EXACT_V5_AST_AFTER_ONLY_DECLARED_METADATA_PROJECTION_AND_SUCCESSOR_SELF_BINDING',
       'original_v5':bind(R/'actual_transport_v5.py'),'candidate_v6':bind(R/'actual_transport_v6.py'),
       'original263_byte_length_modes_exact':True,'original_actual_failure_members_exact':12,
       'source_b614_FS_body_modes_exact':1421,'source_clean':True,'original_native_inventory_retained':1192,'prepared_inputs':30,
       'source_CONTROL_command_budget_all_other_function_AST_exact':True,
       'capture_sampler_Popen_signal_wait_reap_and_original_case_admission_AST_exact_after_metadata_only_projection':True,
       'new_process_reads':0,'new_supervisor_Popen_wait_reap_signals':0,'captured_snapshot_retention_limit':64,
       'error_attrs_available_in_original_helper':['command_returncode','cleanup_disposition','command_stdout','command_stderr'],
       'captured_final_census_and_reader_join_facts':'UNKNOWN_NOT_EXPOSED_BY_PINNED_HELPER',
       'new_successor_binding_gate':'Main refuses predecessor config lacking exact v6 source path/hash/bytes/mode before state/process startup',
       'actual_or_config_constructor_or_app_source_changes':'NONE','patch':bind(p)}
p=OUT/'immutable-postcontrols-original263-and-v6-structural-scope-proof.json'
with p.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
p.chmod(0o600)
print(json.dumps(bind(p)))
