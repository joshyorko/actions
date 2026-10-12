"""Storage-only metadata guard; no product tests, RCC/native or installs."""
import hashlib,json,os,stat,subprocess,sys
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

def load_config(path):
    supplement=json.loads(Path(path).read_bytes())
    row=supplement['base_config_binding'];p=Path(row['path'])
    assert p.is_file() and not p.is_symlink() and p.stat().st_size==row['bytes']
    assert sha(p)==row['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode']
    config=json.loads(p.read_bytes())
    config['roots']['original27-log']=config['roots'].pop('robocorp-log')
    config['selected_snapshots']['original27-log']=config['selected_snapshots'].pop('robocorp-log')
    for label,record in supplement['added_roots'].items():
        assert label not in config['roots']
        config['roots'][label]=record['path'];config['selected_snapshots'][label]=record['snapshot']
    config['completion_bindings']+=supplement['completion_bindings']
    config['references']+=[supplement['qualified_current_config_binding'],supplement['base_owner_binding']]
    config['completion_records_extra']=supplement['completion_records']
    assert len(config['roots'])==len(set(config['roots'].values()))==4
    return config

def exact(row):
 p=Path(row['path']); assert p.is_file() and not p.is_symlink()
 assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode']

def protected(config):
 for row in config['references']+config['completion_bindings']+[config['source_guard'],config['source_guard_inputs']]:exact(row)
 assert not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE')
 assert 'PYTEST_ADDOPTS' not in os.environ
 code=json.loads(Path(config['source_guard_inputs']['path']).read_bytes())
 for key,value in code['expected_activation_exports'].items():assert os.environ.get(key)==value
 assert len(code['expected_activation_exports'])==18 and os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
 managed=Path(code['cached_toolkit_prefix'])/'bin/python';assert Path(sys.prefix).resolve()==managed.parent.parent.resolve()
 actual=subprocess.run([str(managed),config['source_guard']['path'],config['source_guard_inputs']['path'],'after'],env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},cwd=code['source_root'],capture_output=True,timeout=60,check=False)
 assert actual.returncode==0,'CURRENT_DATA_ONLY_SOURCE_ENV_NATIVE_GUARD_FAIL'
 return {'status':'PASS_DATA_ONLY_CURRENT8D49_1440_ORIGINAL237_NATIVE1192_PREPARED30_FIVE_ORIGINS','metadata_stdout_bytes':len(actual.stdout),'metadata_stdout_sha256':hashlib.sha256(actual.stdout).hexdigest(),'stderr_bytes':len(actual.stderr),'stderr_sha256':hashlib.sha256(actual.stderr).hexdigest(),'source_native_qualification':'UNCHANGED'}

def selected_roots(config):
 for name,path in config['roots'].items():
  root=Path(path);expected=config['selected_snapshots'][name]
  assert root.name==Path(path).name and root.is_dir() and not root.is_symlink()
  assert json.loads(json.dumps(_snapshot(root)))=={k:v for k,v in expected.items() if k in ('root','entries','identities')}
 for row in config['completion_bindings']:exact(row)
 light=json.loads(Path(config['completion_owner']['path']).read_bytes());green=json.loads(Path(config['completion_green']['path']).read_bytes())
 assert light['results']['ToolkitTest_passed']==179 and light['before_returncode']==light['primary_returncode']==light['post_returncode']==0
 assert green['returncode']==0
 for record in config['completion_records_extra']:
  terminal=json.loads(Path(record['terminal']['path']).read_bytes());assert terminal['returncode']==0 and '--robocorp-log-output='+config['roots'][record['label']] in terminal['argv']
 return {'status':'PASS_EXACT_TWO_COMPLETED_OWNED_ROOTS','roots':4,'invented_recycle_markers':False}
