import ast, datetime, hashlib, json, os, stat, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
R=Path('/workspace/engineering/captured-child-cleanup');D=Path('/workspace/engineering/captured-child-cleanup-light-owned');O=Path(__file__).resolve().parent
H='499a83d802ca9a0e2ebe3d77071af10625879297';T='e13ba51b094e429b7c06d6dabbbcc348cc66e86c';P='a0d258a16095b95b1bf9000cb1201cddfaff4779'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def check(v):assert bind(v['path'])=={k:v[k] for k in ('path','bytes','sha256')},v['path']
def g(*a):return subprocess.check_output(['git',*a],cwd=R)
def entries(ref):return {n.decode():m.decode().split() for line in g('ls-tree','-rz',ref).split(b'\0') if line for m,n in [line.split(b'\t')]}
def save(name,a):
 p=O/name;assert not p.exists();p.write_text(json.dumps(a,indent=2,sort_keys=True)+'\n');p.chmod(0o600);return bind(p)
def inventory(root):
 out={}
 for directory,dirs,files in os.walk(root,followlinks=False):
  for n in dirs+files:
   p=Path(directory)/n;s=p.lstat();v={'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid}
   if stat.S_ISLNK(s.st_mode):v.update(kind='symlink',target=os.readlink(p))
   elif stat.S_ISDIR(s.st_mode):v.update(kind='directory')
   elif stat.S_ISREG(s.st_mode):v.update(kind='file',bytes=s.st_size,sha256=sha(p))
   else:raise AssertionError('unexpected inventory kind')
   out[str(p.relative_to(root))]=v
 return out
def suite(name):
 a=ET.parse(D/name).getroot();rows=list(a.iter('testcase'))
 return {'tests':len(rows),'failed':sum(c.find('failure') is not None for c in rows),'errors':sum(c.find('error') is not None for c in rows),'skipped':sum(c.find('skipped') is not None for c in rows),'failure_names':[c.get('name') for c in rows if c.find('failure') is not None],'test_names':[c.get('name') for c in rows]}
ownerp=D/'OWNERFINAL-captured-child-cleanup-LIGHT-source-checkpoint-v2.json';owner=bind(ownerp);assert owner['bytes']==23814 and owner['sha256']=='5afd46dc62231bde85f44381bcb06fbc5d0af98d932dafbcc9d6500e6df6fdf8'
a=json.loads(ownerp.read_bytes());assert len(a['bindings'])==67
for v in a['bindings']:check(v)
assert g('rev-parse','HEAD').decode().strip()==H and g('rev-parse','HEAD^{tree}').decode().strip()==T and g('show','-s','--format=%P',H).decode().strip()==P and not g('status','--porcelain')
old,new=entries(P),entries(H);assert len(old)==1421 and len(new)==1422 and old.keys()<=new.keys()
changed=sorted(n for n in old if old[n]!=new[n]);added=sorted(set(new)-set(old));assert changed==['action_server/src/actions/server/_common/process.py','docs/skills/repository-operations.md'];assert added==['action_server/tests/action_server_tests/common_tests/test_captured_process_tree_deadline.py']
allsource=[]
for n,(mode,kind,blob) in new.items():
 p=R/n;b=os.readlink(p).encode() if mode=='120000' else p.read_bytes();assert b==g('cat-file','blob',blob);assert mode=='120000' or bool(p.stat().st_mode&0o111)==(mode=='100755');allsource.append({'path':n,'mode':mode,'blob':blob,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
proof=save('complete1422-independent-current-source-body-mode-proof-v2.json',{'head':H,'tree':T,'entries':allsource,'unchanged_parent_entries':len(old)-len(changed)})
sourcepath=changed[0];original=g('show',P+':'+sourcepath);current=(R/sourcepath).read_bytes();assert hashlib.sha256(original).hexdigest()=='f432e65a488bf06862e548dc45342d3c1fb5ea7fcc26f6371d98aae124ffc082' and original==(D/'original-source-preRED.private.py').read_bytes()
original_ast=ast.parse(original);current_ast=ast.parse(current);fn=next(n for n in current_ast.body if isinstance(n,ast.FunctionDef) and n.name=='force_kill_process_tree_until');added_nodes=[n for n in fn.body if isinstance(n,ast.If) and isinstance(n.test,ast.BoolOp) and isinstance(n.test.values[0],ast.Name) and n.test.values[0].id=='wrapper_reaped'];assert len(added_nodes)==1;node=added_nodes[0];fn.body.remove(node);assert ast.dump(original_ast,include_attributes=False)==ast.dump(current_ast,include_attributes=False)
assert ast.unparse(node.test)=='wrapper_reaped and time.monotonic() < deadline'
node_calls=[ast.unparse(x.func) for x in ast.walk(node) if isinstance(x,ast.Call)];assert 'psutil.wait_procs' in node_calls and not any(x.endswith(('.kill','.terminate','.wait')) or x=='psutil.Process' for x in node_calls)
# All other source and result properties are exactly preserved. New code uses handles, not PID lookup.
assert 'timeout=max(0.0, deadline - time.monotonic())' in ast.unparse(node)
assert 'child.is_running() and child.status() != psutil.STATUS_ZOMBIE' in ast.unparse(node)
assert ast.dump(ast.parse((R/added[0]).read_bytes()),include_attributes=False)==ast.dump(ast.parse((D/'original-permanent-tests-preRED.private.py').read_bytes()),include_attributes=False)
red=suite('permanent-original-RED-successor-junit.xml');green=suite('permanent-GREEN-junit.xml');initial=suite('permanent-original-RED-junit.xml');adjacent=suite('adjacent-source-controls-junit.xml')
assert (red['tests'],red['failed'],red['errors'],red['skipped'])==(10,2,0,0)
assert set(red['failure_names'])=={'test_captured_child_can_finish_after_wrapper_within_same_deadline','test_remaining_descendant_wait_error_is_reported'}
assert (green['tests'],green['failed'],green['errors'],green['skipped'])==(10,0,0,0) and red['test_names']==green['test_names']
assert (initial['tests'],initial['failed'],initial['errors'],initial['skipped'])==(10,0,10,0)
assert (adjacent['tests'],adjacent['failed'],adjacent['errors'],adjacent['skipped'])==(104,0,0,1)
for prefix in ['doctor','own-inputs-and-origins','prepared-copy-v2','permanent-GREEN','authored-configured-format','full-configured-static','toolkit','generator-roundtrip','adjacent-source-controls','source-preservation-v2']:
 assert json.loads((D/(prefix+'-exit.json')).read_bytes())['exit_code']==0
assert json.loads((D/'source-preservation-exit.json').read_bytes())['exit_code']==1
static=(D/'full-configured-static.private.log').read_text();assert 'Success: no issues found in 350 source files' in static and all(x in static for x in ('ruff check','ruff format','isort'))
assert '96 passed' in (D/'toolkit.private.log').read_text()
private_owner=Path('/workspace/engineering/pr306-original-cleanup-deterministic-control-owned/OWNERFINAL-original-cleanup-deterministic-control-v2.json');prior=json.loads(private_owner.read_bytes());assert len(prior['bindings'])==31
for v in prior['bindings']:check(v)
copy=json.loads((D/'own-five-environment-copy-proof.json').read_bytes());storage=Path(copy['unique_owned_storage']);assert stat.S_IMODE(storage.stat().st_mode)==0o700 and len(copy['environments'])==5
records=[]
for v in copy['environments']:
 check(v['inventory']);rec=json.loads(Path(v['inventory']['path']).read_bytes());src=Path('/workspace/engineering/pr306')/v['package']/'.venv';own=Path(rec['physical_owned_env']);link=Path(rec['checkout_link']);assert link.is_symlink() and os.readlink(link)==rec['symlink_target'] and link.resolve()==own.resolve() and own.is_relative_to(storage)
 observed=inventory(src);assert observed==rec['original_complete_inventory'] and len(observed)==v['members']
 # Re-derive the approved path-only copy contents from preserved originals; no extraction/copy/mutation.
 expected={n:dict(row) for n,row in observed.items()};rebound={r['relative']:r for r in rec['path_only_rebindings']}
 for n,r in rebound.items():
  assert n=='pyvenv.cfg' or n.startswith('bin/') or n.endswith('.pth') or n.endswith('/direct_url.json')
  b=(src/n).read_bytes();assert hashlib.sha256(b).hexdigest()==r['original_sha256'];b=b.replace(b'/workspace/engineering/pr306',str(R).encode());assert hashlib.sha256(b).hexdigest()==r['rebound_sha256'];expected[n].update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
 assert expected==rec['own_complete_inventory']
 currentown=inventory(own);diff=sorted(n for n in set(currentown)|set(expected) if currentown.get(n)!=expected.get(n))
 # Runtime imports may legitimately populate bytecode; never claim whole-owned-environment immutability without comparing.
 assert all(n.endswith('.pyc') and '__pycache__' in n for n in diff), 'non-bytecode owned environment difference'
 records.append({'package':v['package'],'original_complete_inventory_exact':True,'original_recorded_members':len(observed),'own_paths_unique_and_initial_complete_record_rederived':True,'current_owned_bytecode_only_difference_count':len(diff),'no_current_owned_noncached_input_difference':True})
prepared=json.loads((D/'checked-own30-and-five-origins.json').read_bytes());assert len(prepared['inputs_sha256'])==30
for n,h in prepared['inputs_sha256'].items():assert sha(R/n)==h
for v in prepared['origins']:
 check(v);r=json.loads(Path(v['path']).read_bytes());assert Path(r['origin']).is_relative_to(R) and Path(r['origin']).is_file() and Path(r['resolved_prefix']).is_relative_to(storage) and Path(r['reported_prefix']).resolve()==Path(r['resolved_prefix'])
fixture=json.loads((D/'own-ignored-pinned-RCC-fixture-preparation.json').read_bytes())
for key in ('source','primary','own_ignored_destination'):assert sha(fixture[key])==fixture['sha256'] and Path(fixture[key]).stat().st_size==fixture['bytes']
assert stat.S_IMODE(Path(fixture['own_ignored_destination']).stat().st_mode)==int(fixture['mode'],8)
plugin=R/'action_server/.venv/lib/python3.12/site-packages/psutil/__init__.py';ps=ast.parse(plugin.read_bytes());isrunning=next(n for n in ps.body if isinstance(n,ast.ClassDef) and n.name=='Process');isrunning=next(n for n in isrunning.body if isinstance(n,ast.FunctionDef) and n.name=='is_running');assert 'self != Process(self.pid)' in ast.unparse(isrunning)
gen=json.loads((D/'generator-roundtrip-successor-v2-receipt.json').read_bytes());assert gen['generated_output_count']==8 and gen['all_tracked_GitHub_YAML_count']==30
for n,h in gen['all30_GitHub_paths_parsed_and_bytes_preserved'].items():assert sha(R/n)==h and new[n]==old[n]
canonical=Path('/workspace/engineering/pr306-original-cleanup-deterministic-control-owned/canonical-captured-tree-unused-deadline-proposed.patch');assert sha(canonical)=='36cc60d3263af329268d80c32f28fdd6ae5909fd71d9fc7bd60ba59c3dd04f93'
lesson=''.join(n[1:] for n in canonical.read_text().splitlines(True) if n.startswith('+') and not n.startswith('+++'));assert len(lesson.splitlines())==12;guide=(R/changed[1]).read_text();oldguide=g('show',P+':'+changed[1]).decode();assert guide.count(lesson)==1 and guide.replace(lesson,'',1)==oldguide
source_delta=save('independent-exact-source-and-guide-patch-binding-v2.json',{'source_patch_SHA256':hashlib.sha256(g('diff',P,H,'--',sourcepath)).hexdigest(),'guide_patch_SHA256':hashlib.sha256(g('diff',P,H,'--',changed[1])).hexdigest(),'accepted_canonical_original':bind(canonical)})
assert not g('status','--porcelain')
result={'verdict':'GO_FROZEN_LIGHT_SOURCE_AND_BOUNDED_FULL_PREPARATION_ONLY','owner':owner,'head':H,'tree':T,'sole_parent':P,'existing_branch':a['branch'],'complete1422_source_proof':proof,'unchanged_parent_body_mode_count':1419,'only3_exact_authorized_path_changes':changed+added,'all67_owner_and31_private_original_bindings_verified':True,'original_whole_source_AST_preserved_after_exact21line_block_removal':True,'semantics_review':'Only captured descendants observed identity-live/nonzombie AFTER exclusive Popen wrapper reap enter psutil.wait_procs with max(0,same deadline-currenttime); no fresh child PID lookup/signals/additional deadline/reader grace; original strict error/live/zombie/snapshot result classification and legacy Process.stop exactly preserved. is_running identity check verified against own locked psutil source; universal identity/race/discovery/reaping not inferred.','meaningful_controls':{'original_setup_failure':initial,'original_source_RED':red,'fixed_source_GREEN':green,'adjacent':adjacent,'coverage':'late child completion0.75 within18; promptcompletion; still-live deadline; unreaped wrapper exclusive Popen; reused handle nonsignal; zombie incomplete; kill/snapshot errors; final wait error; zero budget. Ten fake-handle source controls, not real native OS/lifecycle proof.'},'static_Toolkit_and_workflows':{'Toolkit_pass':96,'configured_lint':'RuffformatIsortPASS','Mypy_files':350,'generated':8,'all_YAML':30,'workflow_receipt_head':'a0d at precommit source inspection; entire generated workflow bodies/Git modes still exact parent/current499, not new production/native qualification'},'environment_readonly_verification':records,'own30_five_origins_ignored_RCC_verified':True,'production_native_scope':{'current_production':274,'selected_tests_separate':5,'combined':279,'old_production':268,'old_matches':260,'old_changed':8,'added':6,'only_new_production_delta_from_actual_parent':sourcepath,'qualification':'UNQUALIFIED; no oldnative carry or source/actual replay'},'retained_failures_and_drafts':'10ERROR setupFAIL, genuine2FAIL8PASS RED, original private1FAIL8PASS and failedconstructor, failed guide-reader anchoring inspector, stale-capacity draft preserved; named v2s correction only, no retroactive GO.','full_gate':'HOLD distinct ROOT serialized release AFTER300 full; fresh capacity/reserve and explicit2 workers600TERM+10 needed. No new full command/run authorization by this review.','fresh_available_bytes_observation_only':os.statvfs(R).f_bavail*os.statvfs(R).f_frsize,'remaining_HOLD':['current full source/finalSOURCE/fullCI/push/PRcreation/integration','hosted FIRST timeout cause/survivoridentity/remainingbudget UNKNOWN; no change to unsampled fourfailures','native/platform/private/provider/browser/fullcleanup/gracefulleases/discovery/Runtime release'], 'documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md','Exact_delta':bind(canonical),'Current_source_patch_proof':source_delta,'Disposition':'Exact accepted12line36cc lesson verified once; sufficient durable correction, no redundant text or source changes.','Durable_learning':'Original two short descendant waits can leave shared deadline unused after quick wrapper reap; preserve strict incomplete classification and exclusive Popen ownership while spending only remainder.','Evidence':'Originalf432 wholeAST; controlledoriginalRED2/8 and fixedGREEN10; newblock and unchangedstrictresult fields; existing real hosted log remains causally unresolved.','Stale_or_ambiguous_guidance_removed':'Wrapper reap and control clock0.41/0.75 do not establish complete reaping or hosted timeout cause; source full gate and capacity observation stay separate.','Remaining_uncertainty':'Current full/platform/native lifecycle and hosted cause remain unverified.'},'upstream_disposition':'none','review_actions':'Read-only Git/blob/AST/receipt/rawJUnit/inventory reads; no gates/tests/consumer/native downloads or application edits.','retained_original_independent_inspector_failure':bind(O/'original-review-failure-mode-scope-diagnosis.json'),'original_failed_constructor':bind(O/'verify-independent-frozen-LIGHT.py'),'immutable_constructor':bind(__file__)}
print(json.dumps(save('OWNERFINAL-independent-captured-child-cleanup-frozen-LIGHT-review-v2.json',result)))
