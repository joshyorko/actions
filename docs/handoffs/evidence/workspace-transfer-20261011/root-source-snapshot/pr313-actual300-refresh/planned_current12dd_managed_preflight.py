"""Future activated preflight; no execution while preparing proposal."""
import json
import os
import sys
from pathlib import Path
import yaml
from verify_current_source_v2 import ROOT,OUT,HEAD,TREE,bind,check

assert Path.cwd().resolve()==ROOT
assert Path(sys.executable).resolve()==Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python3.12')
owner=OUT/'OWNERFINAL-pr313-current-actual300-ordinary-refresh-SOURCE_LIGHT.json'
assert bind(owner)['sha256']=='0171ef23a625807d6f09dabcc25b9695ee622ca570f8b8800a75433c7a1bcbbb'
for row in json.loads(owner.read_bytes())['bindings']:assert bind(row['path'])==row
old=Path('/workspace/engineering/captured-child-cleanup-configured-full-proposal/OWNERFINAL-cleanup499-managed-activation-configured-full-proposal-v2.json')
assert bind(old)['sha256']=='e853c20af0045a217a4c979a973df807ae259c6a85e472fb20273a41dba882ac'
for name,value in json.loads(old.read_bytes())['allowlisted_activation_exports'].items():assert os.environ.get(name)==value,name
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
assert os.environ.get('ACTIONS_REAL_RCC_ARTIFACT_TEST')!='1'
assert os.environ['PR313_CURRENT12DD_SERIALIZED_HEAVY_SLOT']=='root-pr313-current12dd-one-configured-full'
auth=Path(os.environ['PR313_CURRENT12DD_DISTINCT_ROOT_RELEASE_PATH'])
assert bind(auth)['sha256']==os.environ['PR313_CURRENT12DD_DISTINCT_ROOT_RELEASE_SHA256']
release=json.loads(auth.read_bytes())
assert release['head']==HEAD and release['tree']==TREE
assert release['source_LIGHT']==bind(owner)
assert release['attempts']==1 and release['serialized_heavy_slot_clearance'] is True
proposal=OUT/'OWNERFINAL-pr313-current12dd-managed-configured-full-PREEXECUTION-proposal.json'
assert release['full_proposal']==bind(proposal)
for row in json.loads(proposal.read_bytes())['bindings']:assert bind(row['path'])==row
review=release['independent_preexecution_review']
assert bind(review['path'])=={k:review[k] for k in ('path','bytes','sha256')}
decision=json.loads(Path(review['path']).read_bytes())['decision']
assert decision==review['decision'] and decision.startswith('GO')
r=check();assert r['capacity_observation_only']>=1200000000
identity=Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/identity.yaml')
assert yaml.safe_load(identity.read_bytes())==yaml.safe_load((ROOT/'developer/setup.yaml').read_bytes())
sys.path.insert(0,str(ROOT/'developer'));import toolkit
own=json.loads(Path('/workspace/engineering/captured-child-cleanup-light-owned/checked-own30-and-five-origins.json').read_bytes())
attempt=Path(sys.argv[1]).parent
assert attempt==Path('/workspace/engineering/pr313-current12dd-configured-full-once-owned')
fresh=[]
for row in own['origins']:
    observation=json.loads(Path(row['path']).read_bytes());prefix=observation['resolved_prefix'];package=Path(prefix).parent.name
    dest=attempt/('before-full-own-origin-'+package+'.json')
    assert not dest.exists()
    code='import importlib,json,sys;from pathlib import Path\n'
    code+=f"m=importlib.import_module({observation['module']!r});p=Path(m.__file__).resolve();assert Path(sys.prefix).resolve()==Path({prefix!r});assert p.is_relative_to(Path({str(ROOT/package/'src')!r}));Path({str(dest)!r}).write_text(json.dumps(dict(module={observation['module']!r},origin=str(p),prefix=sys.prefix,python=sys.executable))+'\\n')"
    toolkit.poetry(package,'run','python','-c',code);dest.chmod(0o600);fresh.append(bind(dest))
r['true_activated_preflight_before_pytest']=True
r['fresh_five_own_origins']=fresh
r['all19_activation_exports_and_PATH_checked']=True
r['root_distinct_release']=bind(auth)
dest=Path(sys.argv[1])
with dest.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
dest.chmod(0o600)
print('PASS_CURRENT12DD_ACTIVATION_SOURCE_INPUTS_AND_CAPACITY_BEFORE_FULL',flush=True)
