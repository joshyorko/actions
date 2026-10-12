"""Stdlib-only preparation; never imports a reader/test or runs a gate."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

B = Path('/workspace/engineering/rcc-defaultbackend35-concrete-PREEXEC-NOTRUN')
OLD = Path('/workspace/engineering/rcc-current8d49-cgroup-reader28-concrete-PREEXEC-NOTRUN')
S = Path('/workspace/engineering/rcc-current8d49-default-descriptor-walk-controls-PREPARED-NOTRUN')
ROOT = '/workspace/engineering/root-one-current8d49-default-cgroup-walk-pure-controls-1'
RELEASE = '/workspace/engineering/root-one-defaultbackend35-pure-controls-release.json'

def row(path):
    p = Path(path); st = p.lstat()
    assert stat.S_ISREG(st.st_mode) and not p.is_symlink()
    raw = p.read_bytes()
    return dict(path=str(p), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), mode=oct(stat.S_IMODE(st.st_mode)))

def put(name, value):
    p = B / name
    raw = value if type(value) is bytes else (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    with os.fdopen(fd, 'wb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
    return row(p)

source_owner = row(S / 'OWNERFINAL-current8d49-real-default-descriptor-walk-35-controls-SOURCE-PREPARED-NOTRUN.json')
review = row('/workspace/engineering/rcc-current8d49-default-backend35-independent-SOURCE-review/OWNERFINAL-independent-current8d49-default-descriptor19functions35cases-SOURCE-prepared-GO.json')
assert source_owner['sha256'] == 'e7954c3bc19374991213dd70fff3e64d2f7971e84c1c74fa573aee75f16ec7d5'
assert review['sha256'] == 'd3986dbc2335d3655fc204e4702c0dd7a715793dc91072f928cc2752e076506f'
s = json.loads(Path(source_owner['path']).read_text())
j = json.loads(Path(review['path']).read_text())
assert j['proposal_binding'] == source_owner
oldconfig = row(OLD / 'FROZEN-reader28-concrete-source-control-config-NOTRUN.json')
old = json.loads(Path(oldconfig['path']).read_text())
controls = j['controls_binding']; assert row(controls['path']) == controls
ct = ast.parse(Path(controls['path']).read_text())
names = []
translation = {i: '\\x%02x' % i for i in range(128) if i not in range(32, 127)}
translation.update({9: '\\t', 10: '\\n', 13: '\\r'})
def parameter_id(value):
    if type(value) is bytes:
        return value.decode('ascii', 'backslashreplace').translate(translation)
    if type(value) is str:
        return value.encode('unicode_escape').decode('ascii').translate(translation)
    assert type(value) is int
    return str(value)
functions = []
for f in ct.body:
    if not isinstance(f, ast.FunctionDef) or not f.name.startswith('test_'):
        continue
    functions.append(f.name)
    decorators = [d for d in f.decorator_list if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == 'parametrize']
    assert len(decorators) <= 1
    if not decorators:
        names.append(f.name)
    else:
        d = decorators[0]; assert len(d.args) == 2 and not d.keywords
        columns = ast.literal_eval(d.args[0]).split(',')
        values = ast.literal_eval(d.args[1])
        for value in values:
            values_in_case = [value] if len(columns) == 1 else list(value)
            names.append(f.name + '[' + '-'.join(parameter_id(v) for v in values_in_case) + ']')
assert len(functions) == 19 and len(names) == len(set(names)) == 35
expected = put('expected-defaultbackend35-source-derived-cases-NOTRUN.json', dict(schema=1, status='AST_DERIVED_NOT_COLLECTED', controls=controls, named_functions=functions, expected_case_names=names, function_count=19, expanded_case_count=35, pytest_id_protocol='Installed _pytest compat.ascii_escaped/python._idval_from_value read as data only; no imported pytest/test modules. Actual census must exactly match.'))

launcher = (OLD / 'run_root_reader28_pure_once_NOTRUN.py').read_text()
launcher = launcher.replace('READER28', 'DEFAULTBACKEND35').replace('reader28', 'defaultbackend35')
launcher = launcher.replace('READER_OBSERVER28', 'DEFAULT_DESCRIPTOR35')
launcher = launcher.replace('INDEPENDENT_DEFAULT_DESCRIPTOR35_CONCRETE_PREEXECUTION_GO', 'INDEPENDENT_DEFAULTBACKEND35_CONCRETE_PREEXECUTION_GO')
launcher = launcher.replace("a.phase in ('launch','guard','primary')", "a.phase in ('launch','guard')")
launcher = launcher.replace("/workspace/engineering/rcc-current8d49-cgroup-defaultbackend35-concrete-PREEXEC-NOTRUN", str(B))
launcher = launcher.replace("FROZEN-defaultbackend35-concrete-source-control-config-NOTRUN.json", 'FROZEN-defaultbackend35-concrete-config-NOTRUN.json')
launcher = launcher.replace('/workspace/engineering/root-one-cgroup-reader-observer28-pure-release.json', RELEASE)
launcher = launcher.replace('import time\n', 'import time\nimport re\nimport xml.etree.ElementTree as ET\n')
launcher = launcher.replace('for row in (cfg[\'launcher\'],cfg[\'executor\']):', "for row in (cfg['launcher'],):")
launcher = launcher.replace("'launcher_binding':cfg['launcher'],'executor_binding':cfg['executor'],", "'launcher_binding':cfg['launcher'],")
launcher = launcher.replace("'executor_sha256':cfg['executor']['sha256']", "'controls_sha256':cfg['controls']['sha256']")
launcher = launcher.replace("'source':cfg['source'],'tree':cfg['tree'],'config_sha256':a.config_sha256,\n                      'launcher_sha256':cfg['launcher']['sha256'],", "'source':cfg['source'],'tree':cfg['tree'],'config_sha256':a.config_sha256,\n                      'launcher_sha256':cfg['launcher']['sha256'],")
start = launcher.index('    if primary:\n')
end = launcher.index('    return cfg,release_binding\n', start)
launcher = launcher[:start] + "    need(Path(sys.argv[0]).resolve()==Path(cfg['launcher']['path']).resolve(),'DEFAULTBACKEND35_LAUNCHER_ACTUAL_PATH')\n    need(Path(sys.executable).resolve()==Path(CACHED).resolve(),'DEFAULTBACKEND35_CACHED_PARENT_INTERPRETER')\n" + launcher[end:]
launcher = launcher.replace("    primarycmd=['timeout','--signal=TERM','--kill-after=10s','120s',cfg['runtime_python'],cfg['executor']['path'],'--phase','primary',*forwarded]", "    primarycmd=cfg['pytest_argv']")
launcher = launcher.replace("        with (parent/'original.stdout.private').open('xb')", "        parent_seconds = cfg['budgets']['primary_parent'] if name == 'primary' else cfg['budgets']['before_parent']\n        with (parent/'original.stdout.private').open('xb')")
launcher = launcher.replace('timeout=135,check=False', 'timeout=parent_seconds,check=False').replace('parent_seconds=135,stdout_binding=', 'parent_seconds=parent_seconds,stdout_binding=')
start = launcher.index("        census_path=root/'primary'/'original-unittest-node-census.json'")
end = launcher.index('    except BaseException as error:', start)
launcher = launcher[:start] + "        census=admit_census(cfg,root)\n        durable(root/'original-pytest35-node-census.json',census)\n" + launcher[end:]
launcher = launcher.replace("        need(phase('primary',primarycmd)", "        for key in ('basetemp','logger','junit'):\n            p=Path(cfg[key]);need(p.parent==root and not p.exists() and not p.is_symlink(),'DEFAULTBACKEND35_FRESH_OUTPUT_ABSENT')\n        need(phase('primary',primarycmd)")
launcher = launcher.replace("'PASS_28_PURE_CONTROLS_PENDING_INDEPENDENT_ORIGINAL_CENSUS'", "'PASS_35_FAKE_BACKEND_CASES_PENDING_INDEPENDENT_ORIGINAL_CENSUS'")
launcher = launcher.replace("binding(root/'primary'/'original-unittest-node-census.json')", "binding(root/'original-pytest35-node-census.json')")
launcher = launcher.replace("'backend_full_descriptor_walk':'NOT_TESTED_SEPARATE_CONTROLS_REQUIRED'", "'backend_full_descriptor_walk':'OWNED_FAKE_TREE_ONLY'")
launcher = launcher.replace("'scope':'synthetic reader/observer28 only, no cgroup observations/signals/threshold calibration/profile adoption'", "'scope':'35 real default descriptor walks on owned fake trees only, no host cgroup observations/signals/threshold calibration/profile adoption'")
launcher = launcher.replace('OWNERFINAL-root-one-original-reader-observer28-pure-controls.json', 'OWNERFINAL-root-one-original-defaultbackend35-pure-controls.json')
launcher = launcher.replace('"""Concrete ROOT-released synthetic28 only, never native memory-policy adoption."""', '"""Concrete ROOT-released fake descriptor35 only; no native/profile adoption."""')
census_function = '''
def admit_census(cfg, root):
    junit=Path(cfg['junit']);physical(junit,0o600)
    xml=ET.fromstring(junit.read_bytes())
    need(xml.tag=='testsuites' and len(xml)==1 and xml[0].tag=='testsuite','DEFAULTBACKEND35_JUNIT_ENVELOPE')
    suite=xml[0]
    need(all(suite.get(k)==v for k,v in {'tests':'35','failures':'0','errors':'0','skipped':'0'}.items()),'DEFAULTBACKEND35_JUNIT_COUNTS')
    cases=list(suite.findall('testcase')); names=[c.get('name') for c in cases]
    need(len(cases)==len(set(names))==35 and sorted(names)==sorted(cfg['expected_case_names']),'DEFAULTBACKEND35_EXACT_PARAMETER_CASES')
    need(all(not c.findall('failure') and not c.findall('error') and not c.findall('skipped') and c.get('classname')==Path(cfg['controls']['path']).stem for c in cases),'DEFAULTBACKEND35_JUNIT_NO_NONPASS_OR_FOREIGN_CLASS')
    stdout=(root/'primary'/'original.stdout.private').read_text(encoding='utf-8',errors='strict')
    nodes=[]
    for match in re.finditer(r'^(.+?)::(test_\\S+) PASSED(?:\\s+.*)?$',stdout,re.M):
        path,name=match.groups()
        need((root/path).resolve()==Path(cfg['controls']['path']).resolve(),'DEFAULTBACKEND35_ACTUAL_NODE_PATH')
        nodes.append(name)
    need(len(nodes)==len(set(nodes))==35 and sorted(nodes)==sorted(cfg['expected_case_names']),'DEFAULTBACKEND35_TRUE_STDOUT_NODE_CENSUS')
    return {'schema':1,'status':'PASS_35_FAKE_BACKEND_CASES_ONLY','counts':{'passed':35,'failed':0,'errors':0,'skipped':0,'unique_cases':35},'expected_names':cfg['expected_case_names'],'junit_names':names,'stdout_names':nodes,'junit_binding':binding(junit)}

'''
launcher = launcher.replace('\ndef main():', '\n' + census_function + '\ndef main():')
ast.parse(launcher)
launch = put('run_root_defaultbackend35_pure_once_NOTRUN.py', launcher.encode())
refs = old['frozen_bindings'] + [oldconfig, row(OLD / 'run_root_reader28_pure_once_NOTRUN.py'), source_owner, review, expected] + s['all_new_bindings'] + s['all_retained_bindings']
refs += [row('/workspace/engineering/pr308/action_server/.venv/lib/python3.12/site-packages/_pytest/compat.py'),row('/workspace/engineering/pr308/action_server/.venv/lib/python3.12/site-packages/_pytest/python.py')]
unique={}
for r in refs:
    assert row(r['path']) == r
    if r['path'] in unique: assert unique[r['path']] == r
    unique[r['path']]=r
refs=list(unique.values())
assert not Path(ROOT).exists() and not Path(ROOT).is_symlink() and not Path(RELEASE).exists() and not Path(RELEASE).is_symlink()
cfg = {k:v for k,v in old.items() if k not in ('executor','expected_method_ids')}
cfg.update(status='PREPARED_DEFAULTBACKEND35_CONCRETE_PURE_PREEXEC_NOTRUN',root_once=ROOT,root_release_path=RELEASE,launcher=launch,controls=controls,new_module=j['source_module_binding'],source_owner=source_owner,source_independent_review=review,required_source_review_fields={k:j[k] for k in ('schema','status','decision','source','tree')},frozen_bindings=refs,expected_case_names=names,expected_cases_binding=expected,basetemp=ROOT+'/basetemp',logger=ROOT+'/logger',junit=ROOT+'/junit.xml',budgets=dict(before=120,before_kill=10,before_parent=135,primary=120,primary_kill=10,primary_parent=150,alwayspost=120,alwayspost_kill=10,alwayspost_parent=135,root_outer=600,root_kill=10,root_parent=630,fallback_sum=420,margin=180),source_only='35 fake tree default descriptor cases NOTRUN; no host proc/sys reads, signals, native main or profile adoption. Actual census/independent outcome required.')
cfg['pytest_argv']=['timeout','--signal=TERM','--kill-after=10s','120s',cfg['runtime_python'],'-m','pytest','--noconftest','-n0','-vv','-rA',controls['path'],'--basetemp',cfg['basetemp'],'-o','tmp_path_retention_policy=all','--robocorp-log-output',cfg['logger'],'--junitxml',cfg['junit']]
cfg['forbidden_operator_exports']=list(dict.fromkeys(cfg['forbidden_operator_exports']+['PYTEST_PLUGINS','PYTEST_DISABLE_PLUGIN_AUTOLOAD','PYTEST_XDIST_WORKER_COUNT']))
config=put('FROZEN-defaultbackend35-concrete-config-NOTRUN.json',cfg)
pin=Path(cfg['managed_rcc']['path']); st=pin.lstat()
assert stat.S_ISREG(st.st_mode) and not pin.is_symlink() and stat.S_IMODE(st.st_mode)==0o700 and st.st_uid==st.st_gid==1000 and row(pin)['sha256']==cfg['managed_rcc']['sha256']
git=lambda *args:subprocess.check_output(['git','-C','/workspace/engineering/pr308',*args]).decode().strip()
assert git('rev-parse','HEAD')==cfg['source'] and git('rev-parse','HEAD^{tree}')==cfg['tree'] and not git('status','--porcelain','--untracked-files=no')
assert len(subprocess.check_output(['git','-C','/workspace/engineering/pr308','ls-files','-z']).split(b'\0'))-1==1440
release_template=dict(schema=1,status='ROOT_DISTINCT_ONE_READER_OBSERVER28_PURE_CONTROLS',source=cfg['source'],tree=cfg['tree'],config_binding=config,launcher_binding=launch,source_owner_binding=source_owner,source_independent_review=review,root=ROOT,serialized_no_other_heavy_or_storage_mutations=True,independent_preexecution_review=None)
release_template['status']='ROOT_DISTINCT_ONE_READER_OBSERVER28_PURE_CONTROLS'.replace('READER_OBSERVER28','DEFAULT_DESCRIPTOR35')
# The inherited launcher literal must match this namespaced release exactly.
assert release_template['status'] in launcher
contract=put('ROOT-distinct-defaultbackend35-release-and-command-contract-NOTRUN.json',dict(schema=1,status='TEMPLATE_NOT_ROOTAUTH_REQUIRES_INDEPENDENT_CONCRETE_GO',config_binding=config,launcher_binding=launch,ROOT_release_template=release_template,compatible_PREEXEC_required_fields=dict(schema=1,status='INDEPENDENT_DEFAULTBACKEND35_CONCRETE_PREEXECUTION_GO',source=cfg['source'],tree=cfg['tree'],config_sha256=config['sha256'],launcher_sha256=launch['sha256'],controls_sha256=controls['sha256']),ROOT_release_path=RELEASE,ROOT_argv=['timeout','--signal=TERM','--kill-after=10s','600s','bash','-c','export PATH="/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin:$PATH"; source /workspace/actions-cloud/activate.sh && exec "$@"','defaultbackend35-once', '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python',launch['path'],'--phase','launch','--config',config['path'],'--config-sha256',config['sha256'],'--release',RELEASE,'--release-sha256','ROOT_REAL_DISTINCT_RELEASE_SHA256'],ROOT_parent_seconds=630,stage_budgets=cfg['budgets'],ROOT_mandatory_preflight=['Reject inherited pytest/optimize/operator overrides before managed activation; no environment repair.','All bindings exact, source1440 clean/prepared30/own5/native1192 and old V9 evidence guarded before/alwayspost.','Exact ROOT release regular nonsymlink0600 UID/GID1000, typed scope and compatible real independent review; cfg/launcher0400.','Root/basetemp/logger/JUnit ABSENT, no concurrent heavy/storage mutations; native MAIN never invoked.','Original JUnit and complete stdout exactly35 unique parameterized case names,0fail/error/skip; process0 alone insufficient.'],actual_controls='NOT_RUN',real_cgroup_latency_native_adoption='NOT_QUALIFIED'))
proof=put('static-concrete-defaultbackend35-preexecution-proof-NOTRUN.json',dict(schema=1,status='STDLIB_AST_METADATA_ONLY_NO_IMPORT_TEST_EXECUTION',source=cfg['source'],tree=cfg['tree'],source_count=1440,source_clean=True,expected_cases=expected,functions=19,cases=35,old_frozen_refs=len(refs),source_owner=source_owner,source_independent_review=review,launcher=launch,config=config,contract=contract,maximum_fallback_seconds=420,outer600_margin=180,managed_primary_readonly700=True,outputs_absent=True))
locals=[row(p) for p in sorted(B.iterdir()) if p.is_file()]
owner=put('OWNERFINAL-defaultbackend35-concrete-managed-pure-PREEXEC-NOTRUN.json',dict(schema=1,status='DEFAULTBACKEND35_CONCRETE_PREEXEC_PREPARED_NOTRUN',source=cfg['source'],tree=cfg['tree'],source_count=1440,source_clean=True,config_binding=config,launcher_binding=launch,contract_binding=contract,expected_cases_binding=expected,static_proof=proof,all_local_bindings=locals,all_original_bindings=refs,tests_imports_host_cgroup_native='NOT_RUN',writer_B='RELEASED_AFTER_FREEZE',documentation_improvement=dict(canonical_file='docs/skills/repository-operations.md',exact_delta_reuse=j['documentation_improvement'],durable_learning='Reuse8366 default descriptor coverage plus d6c observer/8c28 headroom scope; concrete gate enforces35 expanded cases rather than manual method-count.',evidence=[expected,config,launch],remaining_uncertainty='Actual35 case outcomes remainNOTRUN; realcgroup stalls/calibration/native/profile unqualified.',upstream_disposition='none'),captured=datetime.datetime.now(datetime.timezone.utc).isoformat()))
for r in refs+locals: assert row(r['path'])==r
print(json.dumps(owner))
