import hashlib,json,os,stat,subprocess,sys,shutil
from pathlib import Path
def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        info = path.lstat()
        entry = {'mode': stat.S_IMODE(info.st_mode), 'mtime_ns': info.st_mtime_ns,
                 'uid': info.st_uid, 'gid': info.st_gid}
        if stat.S_ISREG(info.st_mode):
            entry.update(kind='file', bytes=info.st_size, sha256=sha(path))
        elif stat.S_ISLNK(info.st_mode):
            entry.update(kind='symlink', target=os.readlink(path))
        elif stat.S_ISDIR(info.st_mode):
            entry.update(kind='directory')
        elif stat.S_ISFIFO(info.st_mode):
            entry.update(kind='fifo')
        else:
            raise RuntimeError('Nonarchivable type: ' + str(path))
        result[str(path.relative_to(root))] = entry
    return result

def _snapshot(root):
    entries = inventory(root)
    info = root.lstat()
    root_info = {k: getattr(info, 'st_' + k) for k in ('uid', 'gid', 'mtime_ns', 'dev', 'ino', 'nlink')}
    root_info['mode'] = stat.S_IMODE(info.st_mode)
    identities = {}
    groups = {}
    for relative in entries:
        s = (root / relative).lstat()
        identities[relative] = (s.st_dev, s.st_ino, s.st_nlink)
        if stat.S_ISREG(s.st_mode):
            groups.setdefault((s.st_dev, s.st_ino), []).append(relative)
    for relatives in groups.values():
        assert all(identities[r][2] == len(relatives) for r in relatives), 'EXTERNAL_HARDLINK_REFUSED'
    return {'root': root_info, 'entries': entries, 'identities': identities}

def exact(row):
 p=Path(row['path']); assert p.is_file() and not p.is_symlink()
 assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode']
_COMPLETION_CONFIG=Path('/workspace/engineering/completed-current8d49-FULL-scratch-storage-PREEXECUTION-v1/private-exact-one-completed-FULL-scratch-inputs.json')
_COMPLETION_BINDING={'path': '/workspace/engineering/completed-current8d49-FULL-scratch-storage-PREEXECUTION-v1/private-exact-one-completed-FULL-scratch-inputs.json', 'bytes': 9378479, 'sha256': '1ef448b2ee0b2b00462c516a096c858287f5d117d2f43171b9f679c75b9206ee', 'mode': '0o444'}
NAMES=['completed-FULL-once-1']

def load_config(path):
    assert Path(path)==_COMPLETION_CONFIG
    assert sha(Path(path))==_COMPLETION_BINDING['sha256']
    assert Path(path).stat().st_size==_COMPLETION_BINDING['bytes'] and not Path(path).is_symlink()
    assert oct(stat.S_IMODE(Path(path).stat().st_mode))==_COMPLETION_BINDING['mode']
    config=json.loads(Path(path).read_bytes())
    assert set(config['roots'])==set(NAMES) and len(config['roots'])==1
    return config

def protected(config, *, phase, capture_parent):
 for row in config['references']+config['completion_bindings']+[config['source_guard'],config['source_guard_inputs']]:exact(row)
 assert not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE')
 assert 'PYTEST_ADDOPTS' not in os.environ
 code=json.loads(Path(config['source_guard_inputs']['path']).read_bytes())
 for key,value in code['expected_activation_exports'].items():assert os.environ.get(key)==value
 assert len(code['expected_activation_exports'])==18 and os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
 managed=Path(code['cached_toolkit_prefix'])/'bin/python';assert Path(sys.prefix).resolve()==managed.parent.parent.resolve()
 assert os.environ['PATH'].split(os.pathsep)[1]==str(managed.parent),'CACHED_TOOLKIT_PATH1_REQUIRED'
 assert Path(shutil.which('poetry') or '').absolute()==managed.parent/'poetry','CACHED_TOOLKIT_POETRY_REQUIRED'
 assert Path(capture_parent)==Path('/workspace/engineering/root-completed-current8d49-FULL-scratch-storage-one-owned-v1')
 helper=Path('/workspace/engineering/completed8d49-four-root-storage-PREPARATION-v3/guard_capture.py');assert sha(helper)=='7ce1b282a002fbf03371ba0b1c5ba1684253ee68ffcf234f16e58e7902860c2a' and oct(stat.S_IMODE(helper.stat().st_mode))=='0o444' and not helper.is_symlink()
 namespace={'__name__':'verified_private_guard_capture'};exec(compile(helper.read_bytes(),str(helper),'exec'),namespace)
 plan_path=Path('/workspace/engineering/completed8d49-five-root-storage-PREPARATION-v5/private-fixed-nine-original-row-future-archive-member-plan.json');assert sha(plan_path)=='ce099428e2647c6793d3f1d2bc541d5b864c58ebffe40371007cc7d7ac3236e8' and not plan_path.is_symlink()
 alias_path=Path('/workspace/engineering/completed8d49-five-root-storage-PREPARATION-v4/exact_original_row_archive_aliases.py');assert sha(alias_path)=='fdbe4493f59c0256c4ca63f0da390c71d2a1d6c98dfc9f8d4cc0b5187561712e' and oct(stat.S_IMODE(alias_path.stat().st_mode))=='0o444' and not alias_path.is_symlink()
 aliasns={'__name__':'verified_fixed_original_row_alias'};exec(compile(alias_path.read_bytes(),str(alias_path),'exec'),aliasns)
 plan=json.loads(plan_path.read_bytes());plan['_verified_plan_sha256']=sha(plan_path)
 aliases=aliasns['validate_original_rows_or_alias'](plan)
 actual,capture=namespace['captured_guard_call']([str(managed),config['source_guard']['path'],config['source_guard_inputs']['path'],'after'],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},cwd=code['source_root'],phase=phase,capture_parent=capture_parent)
 return {'status':'PASS_DATA_ONLY_CURRENT8D49_1440_ORIGINAL237_NATIVE1192_PREPARED30_FIVE_ORIGINS','metadata_stdout_bytes':len(actual.stdout),'metadata_stdout_sha256':hashlib.sha256(actual.stdout).hexdigest(),'stderr_bytes':len(actual.stderr),'stderr_sha256':hashlib.sha256(actual.stderr).hexdigest(),'source_native_qualification':'UNCHANGED'}
def _completion_admitted(root):
    config=load_config(_COMPLETION_CONFIG)
    assert root==Path(config['roots'][NAMES[0]]) and not root.is_symlink()
    for row in config['completion_bindings']:
        p=Path(row['path']);assert p.is_file() and not p.is_symlink()
        assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode']
    terminal=json.loads(Path(config['completion_terminal']['path']).read_bytes())
    independent=json.loads(Path(config['completion_independent']['path']).read_bytes())
    supplement=json.loads(Path(config['completion_supplement']['path']).read_bytes())
    assert terminal['source']==independent['source']==config['source']
    assert terminal['tree']==independent['tree']==config['tree']
    assert terminal['phase']=='FULL' and terminal['status']=='PASS' and terminal['primary']==terminal['post']==0
    actual=independent['actual_gate_results']
    assert actual['pytest_PASS']==1470 and actual['pytest_SKIP']==13 and actual['pytest_FAIL']==actual['pytest_ERROR']==0
    assert actual['pytest_unique_named_outcomes']==config['full_source_complete_cases']==1483 and actual['pytest_workers']==2
    assert supplement['returncode']==0
    assert json.loads(json.dumps(_snapshot(root)))==config['selected_snapshots'][NAMES[0]]
    return True

def selected_roots(config):
    assert _completion_admitted(Path(config['roots'][NAMES[0]]))
    return {'status':'PASS_EXACT_ONE_COMPLETED_OWNED_FULL_SCRATCH','roots':1,'cases':1483,'recycle_marker':'NOT_APPLICABLE_NOT_INVENTED'}
