"""Preparation only: metadata/hash/AST checks; never run the data inspector."""
import ast,hashlib,json,os,stat
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PREP=Path('/workspace/engineering/pr221-current-e2-inner-distribution-inspection-PREPARATION')
OLDPROPOSAL=PREP/'OWNERFINAL-current-e2-exact-source-and-inner-distribution-reuse-PROPOSAL.json'
SOURCE=PREP/'private-authentic-e2-tracked-source-and-generated-input-expectations.json'
OUTER=Path('/workspace/engineering/root-current-e2-one-existing-original-outer-inspection-owned')
IND=Path('/workspace/engineering/pr221-current-e2-original-outer-inspection-independent-review/OWNERFINAL-independent-current-e2-original-outer-inspection-ACTUAL-data-integrity-review-v2.json')
def sha(data):return hashlib.sha256(data).hexdigest()
def bind(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode)
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return {'path':str(p),'bytes':s.st_size,'sha256':h.hexdigest(),'mode':oct(stat.S_IMODE(s.st_mode))}
def write(p,d):
 b=(json.dumps(d,indent=2,sort_keys=True)+'\n').encode();fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o400)
 with os.fdopen(fd,'wb') as f:f.write(b)
 return bind(p)
old=json.loads(OLDPROPOSAL.read_bytes());assert bind(OLDPROPOSAL)['sha256']=='2dac6a6cf0641a2a6f6c1165dc05ed17225e720b49bc2dbd1b25ad18b922efb0'
ind=json.loads(IND.read_bytes());assert bind(IND)['sha256'].startswith('22eed535')
source=json.loads(SOURCE.read_bytes());assert source['tracked_actions_files']==217 and source['tracked_python_files']==202 and source['tracked_nonpython_files']==15
bindings=old['frozen_bindings']+[bind(OLDPROPOSAL),bind(IND),ind['actual_root_owner_binding'],ind['actual_result_binding'],ind['original_failure_owner_binding'],bind(OUTER/'private-original-eight-member-outer-inventory.json')]
ziprow=json.loads((OUTER/'OWNERFINAL-one-existing-original-outer-inspection-result.json').read_bytes())['whole_ZIP'];bindings.append(ziprow)
for r in bindings:assert bind(r['path'])==r
cfg={'schema':'CURRENT_E2_INNER_DATA_EXECUTOR_FROZEN_INPUTS','bindings':bindings,'source_expectations':source,'zip_binding':ziprow,'outer_inventory':json.loads((OUTER/'private-original-eight-member-outer-inventory.json').read_bytes()),'outer_independent':bind(IND),'outer_result':ind['actual_result_binding']}
m=write(ROOT/'frozen-executor-inputs.json',cfg)
p=ROOT/'inspect_current_e2_inner_once.py';s=p.read_text().replace('__MANIFEST_SHA__',m['sha256']);p.write_text(s);os.chmod(p,0o400)
compile(s,str(p),'exec') # Compilation only: does not execute/import the module.
new=ast.parse(s);oldtext=Path(old['reuse']['accepted_old_inspector']['path']).read_text();oldast=ast.parse(oldtext)
f=lambda t:{n.name:sha(ast.dump(n,include_attributes=False).encode()) for n in t.body if isinstance(n,ast.FunctionDef)}
a,b=f(oldast),f(new);names=[r['name'] for r in old['reuse']['functions']]
proof=write(ROOT/'syntax-and-accepted-function-AST-only-proof.json',{'schema':'PREPARATION_SYNTAX_AST_ONLY','executor':bind(p),'syntax_compile':'PASS_NO_EXECUTION','inspector_archive_execution':'NOT_RUN','controls':'NOT_RUN_DURING_ROOT_FULL','ten_functions':[{'name':n,'old_AST_sha256':a[n],'new_AST_sha256':b[n],'exact':a[n]==b[n]} for n in names],'expected_changes':{'zip_payload':'narrow128MiB expanded/64MiB member caps; strict regular/directory types/case uniqueness','inspect_wheel':'narrow64MiB compressed, exactfourdistinfo/RECORD counts,217source+generatedwhitelist, data-onlyreference/staticcategories','inspect_sdist':'narrowcaps/streamcensus/case/types; wholegzipCRCISIZEEOF;217source+OAuth whitelist; data-onlyreference/staticcategories'},'immutable_reference':'outerZIP+member+digest only; no extraction/copy','same_functions_exact':sum(a[n]==b[n] for n in names)})
proposal={'schema':'OWNERFINAL_CURRENT_E2_INNER_DATA_EXECUTOR_PREEXECUTION','status':'FROZEN_PREPARATION_ONLY_NOT_EXECUTED','source':old['source'],'tree':old['tree'],'artifact_id':11708952448,'producer_identity':old['producer_identity'],'executor_binding':bind(p),'manifest_binding':m,'proposal_predecessor':bind(OLDPROPOSAL),'outer_actual_independent_binding':bind(IND),'original_transfer_failure_binding':ind['original_failure_owner_binding'],'outer_actual_result_binding':ind['actual_result_binding'],'evidence':bindings+[m,bind(p),proof,bind(__file__)],'exact_argv':['timeout','--signal=TERM','--kill-after=10s','120s','/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python',str(p),'--execute-root-reviewed-one-inner-inspection'],'cwd':'/workspace','env_contract':'Inherited environment; no RCC/Poetry/product imports, no installer/network. Standard-library data-only executor; no managed-toolchain changes.','bounds':{'whole_command_seconds':120,'kill_grace_seconds':10,'internal_alarm_seconds':110,'memory_bytes':805306368,'original_compressed_bytes_ceiling':100663296,'inner_expanded_bytes_ceiling':134217728,'inner_single_bytes_ceiling':67108864,'inner_entry_ceiling':5000,'output_bytes_ceiling':8388608},'root_release':{'path':'/workspace/engineering/root-current-e2-one-inner-data-inspection-release.json','schema':'ROOT_ONE_CURRENT_E2_INNER_DATA_INSPECTION','execute':True,'proposal_binding':'exactthisOWNER','independent_review_binding':'exactowner-announcedindependentreviewwithproposal_binding','independent_decision':'GO_CURRENT_E2_INNER_DATA_INSPECTION_PREEXECUTION'},'fresh_output_required_absent':'/workspace/engineering/root-current-e2-one-inner-data-inspection-owned','outputs_mode':'0700 directory /0600 private JSON','cleanup':'No inputs removed/extracted/copied. Partial JSON and primary/secondary exceptions retained on failure; no retry. Bindings/Git-source fingerprints checked before and in finally after inspection.','expected_not_yet_observed':{'tracked':217,'trackedPython':202,'trackedNonPython':15,'wheelPackage':219,'wheelPython':203,'wheelRECORD':223,'wheelRECORDhashed':222,'sdistPackage':218},'assertion_scope':'All derived217 exactsourceentries accounted; exactgeneratedOAuth+platformRCC exceptions; RECORD/hash/size/selfonly; fourdistinfo+metadata/deps/scripts/tags; sdistsourcepyproject. Body/mode differences retained individually as sourceauthority HOLD; not semantic equivalence.','actual_scope':'NOT_RUN. No controls or package/inspector execution during ROOT FULL. Only source construction, standard-library syntax compile and AST/hash checks.','remaining_holds':old['source_expected']|{'release':'All install/consumer/native/private/platform/sourceauthority/OAuth/publication gates separate; counts above not measured until authorized inspection.'},'documentation_improvement':old['documentation_improvement']|{'Evidence':'Current217 authenticGitmanifest + actualoriginalouter51d8/ind22eed535 + ten acceptedfunctionsAST proof. Structural integrity never admits emptyOAuth/HTML or generatedfrontend sourceauthority.','Remaining_uncertainty':'Inspector and controls NOT_RUN; concrete executor requires independent PREEXEC and distinct root authorization. Current body/metadata counts unobserved.'},'upstream_disposition':'none; original transfer boundary is local executor failure, no authorized external mutation'}
owner=write(ROOT/'OWNERFINAL-current-e2-private-inner-data-executor-PREEXECUTION.json',proposal)
for r in proposal['evidence']:assert bind(r['path'])==r
print(json.dumps({'owner':owner,'executor':bind(p),'manifest':m,'AST_same_functions':sum(a[n]==b[n] for n in names),'references':len(proposal['evidence']),'execution':'NOT_RUN'}))
