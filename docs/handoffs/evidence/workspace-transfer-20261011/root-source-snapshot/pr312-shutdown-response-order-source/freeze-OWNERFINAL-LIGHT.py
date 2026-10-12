import ast,hashlib,json,os,stat,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
R=Path('/workspace/engineering/runtime-checkout-eol');D=Path('/workspace/engineering/pr312-shutdown-response-order-source')
PARENT='77065131a0aee63d2b1f8621476374bdde3c7b65';TARGET='a0d258a16095b95b1bf9000cb1201cddfaff4779'
def git(*a):return subprocess.check_output(['git',*a],cwd=R)
def bind(p):
 p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
head=git('rev-parse','HEAD').decode().strip();tree=git('rev-parse','HEAD^{tree}').decode().strip()
assert head=='77ed3de24f33412dff30e4e3c18841c4c09933ac' and tree=='943c9b88d5d508a4c59b0461b6220ec86e1a7d62'
assert git('show','-s','--format=%P',head).decode().strip()==PARENT
assert not git('status','--porcelain=v1')
assert git('merge-base','--is-ancestor',TARGET,head)==b''
pre=json.loads((D/'immutable-pre-edit-original770-all1423-and-source-final-CI-retention.json').read_text())
for row in pre['distinct_preserved_refs']:
 observed=bind(row['path']);assert observed['bytes']==row['bytes'] and observed['sha256']==row['sha256'],row['path']
entries=[]
for line in git('ls-tree','-r','-z',head).split(b'\0'):
 if not line:continue
 meta,name=line.split(b'\t',1);mode,kind,blob=meta.decode().split();name=name.decode();assert kind=='blob'
 p=R/name;data=p.read_bytes();body=git('cat-file','blob',blob)
 assert body==data,name
 assert bool(p.stat().st_mode&0o111)==(mode=='100755'),name
 entries.append({'path':name,'mode':mode,'blob':blob,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()})
assert len(entries)==1424
old={x['path']:x for x in pre['entries']};now={x['path']:x for x in entries}
changed=[n for n in old if old[n]!=now[n]];added=sorted(set(now)-set(old))
assert sorted(changed)==['action_server/src/actions/server/_server.py','docs/skills/repository-operations.md']
assert added==['action_server/tests/action_server_tests/test_shutdown_response_order.py']
proof={'head':head,'tree':tree,'sole_parent':PARENT,'actual_target_ancestor':TARGET,'all1424_Git_FS_body_exec_exact':True,'entries':entries,'unchanged_original_parent_leaves':1421,'original1423parent_no_deletion':True,'changed_old_paths':sorted(changed),'added_paths':added,'all141original_bound_refs_exact':True,'constructor':bind(__file__)}
p=D/'immutable-post-LIGHT-committed-all1424-typed-source-proof.json'
with p.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
p.chmod(0o600)
def census(path):
 cases=ET.parse(path).getroot().findall('.//testcase');names=[x.attrib['classname']+'::'+x.attrib['name'] for x in cases]
 assert len(names)==len(set(names))
 return {'items':len(cases),'PASS':sum(not any(x.find(t) is not None for t in ('failure','error','skipped')) for x in cases),'FAIL':sum(x.find('failure') is not None for x in cases),'ERROR':sum(x.find('error') is not None for x in cases),'SKIP':sum(x.find('skipped') is not None for x in cases),'names':names}
red=census(D/'ordering-RED-junit.xml');green=census(D/'ordering-GREEN-junit.xml');final=census(D/'final-scoped-junit.xml')
assert (red['items'],red['PASS'],red['FAIL'],red['ERROR'],red['SKIP'])==(10,5,5,0,0)
assert (green['items'],green['PASS'],green['FAIL'],green['ERROR'],green['SKIP'])==(10,10,0,0,0)
assert (final['items'],final['PASS'],final['FAIL'],final['ERROR'],final['SKIP'])==(86,86,0,0,0)
assert set(green['names'])==set(red['names']) and set(green['names']).issubset(final['names'])
log=(D/'final-cached-LIGHT.private.log').read_text();assert 'PURE_CACHED_SHUTDOWN_LIGHT_ALL_PASS' in log and '96 passed' in log and '10 passed' in log and '314 files already formatted' in log and 'no issues found in 350 source files' in log
files=[x for x in D.iterdir() if x.is_file() and x.name!='OWNERFINAL-pr312-shutdown-response-order-LIGHT-source-checkpoint.json']
refs=[bind(x) for x in sorted(files)]
result={'schema':'actions-pr312-assembled-shutdown-response-order-LIGHT/v1','status':'OWNERFINAL_LIGHT_SOURCE_READY_FOR_INDEPENDENT_REVIEW_FULL_AND_CI_HOLD','head':head,'tree':tree,'sole_parent':PARENT,'actual_target':TARGET,'existing_branch':git('branch','--show-current').decode().strip(),'clean':True,'complete_typed_proof':bind(p),'before_source':bind(D/'immutable-pre-edit-original770-all1423-and-source-final-CI-retention.json'),'before_commit':bind(D/'immutable-before-commit-LIGHT-preservation-proof.json'),'preserved_original_bound_refs':pre['ref_count'],'novel_scope':{'allowed_paths':sorted(changed)+added,'unchanged_parent_leaves':1421,'old_parent_leaves':1423,'current_leaves':1424,'all_original_non_guide_EOLog_paths_exact':True,'whole_original_server_AST_after_two_declared_changes_exact':True,'no_original_integration_node_or_status_or_exit_or_timeout_changes':True},'implementation':'Existing guarded/authenticated POST shutdown schedules original _thread.interrupt_main as existing FastAPI response BackgroundTasks; timeout default/query and JSONnull response remain; Starlette completes final ASGI body send before task; failed sends and denied requests do not run task. No guarantees of TCP client receipt.', 'measured_source_controls':{'original_prepytest_cached_setup_failure':'FileNotFoundError poetry before pytest; no test counts/RED claim; immutable owner5c61 retained. Named PATH correction uses existing owned cached holotreebin only, frozen activation unchanged, no installer/gateway.','genuine_original_behavior_RED':red,'first_source_GREEN':green,'final_after_AST_equivalent_format_scoped_auth':final,'Toolkit':{'PASS':96,'seconds':15.85},'original_EOLog_scoped':{'PASS':10,'seconds':4.53},'Doctor':'PASS cached prepared toolchain; no RCC gateway invoked','Bootstrap':'30 checked prepared source inputs; five actual own prefixes and concrete source origins; no install','configured_Runtime_lint':'PASS Ruffcheck/Ruffformat314/Isort; Markdownlint unavailable existing warning preserved','configured_Runtime_typecheck':'PASS350files; existing annotation-unchecked notes preserved','generator':'8 generated outputs plus dependabot/all30trackedYAML bytes exact'},'execution':'PURE_CACHED_TOOLKIT_ONLY; owned pinned holotree Python/Poetry and managed activation plus explicit reviewed binPATH; zero RCC gateway/native/provider/browser/full executions','private_refs':refs,'documentation_improvement':{'canonical_file':'docs/skills/repository-operations.md','exact_delta':bind(D/'exact-canonical-response-order-and-client-completion.patch'),'learning':'Replace stale synchronous shutdown-call description with response BackgroundTasks after completed ASGI finalbody; explain denied/failedsend no interrupt, access200 is not clientdelivery, keep naturalexit/cleanup distinct.','evidence':'Genuine5FAIL5PASS RED, 10GREEN, final86 real assembled/auth tests; original owned Windows ReadError10053 after access200.','stale_removed':'Synchronous endpoint-call wording now qualified by exact response-send ordering.','uncertainty':'Windows TCP client delivery and expected naturalrc1 remain fresh platform acceptance, no EOLcausal claim/no universal cleanup.'},'remaining_HOLD':['ONE affected-package configured full after independent LIGHT and distinct root serialized release/fresh capacity','Fresh complete current-head CI and original strict watched Windows client200/naturalrc1 result','Whole frozen/native inputs unqualified after new server production change; no old artifact carry','Runtime1.0.3/OAuthsourceauthority/fullrelease/private134/99/backend/ChatGPT gates unchanged'],'constructor':bind(__file__),'Upstream_disposition':'none'}
owner=D/'OWNERFINAL-pr312-shutdown-response-order-LIGHT-source-checkpoint.json'
with owner.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
owner.chmod(0o600);print(json.dumps(bind(owner)))
