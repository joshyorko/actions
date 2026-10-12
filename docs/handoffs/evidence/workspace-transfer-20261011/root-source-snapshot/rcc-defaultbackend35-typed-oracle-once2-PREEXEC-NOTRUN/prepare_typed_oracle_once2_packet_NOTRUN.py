"""Named stdlib-only control preparation. No module/test imports or execution."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

B=Path('/workspace/engineering/rcc-defaultbackend35-typed-oracle-once2-PREEXEC-NOTRUN')
OLD=Path('/workspace/engineering/rcc-defaultbackend35-concrete-PREEXEC-NOTRUN')
DIAG=Path('/workspace/engineering/rcc-defaultbackend35-original-ACTUALFAIL-independent-diagnosis')
ROOT='/workspace/engineering/root-one-current8d49-default-cgroup-walk-pure-controls-2'
RELEASE='/workspace/engineering/root-one-defaultbackend35-typed-oracle-once2-pure-controls-release.json'

def row(path):
    p=Path(path);st=p.lstat();assert stat.S_ISREG(st.st_mode) and not p.is_symlink()
    raw=p.read_bytes()
    return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),mode=oct(stat.S_IMODE(st.st_mode)))

def put(name,value):
    p=B/name;raw=value if type(value) is bytes else (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o400)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return row(p)

diagnosis=row(DIAG/'OWNERFINAL-independent-original-defaultbackend35-ACTUALFAIL-and-typed-marker-proposal.json')
assert diagnosis['sha256']=='a4bca9580479e17321d29aa721df8f3faade600f422006b0c20c6d089761b3a8'
d=json.loads(Path(diagnosis['path']).read_text())
assert d['counts']==dict(errors=0,failed=1,passed=34,skipped=0,tests=35)
failureproof=json.loads(Path(d['independent_proof']['path']).read_text())
oldconfig=row(OLD/'FROZEN-defaultbackend35-concrete-config-NOTRUN.json')
assert oldconfig['sha256']=='727141f5bf2e87ffad42a16e4e6fb352c807c45e06be60f32af494ecc05ac5f6'
old=json.loads(Path(oldconfig['path']).read_text())
original=Path(old['controls']['path']);assert row(original)==old['controls']
oldraw=original.read_text()
oldblock="""    with pytest.raises(AssertionError, match='^DEFAULT_WALK_OPEN_DESCRIPTORS$'):
        default_snapshot(tree, audit)
    assert audit.omitted and not audit.active
"""
newblock="""    with pytest.raises(AssertionError) as caught:
        default_snapshot(tree, audit)
    assert type(caught.value) is AssertionError
    assert str(caught.value).splitlines()[0] == 'DEFAULT_WALK_OPEN_DESCRIPTORS'
    traceback = caught.value.__traceback__
    audit_frames = []
    while traceback is not None:
        if traceback.tb_frame.f_code is SyscallAudit.assert_closed.__code__:
            audit_frames.append(traceback.tb_frame)
        traceback = traceback.tb_next
    assert len(audit_frames) == 1 and audit_frames[0].f_locals.get('self') is audit
    assert audit.omitted and not audit.active
    closed_generations = {row['generation'] for row in audit.closed}
    unmatched = [row for row in audit.records if row['generation'] not in closed_generations]
    assert len(unmatched) == 1 and unmatched[0]['origin'] == 'dup'
"""
assert oldraw.count(oldblock)==1
newraw=oldraw.replace(oldblock,newblock)
controls=put(original.name,newraw.encode())
oldast=ast.parse(oldraw);newast=ast.parse(newraw)
name='test_descriptor_audit_detects_deliberately_suppressed_close_after_valid_baseline'
for node in newast.body:
    if isinstance(node,ast.FunctionDef) and node.name==name:
        replacement=next(n for n in oldast.body if isinstance(n,ast.FunctionDef) and n.name==name)
        node.body=replacement.body
assert ast.dump(oldast,include_attributes=False)==ast.dump(newast,include_attributes=False)
import difflib
patch=put('exact-one-control-typed-marker-traceback-posterior-successor.patch',''.join(difflib.unified_diff(oldraw.splitlines(True),newraw.splitlines(True),fromfile=str(original),tofile=controls['path'])).encode())
proof=put('typed-oracle-only-source-delta-and-sensitivity-contract-NOTRUN.json',dict(schema=1,status='STDLIB_AST_ONLY_SOURCE_PREPARED_NOT_EXECUTED',source=old['source'],tree=old['tree'],original_controls=old['controls'],successor_controls=controls,exact_patch=patch,whole_AST_outside_one_final_test_body_exact=True,reader_audit_backend_classes_helpers_other34_cases_exact=True,baseline_before_poison_exact=True,posterior_omitted_and_not_active_assertion_exact=True,original_ACTUALFAIL=diagnosis,original_measured_dup=dict(count=1,generation=4,origin='dup'),strengthened_expected_state='Exactly one recorded generation absent from audit.closed and origin dup; no assumed numeric FD, generation4 or kernel census.',typed_marker_source_predicates=['exact type is AssertionError (subclasses excluded)','first line equals fixed marker (substring/suffix/prefix excluded)','exact one frame whose code is SyscallAudit.assert_closed.__code__ and self is this audit','unchanged omitted and not active posterior; exactly one unmatched dup generation'],baseline_first_sensitivity=[dict(poison=p,expected_refusal=reason,execution='NOT_RUN') for p,reason in [('wrong exception/subclass','exact type'),('wrong first marker/substring','exact first line'),('generic marker assertion elsewhere','code identity'),('other audit instance','same self'),('missing suppression or active posterior','retained posterior assertion'),('zero/multiple/nondup unmatched generations','exact unmatched dup state')]],limits='Actual named35 outcomes require new separate ROOT execution. Posterior logical audit closure does not prove host-wide/kernel-FD census or native cleanup.'))

refs=old['frozen_bindings']+[oldconfig,row(OLD/'run_root_defaultbackend35_pure_once_NOTRUN.py'),row(OLD/'OWNERFINAL-defaultbackend35-concrete-managed-pure-PREEXEC-NOTRUN.json'),diagnosis,d['independent_proof'],d['minimum_source_proposal']]+failureproof['original_refs']+[controls,patch,proof]
unique={}
for r in refs:
    assert row(r['path'])==r
    if r['path'] in unique:assert unique[r['path']]==r
    unique[r['path']]=r
refs=list(unique.values())
assert not Path(ROOT).exists() and not Path(ROOT).is_symlink() and not Path(RELEASE).exists() and not Path(RELEASE).is_symlink()
launcher=Path(OLD/'run_root_defaultbackend35_pure_once_NOTRUN.py').read_text()
launcher=launcher.replace(str(OLD),str(B)).replace('FROZEN-defaultbackend35-concrete-config-NOTRUN.json','FROZEN-defaultbackend35-typed-oracle-once2-config-NOTRUN.json').replace('/workspace/engineering/root-one-defaultbackend35-pure-controls-release.json',RELEASE)
launcher=launcher.replace('ROOT_DISTINCT_ONE_DEFAULT_DESCRIPTOR35_PURE_CONTROLS','ROOT_DISTINCT_ONE_DEFAULT_DESCRIPTOR35_TYPED_ORACLE_ONCE2_PURE_CONTROLS')
launcher=launcher.replace('INDEPENDENT_DEFAULTBACKEND35_CONCRETE_PREEXECUTION_GO','INDEPENDENT_DEFAULTBACKEND35_TYPED_ORACLE_ONCE2_SOURCE_PREEXECUTION_GO')
launcher=launcher.replace("'controls_sha256':cfg['controls']['sha256']", "'controls_sha256':cfg['controls']['sha256'],'control_successor_proof_sha256':cfg['control_successor_proof']['sha256']")
ast.parse(launcher)
launch=put('run_root_defaultbackend35_typed_oracle_once2_NOTRUN.py',launcher.encode())
cfg=dict(old)
cfg.update(status='PREPARED_DEFAULTBACKEND35_TYPED_ORACLE_ONCE2_NOTRUN',root_once=ROOT,root_release_path=RELEASE,launcher=launch,controls=controls,control_successor_proof=proof,original_failed_diagnosis=diagnosis,frozen_bindings=refs,basetemp=ROOT+'/basetemp',logger=ROOT+'/logger',junit=ROOT+'/junit.xml',source_only='Original35 ACTUALFAIL34P1F preserved. Named one-oracle correction only; 35 new cases NOTRUN. Backend/source/helper unchanged. No realcgroup/native/profile adoption.')
cfg['pytest_argv']=[x.replace(str(original),controls['path']).replace(old['root_once'],ROOT) for x in old['pytest_argv']]
assert len(cfg['expected_case_names'])==len(set(cfg['expected_case_names']))==35
config=put('FROZEN-defaultbackend35-typed-oracle-once2-config-NOTRUN.json',cfg)
contractold=json.loads(Path(OLD/'ROOT-distinct-defaultbackend35-release-and-command-contract-NOTRUN.json').read_text())
contract=dict(contractold)
contract.update(status='TEMPLATE_ONLY_TYPED_ORACLE_ONCE2_SOURCE_AND_PREEXEC_GO_PLUS_ROOT_RELEASE_REQUIRED',config_binding=config,launcher_binding=launch,ROOT_release_path=RELEASE,ROOT_release_template=dict(schema=1,status='ROOT_DISTINCT_ONE_DEFAULT_DESCRIPTOR35_TYPED_ORACLE_ONCE2_PURE_CONTROLS',source=cfg['source'],tree=cfg['tree'],config_binding=config,launcher_binding=launch,source_owner_binding=cfg['source_owner'],source_independent_review=cfg['source_independent_review'],root=ROOT,serialized_no_other_heavy_or_storage_mutations=True,independent_preexecution_review=None),compatible_PREEXEC_required_fields=dict(schema=1,status='INDEPENDENT_DEFAULTBACKEND35_TYPED_ORACLE_ONCE2_SOURCE_PREEXECUTION_GO',source=cfg['source'],tree=cfg['tree'],config_sha256=config['sha256'],launcher_sha256=launch['sha256'],controls_sha256=controls['sha256'],control_successor_proof_sha256=proof['sha256']))
contract['ROOT_argv']=[x.replace(str(OLD/'run_root_defaultbackend35_pure_once_NOTRUN.py'),launch['path']).replace(oldconfig['path'],config['path']).replace(oldconfig['sha256'],config['sha256']).replace(old['root_release_path'],RELEASE) for x in contractold['ROOT_argv']]
contract['required_new_output_root']=ROOT
contract['original_consumed_attempt']='FAIL34PASS1FAIL; originalonce1/release consumed, never reused'
contract=put('ROOT-distinct-typed-oracle-once2-release-and-concrete-command-contract-NOTRUN.json',contract)
git=lambda *args:subprocess.check_output(['git','-C','/workspace/engineering/pr308',*args]).decode().strip()
assert git('rev-parse','HEAD')==cfg['source'] and git('rev-parse','HEAD^{tree}')==cfg['tree'] and not git('status','--porcelain','--untracked-files=no')
local=[row(p) for p in sorted(B.iterdir()) if p.is_file()]
owner=put('OWNERFINAL-defaultbackend35-typed-oracle-once2-SOURCE-and-PREEXEC-NOTRUN.json',dict(schema=1,status='NAMED_TYPED_ORACLE_ONCE2_SOURCE_AND_CONCRETE_PREEXEC_PREPARED_NOTRUN',source=cfg['source'],tree=cfg['tree'],source_count=1440,source_clean=True,controls_binding=controls,source_delta_proof=proof,patch_binding=patch,config_binding=config,launcher_binding=launch,contract_binding=contract,original_ACTUALFAIL=diagnosis,all_local_bindings=local,all_original_bindings=refs,tests_imports_native_cgroup_signals='NOT_RUN',future35census='19functions35expandedcases; originalnames unchanged; zeroFAIL/ERROR/SKIP plus true stdout and JUnit census required',outputs_and_ROOTrelease='FRESH_ONCE2_ABSENT',bounds=cfg['budgets'],documentation_improvement=d['documentation_improvement'],canonical_disposition='Reuse exact installed assertion-emitter versus semantic-marker and8366/d6c/8c28 existing lessons; no cosmetic paragraph. Typed/source/state oracle strengthening statically specified, actual35 stillNOTRUN.',writer_A='RELEASED_AFTER_FREEZE',upstream_disposition='none',captured=datetime.datetime.now(datetime.timezone.utc).isoformat()))
for r in refs+local:assert row(r['path'])==r
print(json.dumps(owner))
