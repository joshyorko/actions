from pathlib import Path
import collections,hashlib,json,os,re,stat,subprocess
D=Path('/workspace/engineering/pr312-actual309-refresh');O=Path('/workspace/engineering/pr312-current-a0d-independent-sourcefinal-review');R=Path('/workspace/engineering/runtime-checkout-eol');O.chmod(0o700)
S='77065131a0aee63d2b1f8621476374bdde3c7b65';T='edf1801e565692fb3f07b809b3a95b27981fe2fe';A='92e6deda5c252a503510c4b6261a86cb51f73cb6';B='a0d258a16095b95b1bf9000cb1201cddfaff4779'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
checked={}
def check(row):
 p=Path(row['path']);q=bind(p);assert all(q[k]==row[k] for k in ('path','bytes','sha256'));checked[q['path']]=q
 return q
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def tree(rev):
 out={}
 for rec in git('ls-tree','-rz',rev).split(b'\0'):
  if rec:
   a,p=rec.split(b'\t',1);mode,kind,blob=a.decode().split();out[p.decode()]={'mode':mode,'type':kind,'blob':blob}
 return out
owner=D/'OWNERFINAL-pr312-current-a0d-SOURCEFINAL.json';q=bind(owner);assert q['bytes']==21917 and q['sha256']=='d922c435dd20c585f134bbc9bae76ede367ff2bd40f901c5952fd65ffc64c82b';d=json.loads(owner.read_text())
assert d['source_head']==S and d['source_tree']==T and d['ordered_parents']==[A,B]
for row in d['immutable_current_evidence_bindings']:check(row)
for key in ['root_ONE_full_authorization','independent_LIGHT_and_worker_bound_proposal_review','independent_batch17_capacity_review','original_SOURCEFINAL','current_LIGHT']:check(d[key])
light=json.loads(Path(d['current_LIGHT']['path']).read_text());old=json.loads(Path(d['original_SOURCEFINAL']['path']).read_text());assert len(old['immutable_evidence_bindings'])==62
for row in light['immutable_evidence_bindings']+old['immutable_evidence_bindings']:check(row)
assert git('rev-parse','HEAD').decode().strip()==S and git('rev-parse',S+'^{tree}').decode().strip()==T and git('show','-s','--format=%P',S).decode().split()==[A,B] and git('status','--porcelain')==b'' and git('branch','--show-current').decode().strip()==d['branch']
a,b,m=tree(A),tree(B),tree(S);assert len(m)==1423 and set(m)==set(a)|set(b)
for path,row in m.items():
 p=R/path;body=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes();assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==row['blob']
 if row['mode']!='120000':assert bool(p.stat().st_mode&0o111)==(row['mode']=='100755')
 if not path.startswith('docs/'):assert row==a.get(path) or row==b.get(path)
pre=json.loads((D/'committed-complete-union-current-full-pre.json').read_text());post=json.loads((D/'committed-complete-union-current-full-post.json').read_text());assert pre['typed_leaves']==post['typed_leaves']==m
selected=pre['selected207'];assert len(selected)==207 and len([p for p in selected if p.endswith('.py')])==201
for p in selected:assert m[p]==a[p]
for p in light['original7_delta_paths_retained']:
 if not p.startswith('docs/'):assert m[p]==a[p]
for p in ['action_server/tests/action_server_tests/test_auth_route_inventory.py','action_server/tests/action_server_tests/test_auth_route_enforcement.py']:assert m[p]==b[p]
lesson=pre['documentation_exact_imported_lesson'];assert len(lesson.splitlines())==16
path='docs/skills/repository-operations.md';guide=git('show',S+':'+path).decode();assert guide.count(lesson)==1 and guide.replace(lesson,'',1)==git('show',B+':'+path).decode()
actual=d['actual_current_full'];check(actual['launcher']);check(actual['raw_log']);assert stat.S_IMODE(Path(actual['raw_log']['path']).stat().st_mode)==0o600
terminal=json.loads((D/'current-full-terminal.json').read_text());auth=json.loads(Path(d['root_ONE_full_authorization']['path']).read_text());assert terminal['returncode']==0 and terminal['actual_full_attempt_count']==1 and not terminal['retry'];assert terminal['argv']==actual['full_argv']==auth['next_full']['argv']
assert terminal['source_head']==auth['head']==S and terminal['source_tree']==auth['tree']==T
raw=Path(actual['raw_log']['path']).read_text();assert '162 passed in 11.12s' in raw and '1295 passed, 13 skipped, 15 warnings in 137.55s' in raw and 'pytest -q tests -n 2' in raw and 'bringing up nodes...' in raw and '2 workers [1308 items]' in raw and '"actual main robot run" was SUCCESS' in raw
assert terminal['elapsed_seconds']==actual['elapsed_seconds'] and 0<terminal['elapsed_seconds']<600
assert (D/'full-source-gates-explicit-two-workers-root-release-required.py').read_bytes()==Path('/workspace/engineering/runtime-checkout-eol-source/full-source-gates-explicit-worker-bound-v2.py').read_bytes()
# Recorded preservation indices identical before/after; independently rehash original referenced files without execution.
for n1,n2 in [('retained-native-helper-browser-and-V5-proof-current-full-pre.json','retained-native-helper-browser-and-V5-proof-current-full-post.json'),('raw18-frozen50-Node-frontend-retained-current-full-pre.json','raw18-frozen50-Node-frontend-retained-current-full-post.json')]:assert (D/n1).read_bytes()==(D/n2).read_bytes()
native=json.loads((D/'retained-native-helper-browser-and-V5-proof-current-full-post.json').read_text())
for key in ['original_manifest','original_inventory','original_assets_zip','original_frozen_executable','browser','historical_V5_checkpoint','historical_V5_independent_review','immutable_proposal']:check(native[key])
for group in native['frozen_helper_original_and_snapshot_bindings'].values():
 for key in ('original','snapshot'):check(group[key])
 assert stat.S_IMODE(Path(group['snapshot']['path']).stat().st_mode)==0o444
proposal=json.loads(Path(native['immutable_proposal']['path']).read_text());layout=Path(proposal['native']['layout'])/'dist/action-server';inventory=json.loads(Path(native['original_inventory']['path']).read_text());assert len(inventory)==1192
observed=set()
for p in layout.rglob('*'):observed.add(p.relative_to(layout).as_posix())
assert observed=={r['path'] for r in inventory}
for row in inventory:
 p=layout/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert p.is_file() and not p.is_symlink() and sha(p)==row['content_sha256']
 elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert row['kind']=='symlink' and p.is_symlink() and os.readlink(p)==row['link_target']
v5=json.loads(Path(native['historical_V5_checkpoint']['path']).read_text());assert len(v5['raw_receipts_private_do_not_commit'])==18 and len(v5['frozen_posthashes'])==50
for row in v5['raw_receipts_private_do_not_commit']:check(row)
cats=collections.Counter()
for row in v5['frozen_posthashes']:
 p=Path(row['path']);got=sha(p);assert row['sha256']==row['expected_sha256']
 if got==row['sha256']:cats['retained_external_bytes']+=1
 else:
  rel=p.relative_to('/workspace/engineering/pr305').as_posix();body=subprocess.check_output(['git','-C','/workspace/engineering/pr305','show','3ec9d0acbe30ad94d02e4c24fef2587127964495:'+rel]);assert hashlib.sha256(body).hexdigest()==row['sha256'];cats['historical305Gitbody_retained_original3ec_current_union_changed']+=1
ret=json.loads((D/'raw18-frozen50-Node-frontend-retained-current-full-post.json').read_text());assert dict(cats)==ret['frozen50_counts'];driver=proposal['driver'];assert sha(driver['frontend_lock']['path'])==driver['frontend_lock']['sha256'];assert sha(driver['browser'])==driver['browser_sha256'] and sha(driver['node'])==ret['prepared_node_binary_sha256'] and Path(driver['prepared_node_modules']).is_dir()
reuse=json.loads((D/'own-Bootstrap-reuse-inputs-and-origins.json').read_text());assert len(reuse['inputs_exact_prepared_git_bytes_sha256'])==30
for p,h in reuse['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/p)==h
for pkg,row in reuse['own5venvs_current_config_and_python'].items():assert sha(R/pkg/'.venv/pyvenv.cfg')==row['config_sha256'] and str((R/pkg/'.venv/bin/python').resolve())==row['python_resolved']
pin=R/'action_server/src/actions/server/bin/rcc-18.19.3';assert sha(pin)=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428' and stat.S_IMODE(pin.stat().st_mode)==0o711
out={'schema':'actions-independent-pr312-current-a0d-SOURCEFINAL/v1','verdict':'GO_NORMAL_EXISTING_PR312_BRANCH_SOURCE_PUSH_ONLY','owner_final':q,'head':S,'tree':T,'ordered_parents':[A,B],'existing_branch':d['branch'],'verified':{'complete_Git_FS_body_exec_typed_parent_union':1423,'prepost_exact':True,'protected_inputs':207,'protected_Python':201,'protected_text_frontend':6,'original_seven_LF_rules_two_filters_preserved':True,'target_auth_files_preserved':2,'old_source_refs':62,'unique_binding_files_rehashed':len(checked),'current_one_full':{'devutils':{'PASS':162,'SKIP':0,'fixed_n2_argv':True,'raw_worker_count_UNREPORTED_quiet_output':True,'seconds':11.12},'configured_Runtime':{'PASS':1295,'SKIP':13,'warnings':15,'items':1308,'workers':2,'seconds':137.55},'RCC_returncode':0,'elapsed_seconds':terminal['elapsed_seconds'],'timeout_TERM':600,'kill_after':10,'attempts':1},'original_native_tree_entries_independently_rehashed_mode_checked':1192,'original_helper_snapshots_mode0444':True,'original_raw_V5_receipts':18,'original_frozen_V5_member_hash_scope':50,'V5_original_source3ec_and_native92498_preserved_no_current_actual_carry':True,'prepared_inputs':30,'own_config_prefix_origin_count':5,'RCC_pin_mode0711':True},'raw_log_binding_private':actual['raw_log'],'history':'Independent unannounced inspector expected verbose devutils worker count in quiet output; corrected to measured fixed-n2 argv/node startup before final freeze. Original wrong-task inspector and wrong own-prefix metadata preflight failures retained; corrected metadata successor preceded ONE current full. No source gate failure or retry relabeling. Original92e/618 full and hosted tuples historical.','remaining_HOLD':['Root live PRhead/base/existing remote ref before normal source push','Fresh complete770/a0d hosted tests/builds and current distribution bytes','13 skipped source tests remain unverified','Windows effective-checkout/compiler cause and embedded HTML semantics UNKNOWN','Current native/provider/private01f/frozen-v6/OAuth authority/full7 consumers/ChatGPT/issues/release/tag/publication unqualified'],'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; accepted source1306 16-line lesson and accepted a113 explicit-worker lesson reused','Exact_delta':'Source guide minus exactly one16-line EOL lesson equals complete targeta0d guide; all target registration/credential/history guidance preserved. Explicit xdist environment2 precedes BOTH sequential commands; no cosmetic child.','Durable_learning_captured':'Tracked text/owning workflow filters need complete checkout qualification; actual configured n-auto worker count must inherit explicit bound and be measured independently from devutils-n2.','Evidence':'207 unchanged protected bodies/modes,1423 complete pre/post union,exact launcher876a and rootdc19,current raw24e9 devutils162 fixed-n2 argv+Runtime1295 observed2workers, unchanged original native/3ecV5 inputs','Stale_or_ambiguous_guidance_removed':'No old92e/618 full or hosted carry; NOT_RUN retained-native label interpreted as original native/browser execution only, not denial of separate current source full execution','Remaining_uncertainty':'Fresh current hosted/cross-platform generated distributions, skipped integrations, native/private/content authority and release remain HOLD'},'Upstream_disposition':'none','read_only_no_tests_gateway_source_index_download_ref_push_merge_mutation':True,'review_script':bind(__file__)}
p=O/'OWNERFINAL-independent-pr312-current-a0d-SOURCEFINAL-review.json';p.write_text(json.dumps(out,indent=2)+'\n');p.chmod(0o600);print(json.dumps(bind(p)))
