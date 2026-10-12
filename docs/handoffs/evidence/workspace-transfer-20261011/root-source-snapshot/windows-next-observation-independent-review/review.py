from pathlib import Path
import hashlib
import json
import re
import subprocess

OWNED=Path('/workspace/engineering/windows-next-observation-owned')
OUT=Path('/workspace/engineering/windows-next-observation-independent-review')
REPO='/workspace/engineering/pr311'
HEAD='d75b25fb4c354e5c95bc0f639b426d6ff402104b'

def binding(p):
    b=p.read_bytes()
    return {'path':str(p),'size':len(b),'sha256':hashlib.sha256(b).hexdigest()}

expected={'design.md':'3a22e015f95dc8e3297e0793f479f224e17c9033262e620e03c3304182d1086c','design-receipt.json':'2d1824429334c375051110ec6b5c10754b458f93e6ff31f9102a08128e95569f','canonical-guide-proposed.patch':'bef15c13e9bb844ca64a89d5c17b9933a02804f844e8f7024b985967abf23f5c','design-v2.md':'a23775765d3295a8019a2d88ddaea571049b8a55ed988a9b10635c7bcf28257c','design-v2-receipt.json':'7c9e9f36c299e382f783865c84e4057d1170d8ce723b7225f5f98f37654bebe8','canonical-guide-v2-proposed.patch':'d7c816ddc2d8ab467e1975a0012117d40cb860e2ccfa37e5abc6f7d2a0554993'}
for n,h in expected.items():assert binding(OWNED/n)['sha256']==h
d=json.loads((OWNED/'design-v2-receipt.json').read_text())
assert d['current_source']['head']==HEAD
assert d['current_source']['tree']=='22c984ea5ce5275803308790c519263e7027b40c'
for relative,source in d['current_source']['files'].items():
    p=Path(source['path']);assert binding(p)==source
    blob=subprocess.check_output(['git','-C',REPO,'show',HEAD+':'+relative])
    assert p.read_bytes()==blob
assert not subprocess.check_output(['git','-C',REPO,'status','--porcelain'])
for source in d['prior299']['immutable_rcc_source'].values():
    assert hashlib.sha256(Path(source['local_path']).read_bytes()).hexdigest()==source['sha256']
    assert source['commit']=='4148c2b71705c9d2baf0e88b48d08a79cb7bda0f'
old299=json.loads(Path('/workspace/engineering/pr299-windows-independent-diagnosis.json').read_text())
log=Path(old299['log']['path']);assert hashlib.sha256(log.read_bytes()).hexdigest()==old299['log']['sha256']
marks=[]
for line in log.read_text().splitlines():
    m=re.search(r'Progress: (\d\d)/15\s+v18\.19\.3\s+(\d+\.\d{3})s',line)
    if m:marks.append((int(m[1]),float(m[2])))
assert [m[0] for m in marks]==list(range(16))
assert round(sum(m[1] for m in marks),3)==89.259
assert old299['observations']['rcc_variables_caller_seconds']==89.28
source=Path('/workspace/engineering/rcc-pretty-functions.go').read_text()
for needle in ['previous := ProgressMark','ProgressMark = time.Now()','ProgressMark.Sub(previous)']:
    assert needle in source
callback=Path(REPO,'action_server/src/actions/server/_robo_utils/callback.py').read_text()
assert 'logger.exception(f"Error calling: {c}.")' in callback
design=(OWNED/'design-v2.md').read_text()
for needle in ['PERMANENTLY latches sum unavailable','probe catches it internally','Callback logger.exception is NOT called','same original exception','server._port > 0','LOWER bound','Future state remains explicitly unavailable','existing80/88 snapshots','original cleanup20','No new thread/process/wait/IO']:
    assert needle in design
result={
 'verdict':'GO_V2_BOUNDED_TEST_ONLY_OBSERVATION_DESIGN; HOLD_IMPLEMENTATION_NATIVE_EXECUTION_CHILD_BOUNDARY_AND_ROOT_CAUSE',
 'scope':'independent read-only review of exact immutable design and existing source/evidence; no source edit, tests/native run, cancellation, retry or infrastructure',
 'proposal_bindings':[binding(OWNED/n) for n in expected],
 'current_source':d['current_source'],
 'independent_grounding':{'original311_review_sha256':'81b819b9eb7a4d25bb46e0517b27bc303f78b80c32c7df89a6da4198967afe95','original311':'six first90-second readiness failures; only two instrumented activeCPU/IO80/88 snapshots; no rawProgress; five incomplete20-secondcleanup notes; host-onlyfinal fields cannot prove descendantreap','original299_rawlog_binding':binding(log),'original299_numeric_marks': [{'step':n,'since_previous_seconds':v} for n,v in marks],'original299_sum_seconds':89.259,'original299_caller_seconds':89.28,'immutable_RCC_source':d['prior299']['immutable_rcc_source'],'previous_mark_semantics_independently_verified':True,'historical299_timing_is_not311_timing':True},
 'accepted_design_boundaries':['Change only existing test observer/test/guide after root assigns a source lane; retain exactly first native actions_sync start of the two selected nodes.', 'Reuse existing completed-line callback delivery only; no new pipe consumer, reader thread, flush, logging mode, file IO in callbacks or production bytes.', 'Strict8192-character line bound and32 numeric marks with16KiB state/65535 saturating counts; fixed categorical output only, no raw suffix/config/environment/args/URL or exception text.', 'Exact18.19.3 unique ordered0..15 sequence alone may provide previous-mark interval sum; any loss/drop/overflow/cap/parser-invariant/version error latches sum unavailable permanently.', 'Diagnostic failures are caught internally before existing Callback logger.exception can expose exception text; negative secret-bearing callback failure test required.', 'Readiness compares exact existing HTTP/HTTPS regex and stderr channel without ANSI/acceptance normalization; startup return timestamp is a conservative lower bound for the actual wait origin, Future state unavailable.', 'Scoped owned Process start/cleanup wrapper immediately delegates other objects, passes exact original deadline, returns same tuple/result or raises identical original exception, and unregisters only probe callbacks.', 'Observe actual cleanup result scalar predicates/counts, including snapshot and zombie distinction, without an extra kill/wait/traversal or raw errors/PIDs/names.', 'Keep90-second readiness,20-second cleanup,80/88 samples and50ms samplerjoin unchanged; OS query overrun and pending daemon remain explicit unavailable/late-drop limits.', 'Current d75 hosted result is root-owned evidence to read before any newly authorized source/execution wave.'],
 'required_implementation_proofs':['Meaningful baseline then per-invariant negative progress tests including later valid16marks after loss/overflow; no sum recovery.', 'Existing capture/readiness callbacks receive original line once; no kwargs/Future/port/pipe/env or original acceptance changes.', 'Exact-channel/matcher/timing/HTTPS/late/over-limit cases preserve source acceptance and original TimeoutError object/notes.', 'Each cleanup failed disjunction and separate zombie state tested against real result type; same returned object/deadline and no extra process action.', 'Secret-bearing probe exception caught internally without Callback logger/output leak, while delegated original exceptions still propagate unchanged.', 'Disabled/source-mode/other-node/second-start/other-process paths install no callbacks; owned cleanup and registration ordering protected.', 'Current frozen source tuple, configured source/static/Toolkit checks and exact production/workflow/protected-input parity before root authorizes any actual gate.'],
 'remaining_uncertainty':['This host-only design cannot observe RCC internal pipe arrival, actual unbuffered/buffered forwarding state, native ready-log emitter or Future state.', 'Complete delivered RCC marks do not prove process exit, environment JSON admission, action import or native readiness.', 'Absent host lines do not identify internal inactivity or propagation failure; no root cause or#299-specific regression established.', 'Original cleanup returned result flags remain absent from historical reports; prospective observations cannot retroactively fill them.', 'Future child-side instrumentation/transport/source/artifact qualification is deferred and not approved by this GO.', 'Current d75 CI outcome, future source implementation and actual Windows execution remain separate gates.'],
 'canonical_documentation':{'canonical_file':'docs/skills/repository-operations.md','exact_proposed_delta':binding(OWNED/'canonical-guide-v2-proposed.patch'),'disposition':'PROPOSED V2 accepted for bounded test-only next source design; V1 retained unchanged; no repository mutation','durable_learning':'casecensus vsobservercoverage, previousmark intervals vselapsed, hostdelivery vsnative stage, actualcleanup result vshost-onlypoll/readers, secretproof callback exceptions, irrevocable loss invalidation','evidence':'original31181b, original2994eef/rawee8e+immutable4148 source and exactd75 current callback/process/Rcc/selftest/server sourcebindings','stale_ambiguity':'two observed cases represent allsix; finalstep is total; missinglines prove idle/forwardinggap; callback exception logging is automatically safe; dropped marks may still qualify sum; rc15/readersfalse prove fullcleanup','remaining_uncertainty':'invisible native/RCC phases,currentCI/source/actualacceptance gates above','upstream':'none; no maintained upstream defect or authorized external target'},
 'private_metadata_release_policy':'unchanged HOLD; no private metadata substitution or Runtime publication admission',
}
p=OUT/'independent-v2-design-review.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(binding(p)))
