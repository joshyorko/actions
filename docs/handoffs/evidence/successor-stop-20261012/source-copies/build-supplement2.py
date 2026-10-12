import datetime
import hashlib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path('/workspace/successor-evidence')
OUT = pathlib.Path('/workspace/actions-checkpoint/docs/handoffs/evidence/successor-20261012-supplement2')
OUT.mkdir(parents=True, exist_ok=True)

def gh(*args):
    return json.loads(subprocess.check_output(['gh','api',*args]))

def write(path, obj):
    p=ROOT/path
    p.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')

now=datetime.datetime.now(datetime.timezone.utc).isoformat()
checks=gh('repos/joshyorko/actions/commits/0546ef30a30ff8229cb8fa6268e492c5cd74134e/check-runs?per_page=100')
write('current-checks-supplement2.json',{'observed_at':now,'head':'0546ef30a30ff8229cb8fa6268e492c5cd74134e','checks':[{k:c[k] for k in ('name','status','conclusion','html_url')} for c in checks['check_runs']]})
log=ROOT/'pr308/decoded-0546-macos114668292448.log'
b=log.read_bytes(); t=b.decode()
assert '6433af24a322be5f8a715934663b925d5b3cf044' in t
assert '1 failed, 1420 passed, 216 skipped' in t
assert 'provider_stopped = False' in t
producer=gh('repos/joshyorko/actions/git/commits/6433af24a322be5f8a715934663b925d5b3cf044')
assert producer['tree']['sha']=='cca24f6fd8f6c18034ef3a12b77dd37e5fe64a97'
assert [p['sha'] for p in producer['parents']]==['48eeaf171e695d9b8ac140ea53239eaeb6eff331','0546ef30a30ff8229cb8fa6268e492c5cd74134e']
write('pr308/0546-macos-source-terminal-diagnosis.json',{'observed_at':now,'run':38205604794,'job':114668292448,'head':'0546ef30a30ff8229cb8fa6268e492c5cd74134e','producer':{'sha':producer['sha'],'tree':producer['tree']['sha'],'parents':[p['sha'] for p in producer['parents']]},'conclusion':'failure','unit':{'failed':1,'passed':1420,'skipped':216,'seconds':141.71},'failure_node':'test_dakota_rcc_acceptance.py::test_provider_startup_failure_uses_bounded_kill_fallback','assertion':'provider_stopped = False','actual_root_cause':'UNKNOWN: prior test discarded typed cleanup result; controlled scheduler overshoot is a viable route, not proof of actual macOS cause','raw_log':{'path':str(log),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'local_only':True},'native_baseline_attempts':0})
write('workspace-access-restored-readonly.json',{'observed_at':now,'requested_after_disconnect':'05:10 UTC','actual_command':'hostname\npwd\ngit -C /workspace/actions-pr308 rev-parse HEAD\ngit -C /workspace/actions-pr308 branch --show-current\ngit -C /workspace/actions-pr308 status --short','exit_status':0,'hostname':'9e619bc297a7','cwd':'/workspace','checkout_head':'b30e220cbc458edaad605d36081c014e2cec190b','branch':'fix/rcc-candidate-wheel-identities-20261010','worktree_clean':True,'existing_workspace_retained':True,'work_can_continue':True,'workers_preserved':True})
names=['current-checks-supplement2.json','workspace-access-restored-readonly.json','final-pr-scope-metadata-readback.json']
names += ['pr308/'+s for s in ['0546-macos-source-terminal-diagnosis.json','0546ef30-remote-source-readback.json','pr308-0546ef30-windows-wait-source-receipt.json','native-baseline-profile-0546ef30-v7-SOURCE-PREPARED-NOTRUN.json','fe1-windows-source-terminal-diagnosis.json','windows-fe1-missing-wnohang-bounded-reproduction.json','fe1-source-ci-cancel-preflight.json','fe1-source-ci-cancel-requested.json','fe1-source-ci-cancel-terminal-observation.json','mac-provider-deadline-model-0546.json','pr308-b30e220c-mac-provider-source-receipt.json','native-baseline-profile-b30e220c-v8-SOURCE-PREPARED-NOTRUN.json']]
for group in ['review308-packaged','review308-windows-wait','review-checkpoint-remote363606']:
    names += [str(p.relative_to(ROOT)) for p in (ROOT/group).glob('*.json')]
names += ['pr308-packaged/'+s for s in ['installed-verification.json','producer-and-download-admission.json','installed-command-receipt.json','download-once-FAIL.json','bundled-rcc-hashes.json','download-connector-receipt.json','installed-minimum-core-consumer/admission.json','installed-minimum-core-consumer/startup-once2/startup-receipt.json']]
existing=set()
for group in ['successor-20261012','successor-20261012-supplement1']:
    for row in json.loads((OUT.parent/group/'manifest.json').read_text()): existing.add(row['path'])
manifest=[]
for name in sorted(set(names)):
    data=(ROOT/name).read_bytes()
    json.loads(data)
    assert not re.search(rb'file://|x-amz-signature=|github_pat_|ghp_[A-Za-z0-9]|Authorization.{0,10}Bearer|client_secret\s*=|api_key\s*=',data,re.I),name
    if name in existing: continue
    dst=OUT/name; dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists(): assert dst.read_bytes()==data,name
    else: dst.write_bytes(data)
    manifest.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'payloads':len(manifest),'bytes':sum(r['bytes'] for r in manifest),'observed_at':now}))
