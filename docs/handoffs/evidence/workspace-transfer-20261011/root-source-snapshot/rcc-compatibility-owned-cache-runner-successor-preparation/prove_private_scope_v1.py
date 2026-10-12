"""Readonly AST/body preservation proof, not a qualification/native launch."""
import ast
import copy
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).parent
OLD = Path('/workspace/engineering/rcc-compatibility-actual-runner-readonly-preparation')


def dump(node): return ast.dump(node, include_attributes=False)


def main():
    old = ast.parse((OLD/'actual_transport_v6.py').read_bytes())
    new = ast.parse((ROOT/'actual_transport_v7.py').read_bytes())
    before = {n.name: n for n in old.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    after = {n.name: n for n in new.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    identical = []
    for name, node in before.items():
        if name in {'main', 'read_bound', 'require_release'}: continue
        assert dump(node) == dump(after[name]), name
        identical.append(name)
    original_release = copy.deepcopy(after['_require_original_release']); original_release.name = 'require_release'
    assert dump(original_release) == dump(before['require_release'])
    reader = copy.deepcopy(after['read_bound'])
    reader.body = [n for n in reader.body if not isinstance(n, ast.If)]
    assert dump(reader) == dump(before['read_bound'])
    main = copy.deepcopy(after['main'])
    removed = []
    for node in list(main.body):
        text = ast.unparse(node)
        if (isinstance(node, ast.Expr) and ('INHERITED_OPERATOR_CACHE_CONFIG' in text or text.startswith('cache_plan('))) \
           or (isinstance(node, ast.Assign) and 'ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG' in text):
            main.body.remove(node); removed.append(text)
        if isinstance(node, ast.FunctionDef) and node.name == 'guard':
            for inner in list(node.body):
                if isinstance(inner, ast.If) and 'validate_created_cache(' in ast.unparse(inner):
                    node.body.remove(inner); removed.append(ast.unparse(inner))
    assert len(removed) == 4
    assert dump(main) == dump(before['main'])
    source = '/workspace/engineering/pr308'
    head = subprocess.check_output(['git','-C',source,'rev-parse','HEAD'],text=True).strip()
    tree = subprocess.check_output(['git','-C',source,'rev-parse','HEAD^{tree}'],text=True).strip()
    assert head == 'e4ff080375a8422bb656e52d218f198521dda078' and tree == '973ff38f49a17a896e4d90f829a72e2ea0ea15e8'
    assert not subprocess.check_output(['git','-C',source,'status','--porcelain'],text=True)
    fixture = 'action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'
    older = ast.parse(subprocess.check_output(['git','-C',source,'show','b614864ba9da55c13662894b6ef3c8515d9fdb25:'+fixture]))
    current = ast.parse((Path(source)/fixture).read_bytes())
    names = ['test_published_artifact_details_preserves_one_rcc_identity_pair', 'test_staged_package_executes_in_managed_rcc_runtime']
    for name in names:
        a = next(n for n in older.body if isinstance(n,ast.FunctionDef) and n.name == name)
        b = copy.deepcopy(next(n for n in current.body if isinstance(n,ast.FunctionDef) and n.name == name))
        inserted = [n for n in b.body if isinstance(n,ast.If) and '_prepare_owned_rcc_test_package_cache(' in ast.unparse(n)]
        assert len(inserted) == 1
        b.body = [n for n in b.body if n not in inserted]
        assert dump(a) == dump(b), name
    copies = {}
    for name in ('fixture_records_v2.py','owned_monitor_v1.py','runner_contracts_v3.py','managed_metadata_only_preflight.py','actual_transport_v6.py'):
        raw = (ROOT/name).read_bytes(); assert raw == (OLD/name).read_bytes()
        copies[name] = hashlib.sha256(raw).hexdigest()
    for path in ROOT.glob('*.py'): compile(path.read_bytes(),str(path),'exec')
    cfg = json.loads((ROOT/'FROZEN-current-e4ff-control3-cache-config-CONDITIONAL-v3.json').read_bytes())
    assert cfg['source'] == head and cfg['tree'] == tree and len(cfg['source_body_modes']) == 1423
    for row in cfg['bindings']:
        if row['path'].startswith(str(ROOT)+'/'):
            path = Path(row['path']); raw = path.read_bytes()
            assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
            assert stat.S_IMODE(path.stat().st_mode) == int(row['mode'],8)
    result = {'status':'READONLY_SCOPE_PROOF_PASS', 'source':head,'tree':tree,
              'original_transport_functions_classes_exact':identical,
              'original_release_body_exact_after_name_normalization':True,
              'original_main_AST_exact_except_four_cache_wiring_additions':removed,
              'original_read_bound_exact_except_fixed_historical_alias':True,
              'original_two_fixture_functions_AST_exact_except_guarded_cache_helper':names,
              'exact_dependency_copies':copies,'conditional_config_current_source_rows':1423,
              'current_source_full':'NOT_RUN_NOT_INHERITED_FROM_B614','native_or_gateway_run':False}
    target = ROOT/'private-scope-and-current-config-proof.json'
    fd = os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as stream: json.dump(result,stream,sort_keys=True,indent=2); stream.write('\n')
    print('PASS_READONLY_PRIVATE_SCOPE_AND_CURRENT_E4FF_SOURCE_CONFIG')


if __name__ == '__main__': main()
