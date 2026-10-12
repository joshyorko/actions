from pathlib import Path
import subprocess,json,hashlib,stat,os,ast,re,zipfile
R=Path('/workspace/engineering/pr308');D=Path('/workspace/engineering/pr308-actual299-independent-control-review');O=Path('/workspace/engineering/pr308-actual299-control-refresh');S=Path('/workspace/engineering/pr308-actual299-source-refresh')
H='d5a3d2f53737f4f5380b6ecb7fb93d1a651f005d';T='fa3f7728d315c9a192f88e17acf15f164d4eee13';A='c10380a4d2ebc6f0aca63eb85c8f84a337da4962';AT='21676c626a933c2d55761ec85ecf26fe0eef26bb';B='6181b044c75de35386f1ae30e71725398b6a7feb';N='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e';V='3ec9d0acbe30ad94d02e4c24fef2587127964495'
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def leaves(c):return {n.decode():meta.decode().split() for row in git('ls-tree','-rz',c).split(b'\0') if row for meta,n in [row.split(b'\t',1)]}
owner=O/'CONTROL-frozen-owner-final-checkpoint.json';assert owner.stat().st_size==141218 and sha(owner)=='c646a010c8b4108f19a6897761a6cd6469f59d8ff90b7e2ecd700eadac37832c'
v=json.loads(owner.read_text());refs=[]
def inspect(x):
 if isinstance(x,dict):
  if {'path','sha256'}<=x.keys() and isinstance(x['path'],str) and x['path'].startswith('/'):
   assert sha(x['path'])==x['sha256'];e=bind(x['path']);assert 'bytes' not in x or e['bytes']==x['bytes'];refs.append(e)
  for e in x.values():inspect(e)
 elif isinstance(x,list):
  for e in x:inspect(e)
inspect(v);assert len(v['evidence_refs'])==188 and len({e['path'] for e in v['evidence_refs']})==188
assert hashlib.sha256(json.dumps(sorted(v['evidence_refs'],key=lambda e:e['path']),sort_keys=True,separators=(',',':')).encode()).hexdigest()==v['evidence_refs_fingerprint_sha256']
assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse',H+'^{tree}').decode().strip()==T and git('show','-s','--format=%P',H).decode().split()==[A] and git('status','--porcelain')==b'' and git('branch','--show-current').decode().strip()==v['branch']=='fix/rcc-candidate-wheel-identities-20261010'
assert git('rev-parse',A+'^{tree}').decode().strip()==AT and git('show','-s','--format=%P',A).decode().split()==v['SOURCE_ordered_parents'] and v['SOURCE_ordered_parents'][1]==B
source=json.loads(Path(v['SOURCE_owner_final']['path']).read_text());ind=json.loads(Path(v['SOURCE_independent_GO']['path']).read_text());assert v['SOURCE_owner_final']['sha256']=='de231c011ee899c8e3ce6c6de4f2448136350758231f3f873f760d30600f4678' and v['SOURCE_independent_GO']['sha256']=='9480a381d5be565b70c34c7b1672cecbb651159dad4595021e74fa5ff9836f25'
assert v['all147_original_SOURCE_refs_byte_hash_size_exact']==source['evidence_refs'] and len(source['evidence_refs'])==147
c,a=leaves(H),leaves(A);assert len(c)==len(a)==1419 and set(c)==set(a)
paths={'.github/workflows/_gen_workflows.py','.github/workflows/actions_runtime_rcc_provider_rollback.yml','developer/tests/test_rcc_provider_rollback_workflow.py'}
assert {p for p in c if c[p]!=a[p]}==paths
pre=json.loads((O/'precommit-CONTROL-all-source-and-original-input-proof.json').read_text());post=json.loads((O/'postcommit-CONTROL-all-source-and-original-input-proof.json').read_text());assert pre==post
rows=post['all1419_current_typed_body_modes_execbits'];assert len(rows)==1419 and len({e['path'] for e in rows})==1419
staged=json.loads((O/'staged-CONTROL-tree-all1419-proof.json').read_text());assert staged['staged_tree']==T and staged['all1419_staged_body_modes_execbits_equal_precommit_proof']
for e in rows:
 p=e['path'];body=(R/p).read_bytes();assert c[p]==[e['mode'],'blob',e['blob']] and len(body)==e['bytes'] and hashlib.sha256(body).hexdigest()==e['sha256'] and body==git('show',H+':'+p);assert bool((R/p).stat().st_mode&0o111)==(e['mode']=='100755')
 if p not in paths:assert c[p]==a[p]
oldS='7eb5bce946750555ab009f77592862920a901506';oldT='3ff76037779763d0461ff3a755b900c9ed83dcf8'
changes=[]
for p in sorted(paths):
 before=git('show',A+':'+p);after=git('show',H+':'+p);assert after.replace(A.encode(),oldS.encode()).replace(AT.encode(),oldT.encode())==before
 assert c[p][0]==a[p][0]=='100644'
 if p.endswith('.py'):assert ast.dump(ast.parse(after.replace(A.encode(),oldS.encode()).replace(AT.encode(),oldT.encode())),include_attributes=False)==ast.dump(ast.parse(before),include_attributes=False)
 changes.append({'path':p,'mode':c[p][0],'before_blob':a[p][2],'current_blob':c[p][2],'source_sha_occurrences':after.count(A.encode()),'source_tree_occurrences':after.count(AT.encode()),'whole_bytes_equal_after_only_source_identity_substitution':True})
assert [e['source_sha_occurrences'] for e in changes]==[1,3,1] and [e['source_tree_occurrences'] for e in changes]==[1,2,1]
assert git('diff',A,H,'--',*sorted(paths))==(O/'exact-three-CONTROL-path-pins.patch').read_bytes()
ctor=Path(v['immutable_constructor']['path']);assert ctor.stat().st_size==7541 and sha(ctor)=='b1a4393281c1de7dc7a4be026fd3cadb3b33b862df6daa45b3a79e745c338f59';ctorBody=ctor.read_text();assert H in ctorBody and T in ctorBody and "assert not p.exists()" in ctorBody and "assert git('rev-parse','HEAD')==H" in ctorBody
nine=v['current_nine_candidate_body_Gitpins'];assert nine['SOURCE']==A and nine['CONTROL']==H and len(nine['nine_bindings'])==9
for e in nine['nine_bindings']:
 p=e['path'];body=git('show',H+':'+p);assert c[p]==a[p] and c[p][2]==e['current_SOURCE_and_CONTROL_blob'] and len(body)==e['bytes'] and hashlib.sha256(body).hexdigest()==e['sha256']
# Complete typed production input census distinct from five selected tests.
def prod(z):return {p:e for p,e in z.items() if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in {f'{pkg}/{s}' for pkg in ['actions','action_server','actions-http-helper'] for s in ['pyproject.toml','poetry.lock']}}
n=leaves(N);inputs=prod(c);native=prod(n);pi=v['production_and_selected_native_inventory'];assert len(inputs)==274 and len(native)==268 and inputs==prod(a)==pi['all_current_mode_blob_inputs']
assert sum(c[p]==n.get(p) for p in inputs)==261 and len([p for p in inputs if p in native and c[p]!=n[p]])==7 and len(set(inputs)-set(native))==6
five=pi['five_selectors_separate_exact'];assert len(five)==5 and not inputs.keys()&five.keys() and all(c[p]==a[p]==n[p] for p in five)
# Original historical actual ZIP member bytes, CRC, recorded modes, all existing copies0600.
actualPath=Path(v['historical776_actual_scope_NOT_current_acceptance']['authoritative_frozen_receipt']['path']);actual=json.loads(actualPath.read_text());assert actual['source_S']['commit']==oldS and actual['control_C']['commit']=='b673ddd761ba4ccd68e9baa8faaa9ab666df794e' and actual['target']=='77647484b3cdd8e18aabf344a4018ea8ed8e3ea0'
for e in actual['evidence']:inspect(e)
inspect(actual['acquisition']['ZIP'])
with zipfile.ZipFile(actual['acquisition']['ZIP']['path']) as z:
 infos=z.infolist();assert len(infos)==len({i.filename for i in infos})==7
 for e in actual['archive_members']:
  info=z.getinfo(e['member']);body=z.read(info);assert len(body)==e['bytes'] and hashlib.sha256(body).hexdigest()==e['sha256'] and oct(info.external_attr>>16)==e['zip_recorded_mode'] and f'{info.CRC:08x}'==e['zip_CRC32']
  copies=[x for x in actual['evidence'] if x['sha256']==e['sha256'] and x['bytes']==e['bytes']];assert copies and all(stat.S_IMODE(Path(x['path']).stat().st_mode)==0o600 and Path(x['path']).read_bytes()==body for x in copies)
# Original RED observations, no rerun or false count correction.
pinlog=(O/'pin-RED.log').read_text();branchlog=(O/'branch-RED.log').read_text();greenlog=(O/'GREEN55-static.log').read_text();toolkit=(O/'ToolkitTest.log').read_text()
assert '1 failed, 4 passed' in pinlog and '2 failed, 3 passed' in branchlog and '55 passed' in greenlog and '96 passed' in toolkit
for node in ['test_generated_workflow_is_checkout_equivalent','test_rcc_rollback_workflow_is_opt_in_pinned_and_secret_free']:assert node in branchlog
branch=json.loads((O/'branch-RED-actual-successor-v2-result.json').read_text());failed=json.loads((O/'initial-branch-count-collector-failure-preserved.json').read_text());assert branch['actual_failed']==2 and branch['actual_passed']==3 and failed['expected']=={'failed':1,'passed':4} and failed['actual']=={'failed':2,'passed':3} and failed['GREEN_launch_preceded_collector_failure_readback']
assert v['pin_and_branch_RED_original_preservation']['sequencing_limit'].startswith('GREEN began after restoration before failed collector readback')
assert "finally" in (O/'CONTROL-safe-gate-results.json').read_text() or failed['restoration_in_finally_before_GREEN']
roundtrip=json.loads((O/'generator-roundtrip-successor-v2-receipt.json').read_text());assert roundtrip['head']==A and roundtrip['generated_output_count']==len(roundtrip['generated_outputs'])==8 and roundtrip['all_tracked_GitHub_YAML_count']==30
for p,e in roundtrip['all30_GitHub_paths_parsed_and_bytes_preserved'].items():assert sha(R/p)==e
import yaml
beforeY=yaml.load(git('show',A+':.github/workflows/actions_runtime_rcc_provider_rollback.yml'),Loader=yaml.BaseLoader);afterY=yaml.load(git('show',H+':.github/workflows/actions_runtime_rcc_provider_rollback.yml'),Loader=yaml.BaseLoader)
assert beforeY['on']==afterY['on'] and beforeY.get('permissions')==afterY.get('permissions') and beforeY.get('concurrency')==afterY.get('concurrency')
push=afterY['on']['push'];assert push['branches']==['test/rcc-provider-rollback-hosted-20261010','fix/rcc-published-artifact-details-20261010','fix/rcc-candidate-wheel-identities-20261010'] and len(push['paths'])==8
assert v['SOURCE_full_inherited_not_executed_CONTROL']['head']==A and v['SOURCE_full_inherited_not_executed_CONTROL']['tree']==AT and v['SOURCE_full_inherited_not_executed_CONTROL']['full_not_repeated'] and v['gates_executed_current_CONTROL']['SOURCE_full_inherited_only']['not_RUN_on_CONTROL']
full=(S/'SOURCE-full-configured-runtime-source.log').read_text();assert '1240 passed, 13 skipped, 15 warnings in 137.04s' in full
# Prepared30inputs/five actual origins, no reviewer gateway execution.
reuse=json.loads((O/'after-full-own-Bootstrap-reuse-inputs-and-origins.json').read_text());assert reuse==json.loads((S/'after-full-own-Bootstrap-reuse-inputs-and-origins.json').read_text()) and len(reuse['inputs_exact_prepared_git_bytes_sha256'])==30
for p,e in reuse['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/p)==e
for pkg,e in reuse['own5venvs_current_config_and_python'].items():assert sha(R/pkg/'.venv/pyvenv.cfg')==e['config_sha256'] and str((R/pkg/'.venv/bin/python').resolve())==e['python_resolved']
assert len(reuse['own5actual_prefix_and_source_origin_assertions'])==5
for e in reuse['own5actual_prefix_and_source_origin_assertions']:assert Path(e['prefix']).is_relative_to(R) and Path(e['origin']).is_relative_to(R) and Path(e['origin']).is_file()
rcc=R/'action_server/src/actions/server/bin/rcc-18.19.3';assert sha(rcc)=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428' and stat.S_IMODE(rcc.stat().st_mode)==0o711
retained=json.loads((S/'after-full-retained-native-helper-browser-and-V5-proof.json').read_text());inspect(retained);inventory=json.loads(Path(retained['original_inventory']['path']).read_text());root=Path('/workspace/engineering/pr310-runner-qualification-owned/dist/action-server');entries=[]
for p in sorted(root.rglob('*'),key=lambda z:z.relative_to(root).as_posix()):
 kind='symlink' if p.is_symlink() else 'directory' if p.is_dir() else 'file' if p.is_file() else 'UNSUPPORTED';assert kind!='UNSUPPORTED';entries.append({'path':p.relative_to(root).as_posix(),'kind':kind,'mode':stat.S_IMODE(p.lstat().st_mode),'link_target':p.readlink().as_posix() if p.is_symlink() else None,'content_sha256':sha(p) if p.is_file() else None})
assert len(entries)==1192 and entries==inventory;assert retained['historical_V5_source']['head']==V and retained['historical_V5_source']['native_producer']==N
for e in retained['frozen_helper_original_and_snapshot_bindings'].values():assert e['original']['sha256']==e['snapshot']['sha256'] and stat.S_IMODE(Path(e['snapshot']['path']).stat().st_mode)==0o444
base=Path('/workspace/actions-cloud/receipts/pr305-runner');actual=json.loads((base/'actual-v5-passed-checkpoint-corrected.json').read_text());assert len(actual['raw_receipts_private_do_not_commit'])==18
for e in actual['raw_receipts_private_do_not_commit']:inspect(e)
assert len(actual['frozen_posthashes'])==50
for e in actual['frozen_posthashes']:assert e['sha256']==e['expected_sha256']==sha(e['path'])
raw=json.loads((S/'immediate-pre-full-raw18-frozen50-Node-frontend-retained.json').read_text());assert (S/'immediate-pre-full-raw18-frozen50-Node-frontend-retained.json').read_bytes()==(S/'after-full-raw18-frozen50-Node-frontend-retained.json').read_bytes();assert raw['frozen50_counts']=={'retained_external_bytes':50};proposal=json.loads((base/'immutable-runner-proposal-v5.json').read_text());driver=proposal['driver'];assert sha(driver['node'])==raw['prepared_node_binary_sha256'];assert sha(driver['frontend_lock']['path'])==raw['frontend_lock_sha256'];assert Path(driver['prepared_node_modules']).is_dir()


for e in v['documentation_improvement']['Exact_imported_deltas']+[v['documentation_improvement']['Exact_novel_correction']]:inspect(e)
for path in ['docs/skills/repository-operations.md','docs/skills/provenance-observability.md']:assert c[path]==a[path]
assert git('status','--porcelain')==b'' and git('rev-parse','HEAD').decode().strip()==H
proof={'head':H,'tree':T,'sole_parent_SOURCE':A,'SOURCE_tree':AT,'SOURCE_ordered_parents':v['SOURCE_ordered_parents'],'actual_target':B,'clean':True,'all1419_typed_body_modes_FS_exec_prepost_exact':True,'all1416_other_leaves_exact_SOURCE':True,'three_control_path_identity_substitution_only':changes,'whole_generator_developer_AST_and_workflow_raw_after_pin_normalization_exact':True,'all_workflow_events_branches8paths_matrices_needs_permissions_cases_receipts_deadlines_retry_skip_publisher_guards_unchanged':True,'current_push_branches':push['branches'],'all188_owner_final_refs_and147_SOURCE_refs_hash_size_fingerprint_verified':True,'verified_unique_bindings':list({e['path']:e for e in refs}.values()),'nine_current_source_samples_exact_not_complete_native_qualification':True,'original_seven_unique_actual_ZIP_members_SHA_size_CRC_recorded_modes_and0600_copies_exact':True,'historical_actual_tuple':[oldS,'b673ddd761ba4ccd68e9baa8faaa9ab666df794e','77647484b3cdd8e18aabf344a4018ea8ed8e3ea0'],'RED':{'pin_failed':1,'pin_passed':4,'branch_failed':2,'branch_passed':3,'initial_collector_wrong_expected1FAIL4PASS_retained':True,'GREEN_launch_before_failed_collector_readback_honestly_retained':True,'successor_observation_only_no_RED_rerun':True},'current_CONTROL_gates':v['gates_executed_current_CONTROL'],'SOURCE_full1240PASS13SKIP_inherited_only_not_RUN_CONTROL':True,'generator_roundtrip8_allGitHub30_recorded_PASS_current_bytes_verified':True,'generator_receipt_HEAD_SOURCE_current_CONTROL_working_bytes_precommit_staged_postcommit_bound_to_final_tree':{'receipt_HEAD':A,'final_CONTROL':H,'final_tree':T,'scope':'Roundtrip observed SOURCE Git HEAD with changed CONTROL working bytes; all current hashes match complete precommit/staged/postcommit body-mode proof, not a committedHEAD d5a3 rerun'},'prepared30inputs5origins_prefix_config_RCC0711_exact':True,'original1192_helper0444_browser_Node_frontend_raw18_frozen50_exact':True,'native_producer':{'current':274,'old':268,'matches':261,'changed':7,'added':6,'five_selected_tests_separate_exact':True,'qualification':'UNQUALIFIED_CURRENT_NATIVE'},'constructor_fixed_current_head_tree_no_overwrite_SHA_bytes_not_reexecuted':bind(ctor),'canonical_unchanged_from_reviewed_SOURCE':v['documentation_improvement'],'no_source_test_gateway_native_provider_browser_installer_download_push_merge_execution':True,'upstream_disposition':'none'}
p=D/'independent-complete-CONTROL-scope-gates-and-retained-byte-proof.json';p.write_text(json.dumps(proof,indent=2)+'\n');p.chmod(0o600)
final={'schema':'actions.independent-current308-CONTROL-review/v1','verdict':'GO_NORMAL_EXISTING_BRANCH_SOURCE_CONTROL_CHECKPOINT_PUSH_ONLY','execution_subject':{'CONTROL':H,'CONTROL_tree':T,'SOURCE':A,'SOURCE_tree':AT,'SOURCE_ordered_parents':v['SOURCE_ordered_parents'],'actual_target':B,'branch':v['branch']},'owner_final':bind(owner),'independent_proof':bind(p),'findings':[],'verified_scope':['1419 complete typed/filesystem body and execute-mode union; only three control paths change two source identity values','All1416 other leaves and guide bodies/modes exactly reviewedSOURCE','All188 final and147 originalSOURCE bindings verified; seven old actual members and original native/helper/browser/Node/frontend/V5 bytes preserved','Original pinRED1FAIL4PASS, actualbranchRED2FAIL3PASS and mistakencollectorFAIL retained; GREEN55+Toolkit96+static/gen8/YAML30 currentCONTROL checks; full1240/13 remains SOURCE-only'],'generator_and_gate_execution_identity':'Prepared CONTROL working bytes checked before child commit; roundtrip receipt observes SOURCEHEADc103, current30YAML hashes plus complete precommit/staged/postcommit1419 proofs bind checked bytes to final fa3f tree; no claimed committedHEADd5a3 generator rerun','sequencing_limit':'GREEN launched after valid workflow restoration before failed branch-count collector readback; successor metadata records original observed2FAIL3PASS only, no RED rerun or retroactive collector GO','required_next_gates':['Root normal existing-branch push with pinned CONTROL; no reviewer push','Fresh exact SOURCE/CONTROL hosted original three-case proof and complete current source/base CI, actual checkout, reviews/threads/draft and policy admission','Whole134/private01f/frozen-v6/positive2510/public639profile/native/provider/backend/publication/release remain HOLD; no old776 actual or fullCI carry'],'documentation_improvement':{'Canonical_files_changed_or_proposed':['docs/skills/repository-operations.md','docs/skills/provenance-observability.md'],'Exact_delta_disposition':'Accept verified existing SOURCE b800238a three-branch correction and both-parent imports3b1c8448/7330b295, unchanged in CONTROL; no cosmetic child','Durable_learning_captured':'Source-first then separately reviewed control pins and new actual proof; all three declared push branches share retained eight paths; immutable original RED evidence and named successor observations preserve actual sequencing','Evidence':'Whole generator/test AST and emittedworkflow raw exact after only sourceSHA/tree substitutions; 1419leaf union; originalRED counts; fresh55controls96Toolkit8outputs30YAML; source and historicalactual bindings distinct','Stale_or_ambiguous_guidance_removed':'SOURCE corrects stale two-branch list; CONTROL does not relabel old7eb/b673/776 proof or SOURCEfull1240/13 as new currentCONTROL actual','Remaining_uncertainty':'Fresh current hosted three-case/fullCI/policy acceptance and all positive2510/private/native/provider/release gates still pending'},'upstream_disposition':'none'}
f=D/'OWNERFINAL-independent-current308-CONTROL-review.json';assert not f.exists();f.write_text(json.dumps(final,indent=2)+'\n');f.chmod(0o600);print(json.dumps({'OWNERFINAL':bind(f),'proof':bind(p)}))
