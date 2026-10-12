from pathlib import Path
import json,hashlib,subprocess,stat,os,ast,difflib,collections,xml.etree.ElementTree as ET,re
D=Path(__file__).parent;ROOT=Path('/workspace/engineering');R=ROOT/'pr305';L=ROOT/'pr305-current-a54-source-LIGHT';P=ROOT/'pr305-current5306-SOURCEFULL-preexecution'
H='5306eeb26595da4ce571b99812eb50f047cfc903';T='8418e9ffeeaaf2446771e34b5b4602bab3d357a5';OLD='584a7ed0cb7112fe6691103931c007b5cc0be5f3';B='a54c982462d1e7ad011d8152bfc299d997503fb3';CURRENT=B
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def load(p):return json.loads(Path(p).read_text())
def git(*a):return subprocess.check_output(['git','-C',str(R),*a],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
def check(row,mode=True):
 p=Path(row['path']);q=bind(p);assert q['sha256']==row['sha256']
 if 'bytes' in row:assert q['bytes']==row['bytes']
 if mode and 'mode' in row:assert q['mode']==row['mode']
 return q
lp=L/'OWNERFINAL-current5306-ordinary-a54-source-LIGHT-full-and-actual-HOLD.json';q=bind(lp);assert (q['bytes'],q['sha256'])==(17431,'2c277550c5475cb6c9698dfbe092dd373a5398b553769f68a230451c96c1ca14')
light=load(lp);assert light['binding_count']==len(light['frozen_bindings'])==38;lightbindings=[check(x) for x in light['frozen_bindings']]
assert git('show','-s','--format=%H %T %P',H).decode().split()==[H,T,OLD,B]
assert git('rev-parse','HEAD').decode().strip()==H and not git('status','--porcelain')
def typed(s,paths=()):
 out={}
 for row in git('ls-tree','-rz',s,'--',*paths).split(b'\0'):
  if row:
   pre,p=row.split(b'\t');mode,kind,blob=pre.decode().split();assert kind=='blob';out[p.decode()]={'mode':mode,'kind':kind,'blob':blob}
 return out
a,b,c=typed(OLD),typed(B),typed(H);assert len(c)==1427 and set(c)==set(a)|set(b)
novel=[p for p,v in c.items() if v!=a.get(p) and v!=b.get(p)];assert novel==['docs/skills/repository-operations.md']
rows=load(L/'private-current-5306-complete-source-body-mode-inventory.json');assert len(rows)==1427
for row in rows:
 p=R/row['path'];raw=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes();v=c[row['path']];assert (row['mode'],row['kind'],row['blob'])==(v['mode'],v['kind'],v['blob'])
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==v['blob'] and len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'] and stat.S_IMODE(p.lstat().st_mode)==row['fs_mode']
 if v['mode']!='120000':assert bool(p.stat().st_mode&0o111)==(v['mode']=='100755')
for path in c:
 if path in ['action_server/src/actions/server/_rcc_runtime_adapter.py','action_server/src/actions/server/_rcc.py']:assert c[path]==a[path]
owned=['action_server/tests/action_server_tests/mcp/test_canvas_runtime_admission.py','action_server/tests/action_server_tests/test_browser_origin_acceptance.py','action_server/tests/action_server_tests/mcp/test_mcp_apps_authoring.py','action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py']
for path in owned:assert c[path]==a[path]
verifier=ast.parse(git('show',H+':action_server/scripts/verify_frozen_catalog_harness.py'));inputpaths=ast.literal_eval(next(n.value for n in verifier.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='INPUT_PATHS' for t in n.targets)))
producer=typed(H,inputpaths);native=typed('92498aff',inputpaths);s5=['action_server/tests/action_server_tests/'+n for n in ['test_cli_mcp_catalog_rollback.py','test_cli_live_reload_multi_package.py','test_cli_successful_generation_drain.py','test_cli_multi_package_sync.py','test_cli_mcp_resource_history.py']]
assert len(producer)==275 and len(native)==268 and sum(producer.get(p)==v for p,v in native.items())==260
assert sum(p in native and producer[p]!=native[p] for p in producer)==8 and len(set(producer)-set(native))==7 and not set(native)-set(producer)
assert typed(H,s5)==typed('92498aff',s5)
actual=load(L/'typed-current-production-and-five-selector-inventory.json');assert actual['current']==producer and actual['original_native']==native
j=ET.parse(L/'current-scoped-source-junit.xml');cases=j.findall('.//testcase');counts=collections.Counter('SKIP' if n.find('skipped') is not None else 'FAIL' if n.find('failure') is not None else 'ERROR' if n.find('error') is not None else 'PASS' for n in cases);assert counts=={'PASS':275,'SKIP':1}
log=(L/'LIGHT-current-a54-original.private.log').read_text();assert '96 passed' in log and '275 passed, 1 skipped, 7 deselected' in log and 'Success: no issues found in 353 source files' in log
terminal=load(L/'current-source-LIGHT-terminal.json');assert terminal['status']=='PASS' and all(r['returncode']==0 for r in terminal['records'])
roundtrip=load(L/'current-generator8-allYAML30-roundtrip.json');assert roundtrip['generated_output_count']==8 and len(roundtrip['all30_bytes_sha256'])==30
for path,digest in roundtrip['all30_bytes_sha256'].items():assert sha(R/path)==digest==hashlib.sha256(git('show',H+':'+path)).hexdigest()
prepared=load(L/'own-current30-input-and-five-concrete-origins-Bootstrap-reuse.json');assert len(prepared['inputs'])==30 and len(prepared['origins'])==5
for path,digest in prepared['inputs'].items():assert sha(R/path)==digest
assert sha(prepared['original_bootstrap_log'])==prepared['original_bootstrap_log_sha256']
for record in prepared['origins']:
 assert Path(record['prefix']).resolve().is_relative_to(R.resolve()) and Path(record['origin']).resolve().is_relative_to((Path(record['prefix']).parent/'src').resolve()) and Path(record['origin']).is_file()
# Read-only native member equivalence without importing the product or frozen helper.
baseline=load(ROOT/'rcc-compatibility-actual-runner-readonly-preparation/FROZEN-control3-current-b614-actual-config-v2.json');layout=Path(baseline['native_original_root']);members=baseline['native_original_members'];assert len(members)==1192
assert {p.relative_to(layout).as_posix() for p in layout.rglob('*')}=={r['path'] for r in members}
for row in members:
 p=layout/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert p.is_file() and not p.is_symlink() and sha(p)==row['content_sha256']
 elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert p.is_symlink() and os.readlink(p)==row['link_target']
retention=load(L/'retained-native-helper-browser-and-V5-proof-postLIGHT.json');retention_checked=[]
def all_path_sha(x):
 if isinstance(x,dict):
  if isinstance(x.get('path'),str) and x['path'].startswith('/') and isinstance(x.get('sha256'),str) and 'bytes' in x:retention_checked.append(check(x,False))
  for v in x.values():all_path_sha(v)
 elif isinstance(x,list):
  for v in x:all_path_sha(v)
all_path_sha(retention)
for pair in retention['frozen_helper_original_and_snapshot_bindings'].values():assert stat.S_IMODE(Path(pair['snapshot']['path']).stat().st_mode)==0o444
v5=load(retention['historical_V5_checkpoint']['path']);raw18=v5['raw_receipts_private_do_not_commit'];assert len(raw18)==18
for row in raw18:check(row,False)
assert len(v5['frozen_posthashes'])==50
for row in v5['frozen_posthashes']:assert row['sha256']==row['expected_sha256']==sha(row['path'])
v5proposal=load(retention['immutable_proposal']['path']);driver=v5proposal['driver'];check(driver['frontend_lock'],False);assert sha(driver['browser'])==driver['browser_sha256'] and Path(driver['prepared_node_modules']).is_dir()
raw_report=load(L/'raw18-frozen50-Node-frontend-retained-postLIGHT.json');assert sha(driver['node'])==raw_report['prepared_node_binary_sha256']
# Exact owning-guide import and every newly added/replaced block from BOTH parents.
guides=['docs/skills/repository-operations.md','docs/skills/provenance-observability.md'];patch=L/'exact-imported-e3-canonical-guide-delta.patch';assert git('diff',OLD,H,'--',*guides)==patch.read_bytes()
mb=git('merge-base',OLD,B).decode().strip();blocks=[]
for path in guides:
 original=git('show',mb+':'+path).decode().splitlines(True);currentguide=git('show',H+':'+path).decode()
 for parent in [OLD,B]:
  parentguide=git('show',parent+':'+path).decode().splitlines(True)
  for tag,i1,i2,j1,j2 in difflib.SequenceMatcher(a=original,b=parentguide,autojunk=False).get_opcodes():
   if tag in ('insert','replace') and j2>j1:
    block=''.join(parentguide[j1:j2]);assert block in currentguide;blocks.append({'guide':path,'parent':parent,'lines':j2-j1,'sha256':hashlib.sha256(block.encode()).hexdigest()})
assert blocks
# Narrowly normalize only the TWO accepted incoming checkout path filters.
import copy,yaml
GP='.github/workflows/_gen_workflows.py';expected_append=ast.dump(ast.parse('parts["on"]["pull_request"]["paths"].append(".gitattributes")').body[0],include_attributes=False)
class FilterOnly(ast.NodeTransformer):
 def __init__(self):self.removals=0
 def visit_ClassDef(self,node):
  if node.name in ['ActionServerTests','ActionServerPyPiRelease']:
   for item in ast.walk(node):
    if isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef)):
     oldbody=item.body;item.body=[e for e in oldbody if ast.dump(e,include_attributes=False)!=expected_append];self.removals+=len(oldbody)-len(item.body)
    if isinstance(item,ast.List):
     oldelts=item.elts;item.elts=[e for e in oldelts if not(isinstance(e,ast.Constant) and e.value=='.gitattributes')];self.removals+=len(oldelts)-len(item.elts)
  return node
f_old=FilterOnly();f_new=FilterOnly();ta=f_old.visit(ast.parse(git('show',OLD+':'+GP)));tb=f_new.visit(ast.parse(git('show',H+':'+GP)));assert f_old.removals==0 and f_new.removals==2 and ast.dump(ta,include_attributes=False)==ast.dump(tb,include_attributes=False)
for path in ['.github/workflows/actions_runtime_tests.yml','.github/workflows/actions_runtime_pypi_release.yml']:
 oldyaml=yaml.safe_load(git('show',OLD+':'+path));newyaml=yaml.safe_load(git('show',H+':'+path));assert newyaml['on']['pull_request']['paths'].count('.gitattributes')==1;newyaml['on']['pull_request']['paths'].remove('.gitattributes');assert newyaml==oldyaml
old_owner=load(ROOT/'pr305-current-e3c-source-LIGHT/OWNERFINAL-current584a-ordinary-e3-source-LIGHT-full-and-actual-HOLD.json');assert len(old_owner['frozen_bindings'])==32
for row in old_owner['frozen_bindings']:check(row)
checkout=ET.parse(L/'current-checkout-source-junit.xml').findall('.//testcase');assert len(checkout)==10 and all(n.find('skipped') is None and n.find('failure') is None and n.find('error') is None for n in checkout)
shutdown=[n for n in cases if n.get('classname','').endswith('test_shutdown_response_order')];assert len(shutdown)==10 and all(n.find('skipped') is None and n.find('failure') is None and n.find('error') is None for n in shutdown)
proof={'source':H,'tree':T,'ordered_parents':[OLD,B],'complete_source_body_modes':1427,'full_parent_union_no_deleted_or_novel_app':True,'only_combined_path':novel,'old58432bindings_exact':True,'generator_whole_AST_and_two_whole_YAML_exact_after_only_two_EOL_PR_filters_removed':True,'all_originalCanvas3_whole_bodies_modes_exact_parent584':True,'separate_PR28239_gate_not_claimed':True,'producer':{'original':268,'current':275,'match':260,'changed':8,'added':7,'five_selectors':5,'selector_changes':0,'native_qualification':'UNQUALIFIED'},'eight_or_more_accepted_parent_blocks':blocks,'all1192_original_native_and0444helpers_raw18_frozen50_Node_browser':True}
p=D/'independent-current5306-source-LIGHT-union-and-preservation-proof.json';p.open('x').write(json.dumps(proof,indent=2)+'\n');p.chmod(0o600)
pp=P/'OWNERFINAL-current5306-managed-configured-SOURCEFULL-preexecution-proposal.json';q=bind(pp);assert(q['bytes'],q['sha256'])==(8597,'fbdaba2989e187ad11547f56ff0107092a479d4592aaa48b9170cc7a2339e553');proposal=load(pp);assert proposal['source']==H and proposal['tree']==T
metadata_defects={'source_LIGHT_status':'Owner status string retains ORDINARY_E3 while structured source head/parents/target correctly bind5306/a54; qualified subject derived from exact Git/source fields','preexecution_status':proposal['status'],'preexecution_historical_label':proposal['historical_preexecution'],'root_disposition':'Original fbdaba packet preserved; ROOT will adopt only named metadata-corrected successor before release; no source or gate replay required'}
ct=(ROOT/'campaign-checkpoint/docs/skills/repository-operations.md').read_text();anchor='Hash receipts as exact file bytes and test Git ancestry with full source commit\nIDs. A receipt SHA-256 is not a commit ID.';assert anchor in ct
proposal_delta='Construct current-source, branch and historical-predecessor labels from the bound\nsource checkpoint. Check status and history labels against executable pins; retain\na contradictory predecessor packet and issue a named metadata-only successor\nwithout replaying accepted gates.\n'
patch=D/'canonical-execution-packet-subject-label-consistency-proposed.patch';patch.open('x').write('--- a/docs/skills/repository-operations.md\n+++ b/docs/skills/repository-operations.md\n@@\n '+anchor.replace('\n','\n ')+'\n+\n'+''.join('+'+l for l in proposal_delta.splitlines(True)));patch.chmod(0o600)
remaining=['CurrentSOURCEFULL NOT_RUN; named corrected preexec required before ROOT adoption; current active282 FULL means serialized slot unavailable','Fresh>=1.2GiB strictcapacity required; proposal current1278365696B belowfloor, no execution release by review','Hosted current5306/a54 source CI, actualnative/browser/provider/private/backend/full99/release remain HOLD','Current275production260match8changed7added+5selectors is UNQUALIFIED for old92498; originalV5/source40ad/584 retain their identities']
out={'schema':'actions-independent-current3055306-SOURCE-LIGHT/v1','decision':'GO_EXACT_CURRENT5306_ORDINARY_A54_SOURCE_LIGHT_ONLY_FULL_PREEXEC_ADOPTION_HOLD_PENDING_NAMED_METADATA_CORRECTION','source':light['source'],'owner':bind(lp),'all38_frozen_bindings_hash_size_mode_exact':lightbindings,'complete_source_union_proof':bind(p),'observed_current_LIGHT':{'Doctor':'PASS','Toolkit_PASS':96,'checkout_PASS':10,'scoped_PASS':275,'scoped_SKIP':1,'scoped_DESELECT':7,'shutdown_source_PASS':10,'Mypy_PASS_files':353,'configured_lint':'PASS','generator_roundtrip':8,'all_YAML':30,'prepared_own_inputs':30,'five_concrete_origins':5},'original_artifact_retention':'Native1192/0444helpers/raw18/frozen50/Node/browser rehashed read-only, historicalV5 not relabeled; originalCanvas3 distinct from separately ownedPR28239 gate','metadata_identity_findings':metadata_defects,'original_current_preexecution_owner_HOLD':bind(pp),'remaining_HOLD':remaining,'Documentation_improvement':{'Canonical_files_changed_or_proposed':guides,'Exact_verified_import_reuse':bind(L/'exact-imported-a54-canonical-guide-delta.patch'),'Verified_durable_additional_proposal':bind(patch),'Exact_proposed_text':proposal_delta,'Durable_learning_captured':'Derive execution packet subject/history labels from its frozen sourcecheckpoint and verify them alongside exact executablepins; correct contradictory metadata in a named successor while preserving original failures and accepted gates. Accepted inherited EOLfilter/shutdown/transport/receipt lessons are present exactly.','Evidence':'1427 wholebody/mode union; exact3547B/c6126de sourceguide import and bothparent blocks; original17431B sourceLight status stillE3 despite source5306/a54; original8597B/fbdaba preexec status1299 and PR282c35 history despite correct5306 execution pins','Stale_or_ambiguous_guidance_removed':'No old584/e3 execution carry; wrongcrossbranch subject/history labels require named metadata successor, not source/gate replay. CurrentPR305 fixtures not inventedPR28239 gate.','Remaining_uncertainty':remaining},'Upstream_disposition':'none','no_source_tests_import_product_gateway_native_browser_provider_download_install_push_ready_merge':True,'review_script':bind(__file__)}
p=D/'OWNERFINAL-independent-current5306-SOURCE-LIGHT-review.json';p.open('x').write(json.dumps(out,indent=2)+'\n');p.chmod(0o400);print(json.dumps(bind(p)))
