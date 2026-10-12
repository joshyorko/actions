import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

BASE=Path('/workspace/engineering/pr308-owned-package-cache-private-source')
REPO=Path('/workspace/engineering/pr308')
SOURCE='b614864ba9da55c13662894b6ef3c8515d9fdb25'
TREE='6fa4f5c1e9837a0d893868255575b355b3977fae'
ENV=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
def git(*args):
    return subprocess.check_output(['git','-C',str(REPO),*args],env=ENV,stderr=subprocess.PIPE)
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()
def ref(path):
    p=Path(path); assert p.is_file()
    return {'path':str(p),'sha256':digest(p),'bytes':p.stat().st_size,'mode':oct(p.stat().st_mode&0o777)}
def dump(node): return ast.dump(node,include_attributes=False)
index=Path(git('rev-parse','--path-format=absolute','--git-path','index').decode().strip())
index_before=ref(index)
assert git('rev-parse','HEAD').decode().strip()==SOURCE
assert git('rev-parse','HEAD^{tree}').decode().strip()==TREE
assert git('status','--porcelain','--untracked-files=no')==b''
leaves=[]
for row in git('ls-tree','-rz','HEAD').split(b'\0'):
    if not row: continue
    meta,name=row.split(b'\t'); mode,kind,oid=meta.decode().split(); path=REPO/os.fsdecode(name)
    if mode=='120000': body=os.fsencode(os.readlink(path)); assert path.is_symlink()
    else:
        assert path.is_file() and not path.is_symlink(); body=path.read_bytes()
        assert bool(path.stat().st_mode&0o111)==(mode=='100755')
    observed=hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
    assert observed==oid,(name,observed,oid)
    leaves.append({'path':os.fsdecode(name),'git_mode':mode,'git_blob':oid,'body_sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)})
assert len(leaves)==1421
inventory=BASE/'private-original-b614-complete-tracked-body-mode-inventory.json'
assert not inventory.exists(); inventory.write_text(json.dumps(leaves,sort_keys=True)+'\n');inventory.chmod(0o600)
paths={'original-test_source_staging_rcc_consumer.py':'action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py','original-repository-operations.md':'docs/skills/repository-operations.md'}
for local,tracked in paths.items(): assert (BASE/local).read_bytes()==git('show',SOURCE+':'+tracked)
old=ast.parse((BASE/'original-test_source_staging_rcc_consumer.py').read_text())
new=ast.parse((BASE/'test_source_staging_rcc_consumer.py').read_text())
olddefs={n.name:n for n in old.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
newdefs={n.name:n for n in new.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
selected={'test_published_artifact_details_preserves_one_rcc_identity_pair','test_staged_package_executes_in_managed_rcc_runtime'}
removed=[]
for name,node in olddefs.items():
    candidate=copy.deepcopy(newdefs[name])
    if name in selected:
        kept=[]
        for child in candidate.body:
            if isinstance(child,ast.If) and 'ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG' in ast.unparse(child.test):
                assert not child.orelse and len(child.body)==1
                call=child.body[0]; assert isinstance(call,ast.Expr) and isinstance(call.value,ast.Call)
                assert isinstance(call.value.func,ast.Name) and call.value.func.id=='_prepare_owned_rcc_test_package_cache'
                expected="os.environ.get('ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG') is not None"
                assert ast.unparse(child.test)==expected
                removed.append(name)
            else: kept.append(child)
        candidate.body=kept
    assert dump(candidate)==dump(node),name
assert set(removed)==selected and len(removed)==2
oldother=[n for n in old.body if not isinstance(n,(ast.FunctionDef,ast.ClassDef))]
newother=[n for n in new.body if not isinstance(n,(ast.FunctionDef,ast.ClassDef))]
assert [dump(n) for n in oldother]==[dump(n) for n in newother]
newtests=[n for n in new.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_owned_rcc_package_cache')]
assert len(newtests)==5
for n in newtests:
    assert all('integration' not in ast.unparse(d) and 'real_rcc' not in ast.unparse(d) for d in n.decorator_list)
def junit(name):
    root=ET.parse(BASE/name).getroot(); cases=root.findall('.//testcase')
    failures=[n.find('failure') for n in cases if n.find('failure') is not None]
    return {'cases':len(cases),'pass':sum(n.find('failure') is None and n.find('error') is None and n.find('skipped') is None for n in cases),'fail':len(failures),'error':len(root.findall('.//error')),'skip':len(root.findall('.//skipped')),'DID_NOT_RAISE':sum('DID NOT RAISE' in (f.get('message') or '') for f in failures),'FileExistsError':sum('FileExistsError' in (f.get('message') or '') for f in failures)}
red=junit('RED-v2-junit.xml');scalar=junit('marker-scalar-RED-junit.xml');green=junit('final-v3-private-GREEN-junit.xml')
assert red=={'cases':31,'pass':1,'fail':30,'error':0,'skip':0,'DID_NOT_RAISE':29,'FileExistsError':1}
assert scalar['fail']==2 and scalar['pass']==32 and scalar['DID_NOT_RAISE']==2
assert green['pass']==34 and green['fail']==green['error']==green['skip']==0
assert json.loads((BASE/'final-v3-static-terminal.json').read_text())['returncode']==0
log=(BASE/'final-v3-configured-private-static-and-controls.private.log').read_text()
assert 'Success: no issues found in 1 source file' in log
check=subprocess.run(['git','-C',str(REPO),'apply','--check',str(BASE/'owned-package-cache-two-path.patch')],env=ENV,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
assert check.returncode==0
proof={'original_functions_whole_AST_preserved_when_explicit_configuration_absent':len(olddefs),'exact_original_module_nonfunction_AST':True,'only_two_guarded_call_insertions':sorted(removed),'permanent_new_linux_servicefree_cases':34,'original_integration_marks_and_selectors_whole_AST_unchanged':True,'positive_mount_spy':'exact forwarding call once with original args and return','negative_mount_spy':'no attempted mount for all 33 poison cases','complete_original_b614_tracked_git_body_and_mode_bindings':len(leaves),'read_only_git_apply_check':0}
proofpath=BASE/'default-fixture-and-original-source-preservation-proof.json';assert not proofpath.exists();proofpath.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');proofpath.chmod(0o600)
external=[
 '/workspace/engineering/root-rcc-compatibility-control3-one-actual/OWNERFINAL-root-one-control3-terminal.json',
 '/dev/shm/actions-rcc-compatibility-actual-control3-20261011-1/OWNERFINAL-one-version-actual-result.json',
 '/workspace/engineering/rcc-control3-owned-capacity-fixture-diagnosis/private-current-retained-state-inode-and-cache-pair-inventory.json',
 '/workspace/engineering/pr308-rcc-compatibility-source/OWNERFINAL-current-a0d-approved-RCC-compatibility-SOURCE-LIGHT.json',
 '/workspace/engineering/pr308-compatibility-current-sourcefull-independent-actual-review/OWNERFINAL-independent-current-b614-configured-SOURCEFULL-review.json',
 '/dev/shm/actions-rcc-compatibility-originals-20261011/OWNERFINAL-three-original-RCC-acquisition-data-qualification.json',
 '/workspace/engineering/rcc-original-acquisition-independent-review/OWNERFINAL-independent-three-original-RCC-acquisition-data-review.json',
 '/workspace/engineering/root-two-exact-approved-test-only-binary-copies.json',
 '/workspace/engineering/pr308-persistent-fixture-private-source/OWNERFINAL-private-current-b614-persistent-fixture-two-path-source-patch.json',
 '/workspace/actions-cloud/receipts/pr305-runner/frozen-helpers/verify_dakota_rcc_acceptance.py']
assert digest(Path(external[0]))=='72cb3d7fb9ff99386f2c9e2a8d43282ec77ac609d1eb813543d23a6596047697'
assert digest(Path(external[1]))=='8dc25bb1b99503af386d12d32c0637aa3503617c6f97d66a83f4643969934d4c'
assert digest(Path(external[2]))=='68d9171528bfa54ff69fcf4c1ea1ea1b2627d0dedabcd5538a2f353e5152260d'
references=[ref(p) for p in sorted(BASE.iterdir()) if p.is_file()]+[ref(p) for p in external]
assert ref(index)==index_before
assert git('status','--porcelain','--untracked-files=no')==b''
assert git('rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[SOURCE,TREE]
owner={
 'schema':1,'disposition':'GO_PRIVATE_PATCH_FOR_INDEPENDENT_SOURCE_REVIEW_ONLY','source':{'commit':SOURCE,'tree':TREE,'tracked_leaves':1421,'checkout_index_before_and_after':index_before,'branch_ref_unchanged':True},
 'scope':{'patch_paths':list(paths.values()),'applied_to_checkout':False,'actual_rcc_execution':'NOT_RUN','default_behavior':'whole original fixture AST preserved with explicit cache config absent','production_toolkit_pin_helper_native_browser':'UNCHANGED','original_b614_full':'HISTORICAL_UNCHANGED_NOT_NEW_PATCH_FULL'},
 'tests':{'unchecked_guard_sensitivity_RED':red,'first_marker_scalar_guard_RED':scalar,'final_permanent_controls_GREEN':green,'configured_static':{'Ruff':'PASS','format':'PASS','Isort':'PASS','Mypy_private_fixture_file':'PASS'},'original_first_launch':'SETUP_FAIL_BEFORE_PYTEST_PRESERVED','collection':'34 permanent new unmarked tests collected by Linux nonintegration suite after application; own synthetic /dev/shm fixture skips these new POSIX controls outside Linux, no original native selector or marks altered','spy':'same original Path.symlink_to forwarding once for valid stage; zero attempts for each poisoned guard'},
 'operator_interface':{'environment_key':'ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG','config_keys':['schema','runtime_source_sha','runtime_source_tree','label','binary_sha256','state_root','package_cache_root','state_marker_sha256'],'config_schema':'exact integer 1, duplicate/unknown keys rejected','marker':'seven config identity fields excluding marker SHA; fixed 0600 file beneath version-owned 0700 root; exact digest before mount','source_identity':'40-character Git candidate SHA/tree, not runner digest','shared_only':'once-owned actions-home/pkgs; no holotree/artifacts/provider sharing','cold_scope':'first publication package cache empty; staged package cache warm from that same publication','cross_version':'source/binary/label/root prefix/receipt all bound before mount','future_runner_config':'NOT_WIRED; distinct reviewed config/transport successor and original publication proof required'},
 'original_failed_actual':{'label':'control3','primary':'CAPACITY_THRESHOLD','sampled_max_bytes':2529735510,'operational_stop_bytes':2523293286,'hard_admission_bytes':2576980377,'cleanup':'FAIL ProcessTreeCleanupError','publication_case':'PASS','staged_case':'STARTED_NO_TERMINAL','released5':'STOP_NOT_RUN','candidate7276':'STOP_NOT_RUN','observed_terminated_pytest_pid':564683,'other_helper_descendant_identities':'UNAVAILABLE_IN_V5','current_pid_absence':'OBSERVATION_ONLY_NOT_HISTORICAL_CLEANUP_PROOF','original_log_receipts_state':'RETAINED_UNMODIFIED'},
 'capacity_diagnosis':{'retained_current_logical_bytes':2775060974,'retained_current_entries':49131,'duplicate_repodata_pair_bodies':4,'duplicate_repodata_bytes':954086630,'counterfactual_single_copy_logical_bytes':1820974344,'provider_roots_separate_and_small':True,'limitations':['Current retained-state measurement is not original sampled peak.','Reduction is prospective, not a guarantee of future peak or RCC symlink support.','Sampler threshold/hard budget/cleanup admission unchanged.','No RCC version incompatibility conclusion.']},
 'documentation_improvement':{'canonical_file_proposed':'docs/skills/repository-operations.md','exact_delta':'11-line addition adjacent to staged worker lease evidence; share only admitted same-version pkgs, retain per-case roots and cold first/warm second boundary, no peak/compatibility inference','evidence':['exact original publication inherited actions-home and staged fresh managed-home source','four original equal distinct-inode repodata pairs','34 permanent actual helper guard/mount forwarding controls'],'stale_or_ambiguous_guidance_removed':'Clarifies package-cache warmth separately from per-case Holotree/provider isolation and whole cold-install claims; no earlier receipt relabeled.','remaining_uncertainty':'RCC symlink compatibility and actual capacity/cleanup behavior require a separately reviewed successor source/full/transport and once-only actual.'},
 'remaining_holds':['Independent private-patch source review.','Root application/composition with persistent patch on announced successor source.','New exact source FULL and reviewed immutable operator/transport successor.','No original native producer qualification upgrade.','No new 5/6 functional, internal-reader, provider recovery/reload/drain/private/full134/135/release qualification.'],
 'upstream_disposition':'none','references':references}
out=BASE/'OWNERFINAL-private-current-b614-owned-package-cache-two-path-source-patch.json';assert not out.exists();out.write_text(json.dumps(owner,indent=2,sort_keys=True)+'\n');out.chmod(0o600)
print(json.dumps({'owner_final':str(out),'sha256':digest(out),'bytes':out.stat().st_size,'references':len(references),'patch':ref(BASE/'owned-package-cache-two-path.patch'),'source_head':SOURCE,'source_tree':TREE,'new_controls':34,'status':'PRIVATE_NOT_APPLIED'}))
