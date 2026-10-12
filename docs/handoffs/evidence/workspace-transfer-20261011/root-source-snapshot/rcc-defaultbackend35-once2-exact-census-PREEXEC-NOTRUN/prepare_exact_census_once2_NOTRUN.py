"""Stdlib-only census metadata preparation; no collector/tests/backend imports."""
import ast
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import xml.etree.ElementTree as ET

B=Path('/workspace/engineering/rcc-defaultbackend35-once2-exact-census-PREEXEC-NOTRUN')
OLD=Path('/workspace/engineering/rcc-defaultbackend35-typed-oracle-once2-PREEXEC-NOTRUN')
REVIEW=Path('/workspace/engineering/rcc-defaultbackend35-typed-oracle-once2-independent-PREEXEC-review')
RELEASE='/workspace/engineering/root-one-defaultbackend35-once2-exact-census-release.json'

def row(p):
    p=Path(p);st=p.lstat();assert stat.S_ISREG(st.st_mode) and not p.is_symlink();raw=p.read_bytes()
    return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),mode=oct(stat.S_IMODE(st.st_mode)))

def put(n,value):
    p=B/n;raw=value if type(value) is bytes else (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o400)
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    return row(p)

hold=row(REVIEW/'OWNERFINAL-independent-backend35-typed-oracle-once2-SOURCE-GO-JUnit-classname-PREEXEC-HOLD.json')
assert hold['sha256']=='e30e7d5b4f687beaf894cd4c504863bb2dc8ceb3610d9872a76adffd1c53e3fd'
h=json.loads(Path(hold['path']).read_text())
ownerold=row(OLD/'OWNERFINAL-defaultbackend35-typed-oracle-once2-SOURCE-and-PREEXEC-NOTRUN.json')
assert ownerold['sha256']=='92691f49c6d85392c4230c5d32b463e1ae60a80786a88197974d0b8d376d428b'
o=json.loads(Path(ownerold['path']).read_text())
cfgold=o['config_binding'];assert row(cfgold['path'])==cfgold
cfg=json.loads(Path(cfgold['path']).read_text());source=Path(cfg['controls']['path'])
assert row(source)['sha256']=='cf43fd5b5774ab61c272dc17acd9b95841a0fcd663dd56947c12c9c8f370b307'
rootdir=Path('/workspace/engineering');classname=re.sub(r'\.py$','',source.relative_to(rootdir).as_posix().replace('/','.'))
stdoutpath=os.path.relpath(source,Path(cfg['root_once']))
oldroot=Path('/workspace/engineering/root-one-current8d49-default-cgroup-walk-pure-controls-1')
oldstdout=row(oldroot/'primary/original.stdout.private');oldxml=row(oldroot/'junit.xml')
stdout=Path(oldstdout['path']).read_text();xml=ET.fromstring(Path(oldxml['path']).read_bytes())
originalsource=Path('/workspace/engineering/rcc-current8d49-default-descriptor-walk-controls-PREPARED-NOTRUN/test_default_cgroup_descriptor_walk_NOTRUN.py')
originalclass=re.sub(r'\.py$','',originalsource.relative_to(rootdir).as_posix().replace('/','.'))
assert re.findall(r'^rootdir: ([^\r\n]+)$',stdout,re.M)==[str(rootdir)]
cases=xml.findall('.//testcase');assert len(cases)==35 and {c.get('classname') for c in cases}=={originalclass}
originalnodes=re.findall(r'^(.+?)::(test_\S+) (PASSED|FAILED)(?:\s+.*)?$',stdout,re.M)
assert len(originalnodes)==35
assert all((oldroot/path).resolve()==originalsource.resolve() for path,name,result in originalnodes)
assert sorted(name for path,name,result in originalnodes)==sorted(cfg['expected_case_names'])
protocol=put('original-producer-rootdir-JUnit-classname-stdout-address-data-proof-NOEXEC.json',dict(schema=1,status='STDLIB_ORIGINAL_DATA_PARSED_ONLY',original_stdout=oldstdout,original_xml=oldxml,installed_junit_source=row('/workspace/engineering/pr308/action_server/.venv/lib/python3.12/site-packages/_pytest/junitxml.py'),producer_functions=['mangle_test_address','_NodeReporter.record_testreport'],original_rootdir=str(rootdir),original_classname=originalclass,original_35classes_exact=True,original_35displayed_addresses_resolve_exact=True,new_controls=cfg['controls'],new_expected_classname=classname,new_expected_stdout_path=stdoutpath,rootdir_relative_source_address=source.relative_to(rootdir).as_posix(),counterexample_to_bare_stem='Original and named moved module classnames include exact rootdir-relative directory; basename equality is insufficient.',original_actual_status='34PASS1FAIL_UNCHANGED'))
launcherold=Path(o['launcher_binding']['path']).read_text()
launcher=launcherold.replace(str(OLD),str(B)).replace('FROZEN-defaultbackend35-typed-oracle-once2-config-NOTRUN.json','FROZEN-defaultbackend35-once2-exact-census-config-NOTRUN.json').replace(cfg['root_release_path'],RELEASE)
launcher=launcher.replace('ROOT_DISTINCT_ONE_DEFAULT_DESCRIPTOR35_TYPED_ORACLE_ONCE2_PURE_CONTROLS','ROOT_DISTINCT_ONE_DEFAULT_DESCRIPTOR35_ONCE2_EXACT_CENSUS_PURE_CONTROLS')
launcher=launcher.replace('INDEPENDENT_DEFAULTBACKEND35_TYPED_ORACLE_ONCE2_SOURCE_PREEXECUTION_GO','INDEPENDENT_DEFAULTBACKEND35_ONCE2_EXACT_CENSUS_SOURCE_PREEXECUTION_GO')
launcher=launcher.replace("c.get('classname')==Path(cfg['controls']['path']).stem", "c.get('classname')==cfg['expected_junit_classname']")
needle="    nodes=[]\n    for match in re.finditer"
assert launcher.count(needle)==1
launcher=launcher.replace(needle,"    need(re.findall(r'^rootdir: ([^\\r\\n]+)$',stdout,re.M)==[cfg['pytest_rootdir']],'DEFAULTBACKEND35_EXACT_OBSERVED_ROOTDIR')\n    nodes=[]\n    for match in re.finditer")
needle="        need((root/path).resolve()==Path(cfg['controls']['path']).resolve(),'DEFAULTBACKEND35_ACTUAL_NODE_PATH')"
assert launcher.count(needle)==1
launcher=launcher.replace(needle,"        need(path==cfg['expected_stdout_node_path'] and (root/path).resolve()==Path(cfg['controls']['path']).resolve(),'DEFAULTBACKEND35_ACTUAL_NODE_PATH')")
ast.parse(launcher)
launch=put('run_root_defaultbackend35_once2_exact_census_NOTRUN.py',launcher.encode())
patch=put('exact-census-launcher-only-delta.patch',''.join(difflib.unified_diff(launcherold.splitlines(True),launcher.splitlines(True),fromfile=o['launcher_binding']['path'],tofile=launch['path'])).encode())
oldast=ast.parse(launcherold);newast=ast.parse(launcher)
changed=[]
for before,after in zip(oldast.body,newast.body):
    if ast.dump(before,include_attributes=False)!=ast.dump(after,include_attributes=False):
        changed.append(getattr(before,'name',type(before).__name__))
assert len(oldast.body)==len(newast.body) and set(changed)=={'Assign','admission','admit_census'}
proof=put('exact-census-binding-only-AST-and-negative-contract-NOTRUN.json',dict(schema=1,status='SOURCE_DATA_AST_ONLY_NO_CONTROL_EXECUTION',changed_topnodes=changed,allowed_delta=['BASE/CONFIG/RELEASE fixed namedpaths','exact typedROOT/PREEXEC status names','admit_census exact classname/rootdir/cwd-relative source address'],all_other_launcher_AST_exact=True,typed_control_unchanged=cfg['controls'],original35_names_unchanged=True,producer_protocol=protocol,negative_contract=[dict(poison=p,expected_refusal=c,execution='NOT_RUN') for p,c in [('foreign directory/classname','DEFAULTBACKEND35_JUNIT_NO_NONPASS_OR_FOREIGN_CLASS'),('bare module stem','DEFAULTBACKEND35_JUNIT_NO_NONPASS_OR_FOREIGN_CLASS'),('wrong/missing/duplicate stdout rootdir','DEFAULTBACKEND35_EXACT_OBSERVED_ROOTDIR'),('foreign or alternative displayed source path','DEFAULTBACKEND35_ACTUAL_NODE_PATH'),('duplicate/missing/name/count/nonpass case','existing exact35 JUnit/stdout guards')]],limits='Data protocol closure proves no executed collection/control outcomes; original34P1F and named typed sourceGO remain distinct.'))
refs=cfg['frozen_bindings']+o['all_local_bindings']+[ownerold,hold,h['independent_proof'],h['minimum_named_successor_proposal'],oldstdout,oldxml,protocol,proof,patch]
unique={}
for r in refs:
    assert row(r['path'])==r
    if r['path'] in unique:assert unique[r['path']]==r
    unique[r['path']]=r
cfg.update(status='PREPARED_DEFAULTBACKEND35_ONCE2_EXACT_CENSUS_NOTRUN',root_release_path=RELEASE,launcher=launch,pytest_rootdir=str(rootdir),expected_junit_classname=classname,expected_stdout_node_path=stdoutpath,census_protocol_proof=protocol,census_delta_proof=proof,original_once2_preexec_HOLD=hold,frozen_bindings=list(unique.values()))
assert '--rootdir' not in cfg['pytest_argv']
cfg['pytest_argv']+=['--rootdir',str(rootdir)]
assert not Path(cfg['root_once']).exists() and not Path(cfg['root_once']).is_symlink() and not Path(RELEASE).exists() and not Path(RELEASE).is_symlink()
config=put('FROZEN-defaultbackend35-once2-exact-census-config-NOTRUN.json',cfg)
oldcontract=json.loads(Path(o['contract_binding']['path']).read_text());contract=dict(oldcontract)
contract.update(status='TEMPLATE_ONLY_NAMED_EXACT_CENSUS_REQUIRES_SOURCE_PREEXEC_GO_AND_DISTINCT_ROOT_RELEASE',config_binding=config,launcher_binding=launch,ROOT_release_path=RELEASE,ROOT_release_template=dict(oldcontract['ROOT_release_template']),compatible_PREEXEC_required_fields=dict(oldcontract['compatible_PREEXEC_required_fields']),required_new_output_root=cfg['root_once'])
contract['ROOT_release_template'].update(status='ROOT_DISTINCT_ONE_DEFAULT_DESCRIPTOR35_ONCE2_EXACT_CENSUS_PURE_CONTROLS',config_binding=config,launcher_binding=launch)
contract['compatible_PREEXEC_required_fields'].update(status='INDEPENDENT_DEFAULTBACKEND35_ONCE2_EXACT_CENSUS_SOURCE_PREEXECUTION_GO',config_sha256=config['sha256'],launcher_sha256=launch['sha256'])
contract['ROOT_argv']=[x.replace(o['launcher_binding']['path'],launch['path']).replace(cfgold['path'],config['path']).replace(cfgold['sha256'],config['sha256']).replace(oldcontract['ROOT_release_path'],RELEASE) for x in oldcontract['ROOT_argv']]
contract['ROOT_alwayspost_external_mandatory']='On every outer outcome, separately bounded readonly config/self/release/source/current input postguard with exact managed env; child finally alone does not prove post after outer SIGKILL. Preserve ROOT primary and post statuses separately.'
contract['census_expected']=dict(rootdir=str(rootdir),classname=classname,stdout_address=stdoutpath,cases=35,failed=0,errors=0,skipped=0)
contract=put('ROOT-distinct-once2-exact-census-command-contract-NOTRUN.json',contract)
git=lambda *a:subprocess.check_output(['git','-C','/workspace/engineering/pr308',*a]).decode().strip()
assert git('rev-parse','HEAD')==cfg['source'] and git('rev-parse','HEAD^{tree}')==cfg['tree'] and not git('status','--porcelain','--untracked-files=no')
local=[row(p) for p in sorted(B.iterdir()) if p.is_file()]
owner=put('OWNERFINAL-defaultbackend35-once2-exact-rootdir-census-SOURCE-and-PREEXEC-NOTRUN.json',dict(schema=1,status='NAMED_EXACT_CENSUS_ONLY_SUCCESSOR_SOURCE_PREEXEC_NOTRUN',source=cfg['source'],tree=cfg['tree'],source_count=1440,source_clean=True,controls_binding=cfg['controls'],config_binding=config,launcher_binding=launch,contract_binding=contract,source_delta_proof=proof,producer_protocol=protocol,original_SOURCEGO_PREEXECHOLD=hold,all_local_bindings=local,all_original_bindings=list(unique.values()),bounds=cfg['budgets'],original_failures_and_typed_control='ALL_UNCHANGED',tests_imports_collector_native_real_cgroup='NOT_RUN',writer_A='RELEASED_AFTER_FREEZE',documentation_improvement=h['documentation_improvement'],canonical_disposition='Reuse installed producer/rootdir-address closure and typed semantic marker guidance; exact new census implementation in named private launcher only, no cosmetic paragraph.',upstream_disposition='none',captured=datetime.datetime.now(datetime.timezone.utc).isoformat()))
for r in unique.values():assert row(r['path'])==r
for r in local:assert row(r['path'])==r
print(json.dumps(owner))
