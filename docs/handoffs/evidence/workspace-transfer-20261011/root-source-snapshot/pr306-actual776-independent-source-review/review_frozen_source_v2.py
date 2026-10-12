from pathlib import Path
import ast,collections,copy,hashlib,json,os,subprocess,yaml
R=Path('/workspace/engineering');repo=R/'pr306';e=R/'pr306-actual776-refresh';out=R/'pr306-actual776-independent-source-review'
H='662014533d8104c1998bce26d91211140acc08e5';D='d3c4cee69ea715779bb28ada0d8fea2ccb72e0d7';A='1a3ab0b580710f776fd2075d39e04720c71541ff';T='77647484b3cdd8e18aabf344a4018ea8ed8e3ea0'
cli='action_server/tests/action_server_tests/test_cli_mcp_resource_history.py';reg='action_server/tests/action_server_tests/mcp/test_resource_history.py';guide='docs/skills/repository-operations.md';owned={cli,reg,guide}
def git(*a):return subprocess.check_output(['git',*a],cwd=repo)
def blob(ref,p):return git('show',ref+':'+p)
def digest(p):b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def leaves(ref):
 return {p.decode():q.decode().split() for row in git('ls-tree','-rz',ref).split(b'\0') if row for q,p in [row.split(b'\t',1)]}
def dump(x):return ast.dump(x,include_attributes=False)
def verify_refs(x):
 seen=[]
 def visit(v):
  if isinstance(v,dict):
   if 'path' in v and 'sha256' in v and isinstance(v['path'],str) and v['path'].startswith('/'):
    p=Path(v['path']);actual=digest(p);assert actual['sha256']==v['sha256'],v['path'];assert 'bytes' not in v or actual['bytes']==v['bytes'];seen.append(actual)
   for z in v.values():visit(z)
  elif isinstance(v,list):
   for z in v:visit(z)
 visit(x);return seen
f=e/'frozen-source-receipt.json';source=json.loads(f.read_text());assert digest(f)['sha256']=='2d85e5b9e3842368e60c2c935680ad2376e0e38e88d832256361fa78f0ae40e6';refs=verify_refs(source);assert len(source['evidence'])==46
assert git('rev-parse','HEAD').decode().strip()==H;assert git('rev-parse','HEAD^{tree}').decode().strip()=='118b7d6f7c51107a08e062825c5fabbb5496975c';assert git('show','-s','--format=%P',H).decode().split()==[D];assert git('show','-s','--format=%P',D).decode().split()==[A,T];assert not git('status','--porcelain')
ls={z:leaves(z) for z in [H,D,A,T]};c,d,a,t=[ls[z] for z in [H,D,A,T]];assert len(c)==1409;assert c.keys()==d.keys()==a.keys()==t.keys();assert {p for p in c if c[p]!=d[p]}==owned;assert all(c[p][0]==d[p][0] for p in c)
novel=[p for p in d if d[p] not in [a[p],t[p]]];assert novel==[guide]
for p in d:
 assert d[p][0]==a[p][0]==t[p][0],p
assert not (collections.Counter(blob(T,guide).splitlines())-collections.Counter(blob(D,guide).splitlines()))
# The accepted target supersedes eleven older RCC paragraph lines; retain every
# source-owned DB/V2/precision paragraph and all accepted target guidance.
oldguide=blob(A,guide).decode();ordinaryguide=blob(D,guide).decode()
removed_old_lines=collections.Counter(oldguide.splitlines())-collections.Counter(ordinaryguide.splitlines())
assert sum(removed_old_lines.values())==11
for line in removed_old_lines:
 assert line not in blob(T,guide).decode().splitlines()
assert git('diff',A,D,'--',guide)==(e/'canonical-imported-accepted-delta.patch').read_bytes()
for start,end in [('For nested database transactions, acquire the SAVEPOINT','Actions Core pull requests'),('RCC environment creation reporting `SUCCESS`','For a native first-readiness timeout'),('Keep the complete terminal failure census','These synthetic observer checks')]:
 section=oldguide[oldguide.index(start):oldguide.index(end,oldguide.index(start))];assert section in ordinaryguide

currenthash={}
for p,v in c.items():
 q=repo/p;b=os.readlink(q).encode() if q.is_symlink() else q.read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==v[2],p;currenthash[p]=hashlib.sha256(b).hexdigest()
pre=json.loads((e/'before-full-source-checkpoint.json').read_text());assert pre['head']==H and pre['tree']==source['tree'];assert pre['tracked_bytes_sha256']==currenthash;assert pre['tracked_leaf_mode_blobs']==c
scope=json.loads((e/'current-handoff-source-scope.json').read_text());assert scope['current_all_tracked_bytes_sha256']==currenthash
# Independently restore only the approved first handoff wait in the current AST.
old=ast.parse(blob(D,cli));new=ast.parse(blob(H,cli));helper=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='_resource_handoff_is_published');new.body.remove(helper)
def native(m):return next(n for n in m.body if isinstance(n,ast.FunctionDef) and n.name=='test_cli_resource_owner_history_across_reload_and_restart')
def first_handoff(n):
 return next(v for v in ast.walk(n) if isinstance(v,ast.For) and any(isinstance(s,ast.Constant) and s.value=='Candidate route was not published: ' for s in ast.walk(v)))
o=first_handoff(native(old));n=first_handoff(native(new));assert len(o.body)==len(n.body)+1;assert dump(ast.Module(body=o.body[2:],type_ignores=[]))==dump(ast.Module(body=n.body[1:],type_ignores=[]));call=n.body[0].value;assert call.func.id=='wait_for_condition';assert dump(call.args[0])==dump(ast.parse('lambda: _resource_handoff_is_published(client)',mode='eval').body);assert [(k.arg,k.value.value) for k in call.keywords if k.arg in ['timeout','sleep']]==[('timeout',30),('sleep',0.05)];assert dump(ast.Module(body=[ast.Expr(value=ast.Call(func=call.func,args=[],keywords=call.keywords))],type_ignores=[]))==dump(ast.Module(body=[ast.Expr(value=ast.Call(func=o.body[1].value.func,args=[],keywords=o.body[1].value.keywords))],type_ignores=[]));n.body=copy.deepcopy(o.body);assert dump(old)==dump(new)
probe=ast.parse((e/'test_handoff_probe_v2.py').read_bytes());ph=next(n for n in probe.body if isinstance(n,ast.FunctionDef) and n.name=='full_handoff');mh=copy.deepcopy(helper);mh.name=ph.name;mh.returns=None;mh.args.args[0].annotation=None
assert dump(ast.Module(body=mh.body[1:3],type_ignores=[]))==dump(ast.parse('assert "result" in surface["resources/list"]\nassert "result" in surface["resources/templates/list"]'))
mh.body[1:3]=copy.deepcopy(ph.body[1:2]);assert dump(mh)==dump(ph)
ro=ast.parse(blob(D,reg));rn=ast.parse(blob(H,reg));assert len(rn.body)==len(ro.body)+1;assert dump(ro)==dump(ast.Module(body=rn.body[:-1],type_ignores=[]));assert rn.body[-1].name=='test_cross_package_handoff_waits_for_previous_declarations_to_disappear'
patch=(e/'proposed-handoff-regression-v2.patch').read_text().splitlines();addition='\n'.join(l[1:] for l in patch if l.startswith('+') and not l.startswith('+++'))+'\n';proposalreg=ast.parse(addition);assert dump(rn.body[-1])==dump(proposalreg.body[0])
# Exact anchored documentation lesson, not only patch headers.
cp=e/'proposed-handoff-canonical-v2.patch';lines=cp.read_text().splitlines();lesson='\n'.join(l[1:] for l in lines if l.startswith('+') and not l.startswith('+++'))+'\n';anchor='Same-owner revisions invoke the current callback and remain permitted.\n';assert blob(H,guide).decode()==blob(D,guide).decode().replace(anchor,anchor+lesson,1);assert len(lesson.splitlines())==10;assert git('diff',D,H,'--',guide)==(e/'actual-handoff-canonical-delta.patch').read_bytes()
# Producer and all five selected test inventories, without exclusions.
nativeid=git('rev-parse','92498aff').decode().strip();oldnative=leaves(nativeid);deps={f'{p}/{s}' for p in ['actions','action_server','actions-http-helper'] for s in ['pyproject.toml','poetry.lock']}
def inputs(m):return sorted(p for p in m if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps)
prod=inputs(c);assert prod==inputs(oldnative) and len(prod)==268;assert all(c[p]==d[p] for p in prod);changedprod=[p for p in prod if c[p]!=oldnative[p]];assert changedprod==['action_server/src/actions/server/_database.py','action_server/src/actions/server/_rcc_runtime_adapter.py'];five=list(json.loads((e/'source-union-proof.json').read_text())['five_selectors']);assert len(five)==5;assert [p for p in five if c[p]!=oldnative[p]]==[cli]
# Complete own bootstrap declared input reuse, and retained actual-origin records.
bp=json.loads((e/'own-Bootstrap-reuse-inputs-and-origins.json').read_text());assert len(bp['inputs_exact_prepared_git_bytes_sha256'])==bp['measured_inputs']==30
bpp=json.loads((R/'pr302-actual310-source-refresh/own-bootstrap-reuse-complete-gateway-proof.json').read_text());bpc=json.loads((R/'pr310-current-refresh/bootstrap-reuse.json').read_text());assert set(bp['inputs_exact_prepared_git_bytes_sha256'])==set(bpp['all19inputs_exact'])|set(bpc['inputs_sha256'])
for p,sha in bp['inputs_exact_prepared_git_bytes_sha256'].items():assert (repo/p).read_bytes()==blob(bp['prepared_source'],p) and currenthash[p]==sha
for package,info in bp['own5venvs_current_config_and_python'].items():
 cfg=repo/package/'.venv/pyvenv.cfg';assert digest(cfg)['sha256']==info['config_sha256'];assert str((repo/package/'.venv/bin/python').resolve())==info['python_resolved']
assert len(bp['own5actual_prefix_and_source_origin_assertions'])==5
for record in bp['own5actual_prefix_and_source_origin_assertions']:
 package=Path(record['prefix']).parent.name;assert record==json.loads((e/('origin-'+package+'.json')).read_text());assert Path(record['prefix'])==repo/package/'.venv';assert Path(record['origin']).is_relative_to(repo/package/'src');assert Path(record['origin']).is_file()
assert bp['new_Bootstrap_executed'] is False
# Byte-exact generated outputs and independently parsed full .github YAML inventory.
gr=json.loads((e/'generator-roundtrip.json').read_text());assert gr['before']==gr['after'];yamlpaths=sorted(p for p in c if p.startswith('.github/') and p.endswith(('.yaml','.yml')));assert len(yamlpaths)==30
for p in yamlpaths:yaml.load(blob(H,p),Loader=yaml.BaseLoader)
assert len(gr['generated_workflows'])==8 and all(c[p]==t[p] for p in c if p.startswith('.github/'))
# Original actual Linux checkout binding remains historical; Windows metadata not logs.
api=json.loads((e/'original1a-tested-commit.raw.json').read_text());assert api['sha']=='11484f93750b51cafc052b46030cfcbd89f2ee18';assert api['commit']['tree']['sha']=='f2bc958f11a15d1f01b5d0d82dd1f3f51bf590fc';assert [p['sha'] for p in api['parents']]==['774438b130afb2ead9bbc1c1b76cb6f91e72150a',A]
priv=e/'original1a-linux-job-114414469493.private.log';assert digest(priv)['sha256']=='6e7a9e074012ecc70df0bd454727183150284385e464e1aee1556bb813eb0de9';original=priv.read_text();assert api['sha'] in original and '131 passed' in original and '17 skipped' in original and '1 failed' in original
# Retained gate output evidence; no gate reruns during independent review.
expected={'doctor.log':['toolkit checks passed','was SUCCESS'],'toolkit.log':['96 passed','was SUCCESS'],'integrated-legacy-handoff-RED.log':['1 failed','was FAILURE'],'integrated-handoff-typed-GREEN.log':['28 passed, 1 deselected','was SUCCESS'],'current-scoped.log':['216 passed, 1 skipped, 14 deselected','was SUCCESS'],'current-static.log':['Unsupported right operand type for in ("object")','was FAILURE'],'current-static-typed-GREEN.log':['Success: no issues found in 337 source files','was SUCCESS'],'current-generator.log':['was SUCCESS'],'current-full-configured-source.log':['1233 passed, 13 skipped, 15 warnings in 132.64s','was SUCCESS']}
for name,tokens in expected.items():
 text=(e/name).read_text();assert all(token in text for token in tokens),(name,tokens)
full=(e/'current-full-configured-source.log').read_text();assert '2 workers' in full
# Final declaration corrections stay distinct from the preliminary construction draft.
draft=e/'frozen-source-receipt-construction-draft.json';assert digest(draft)['sha256']=='efe56fd3b844baae8f7cdfb8a552a81947d7fee71fc4245d44d2ca3c49448eb7';draftbody=json.loads(draft.read_text());assert draftbody['head']==source['head'] and draftbody['validation']==source['validation'] and draftbody['Documentation_improvement']==source['Documentation_improvement'];assert {k for k in draftbody if draftbody[k]!=source[k]}=={'draft_proof_disposition','evidence'}
assert not git('status','--porcelain')
result={'schema':'independent-current776-handoff-source-proof-v1','head':H,'tree':source['tree'],'ordered_parents':[D],'ordinary_parent_order':[A,T],'ordinary_complete_leaf_union':1409,'ordinary_novel_leaves':novel,'ordinary_target_supersedes_old_RCC_lines':dict(removed_old_lines),'all_accepted_target_and_original_DB_V2_precision_guide_blocks_preserved':True,'source_changed_paths':sorted(owned),'source_modes_preserved':True,'current_1409_Gitblob_and_pre_full_SHA256_exact':True,'complete_original_CLI_AST_preserved_after_reversing_only_approved_first_wait':True,'typed_two_fixed_response_asserts_only_proven_helper_AST_refinement':True,'one_regression_exact_proposal_v2_AST_and_all_old_regression_AST_preserved':True,'canonical_10lines_exact_reviewed_dfba_placement':True,'all_268_producer_entries_exact_ordinary':True,'all_current_producer_paths_same_as_historical_native':True,'native_id':nativeid,'native_producer_changes':changedprod,'selected_five_current':{p:c[p] for p in five},'selected_native_changes':[cli],'old_native_qualification':'HOLD','Bootstrap30_inputs_and_5_own_origin_prefix_records_verified_no_install':True,'generated8_parent_bytes_and_all30_YAML_verified':True,'original_actualLinux_tuple_verified_currentnative_qualification':'HISTORICAL_ONLY_UNKNOWN_HOSTED_ORDER_CAUSE','Windows_scope':'METADATA_SUCCESS_ONLY_V2_ARTIFACT_UNAVAILABLE_NO_CHECKOUT_DETAIL_ADMISSION','final_receipt':digest(f),'construction_draft':digest(draft),'pre_freeze_dispatch_identity_disposition':'PRELIMINARY_HOLD_NOT_SOURCE_FAILURE; final owner-announced2d85 authorized by root','all46_final_evidence_hashes_verified':True,'all_verified_source_and_documentation_references':refs,'gate_terminal_tokens_readback':expected,'review_source_gate_runs':0,'source_or_index_mutations':False,'artifact_or_log_downloads':0,'source_worktree_clean_after_review':True,'current_byte_sha256_inventory':currenthash,'Upstream_disposition':'none'}
p=out/'independent-byte-AST-and-evidence-proof.json';p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600);print(json.dumps(digest(p)))
