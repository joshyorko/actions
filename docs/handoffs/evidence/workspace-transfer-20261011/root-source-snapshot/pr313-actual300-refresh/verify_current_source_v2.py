"""Read-only exact current-union guards; no gateway/native execution."""
import ast
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path('/workspace/engineering/captured-child-cleanup')
OUT = Path('/workspace/engineering/pr313-actual300-refresh')
HEAD = '12dd3ec5c4d2a582b192ba11c5f13736757aba16'
TREE = 'd3428cf69580a4ee252b5ad4f251588b837937d0'
OLD = '499a83d802ca9a0e2ebe3d77071af10625879297'
TARGET = 'e3c29cde8878307912e55ed09b6436c0f91d06d5'
ORIGINAL_BINDINGS = OUT/'original499-complete-retained-bindings-before-refresh.json'
OWN = Path('/workspace/engineering/captured-child-cleanup-light-owned/checked-own30-and-five-origins.json')


def bind(path):
    p=Path(path); b=p.read_bytes()
    return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def entries(revision, paths=()):
    result={}
    for record in git('ls-tree','-r','-z',revision,'--',*paths).split(b'\0'):
        if record:
            meta,p=record.split(b'\t',1);mode,kind,blob=meta.decode().split()
            result[p.decode()]={'mode':mode,'kind':kind,'blob':blob}
    return result


def check():
    assert git('rev-parse','HEAD').decode().strip()==HEAD
    assert git('rev-parse','HEAD^{tree}').decode().strip()==TREE
    assert git('show','-s','--format=%P',HEAD).decode().split()==[OLD,TARGET]
    assert git('status','--porcelain')==b''
    assert git('merge-tree','--write-tree',OLD,TARGET).decode().strip()==TREE
    current,old,target=entries(HEAD),entries(OLD),entries(TARGET)
    assert set(old)|set(target)==set(current)
    guide='docs/skills/repository-operations.md'
    for p,row in current.items():
        if p!=guide: assert row==old.get(p) or row==target.get(p),p
    original_delta=['action_server/src/actions/server/_common/process.py',
                    'action_server/tests/action_server_tests/common_tests/test_captured_process_tree_deadline.py',guide]
    assert git('diff','--name-only',TARGET,HEAD).decode().splitlines()==original_delta
    for p in original_delta[:2]: assert current[p]==old[p]
    oldlesson=git('diff','--unified=0',OLD+'^',OLD,'--',guide).decode()
    newtext=(ROOT/guide).read_text()
    additions=[l[1:] for l in oldlesson.splitlines(True) if l.startswith('+') and not l.startswith('+++')]
    assert ''.join(additions) in newtext
    target_delta=git('diff','--unified=0',OLD+'^',TARGET,'--',guide).decode()
    target_additions=[l[1:] for l in target_delta.splitlines(True) if l.startswith('+') and not l.startswith('+++')]
    assert ''.join(target_additions) in newtext
    source=[]
    for p,row in current.items():
        path=ROOT/p;s=path.lstat();b=git('cat-file','blob',row['blob'])
        if row['mode']=='120000': assert stat.S_ISLNK(s.st_mode);actual=os.readlink(path).encode()
        else:
            assert stat.S_ISREG(s.st_mode)
            assert ('100755' if s.st_mode&stat.S_IXUSR else '100644')==row['mode'],p
            actual=path.read_bytes()
        assert actual==b,p
        source.append({'path':p,**row,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    refs=json.loads(ORIGINAL_BINDINGS.read_bytes())['bindings']
    historical_guide_snapshot=OUT/'original499-tracked-guide-exact-Git-snapshot.md'
    for row in refs:
        if row['path']==str(ROOT/guide):
            original=git('show',OLD+':'+guide)
            assert len(original)==row['bytes'] and hashlib.sha256(original).hexdigest()==row['sha256']
            assert historical_guide_snapshot.read_bytes()==original
        else: assert bind(row['path'])==row,row['path']
    own=json.loads(OWN.read_bytes())
    for p,h in own['inputs_sha256'].items(): assert bind(ROOT/p)['sha256']==h,p
    for row in own['origins']:
        assert bind(row['path'])==row
        o=json.loads(Path(row['path']).read_bytes());prefix=Path(o['resolved_prefix']);package=prefix.parent.name
        assert (ROOT/package/'.venv').resolve()==prefix
        assert Path(o['origin']).resolve().is_relative_to(ROOT/package/'src')
        env=json.loads((OWN.parent/f'prepared-environment-{package}.private.json').read_bytes())
        for relative in ['pyvenv.cfg',*[r['relative'] for r in env['path_only_rebindings']]]:
            item=env['own_complete_inventory'][relative];p=prefix/relative
            assert stat.S_IMODE(p.lstat().st_mode)==item['mode']
            assert bind(p)['sha256']==item['sha256']
    for p,mode in [(Path('/workspace/actions-cloud/bin/rcc'),0o700),(ROOT/'action_server/src/actions/server/bin/rcc-18.19.3',0o711)]:
        assert bind(p)['sha256']=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
        assert stat.S_IMODE(p.stat().st_mode)==mode
    native=Path('/workspace/engineering/pr310-runner-qualification-owned')
    inventory=json.loads((native/'output/native-artifact-tree-inventory.json').read_bytes())
    assert len(inventory)==1192
    for row in inventory:
        p=native/'dist/action-server'/row['path'];mode=p.lstat().st_mode
        assert stat.S_IMODE(mode)==row['mode']
        if row['kind']=='directory':assert stat.S_ISDIR(mode)
        elif row['kind']=='symlink':
            assert stat.S_ISLNK(mode) and os.readlink(p)==row['link_target']
            assert bind(p)['sha256']==row['content_sha256']
        else:
            assert stat.S_ISREG(mode) and bind(p)['sha256']==row['content_sha256']
    helpers=json.loads(Path('/workspace/actions-cloud/receipts/pr305-runner/frozen-helper-bindings.json').read_bytes())
    for row in helpers.values():
        p=Path(row['snapshot_path']);assert bind(p)['sha256']==row['sha256'] and stat.S_IMODE(p.stat().st_mode)==0o444
    module=ROOT/'action_server/scripts/verify_frozen_catalog_harness.py'
    inputs=next(ast.literal_eval(n.value) for n in ast.parse(module.read_text()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='INPUT_PATHS' for t in n.targets))
    production=entries(HEAD,inputs);nativeproduction=entries('92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e',inputs)
    tests=json.loads((ROOT/'docs/program/evidence/runtime-frozen-current-source-20261011/selected-test-inventory.json').read_bytes())
    selected=entries(HEAD,tuple(tests));assert len(selected)==5
    return {'head':HEAD,'tree':TREE,'ordered_parents':[OLD,TARGET],
            'status':'CURRENT_SOURCE_UNION_AND_PRESERVATION_PASS',
            'complete_source':source,'complete_source_count':len(source),'old_parent_count':len(old),'target_count':len(target),
            'complete_auto_union_no_novel_child':True,'original_three_cleanup_deltas_retained':original_delta,
            'both_parent_exact_guide_lessons_retained':True,'original_bindings':len(refs),
            'prepared_inputs':len(own['inputs_sha256']),'five_retained_own_origin_bindings':own['origins'],
            'native_inventory_retained':len(inventory),'helper_snapshots_retained':len(helpers),
            'producer_count':len(production),'original_native_producer_count':len(nativeproduction),
            'native_changed_original_paths':[p for p in nativeproduction if production.get(p)!=nativeproduction[p]],
            'native_added_paths':sorted(set(production)-set(nativeproduction)),
            'selected_tests_count':len(selected),'selected_inputs':selected,
            'native_qualification':'UNQUALIFIED_NO_CURRENT_ARTIFACT_NATIVE_EXECUTION',
            'capacity_observation_only':os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize}


if __name__=='__main__':
    import sys
    p=Path(sys.argv[1]);r=check()
    with p.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    p.chmod(0o600)
    print(json.dumps({k:v for k,v in r.items() if k in ('status','head','tree','complete_source_count','producer_count','original_bindings','capacity_observation_only')}))
