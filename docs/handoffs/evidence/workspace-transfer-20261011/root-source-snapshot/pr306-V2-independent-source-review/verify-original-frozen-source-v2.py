import ast, copy, difflib, hashlib, json, pathlib, re, subprocess
repo=pathlib.Path('/workspace/engineering/pr306')
out=pathlib.Path('/workspace/engineering/pr306-V2-independent-source-review')
evidence=pathlib.Path('/workspace/engineering/pr306-windows-v2-source')
cf='cf6352e253c70095c8e09904e730fc18a42f9a65'
parent='e281cbc05dcf2e42d9b37d8879ad986803e6a5e7'
target='774438b130afb2ead9bbc1c1b76cb6f91e72150a'
left='c38e22c74290dca391617e9693fcf5b2968956df'
base='1c7585fe8bb3cb9476c3997570bd3f04466f2bbc'
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
def blob(ref,p):return git('show',ref+':'+p)
def tree(ref):
 d={}
 for e in git('ls-tree','-rz',ref).split(b'\0'):
  if e:
   m,p=e.split(b'\t',1);d[p.decode()]=tuple(m.decode().split())
 return d
def record(p):
 b=pathlib.Path(p).read_bytes();return {'path':str(p),'size':len(b),'sha256':sha(b)}
def write(name,obj):
 p=out/name;p.write_text(json.dumps(obj,indent=2)+'\n');p.chmod(0o444);return record(p)
cp_path=evidence/'implementation-V2-frozen-source-checkpoint.json'
assert sha(cp_path.read_bytes())=='f542bc04747ea8fd8741c309f26de523ee347c8aee82320931f44accf9681be0'
cp=json.loads(cp_path.read_text())
verified=[]
for k,v in cp['evidence_files'].items():
 p=pathlib.Path(v['path']);b=p.read_bytes();assert len(b)==v['size'] and sha(b)==v['sha256'],k;verified.append(record(p))
for p,v in cp['immutable_references'].items():
 b=pathlib.Path(p).read_bytes();assert len(b)==v['size'] and sha(b)==v['sha256'],p;verified.append(record(p))
assert git('show','-s','--format=%T',cf).decode().strip()==cp['tree']
assert git('show','-s','--format=%P',cf).decode().strip()==parent
assert git('show','-s','--format=%P',parent).decode().strip()==left+' '+target
assert git('merge-base',left,target).decode().strip()==base
c,p,l,t,b=[tree(x) for x in (cf,parent,left,target,base)]
allowed=cp['scope_proof']['only_three_authorized_paths']
assert set(c)==set(p) and len(c)==1409
changed=[x for x in c if c[x]!=p[x]];assert sorted(changed)==sorted(allowed)
assert sum(c[x]==p[x] for x in c)==1406
for path in p:
 if path=='docs/skills/repository-operations.md':continue
 expected=t.get(path) if l.get(path)==b.get(path) else l.get(path)
 if l.get(path)!=b.get(path) and t.get(path)!=b.get(path):assert l.get(path)==t.get(path),path
 assert p[path]==expected,path
obs,test,guide=allowed
before=ast.parse(blob(parent,obs));after=ast.parse(blob(cf,obs));normalized=copy.deepcopy(after)
normalized.body=[n for n in normalized.body if not (isinstance(n,ast.ClassDef) and n.name=='DeliveredObservations') and not (isinstance(n,ast.FunctionDef) and n.name=='observe_owned_start') and not (isinstance(n,ast.Import) and any(x.name=='math' for x in n.names))]
for n in normalized.body:
 if isinstance(n,ast.FunctionDef) and n.name=='observe_start':
  i=next(i for i,x in enumerate(n.args.kwonlyargs) if x.arg=='delivered');n.args.kwonlyargs.pop(i);n.args.kw_defaults.pop(i)
  emit=next(x for x in n.body if isinstance(x,ast.FunctionDef) and x.name=='emit');tr=emit.body[0]
  assert isinstance(tr,ast.Try) and isinstance(tr.body[0],ast.If);tr.body.pop(0);tr.handlers[0].body=[ast.Pass()]
  tr=next(x for x in n.body if isinstance(x,ast.Try));tr.finalbody=[x for x in tr.finalbody if not(isinstance(x,ast.If) and ast.unparse(x.test)=='delivered is not None')]
 if isinstance(n,ast.FunctionDef) and n.name=='install':
  calls=[x for x in ast.walk(n) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='observe_owned_start'];assert len(calls)==1
  call=calls[0];assert ast.unparse(call.args[0])=='monkeypatch';call.func.id='observe_start';call.args.pop(0)
assert ast.dump(before)==ast.dump(normalized)
old_tests={n.name:ast.dump(n) for n in ast.parse(blob(parent,test)).body if isinstance(n,ast.FunctionDef)}
new_tests={n.name:ast.dump(n) for n in ast.parse(blob(cf,test)).body if isinstance(n,ast.FunctionDef)}
assert len(old_tests)==8 and all(new_tests[k]==v for k,v in old_tests.items())
newguide=blob(cf,guide).decode();oldguide=blob(parent,guide).decode();addition=(evidence/'exact-canonical-V2-added-paragraphs.md').read_text()
assert newguide.count(addition)==1 and newguide.replace(addition,'',1)==oldguide
assert len(addition.splitlines())==36
for path in ['AGENTS.md','docs/skills/README.md','.agents/skills/actions-repository/SKILL.md','docs/skills/upstream-reporting.md']:
 assert c[path]==p[path]
prod=json.loads((evidence/'current-full-producer-and-selected5-preservation.json').read_text())
assert len(prod['current268_input_full_records'])==268
native=tree(prod['native_producer']);deltas=[]
for path,v in prod['current268_input_full_records'].items():
 assert c[path]==(v['mode'],v['kind'],v['blob']) and sha(blob(cf,path))==v['sha256']
 if c[path]!=native[path]:deltas.append(path)
assert deltas==['action_server/src/actions/server/_database.py']
assert prod['selected5_inputs_exact_original'] is True
# Original selected-five table is backed by exact Git bytes in producer receipt and source preservation.
gh=json.loads((evidence/'github-complete-and-both-YAML-extensions-successor-inventory.json').read_text())
paths=[x for x in c if x.startswith('.github/')];assert len(paths)==34
assert len([x for x in paths if x.endswith(('.yaml','.yml'))])==30
assert len([x for x in paths if x.endswith('.yml')])==29
for path,v in gh['complete_github_files_sha256'].items():
 assert c[path]==p[path]==t[path] and ' '.join(c[path])==v['mode_kind_blob']
 assert sha(blob(cf,path))==v['sha256']
boot=json.loads((evidence/'own-Bootstrap-reuse-inputs-and-origins.json').read_text())
assert len(boot['inputs_exact_prepared_git_bytes_sha256'])==30
for path,digest in boot['inputs_exact_prepared_git_bytes_sha256'].items():
 assert sha(blob(cf,path))==digest and c[path]==tree(boot['prepared_source'])[path]
assert sha(pathlib.Path(boot['original_bootstrap_log']).read_bytes())==boot['original_bootstrap_log_sha256']
for package,v in boot['own5venvs_current_config_and_python'].items():
 env=repo/package/'.venv';assert sha((env/'pyvenv.cfg').read_bytes())==v['config_sha256'];assert str((env/'bin/python').resolve())==v['python_resolved']
for v in boot['own5actual_prefix_and_source_origin_assertions']:
 assert str(repo) in v['prefix'] and v['origin'].startswith(str(repo)+'/');assert pathlib.Path(v['origin']).is_file()
# Inspect only known result summary lines in frozen logs. Do not expose original log bodies.
log_patterns={
 'observer-V2-preimplementation-RED-real-result.log':r'33 failed, 10 passed',
 'observer-V2-final-privacy-GREEN.log':r'58 passed',
 'final-scoped-static-corrected.log':r'80 passed',
 'current-generation-and-complete-DB-source.log':r'61 passed, 12 skipped',
 'current-ToolkitTest.log':r'69 passed',
 'current-full-configured-source.log':r'1202 passed, 13 skipped',
}
for name,pattern in log_patterns.items():assert re.search(pattern,(evidence/name).read_text()),name
static=(evidence/'final-scoped-static-corrected.log').read_text();assert '337 source files' in static
# Static scalar counterexample only; source module never imported or executed.
source=blob(cf,obs).decode();lines=source.splitlines();assert 'return round(value, 3)' in source
start=2.06651;arrival=92.06661;rounded_start=round(start,3);rounded_arrival=round(arrival,3)
exact=arrival<start+90;display=rounded_arrival<rounded_start+90
assert exact is False and display is True
finding={'id':'READY_DEADLINE_DISPLAY_ROUNDING_FALSE_PREDEADLINE','classification':'Actions test-observer correctness; no established upstream or native cause',
 'source':{'head':cf,'path':obs,'sha256':sha(blob(cf,obs)),
 'offset_rounding_line':next(i+1 for i,x in enumerate(lines) if 'return round(value, 3)' in x),
 'threshold_line':next(i+1 for i,x in enumerate(lines) if 'offset < self.start_return_offset + 90' in x)},
 'counterexample':{'private_start_return_offset':start,'private_arrival_offset':arrival,'exact_deadline_lower_bound':start+90,'serialized_start':rounded_start,'serialized_arrival':rounded_arrival,'rounded_computed_lower_bound_repr':repr(rounded_start+90),'exact_predeadline':exact,'cf6352_predeadline':display},
 'scope':'Static source plus standard-library scalar arithmetic only; no source import/test/native/gateway execution',
 'required_fix':'Retain private unrounded monotonic instants for strict less-than classification; round only serialized display. Equality and post-bound delivery must remain false across fractional origins.',
 'prior_guidance_disposition':'cf6352 implemented the 36-line guide, but predeadline attribution claim is HOLD until successor precision controls and source independently qualify; other scope/privacy/cleanup descriptions remain source-backed.',
 'root_and_writer_disposition':'Root accepted HOLD and authorized separate ordinary-child precision fix. This receipt does not assess mutable successor or reuse cf6352 full results for successor.'}
finding_ref=write('original-cf6352-precision-finding.json',finding)
needle='match does not establish predeadline delivery. Future state, native ready-log\n'
replacement='match does not establish predeadline delivery. Compare unrounded monotonic\ninstants for deadline classification and round only serialized offsets; display\nrounding can turn equal or post-bound delivery into a false predeadline claim.\nFuture state, native ready-log\n'
assert newguide.count(needle)==1
proposal=newguide.replace(needle,replacement,1)
patch=''.join(difflib.unified_diff(newguide.splitlines(keepends=True),proposal.splitlines(keepends=True),fromfile='a/'+guide,tofile='b/'+guide))
p=out/'exact-precision-canonical-proposal.patch';p.write_text(patch);p.chmod(0o444);patchref=record(p)
result={'status':'HOLD_ORIGINAL_CF6352_READY_DEADLINE_PRECISION_NO_PUSH_GO',
 'source':{'head':cf,'tree':cp['tree'],'ordered_parents':[parent]},
 'immutable_source_not_mutable_checkout':True,
 'verified_checkpoint':record(cp_path),'verified_evidence_files_count':len(cp['evidence_files']),'verified_immutable_references_count':len(cp['immutable_references']),
 'evidence':verified,'source_preservation':{'total_leaves':1409,'exact_other_leaves_modes':1406,'authorized_paths':allowed,'ordinary_parent_non_doc_union_exact':True,'normalized_original_observer_AST_exact':True,'original_test_functions_AST_exact':list(old_tests),'canonical_added_lines':36,'producer_inputs':268,'producer_delta_only':deltas,'selected_five_report':True,'github_leaves':34,'yaml_yml_inventory_count':30,'original_yml_roundtrip_scope':29,'bootstrap_inputs_exact':30,'own_environment_configs_and_retained_origins':5},
 'reviewed_no_additional_blocker':['Two FIRST Windows native actions_sync timeout90 allowlist, unchanged90/20/80/88/50ms/other30s behavior','Existing callback delivery only; no new readers, processes, launch/argv/env/port/Future/stop/kill/wait','Nonblocking measurement loss, invalid marks, version/count/cap/truncation/overflow permanently disqualify invocation sum','Probe failures caught before Callback logger.exception; fixed scalar/categories only','Process wrappers limited by identity; exact original args/kwargs, tuple/result and exception object preserved','Actual returned cleanup result distinguished from host state, None/unavailable and raised; no inferred successful cleanup'],
 'finding':finding_ref,'remaining_counterexamples':'No additional counterexample found in immutable cf6352 review. Successor unreviewed; root coordinates its own full gate and freeze.',
 'original_configured_results_only':cp['validation'],'original_windows_failure':cp['original_failed_Windows'],'native_92498':cp['native_92498'],
 'remaining_HOLDs':cp['remaining_HOLDs']+['cf6352 strict predeadline attribution has precision defect; no normal-push GO for cf6352','Mutable precision successor needs separate immutable source/control review and current full gates'],
 'Documentation_improvement':{'Canonical_file_changed_or_proposed':guide+'; exact precision proposal external to checkout','Durable_learning_captured':'Unrounded monotonic instants determine strict deadline classification; rounding belongs only to serialized display. Fractional clock origins must be controlled.',
 'Evidence':[finding_ref,patchref,'Immutable cf6352 _offset and threshold source; concrete static false predeadline counterexample'],
 'Stale_or_ambiguous_guidance_removed':'Qualifies cf6352 guide claim that late markers cannot be attributed predeadline; the claim is not implemented correctly until raw-instant successor is qualified.',
 'Remaining_uncertainty':'Successor source/control/full gate and hosted Windows actual evidence; native internal emitter/pipe/Future, actual root cause, current native producer, private/release remain HOLD.',
 'Prior_36_line_delta_disposition':'Retained ae0e988c source-backed scope/privacy/cleanup guidance; timing-attribution implementation claim blocked specifically by this finding until separately reviewed precision successor.',
 'exact_proposed_patch':patchref},'Upstream_disposition':'none; local Actions test observer defect, no confirmed upstream failure or authorized external mutation'}
receipt=write('independent-original-cf6352-source-review-HOLD.json',result)
print(json.dumps({'receipt':receipt,'finding':finding_ref,'canonical_proposal':patchref,'status':result['status'],'other_leaves':1406,'evidence_verified':len(verified),'additional_counterexamples':'none found'},indent=2))
