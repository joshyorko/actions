"""Read frozen fixture/control receipts and source bytes; no gates/product execution."""
import ast,hashlib,importlib.util,json,subprocess
from pathlib import Path
repo=Path('/workspace/engineering/pr305');root=Path('/workspace/actions-cloud/receipts/pr305-crlf-fixture');own=Path(__file__).parent
head='1e9c462fc16534f1a6153ef666ae60a9ac9560d6';parent='3ec9d0acbe30ad94d02e4c24fef2587127964495';tree='4d72bd113397900be41b720282736f6ab4999fb2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ev(p):p=Path(p);return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
def git(*args):return subprocess.check_output(['git',*args],cwd=repo)
def body(ref,path):return git('show',ref+':'+path)
checkpoint=root/'frozen-test-fixture-source-checkpoint.json';assert sha(checkpoint)=='b5be5088acf921984bac61ac6a39a4be3e1a0152d7168566b08509a07e8a76a0';d=json.loads(checkpoint.read_text())
assert git('rev-parse','HEAD').decode().strip()==head and git('rev-parse','HEAD^{tree}').decode().strip()==tree
assert git('rev-list','--parents','-n1','HEAD').decode().strip().split()==[head,parent];assert git('status','--porcelain')==b''
assert git('branch','--show-current').decode().strip()==d['branch'];assert git('diff','--name-only',parent,head).decode().splitlines()==d['changed_files_only'];assert git('diff','--check',parent,head)==b''
for row in d['evidence_files'].values():assert sha(row['path'])==row['sha256'] and Path(row['path']).stat().st_size==row['bytes']
# Independently require every other Git leaf (body+mode/type) to remain identical.
def leaves(ref):
 rows={}
 for x in git('ls-tree','-r','-z',ref).split(b'\0'):
  if x:
   info,path=x.split(b'\t',1);rows[path.decode()]=info.decode()
 return rows
oldleaves,newleaves=leaves(parent),leaves(head);assert set(oldleaves)==set(newleaves)
changed=[p for p in oldleaves if oldleaves[p]!=newleaves[p]];assert sorted(changed)==d['changed_files_only'];preserved=len(oldleaves)-3
# Synthetic-member fixture: whole original module AST unchanged except exact payload read.
p=d['changed_files_only'][0];old=ast.parse(body(parent,p));new=ast.parse(body(head,p));added={'test_public_probe_fixture_ignores_checkout_newline_conversion'}
new.body=[n for n in new.body if not(isinstance(n,ast.FunctionDef) and n.name in added)]
fn=lambda t,n:next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==n)
a=fn(old,'test_public_probe_admits_exact_sample_and_rejects_boundary_poisons');b=fn(new,a.name)
oldassignment=next(n for n in ast.walk(a) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='payload' for t in n.targets));newassignment=next(n for n in ast.walk(b) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='payload' for t in n.targets));assert 'subprocess.check_output' in ast.unparse(newassignment) and 'HEAD:' in ast.unparse(newassignment)
for n in ast.walk(b):
 for field,value in ast.iter_fields(n):
  if isinstance(value,list):
   for i,item in enumerate(value):
    if item is newassignment:value[i]=oldassignment
assert ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
# Browser module: only PID reader/publication controls and poll-boundary delta.
p=d['changed_files_only'][1];old=ast.parse(body(parent,p));new=ast.parse(body(head,p));new.body=[n for n in new.body if not(isinstance(n,ast.FunctionDef) and n.name in {'_read_browser_harness_pid','test_browser_harness_pid_waits_for_complete_valid_handoff','test_browser_harness_atomically_publishes_actual_node_pid'})]
a=fn(old,'test_browser_harness_deadline_reaps_owned_descendant');b=fn(new,a.name)
ow=next(n for n in ast.walk(a) if isinstance(n,ast.While) and 'not browser_processes' in ast.unparse(n.test));nw=next(n for n in ast.walk(b) if isinstance(n,ast.While) and 'not browser_processes' in ast.unparse(n.test));assert ast.dump(ow.body[0].body[1],include_attributes=False)==ast.dump(nw.body[1].body[0],include_attributes=False);assert ast.dump(ast.Module(body=ow.body[1:],type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=nw.body[2:],type_ignores=[]),include_attributes=False);assert ast.unparse(nw.body[0])=='node_pid = _read_browser_harness_pid(child_pid_file)' and ast.unparse(nw.body[1].test)=='node_pid is not None';nw.body=ow.body
js=lambda t:next(n for n in ast.walk(t) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'import assert from' in n.value)
j=js(new);j.value=j.value.replace('readFileSync, writeFileSync, renameSync','readFileSync, writeFileSync').replace('const pendingPidFile = `${input.process_pid_file}.${process.pid}.tmp`;\n            writeFileSync(pendingPidFile, JSON.stringify({pid: process.pid}), {flag: "wx", mode: 0o600});\n            renameSync(pendingPidFile, input.process_pid_file);','writeFileSync(input.process_pid_file, String(process.pid));');assert ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
# Original public-installed probe, candidate/public behavior, constants, manifests,
# package/frontend bytes and helpers remain leaf-identical; no actual reenactment.
proof=json.loads((root/'source-preservation-proof.json').read_text());assert len(proof['inputs'])==273 and proof['counts']==[268,5]
for p,row in proof['inputs'].items():
 original=body(proof['producer'],p);assert hashlib.sha256(original).hexdigest()==row['sha256'] and body(head,p)==original and (repo/p).read_bytes()==original;assert newleaves[p].split()[0]==row['mode']
bootstrap=json.loads((root/'bootstrap-reuse-verified.json').read_text());assert sha(bootstrap['prior_bootstrap_log'])==bootstrap['prior_log_sha256'];assert len(bootstrap['checked_inputs'])==19
for p in bootstrap['checked_inputs']:assert oldleaves[p]==newleaves[p] and body(bootstrap['inputs_equal_checkpoint'],p)==body(head,p)
for row in bootstrap['all_five_prepared_environment_roots']:
 v=Path(row['venv']);assert sha(v/'pyvenv.cfg')==row['configuration_sha256'];assert str((v/'bin/python').resolve())==row['python_resolved']
# Configured gates and reproduced failures read from exact frozen logs only.
checks={'full-configured-source.log':'1197 passed, 12 skipped, 15 warnings in 135.09s','ToolkitTest.log':'69 passed','source-fixtures-GREEN.log':'46 passed, 2 deselected','portable-actual-boundaries-GREEN-regeneration.log':'18 passed','portable-CRLF-RED-corrected.log':'15 failed','atomic-PID-handoff-RED-after-recovery.log':'3 failed','configured-format-static-corrected.log':'Success: no issues found in 338 source files'}
for f,needle in checks.items():assert needle in (root/f).read_text()
assert '302 files already formatted' in (root/'configured-format-static-corrected.log').read_text() and 'actual main robot run\" was SUCCESS' in (root/'configured-format-static-corrected.log').read_text()
assert all(oldleaves[p]==newleaves[p] for p in oldleaves if p.startswith('.github/'))
regen=(root/'portable-actual-boundaries-GREEN-regeneration.log').read_text();assert sum('Writing to' in x and x.rstrip().endswith('.yml') for x in regen.splitlines())==8
# Read only native bytes with its existing frozen inventory helper; no binary run.
nh=json.loads((root/'retained-native-helper-browser-verification.json').read_text());assert sha(nh['inventory'])==nh['inventory_sha256'];assert sha(nh['browser'])==nh['browser_sha256'];helpers=Path('/workspace/actions-cloud/receipts/pr305-runner/frozen-helpers')
for name,digest in nh['frozen_helpers_0444_unchanged'].items():assert sha(helpers/name)==digest and (helpers/name).stat().st_mode&0o777==0o444
spec=importlib.util.spec_from_file_location('readonly_manifest',helpers/'write_native_artifact_manifest.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
inventory=json.loads(Path(nh['inventory']).read_text());assert len(inventory)==1192 and m.packaged_tree_inventory(Path('/workspace/engineering/pr310-runner-qualification-owned/dist/action-server'))==inventory
actual=Path('/workspace/engineering/pr305-v5-independent-runner-review/independent-actual-v5-review.json');assert sha(actual)=='1848613d69513e20039cee94efe960a3609fff451a582c7a33552c8fa4df1108';ar=json.loads(actual.read_text());assert ar['source']['head']==parent and ar['source']['tree']=='8ed17c0c2ed48a3ad4fe89994bab572d028e59ca'
# Exact accepted output/reporter patch is integrated verbatim; PID proposal adapted
# to actual owned Node publication, not a Chromium PID or cleanup claim.
guide=body(head,'docs/skills/repository-operations.md').decode();patch=Path('/workspace/actions-cloud/receipts/pr305-runner/canonical-runner-v5-proposed.patch');assert sha(patch)=='e84eb7659efef7f349231b1b8b5a80ef5c0d8a2f20e9dc2e1a9d59eea8c3e0b0'
for line in patch.read_text().splitlines():
 if line.startswith('+') and not line.startswith('+++'):assert line[1:] in guide
for s in ['Synthetic published-member fixtures','actual Node PID','does not qualify the','does not establish a live PID identity']:assert s in guide
result={'verdict':'GO_SOURCE_NORMAL_PUSH_ONLY','head':head,'tree':tree,'ordered_parents':[parent],'branch':d['branch'],'checkpoint':ev(checkpoint),'review_script':ev(__file__),'scope':d['changed_files_only'],'preservation':{'all_other_Git_body_mode_type_leaves_identical':preserved,'authoring_installed_raw_probe_constants_public_candidate_arguments_byte_identical':True,'synthetic_module_AST_only_Gitblob_read_plus15controls':True,'browser_module_AST_only_PID_boundary_and_readiness_controls':True,'forcedhang15_livepoll10_future25_total30_postcleanup3_budgets_and_live_assertions_unchanged':True,'all268_plus5_producer_body_modes_working_bytes_exact92498':True,'native_original1192_original_inventory_exact':True,'frozen_helpers_browser_unchanged':True,'all8generated_outputs_unmodified':True,'Bootstrap19inputs5existing_environments_verified_no_install':True},'meaningful_evidence':{'CRLF':'15original exact real-fixture RED; current15controls include3valid baselines+12member/version/ownership/prefix rejections; external15GREEN and source scope46GREEN','PID':'3original empty/incomplete/partial-publication RED; current3external GREEN plus11invalid-pending/new standaloneNode actualpublication control; Node PID only, nobrowser launched','retained_initial_errors':'ENOSPC/import/formatter diagnostic errors retained separately; only corrected command controls qualify','configured_current_gates':d['gates'],'frozen_evidence_refs_verified':len(d['evidence_files'])},'historical_actual':d['historical_actual_V5'],'no_actual_packagegate_browser_provider_install_retry_or_source_mutation_by_reviewer':True,'remaining_HOLD':['Fresh exact1e9c hostedWindows/Mac CI required; old b915 failure not cleared by localsource controls','Real forcedhang browser cleanup and actualcombined successor execution NOT RUN','V5 actualGO remains3ec historical; no successor relabeling','WholeCorewheel/coldregistry/realartifact/ChatGPT/OAuth/private134/release notqualified'],'Documentation improvement':{'Canonical file changed or proposed':'docs/skills/repository-operations.md integrated41line delta','Durable learning captured':'Authenticate committed bytes only for synthetic registry samples; retain strict raw installed-member checks. Publish complete exclusive same-dir JSONNodePID before live-descendant polling; preserve deadlines and distinguish handoff from Chromium identity/cleanup. Retain completedraw before assertions; validate locked exact-case stderr launch channel.','Evidence':[ev(root/'canonical-fixture-and-output-preservation.patch'),ev(patch),ev(root/'portable-CRLF-RED-corrected.log'),ev(root/'atomic-PID-handoff-RED-after-recovery.log'),ev(root/'portable-actual-boundaries-GREEN-regeneration.log')],'Stale or ambiguous guidance removed':'Synthetic checkout bytes are registry authority; file existence means completePID publication; outerstderr is onlyDEBUG channel; fallback may erase completedoutput; sourcefix clears actualfailedcleanup','Remaining uncertainty':'Newhead hosted/forcedhang/actual gates remain pending; originalV5 narrow scope unchanged','Proposal disposition':'e84/ce3 output+locked reporter paragraphs integrated verbatim;72ce PID proposal adapted to verified atomicNode publication and unchanged livegate; original V4 unknownreport remainsunknown'},'Upstream disposition':'none'}
out=own/'independent-frozen-fixture-source-review.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'verdict':result['verdict'],'receipt':ev(out)}))
