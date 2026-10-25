import hashlib,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
import psutil
import actions.server.deployments
ROOT=Path('/workspace/actions-recovery-327/capability-bundle-native')
E=ROOT/'evidence'
HOME=Path('/workspace/actions-recovery-327/compiler-core-a3/robocorp')
RECEIPT=HOME.parent/'prepared.json'
RCC=Path('/workspace/actions/action_server/src/actions/server/bin/rcc-18.19.3')
actions.server.deployments.__path__.insert(0,'/workspace/actions-recovery-327/capability-bundle-draft/action_server/src/actions/server/deployments')
from actions.server.deployments.capability_bundle import *
from actions.server.deployments.capability_bundle_compiler import *
from actions.server.deployments.package_revision_compiler import PinnedRccPackageBuildExecutor,load_prepared_rcc_environment,TrustedDeveloperExecutionAdmission,PackageCompilationPolicy
from actions.server.deployments.source_manifest import SuppliedSourceEntry
FLOOR=768*1024*1024
BASELINE={p.stem for p in (HOME/'holotree').glob('*.meta')}
records=[]

def cleanup(label):
    views=HOME/'holotree'
    active=[]
    for p in psutil.process_iter(['pid','exe','cwd','cmdline']):
        try:
            info=p.info
            if any(str(info.get(k) or '').startswith(str(views)+'/') for k in ('exe','cwd')):
                active.append(info['pid'])
            if info['pid']!=os.getpid() and any(str(views) in str(a) for a in info.get('cmdline') or []):
                active.append(info['pid'])
        except (psutil.NoSuchProcess,psutil.AccessDenied): continue
    assert not active, ('active RCC view processes',active)
    ids=sorted(p.stem for p in views.glob('*.meta') if p.stem not in BASELINE and re.fullmatch(r'[0-9a-f]{7}_[0-9a-f]{7}_[0-9a-f]{8}',p.stem))
    out=E/('cleanup-'+label);out.mkdir()
    record={'active_processes':active,'spaces':ids,'before_free':shutil.disk_usage(HOME).free}
    for identity in ids:
        for suffix in ('.meta','.meta.info'):
            p=views/(identity+suffix)
            if p.is_file():shutil.copy2(p,out/p.name)
    if ids:
        env=dict(os.environ,ROBOCORP_HOME=str(HOME),ACTIONS_HOME=str(HOME))
        command=[str(RCC),'holotree','delete',*ids]
        for name,argv in [('dryrun',command+['--dryrun']),('delete',command)]:
            p=subprocess.run(argv,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
            (out/(name+'.log')).write_bytes(p.stdout)
            record[name+'_returncode']=p.returncode
            assert p.returncode==0,record
        assert not any((views/i).exists() for i in ids)
    record['after_free']=shutil.disk_usage(HOME).free
    (out/'receipt.json').write_text(json.dumps(record,indent=2))

class Recorded(PinnedRccPackageBuildExecutor):
    def build_environment(self,*args):
        assert shutil.disk_usage(HOME).free>FLOOR
        result=super().build_environment(*args)
        records.append({'phase':'build','specification':result.specification_digest,'artifact':result.artifact_digest})
        return result
    def import_action(self,*args):
        result=super().import_action(*args)
        safe=json.loads(json.dumps(result))
        for a in safe['actions']:a['file']=Path(a['file']).name
        records.append({'phase':'import','metadata':safe})
        return result
    def run_tests(self,*args):
        super().run_tests(*args)
        records.append({'phase':'tests','status':'passed'})
        cleanup('phase-'+str(len(records)))

prepared=load_prepared_rcc_environment(RECEIPT)
manifest=HOME.parent/'package.yaml'
assert hashlib.sha256(manifest.read_bytes()).hexdigest()==prepared.package_yaml_digest.removeprefix('sha256:')
assert json.loads((HOME.parent/'core-proof.json').read_text())['core_version']=='1.1.0a3'
source={
'package.yaml':manifest.read_bytes(),
'actions_impl.py':b'''from actions import action
@action
def normalize_words(text: str) -> str:
    """Normalize words to single spaces and lowercase.

    Args:
        text: Text to normalize.
    Returns:
        Normalized text.
    """
    return " ".join(text.lower().split())
@action
def add_counts(left: int, right: int) -> int:
    """Add two typed integer counts.

    Args:
        left: First count.
        right: Second count.
    Returns:
        Sum of counts.
    """
    return left + right
''',
 'tests/test_actions.py':b'''import unittest
from actions_impl import normalize_words, add_counts
class GeneratedTests(unittest.TestCase):
    def test_words(self): self.assertEqual(normalize_words(" A   B "), "a b")
    def test_counts(self): self.assertEqual(add_counts(7, 9), 16)
'''}
# Snapshot supplied bytes, remove original selected files before native compiler call.
origin=ROOT/'original';origin.mkdir()
for name,data in source.items():
    p=origin/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes(data)
entries=tuple(SuppliedSourceEntry(name,'file',(origin/name).read_bytes(),0o644) for name in source)
shutil.rmtree(origin)
policy=BundleCompilationPolicy(tuple(PythonCapabilityPolicy(name,PackageCompilationPolicy('two-actions','Two generated Actions','>=1.1.0a37,<2','>=1.1.0a3,<2')) for name in ('normalize_words','add_counts')))
(ROOT/'execution').mkdir(exist_ok=True)
try:
    outcome=compile_generated_python_bundle(entries,policy,protected_input_names=('package.yaml',),admission=TrustedDeveloperExecutionAdmission.TRUSTED,executor=Recorded(prepared),execution_root=ROOT/'execution')
    (E/'compiler-receipts.json').write_text(json.dumps({'failure_code':outcome.failure_code,'receipts':[json.loads(r.to_bytes()) for r in outcome.receipts]},indent=2))
    bundle=verify_bundle_compilation_outcome(outcome)
    members=verify_bundle(bundle)
    assert not origin.exists()
    assert len(members)==2
    selected={}
    for m in members:
        cap=json.loads(m.manifest_json)['capabilities'][0]['id']
        selection=select_capability(bundle,bundle.package_revision_id,cap,m.runtime_plan_header.plan_digest)
        selected[cap]={'input':json.loads(selection.compiled.input_schema_payload),'output':json.loads(selection.compiled.output_schema_payload),'plan':m.runtime_plan_header.plan_digest.root}
    assert selected['action.add_counts']['output']['type']=='integer'
    assert selected['action.normalize_words']['output']['type']=='string'
    assert len(records)==6
    (E/'bundle.json').write_bytes(encode_bundle(bundle));(E/'source.zip').write_bytes(bundle.source_archive)
    (E/'result.json').write_text(json.dumps({'status':'PASS','bundle_revision':bundle.package_revision_id.root,'selections':selected,'source_absent_during_compile':True,'phases':len(records),'prepared_sha256':hashlib.sha256(RECEIPT.read_bytes()).hexdigest()},indent=2))
finally:
    (E/'phases.json').write_text(json.dumps(records,indent=2))
    cleanup('final')
