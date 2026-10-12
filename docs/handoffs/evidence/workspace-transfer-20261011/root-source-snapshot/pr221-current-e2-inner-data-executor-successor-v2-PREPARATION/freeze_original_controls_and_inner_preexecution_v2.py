import ast,hashlib,json,os,stat,xml.etree.ElementTree as E
from pathlib import Path
BASE=Path(__file__).resolve().parent
OWNED=Path('/workspace/engineering/root-current-e2-inner-service-free-controls-v2-once-owned')
OLD=Path('/workspace/engineering/pr221-current-e2-inner-data-executor-PREPARATION')
def bind(p):
 p=Path(p);data=p.read_bytes();return {'path':str(p),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'mode':oct(p.stat().st_mode&0o777)}
def put(name,d):
 p=BASE/name;b=(json.dumps(d,indent=2,sort_keys=True)+'\n').encode();fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o400)
 with os.fdopen(fd,'wb') as f:f.write(b)
 return bind(p)
plan=json.loads((BASE/'OWNERFINAL-current-e2-inner-successor-v2-service-free-CONTROL-PREEXECUTION.json').read_bytes())
for r in plan['evidence']:assert bind(r['path'])==r
terminal=json.loads((OWNED/'original-control-terminal.json').read_bytes());assert terminal['returncode']==0 and terminal['post_bindings']=='PASS'
outer=json.loads((BASE/'root-original-one-control-outer-terminal.json').read_bytes());assert outer['returncode']==0
cases=E.parse(OWNED/'junit.xml').findall('.//testcase');assert len(cases)==50 and all(not list(c) for c in cases if c.tag=='failure')
assert not E.parse(OWNED/'junit.xml').findall('.//failure') and not E.parse(OWNED/'junit.xml').findall('.//error') and not E.parse(OWNED/'junit.xml').findall('.//skipped')
census=put('private-original-control-complete-JUnit-node-census.json',{'cases':[{'classname':c.get('classname'),'name':c.get('name'),'seconds':c.get('time'),'outcome':'PASSED'} for c in cases],'unique':len({(c.get('classname'),c.get('name')) for c in cases}),'passed':50,'failed':0,'errors':0,'skipped':0,'root_returncode':0,'child_returncode':0,'post_bindings':'PASS','source_payload_execution':'NOT_RUN'})
assert len({(c.get('classname'),c.get('name')) for c in cases})==50
originalfiles=[bind(p) for p in sorted(OWNED.rglob('*')) if p.is_file() and not p.is_symlink()]
originalinventory=put('private-complete-one-control-output-file-inventory.json',{'files':originalfiles,'directories_private_root_mode':oct(OWNED.stat().st_mode&0o777),'private_scope':'completeoriginalcontroloutputs retained; no numbered-rootcleanup/no productoutput touched'})
inputs=json.loads((BASE/'frozen-executor-inputs.json').read_bytes())
for r in inputs['bindings']:assert bind(r['path'])==r
canonical=('Data-only inspectors that use assertions must reject optimized Python before\n'
           'reading admission inputs; syntax compilation does not prove those checks ran.\n'
           'Require the root release to be a regular, nonsymlink, mode-0600 file before\n'
           'parsing its typed authorization. Admit all archive headers before reading\n'
           'payloads so a later oversized or special member cannot bypass the initial\n'
           'resource boundary. Exercise the real frozen functions against independent\n'
           'restored baselines and poisons. Structural success retains separate source,\n'
           'generated-content and consumer authority holds.\n')
guide=Path('/workspace/engineering/pr308/docs/skills/repository-operations.md').read_text();anchor='When qualifying generated Runtime frontend content, decode `_static_contents.py`\n';assert guide.count(anchor)==1
import difflib
newguide=guide.replace(anchor,canonical+'\n'+anchor)
p=BASE/'canonical-real-data-inspector-entry-and-boundary-controls-proposed.patch';fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o400)
with os.fdopen(fd,'w') as f:f.write(''.join(difflib.unified_diff(guide.splitlines(True),newguide.splitlines(True),'a/docs/skills/repository-operations.md','b/docs/skills/repository-operations.md')))
canonicalrow=bind(p)
actualrefs=plan['evidence']+[bind(BASE/'OWNERFINAL-current-e2-inner-successor-v2-service-free-CONTROL-PREEXECUTION.json'),bind('/workspace/engineering/pr221-current-e2-inner-v2-control-independent-review/OWNERFINAL-independent-current-e2-inner-v2-service-free-control-PREEXECUTION-review.json'),bind(BASE/'ROOT-one-service-free-control-execution-authorization.json'),bind(BASE/'root-original-one-control-outer-terminal.json'),bind(BASE/'root-outer-stdout.private.log'),bind(BASE/'root-outer-stderr.private.log'),bind(OWNED/'original-control-terminal.json'),bind(OWNED/'stdout.private.log'),bind(OWNED/'stderr.private.log'),bind(OWNED/'junit.xml'),census,originalinventory,canonicalrow,bind(__file__)]
actual=put('OWNERFINAL-original-current-e2-inner-v2-service-free-CONTROLS-actual.json',{'schema':'OWNERFINAL_ORIGINAL_CURRENT_E2_INNER_V2_ACTUAL_SERVICE_FREE_CONTROLS','status':'PASS_REAL_FROZEN_FUNCTION_SERVICE_FREE_CONTROLS_ONLY','proposal_binding':bind(BASE/'OWNERFINAL-current-e2-inner-successor-v2-service-free-CONTROL-PREEXECUTION.json'),'evidence':actualrefs,'census':{'unique':50,'passed':50,'failed':0,'errors':0,'skipped':0,'warnings':499,'pytest_seconds':40.87,'root_elapsed_seconds':outer['elapsed_seconds']},'real_guards':'Actuallauncher8planrefs and activation18+PATH/cachedprefix verifiedbefore/alwayspost; additional executor21historicalbindings rehashed now post-control, not relabeled actuallauncher checks','actual_original_aggregate_inspection':'NOT_RUN','package_import_install_native':'NOT_RUN','shared_product_outputs':'untouched by exactabsoluteownedcontrolargv','remaining_holds':'This is not aggregateinspection, producercheckout/platform/consumer/sourceauthority/generatedOAuth/frontend/release qualification','documentation_improvement':{'Canonical_file_changed_or_proposed':canonicalrow,'Durable_learning':'Unoptimized/privateROOTentry, preflightallheaders and realrestoredbaselinecontrols are executable trust/resource boundaries','Evidence':'50actualcurrent-frozenfunctioncontrols + sourceAST + originalb1f40HOLD kept','Stale_or_ambiguous_guidance_removed':'Syntax-onlyGREEN is not boundaryGREEN; structuralcounts are not consumer/contentauthority','Remaining_uncertainty':'Originalcurrentaggregate innerstillNOTRUN; generatedOAuth/frontend/sourceauthorityhold'},'upstream_disposition':'none'})
oldowner=json.loads((OLD/'OWNERFINAL-current-e2-private-inner-data-executor-PREEXECUTION.json').read_bytes())
newowner=dict(oldowner)
newowner.update({'schema':'OWNERFINAL_CURRENT_E2_INNER_DATA_EXECUTOR_V2_PREEXECUTION','status':'FROZEN_PREEXEC_AFTER_ONE_REAL_SERVICE_FREE_CONTROL_PASS_NOT_INSPECTED','executor_binding':bind(BASE/'inspect_current_e2_inner_once_v2.py'),'manifest_binding':bind(BASE/'frozen-executor-inputs.json'),'predecessor_binding':bind(OLD/'OWNERFINAL-current-e2-private-inner-data-executor-PREEXECUTION.json'),'predecessor_HOLD_binding':bind('/workspace/engineering/pr221-current-e2-inner-independent-review/OWNERFINAL-independent-current-e2-inner-source-and-executable-PREEXECUTION-HOLD.json'),'real_control_actual_binding':actual,'evidence':inputs['bindings']+[bind(BASE/'inspect_current_e2_inner_once_v2.py'),bind(BASE/'frozen-executor-inputs.json'),actual,canonicalrow,bind(__file__)],'exact_argv':['timeout','--signal=TERM','--kill-after=10s','120s','/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python',str(BASE/'inspect_current_e2_inner_once_v2.py'),'--execute-root-reviewed-one-inner-inspection'],'fresh_output_required_absent':'/workspace/engineering/root-current-e2-one-inner-data-inspection-owned-v2','root_release':oldowner['root_release']|{'path':'/workspace/engineering/root-current-e2-one-inner-data-inspection-release-v2.json'},'actual_scope':'One50case private service-freecontrolPASS; originalaggregateinspectionstillNOT_RUN. Independentactual-controlreview/PREEXECGO and newdistinctROOTactualrelease mandatory.','entry_admission':'ExplicitunoptimizedPython/PYOPT refusal beforeassertadmission; regularnonsymlink0600ROOT release beforetyped authorization','function_reuse':'Ten originalfunctions kept:7exact,3previouslyhardened; v2 ZIPnow allheaderpreflight beforeanypayload. Privateguards addedonly; previousexecutorfa649 frozenHOLD retained.','documentation_improvement':{'Canonical_file_changed_or_proposed':canonicalrow,'Durable_learning':'Realboundarycontrols strengthen data-onlyadmission without converting generatedcontent orconsumerHOLD','Evidence':'50PASSzeroSKIP realfunctions/50uniqueJUnit, original015937/b1fHOLD, exact217source/outerACTUALind22eed','Stale_or_ambiguous_guidance_removed':'Rejectoptimizer/privateROOTentry bypass; rejectlateheaderresource failureafterpayloadaccess; prior counts remain expectationsnotoriginalcurrentmeasurement','Remaining_uncertainty':'Currentaggregate innerneverinspected; actualcurrentlayout/RECORD/source/OAuth/frontend unmeasured; releaseholdsseparate'},'upstream_disposition':'none'})
assert not Path(newowner['fresh_output_required_absent']).exists()
final=put('OWNERFINAL-current-e2-inner-data-executor-v2-after-real-controls-PREEXECUTION.json',newowner)
for r in newowner['evidence']:assert bind(r['path'])==r
print(json.dumps({'control_actual':actual,'inspector_preexec':final,'references':len(newowner['evidence']),'originalcontroloutputs':len(originalfiles),'inspector_execution':'NOT_RUN'}))
