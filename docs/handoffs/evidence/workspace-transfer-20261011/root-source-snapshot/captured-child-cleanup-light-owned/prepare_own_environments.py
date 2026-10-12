import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

OUT = Path('/workspace/engineering/captured-child-cleanup-light-owned')
SOURCE = Path('/workspace/engineering/pr306')
DEST = Path('/workspace/engineering/captured-child-cleanup')
proposal_path = OUT / 'proposed-own-prepared-environment-copy.json'
proposal = json.loads(proposal_path.read_bytes())


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inventory(root):
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            s = path.lstat()
            row = {'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid}
            if stat.S_ISLNK(s.st_mode):
                row.update(kind='symlink', target=os.readlink(path))
            elif stat.S_ISDIR(s.st_mode):
                row.update(kind='directory')
            elif stat.S_ISREG(s.st_mode):
                row.update(kind='file', bytes=s.st_size, sha256=digest(path))
            else:
                raise AssertionError('Unexpected prepared environment member kind')
            result[str(path.relative_to(root))] = row
    return result


assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip() == proposal['source_head']
for name, h in proposal['exact30inputs'].items():
    assert digest(SOURCE / name) == h == digest(DEST / name)
records = []
before_capacity = os.statvfs(DEST).f_bavail * os.statvfs(DEST).f_frsize
assert before_capacity >= proposal['total_apparent_bytes'] + 1200 * 1024 * 1024
for env in proposal['environments']:
    source = Path(env['source'])
    dest = Path(env['own_destination'])
    assert not os.path.lexists(dest)
    before = inventory(source)
    subprocess.run(['cp','-a','--reflink=auto',str(source),str(dest)],check=True)
    copied = inventory(dest)
    assert copied == before
    rebindings = []
    for relative, row in copied.items():
        if row['kind'] != 'file':
            continue
        path = dest / relative
        allowed = relative == 'pyvenv.cfg' or relative.startswith('bin/') or relative.endswith('.pth') or relative.endswith('/direct_url.json')
        if not allowed:
            continue
        data = path.read_bytes()
        changed = data.replace(str(SOURCE).encode(), str(DEST).encode())
        if changed != data:
            path.write_bytes(changed)
            assert path.read_bytes() == changed
            rebindings.append({'relative':relative,'original_sha256':row['sha256'],
                               'rebound_sha256':hashlib.sha256(changed).hexdigest(),
                               'only_literal_checkout_prefix_replacement':True})
    after = inventory(dest)
    rebound = {r['relative']:r for r in rebindings}
    assert before.keys() == after.keys()
    for relative, row in before.items():
        expected = dict(row)
        if relative in rebound:
            original = (source / relative).read_bytes()
            changed = original.replace(str(SOURCE).encode(),str(DEST).encode())
            expected.update(bytes=len(changed),sha256=hashlib.sha256(changed).hexdigest())
        assert after[relative] == expected
    assert inventory(source) == before
    record = {'package':env['package'],'original_complete_inventory':before,
              'own_complete_inventory':after,'path_only_rebindings':rebindings,
              'source_original_unchanged':True,'initial_copy_all_bytes_and_recorded_modes_exact':True}
    path = OUT / ('prepared-environment-'+env['package']+'.private.json')
    with path.open('x') as f: json.dump(record,f,indent=2);f.write('\n')
    path.chmod(0o600)
    records.append({'package':env['package'],'members':len(before),'path_rebindings':len(rebindings),
                    'inventory':{'path':str(path),'bytes':path.stat().st_size,'sha256':digest(path)}})
proof = {'status':'COMPLETE_OWN_PREPARED_COPIES_WITH_LITERAL_PATH_ONLY_REBINDING',
         'proposal':{'path':str(proposal_path),'bytes':proposal_path.stat().st_size,'sha256':digest(proposal_path)},
         'before_available_bytes':before_capacity,'after_available_bytes':os.statvfs(DEST).f_bavail*os.statvfs(DEST).f_frsize,
         'no_installs_downloads_or_source_environment_changes':True,'environments':records}
path=OUT/'own-five-environment-copy-proof.json'
with path.open('x') as f: json.dump(proof,f,indent=2);f.write('\n')
path.chmod(0o600)
print('PASS complete five environment copies and path-only rebinding; originals unchanged')
