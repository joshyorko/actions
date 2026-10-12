import ast
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

BASE=Path('/workspace/engineering/captured-child-cleanup-configured-full-proposal')
ROOT=Path('/workspace/engineering/captured-child-cleanup')
LIGHT=Path('/workspace/engineering/captured-child-cleanup-light-owned')
C=Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534')

def bind(p):
 p=Path(p);d=p.read_bytes();return {'path':str(p),'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest()}

def freeze(name,data):
 p=BASE/name
 with p.open('x') as f:json.dump(data,f,indent=2);f.write('\n')
 p.chmod(0o600);return bind(p)

activation=bind('/workspace/actions-cloud/activate.sh')
assert activation['bytes']==987 and activation['sha256']=='6478b7b31155b8594e4dbd66f79d8a9e94e63543740d81508af8b635056f646a'
owner=bind(LIGHT/'OWNERFINAL-captured-child-cleanup-LIGHT-source-checkpoint-v2.json')
ind=bind('/workspace/engineering/captured-child-cleanup-independent-LIGHT-review/OWNERFINAL-independent-captured-child-cleanup-frozen-LIGHT-review-v3.json')
assert owner['bytes']==23814 and owner['sha256']=='5afd46dc62231bde85f44381bcb06fbc5d0af98d932dafbcc9d6500e6df6fdf8'
assert ind['bytes']==20878 and ind['sha256']=='6e5c147b9d6ca432def5b7c56489bd0aa432759d4a337cd6124c17f51bbb3df8'
proof=json.loads((BASE/'readonly-source-guard-proof-v5.json').read_bytes())
assert proof['full_execution']=='NOT_RUN' and proof['source_entries']==1422
own=json.loads((LIGHT/'checked-own30-and-five-origins.json').read_bytes())
expected={'ACTIONS_CLOUD_ROOT': '/workspace/actions-cloud', 'ROBOCORP_HOME': '/workspace/actions-cloud/robocorp', 'XDG_CACHE_HOME': '/workspace/actions-cloud/cache', 'XDG_CONFIG_HOME': '/workspace/actions-cloud/config', 'POETRY_CACHE_DIR': '/workspace/actions-cloud/cache/pypoetry', 'POETRY_CONFIG_DIR': '/workspace/actions-cloud/config/pypoetry', 'UV_CACHE_DIR': '/workspace/actions-cloud/cache/uv', 'npm_config_cache': '/workspace/actions-cloud/cache/npm', 'GOCACHE': '/workspace/actions-cloud/cache/go-build', 'GOPATH': '/workspace/actions-cloud/cache/go', 'PLAYWRIGHT_BROWSERS_PATH': '/workspace/actions-cloud/cache/playwright', 'PYTEST_XDIST_AUTO_NUM_WORKERS': '2', 'POETRY_NO_INTERACTION': '1', 'BUILDX_CONFIG': '/workspace/actions-cloud/cache/buildx', 'ACTIONS_HOME': '/workspace/actions-cloud/actions-home', 'ROBOTS_HOME': '/workspace/actions-cloud/robots-home', 'GOMAXPROCS': '2', 'ACTIONS_RUNTIME_TEST_PYTHON': '/workspace/actions/action_server/.venv/bin/python'}
assert len(expected)+1==19
cache=[bind(C/'identity.yaml'),bind(C/'rcc_plan.log'),bind(C/'bin/python3.12'),bind(C/'bin/poetry')]
assert cache[2]['sha256']=='ba35c76091c86640cd6bbccc8c216e5b2fc52b20c26de803edef79165022037f'
assert cache[3]['sha256']=='f989714d24f334397e5960032f3fb3dd7ebcebf5d600e0d520aa7c780c8b124c'
preflight=f'''"""Planned preflight; not executed while preparing proposal."""
import hashlib,json,os,sys
from pathlib import Path
import yaml
from readonly_source_guards_v5 import guards,binding,verify,ROOT
assert Path.cwd().resolve()==ROOT
assert Path(sys.executable).resolve()==Path({str(C/'bin/python3.12')!r})
expected={expected!r}
for key,value in expected.items(): assert os.environ.get(key)==value,key
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
assert len(expected)+1==19
for row in {cache!r}: verify(row)
assert yaml.safe_load(Path({str(C/'identity.yaml')!r}).read_bytes())==yaml.safe_load((ROOT/'developer/setup.yaml').read_bytes())
assert os.environ.get('CLEANUP499_SERIALIZED_HEAVY_SLOT')=='root-captured-child-cleanup499-one-configured-full'
terminal=Path(os.environ['CLEANUP499_ROOT300_TERMINAL_PATH'])
assert binding(terminal)['sha256']==os.environ['CLEANUP499_ROOT300_TERMINAL_SHA256']
assert json.loads(terminal.read_bytes())['returncode']==0
r=guards()
assert r['available_bytes_observation_only']>=1200000000
r['all19_managed_activation_exports_and_PATH_checked']=True
r['root300_terminal']=binding(terminal)
r['fresh_execution_authority']='ROOT_DISTINCT_RELEASE_REQUIRED'
out=Path(sys.argv[1]); assert out.parent==Path('/workspace/engineering/captured-child-cleanup-configured-full-once-owned')
with out.open('x') as f: json.dump(r,f,indent=2);f.write('\\n')
out.chmod(0o600)
print('PASS_CHECKED_MANAGED_ACTIVATION_SOURCE_AND_FRESH_CAPACITY')
'''
p=BASE/'managed_activation_preflight.py';p.write_text(preflight);p.chmod(0o600);ast.parse(preflight)
origin_specs=[]
for row in own['origins']:
 observation=json.loads(Path(row['path']).read_bytes())
 prefix=Path(observation['resolved_prefix']);package=prefix.parent.name
 origin_specs.append((package,observation['module'],str(prefix)))
inner=f'''import hashlib,os,subprocess
from pathlib import Path
import toolkit
root=toolkit.REPOSITORY_ROOT
assert root==Path({str(ROOT)!r})
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip()=='499a83d802ca9a0e2ebe3d77071af10625879297'
assert subprocess.check_output(['git','rev-parse','HEAD^{{tree}}'],cwd=root).decode().strip()=='e13ba51b094e429b7c06d6dabbbcc348cc66e86c'
assert subprocess.check_output(['git','status','--porcelain'],cwd=root)==b''
assert os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
for name,h in {own['inputs_sha256']!r}.items(): assert hashlib.sha256((root/name).read_bytes()).hexdigest()==h
for package,module,prefix in {origin_specs!r}:
 code="import importlib,sys;from pathlib import Path;m=importlib.import_module("+repr(module)+");assert Path(sys.prefix).resolve()==Path("+repr(prefix)+");assert Path(m.__file__).resolve().is_relative_to(Path("+repr(str(ROOT))+ ")/"+repr(package)+"/'src')"
 toolkit.poetry(package,'run','python','-c',code)
os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']='2'
toolkit.poetry('action_server','run','invoke','test-not-integration')
'''
ast.parse(inner)
innerp=BASE/'planned_toolkit_configured_full_body.py';innerp.write_text(inner);innerp.chmod(0o600)
execution=Path('/workspace/engineering/captured-child-cleanup-configured-full-once-owned')
assert not execution.exists()
argv=['bash','--noprofile','--norc','-c','set -euo pipefail\nsource "$1"\n"$2" "$3" "$4"\nshift 4\nexec "$@"\n','captured-child-cleanup499-managed-full',activation['path'],str(C/'bin/python'),str(p),str(execution/'before-full-checked-source-capacity.json'),'env','PYTEST_XDIST_AUTO_NUM_WORKERS=2','timeout','--signal=TERM','--kill-after=10s','600s','/workspace/actions-cloud/bin/rcc','task','script','-r','developer/toolkit.yaml','--','python','-c',inner]
post=f'''import json,sys
from pathlib import Path
from readonly_source_guards_v5 import guards
r=guards();r['capacity_threshold_after_full_not_required']=True
p=Path(sys.argv[1]);assert p.parent==Path({str(execution)!r})
with p.open('x') as f:json.dump(r,f,indent=2);f.write('\\n')
p.chmod(0o600)
'''
postp=BASE/'post_full_readonly_guards.py';postp.write_text(post);postp.chmod(0o600);ast.parse(post)
source_rcc=Path('/workspace/engineering/pr306/action_server/src/actions/server/bin/rcc-18.19.3')
assert bind(source_rcc)['sha256']=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
assert stat.S_IMODE(source_rcc.stat().st_mode)==0o711
actual=bind('/workspace/engineering/root-failed300-default-cache-preservation-actual/OWNERFINAL-root-whole-default-cache-preservation-actual.json')
actualind=bind('/workspace/engineering/root-failed300-default-cache-independent-actual-review/OWNERFINAL-independent-actual-whole-default-cache-preservation-review.json')
assert actual['sha256']=='fdbdc5705b6a15863d3a065e1e6821f4411d2297bb2268eb268946cecbb0ac6c'
assert actualind['sha256']=='dd95e137add3eb9b2a7213495a55886ee59cdb7e8996aa0bdb6d96618be7c7f9'
refs=[owner,ind,activation,*cache,actual,actualind,bind(BASE/'readonly_source_guards_v5.py'),bind(BASE/'readonly-source-guard-proof-v5.json'),bind(p),bind(innerp),bind(postp),bind(LIGHT/'checked-own30-and-five-origins.json'),bind('/workspace/engineering/pr310-runner-qualification-owned/output/native-artifact-tree-inventory.json'),bind('/workspace/engineering/pr310-runner-qualification-owned/output/native-artifact-manifest.json'),bind('/workspace/actions-cloud/receipts/pr305-runner/frozen-helper-bindings.json'),bind(source_rcc),bind(ROOT/'docs/skills/repository-operations.md')]
for q in BASE.iterdir():
 if q.name.startswith('readonly_') or q.name.startswith('readonly-'): 
  row=bind(q)
  if row not in refs: refs.append(row)
for row in refs: assert bind(row['path'])==row
proposal={'schema':'captured-child-cleanup499-managed-configured-full-proposal-v1','decision':'READY_FOR_ROOT_REVIEW_ONLY_NOT_EXECUTED_NO_FULL_AUTHORITY','head':'499a83d802ca9a0e2ebe3d77071af10625879297','tree':'e13ba51b094e429b7c06d6dabbbcc348cc66e86c','sole_parent':'a0d258a16095b95b1bf9000cb1201cddfaff4779','LIGHT':owner,'independent_LIGHT':ind,'read_only_verification':proof,'activation':activation,'allowlisted_activation_exports':expected,'PATH_condition':'First entry exactly /workspace/actions-cloud/bin; inherited remaining PATH retained','activation_export_count_including_PATH':19,'command':{'cwd':str(ROOT),'argv':argv,'scope':'Exact configured invoke test-not-integration task; explicit2worker env precedes invoke; not targeted replacement','deadline_TERM_seconds':600,'KILL_grace_seconds':10,'attempts':1,'before_full_preflight':'Same activated shell; checked ROOT300 successful terminal and fresh >=1.2GB; retained references and1422source/30inputs rehashed; five concrete origins checked through toolkit.poetry before invoke','log':str(execution/'one-configured-full.private.log'),'terminal':str(execution/'one-configured-full-terminal.json'),'post_argv':[str(C/'bin/python'),str(postp),str(execution/'post-full-source-guards.json')],'parent_recording':'Root owner uses private0700 execution directory and0600 log/terminal; records actual returncode/time/hash before post-guards even if failure; no retry or overwritten predecessor','unexpected_failure':'Preserve log/terminal; source/runtime/native equivalence not inferred; root disposition required'},'execution_prerequisites':{'ROOT_distinct_release':'REQUIRED_NOT_GRANTED_BY_PROPOSAL','root300_serialized_full_terminal':'REQUIRED_FRESH_PATH_SHA_AND_returncode0','root_serialized_heavy_slot':'REQUIRED_NO_OTHER_FULL_INSTALLER_OR_ACTUAL','fresh_workspace_available_bytes_minimum':1200000000,'current_capacity':'Observation only, not execution clearance','storage':'Existing owned executable /dev/shm package envs; no install/copy/rebinding now','no_native_provider_browser_consumer_registry_tag_release':True},'preservation':{'all67_LIGHT':True,'all1422_source_body_modes':True,'own30_inputs_and_five_recorded_origins':True,'source_Rcc_0711_primary_0700_owned_fixture_0711':True,'private_original31':True,'original_native1192_and4helpers0444':True,'all_failed_readonly_drafts_retained':'v1 wrongly required primary0711; v2 wrongly assumed0755; v3 used inventory-relative wrong root; v4 hashed symlink text instead of recorded target bytes. v5 corrected against actual retained LIGHT/native inventory; failures are read-only proof construction, not package/runtime failures.'},'native_source_scope':'274 production inputs:8 old paths changed+6 added vs92498;5selected tests exact but separately typed; UNQUALIFIED, no original native receipt upgrade','cache_preservation_history_only':[actual,actualind],'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; exact accepted managed-activation proposal reused, no source edit','Durable_learning_captured':'The activated shell and toolkit identity must be checked before dependency-sensitive full commands; exact activation export contract, configured task and explicit worker budget stay bound together. Distinguish primary/fixture modes and native symlink-target byte hashes from assumed defaults.','Evidence':'987B activation6478; LIGHT5afd/ind6e5c; read-only v5 source proof; exact configured task body lines652-672; accepted canonical activation patch separately bound below','Stale_or_ambiguous_guidance_removed':'No default-cache or bare-host gateway substitution, no old failed full-command adoption, no after-run probe represented as before-run evidence.','Remaining_uncertainty':'Full suite NOT_RUN; fresh >=1.2GB/root300 terminal/serialized authority pending; hosted readiness cause and native qualification unchanged.'},'Upstream_disposition':'none','bindings':refs}
patch=Path('/workspace/engineering/pr300-current74-managed-activation-independent-review/canonical-managed-gateway-activation-exact-context-v2.patch')
proposal['bindings'].append(bind(patch));proposal['Documentation_improvement']['accepted_exact_canonical_delta']=bind(patch)
result=freeze('OWNERFINAL-cleanup499-managed-activation-configured-full-proposal.json',proposal)
print(json.dumps(result))
