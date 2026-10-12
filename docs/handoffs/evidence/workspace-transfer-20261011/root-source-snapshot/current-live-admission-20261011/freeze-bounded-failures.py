import difflib
import hashlib
import json
import pathlib
import re
import subprocess

out=pathlib.Path('/workspace/engineering/current-live-admission-20261011')
def git(repo,*args):return subprocess.check_output(['git','-C',repo,*args])
def bind(p):
    p=pathlib.Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
head305='3ec9d0acbe30ad94d02e4c24fef2587127964495'
repo305='/workspace/engineering/pr305'
guide=git(repo305,'show',head305+':docs/skills/repository-operations.md').decode()
anchor='across Windows and POSIX test runners.\n'
assert guide.count(anchor)==1
fixture='''
Public-wheel sample controls require the exact accepted member bytes. A checkout
can convert committed LF files to CRLF, so copying `Path.read_bytes()` from that
checkout need not preserve a published member digest. Use an owned fixture made
from the recorded Git blob or authenticated wheel member and verify its fixed
digest before executing the generated probe. Keep actual worker/module digest
predicates unchanged. Require a valid baseline before each member, version,
ownership or prefix poison; a fixture-setup failure exercises none of those
rejection predicates and does not establish a public Runtime/browser failure.
'''
staging_anchor='failure cleanup; it does not establish an RCC consumer/import proof.\n'
assert guide.count(staging_anchor)==1
staging='''
A mutation-rejection control must establish that its injection ran at the intended
read stage. Preserve that observation and the measured byte/identity evidence
separately from the expected exception. A `DID NOT RAISE` failure alone does not
distinguish an injection that never ran from a verifier that accepted a mutation;
an assertion after the failed raises-block supplies no observation. Keep the
executed source-contract gate held without inferring an acquisition failure,
timestamp cause or production bypass from that incomplete failure record.
'''
proposed=guide.replace(anchor,anchor+fixture).replace(staging_anchor,staging_anchor+staging)
patch=out/'canonical-fixture-and-mutation-evidence-proposed.patch'
patch.write_text(''.join(difflib.unified_diff(guide.splitlines(True),proposed.splitlines(True),fromfile='a/docs/skills/repository-operations.md',tofile='b/docs/skills/repository-operations.md')))
log305=out/'305-windows-3ec-original-private.log'
s305=log305.read_bytes().decode();assert '5 failed, 1083 passed, 94 skipped' in s305
nodes305=re.findall(r'FAILED (action_server_tests[^\r\n]+?) - AssertionError: Failed: assert hashlib.sha256\(payload\)',s305)
assert len(nodes305)==5
samples={}
for p in ['actions/src/actions/__init__.py','actions/src/actions/mcp/__init__.py','actions/src/actions/mcp/_metadata.py']:
    b=git(repo305,'show',head305+':'+p)
    samples[p]={'Git_blob_sha256':hashlib.sha256(b).hexdigest(),'LF_to_CRLF_data_transform_sha256':hashlib.sha256(b.replace(b'\n',b'\r\n')).hexdigest()}
assert samples['actions/src/actions/__init__.py']['Git_blob_sha256']=='790b5e45f1a570f4d209879a47007ce94b73aab76c522bd6400867168726b0d2'
assert samples['actions/src/actions/__init__.py']['LF_to_CRLF_data_transform_sha256']=='93e2fd8677315fe4fa8672a5f88fe7834c6b3bf06609c39810c01bfb03ce91cc'
assert all(h in s305 for h in samples['actions/src/actions/__init__.py'].values())
test305='action_server/tests/action_server_tests/mcp/test_canvas_runtime_admission.py'
receipt305={'verdict':'HOLD_CURRENT305_COMPLETE_CI; GO_BOUNDED_SYNTHETIC_FIXTURE_REPRESENTATION_DIAGNOSIS','head':head305,'tested_merge':'8e9436faf78eff31aa5f60699db01a51815bfc84','tested_tree':'8ed17c0c2ed48a3ad4fe89994bab572d028e59ca','ordered_parents':['1c7585fe8bb3cb9476c3997570bd3f04466f2bbc',head305],'run':38114004651,'job':114395155610,'failed_step':'Test (not integration)','failed_nodes':nodes305,'counts':{'failed':5,'passed':1083,'skipped':94,'warnings':14,'seconds':445.88,'later_typecheck':'PASS339files'},'stage':'Synthetic sample setup at test_canvas_runtime_admission.py:82 before generated worker probe execution and baseline/poison assertions','source_sample_measurements':samples,'observed_first_member_digest':'93e2fd8677315fe4fa8672a5f88fe7834c6b3bf06609c39810c01bfb03ce91cc','source_attribution':'Actual observed first-member hash exactly equals CRLF-transformed committedLF actions.__init__ bytes; source fixture reads working-tree bytes. No checkout config/whole worker receipt measured. Public sample constants and Git blobs match the retained published samples.','test_mode_blob':git(repo305,'ls-tree',head305,test305).decode().strip(),'actual_Runtime_browser_provenance_cleanup':'NOT_EXERCISED by these five failed controls; V4 product browser HOLD is separate','raw_original_private_log':bind(log305),'scope':'No source edits/test rerun/acquisition/install/runtime execution; LFtoCRLF is an in-memory read-only byte comparison, not hosted rerun','Documentation improvement':{'Canonical file changed or proposed':'docs/skills/repository-operations.md exact owned patch','Exact delta':bind(patch),'Durable learning captured':'Fixed public digest fixture bytes must be committed/authenticated bytes; require valid baseline before poison assertions; retain actual worker strict checks','Evidence':'Current5-node failure, exact observed93e digest and committed790b LF/CRLF byte comparison','Stale or ambiguous guidance removed':'Checkout bytes necessarily equal public member bytes; failed fixture poisons prove boundary rejection or public browser failure','Remaining uncertainty':'Fresh corrected source/CRLF controls/currentCI; no actual full public wheel/coldregistry or V4 browser acceptance'},'Upstream disposition':'none; local test fixture attribution, no maintained upstream defect established'}
p305=out/'305-current-Windows-independent-failure-review.json';p305.write_text(json.dumps(receipt305,indent=2)+'\n')
head282='a0b8816a17b50aae5af1372cf89f71640fa10d3b';repo282='/workspace/engineering/pr282';log282=out/'282-a0-primary-linux-toolkit-original-private.log';s282=log282.read_bytes().decode();assert '1 failed, 1141 passed, 13 skipped' in s282
paths282=['action_server/src/actions/server/deployments/source_staging.py','action_server/src/actions/server/deployments/source_read.py','action_server/tests/contract_tests/test_source_staging.py'];sources282={}
for p in paths282:
    b=git(repo282,'show',head282+':'+p);assert b==git(repo282,'show','ba85aac7324ea4463bfba8c5f8586e27706dc2fe:'+p);sources282[p]={'mode_blob':git(repo282,'ls-tree',head282,p).decode().strip(),'sha256':hashlib.sha256(b).hexdigest()}
receipt282={'verdict':'HOLD_CURRENT282_COMPLETE_CI; GO_BOUNDED_EXECUTED_STAGING_CONTRACT_FAILURE_CENSUS','head':head282,'tested':json.loads((out/'282-a0-test-subject-authenticated.json').read_text()),'live_target':'1c7585fe8bb3cb9476c3997570bd3f04466f2bbc','stale_REST_PR_base_snapshot':'ba85aac7324ea4463bfba8c5f8586e27706dc2fe; not authoritative live target','tested_target_is_prior_fbde_not_live1c75':True,'run':38113263905,'job':114393029554,'only_failed_step':'Package task smoke (Linux)','failed_node':'contract_tests/test_source_staging.py::test_staged_bytes_are_rechecked_and_mutation_cleans_owned_tree','location':'test_source_staging.py:516','counts':{'failed':1,'passed':1141,'skipped':13,'warnings':15,'seconds':120.91},'primary':'Failed: DID NOT RAISE ValueError from expected staged-change rejection','classification':'Executed Runtime source-contract failure after successful gateway preparation/Toolkit; not environment/control-plane acquisition','observed_control_flow':'Hook obtains original chunk then conditionally mutates same-sized staged file; mutated assertion follows raises-block and was not reached. No injection flag/readstage/stat/timestamp/digest observations emitted.','unresolved_cause':'Whether intended mutation fired and actual before/after file observations are UNKNOWN; no proven production mutation bypass, timestamp precision or nondeterminism cause','preserved_guard':'Production rechecks staged digest,size,descriptor/name observations including mtime_ns and ctime_ns; no waiver, cleanup/provenance observations unavailable for this failed testcase','source_modules_and_test_exact292':sources282,'browser_scope':'All39 strict browser predicates unchanged; separate passing Runtime/browser cells do not erase required source-contract failure or relabel prior tested target','raw_original_private_log':bind(log282),'delegated_diagnosis':'windows_311 reuses original acquisition for authorized bounded diagnosis; no source fix/rerun by this reviewer','Documentation improvement':{'Canonical file changed or proposed':'docs/skills/repository-operations.md mutation-evidence paragraph in exact owned patch','Exact delta':bind(patch),'Durable learning captured':'DIDNOTRAISE alone does not establish injection or production verifier failure; source-contract vs acquisition/currenttarget scopes distinct','Evidence':'Exact Toolkit failedstep/node/log plus unchanged staging/read/test Git bytes and control flow; live1c75 versus failed syntheticfbde/a0','Stale or ambiguous guidance removed':'Assertions after failed raises-block report successful injection; successful gateway/browser admission admits whole Toolkit; stale PRbase is true target','Remaining uncertainty':'Precise mutation/read-stage/metadata cause, currenttarget refresh/configuredCI, actual browser tuples and full release contracts'},'Upstream disposition':'none; no maintained upstream defect established'}
p282=out/'282-current-Linux-Toolkit-independent-failure-review.json';p282.write_text(json.dumps(receipt282,indent=2)+'\n')
print(json.dumps({'305':bind(p305),'282':bind(p282),'canonical_proposal':bind(patch)}))
