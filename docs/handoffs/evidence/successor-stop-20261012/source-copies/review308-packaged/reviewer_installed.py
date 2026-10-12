"""Read existing installed bytes and receipts; never launch Runtime or RCC."""
import hashlib
import importlib.metadata as md
import json
import pathlib
import stat
import subprocess
import tomllib
import zipfile

E = pathlib.Path('/workspace/successor-evidence/pr308-packaged')
C = E / 'installed-minimum-core-consumer'
O = pathlib.Path('/workspace/successor-evidence/review308-packaged')
R = pathlib.Path('/workspace/actions-pr308')
HEAD = 'fe1bdee3d5014d39a763d088535c29d65b38315d'
def sha(b): return hashlib.sha256(b).hexdigest()
def file_receipt(p): return {'path': str(p), 'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size}
lock = tomllib.loads((C/'poetry.lock').read_text())
project = tomllib.loads((C/'pyproject.toml').read_text())
assert 'source' not in project['tool']['poetry']
dependencies = []
for name, version, digest, count in [
    ('actions-core', '1.0.2', '9d527edf540978172178894546add75f117f240786aec804cb75c308615a7e80', 47),
    ('actions-http-helper', '1.0.3', '46ed7ce0e0d3e2e05456d937b5b24bc9dfa0d7d4b98f8119b9fdf00d4fa7e9f9', 2),
    ('actions-runtime', '1.0.3', 'db0f4f60f4cd46c3ac8f11dc824582e5d4b77d651bfd66e9d94b006b4dea0be4', 203),
]:
    dist = md.distribution(name)
    assert dist.version == version
    located = pathlib.Path(dist.locate_file('')).resolve()
    assert located.is_relative_to(C/'.venv')
    package = next(p for p in lock['package'] if p['name'] == name)
    assert package['version'] == version
    if name != 'actions-runtime':
        assert 'source' not in package and dist.read_text('direct_url.json') is None
        assert project['tool']['poetry']['dependencies'][name] == version
        filename = name.replace('-', '_') + '-' + version + '-py3-none-any.whl'
        wheels = list(pathlib.Path('/workspace/successor-toolkit/cache/poetry/artifacts').rglob(filename))
        matching = [p for p in wheels if sha(p.read_bytes()) == digest]
        assert matching
        wheel = matching[0]
    else:
        wheel = E/'actions_runtime-1.0.3-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl'
        direct = json.loads(dist.read_text('direct_url.json'))
        assert direct['archive_info']['hashes']['sha256'] == digest
    assert sha(wheel.read_bytes()) == digest
    assert any(f['hash'] == 'sha256:'+digest for f in package['files'])
    with zipfile.ZipFile(wheel) as z:
        members = [n for n in z.namelist() if n.endswith('.py')]
        assert len(members) == count
        for member in members:
            assert pathlib.Path(dist.locate_file(member)).read_bytes() == z.read(member), member
    dependencies.append({'name':name,'version':version,'wheel_sha256':digest,'installed_python_members_exact':count,'default_public_lock_and_no_direct_url':name!='actions-runtime'})

authority = json.loads(subprocess.check_output(['git','show',HEAD+':docs/program/evidence/core-1.0.2-pypi-verification-20261009.json'],cwd=R))
assert '9d527edf540978172178894546add75f117f240786aec804cb75c308615a7e80' in json.dumps(authority)
commands = json.loads((E/'installed-command-receipt.json').read_text())
assert commands['source'] == HEAD and commands['artifact'] == 11725299041
command_receipts=[]
for item in commands['results']:
    p=E/(item['label']+'.log')
    assert item['exit_code']==0 and str(C) in item['command']
    assert sha(p.read_bytes())==item['output_sha256'] and p.stat().st_size==item['bytes']
    command_receipts.append({'label':item['label'],'exit_code':0,**file_receipt(p)})
assert len(command_receipts)==5
assert '9 passed in 0.70s' in (E/'installed-oauth.log').read_text()
assert (E/'installed-pip-check.log').read_text()=='No broken requirements found.\n'
template=C/'real-private-template/oauth2_config.yaml'
blob=subprocess.check_output(['git','show',HEAD+':action_server/oauth2/oauth-config.yaml'],cwd=R)
assert template.read_bytes()==blob and stat.S_IMODE(template.stat().st_mode)==0o600
startup=json.loads((C/'startup-once2/startup-receipt.json').read_text())
assert startup['runtime_source']==HEAD and startup['status']=='PASS_IDLE_STARTUP_SCOPED'
assert [x['status'] for x in startup['http']]==[200,403,200]
cleanup=startup['cleanup']
assert cleanup['wrapper_reaped'] and cleanup['descendant_snapshot_complete']
assert all(not cleanup[x] for x in ('live_descendant_pids','zombie_descendant_pids','errors'))
assert startup['managed_actions']==0
parent=json.loads((E/'installed-verification.json').read_text())
assert parent['startup']==startup
modes={}
for n in ['.','datadir','actions-home','robots-home','tmp','stdout.log','stderr.log']:
    modes[n]=oct(stat.S_IMODE((C/'startup-once2'/n).stat().st_mode))
assert modes==parent['poststartup_modes']
assert modes=={'.':'0o700','datadir':'0o700','actions-home':'0o750','robots-home':'0o700','tmp':'0o700','stdout.log':'0o600','stderr.log':'0o600'}
result={'verdict':'GO_INSTALLED_MINIMUM_CORE_OAUTH_TEMPLATE_IDLE_SCOPED','runtime_source':HEAD,'artifact_id':11725299041,'consumer_root':str(C),'consumer_lock':file_receipt(C/'poetry.lock'),'dependencies':dependencies,'commands':command_receipts,'template':{**file_receipt(template),'mode':'0o600','exact_tracked_public_template':True},'startup':startup,'poststartup_modes':modes,'inputs':[file_receipt(E/n) for n in ('installed-verification.json','installed-command-receipt.json')],'bounds':'No reviewer CLI, RCC, OAuth rerun, installs or downloads. Prior commands are verified receipts. Idle uses synthetic API key/no sync/min-processes0; captured cleanup only, not uncapped census/readers/leases/native/MCP/managed Action/publication.'}
(O/'reviewer-installed-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'verdict':result['verdict'],'Python_members':[x['installed_python_members_exact'] for x in dependencies],'commands_verified':5,'HTTP':[200,403,200],'template_mode':'0600'}))
