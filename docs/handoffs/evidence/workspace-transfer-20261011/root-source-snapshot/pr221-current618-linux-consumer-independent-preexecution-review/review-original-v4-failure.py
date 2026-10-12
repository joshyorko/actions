import ast
import datetime
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

B=Path('/workspace/engineering/pr221-current618-linux-consumer-preflight')
O=Path('/workspace/engineering/pr221-current618-linux-consumer-independent-preexecution-review')
R=Path('/workspace/engineering/pr282')
def sha(data):return hashlib.sha256(data).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def bind(row):
 p=Path(row['path']);v=p.read_bytes();assert len(v)==row['bytes'] and sha(v)==row['sha256'];return row
def ownbind(p):
 p=Path(p);v=p.read_bytes();return {'path':str(p),'bytes':len(v),'sha256':sha(v)}
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*args])
owner=bind({'path':str(B/'OWNERFINAL-original-current618-consumer-gateway-failure.json'),'bytes':2740,'sha256':'6f29ccd4b905b0036e6347aac23c12bda82cb6a719a1e7da0008eec951c0e773'})
d=load(owner['path'])
for key in ['proposal','authorization','gateway_exit','original_gateway_log','post_harness']:bind(d[key])
p=load(d['proposal']['path']);authorization=load(d['authorization']['path']);exit=load(d['gateway_exit']['path'])
assert d['observed_gateway_exit']==exit['exit_code']==10 and exit['automatic_retry'] is False
assert authorization['actual_attempts_authorized']==1
bind(authorization['independent_GO'])
assert authorization['independent_GO']['sha256']=='856e104d0bba81067e682dd9c5b959ae52b04579f2785b4b63822f9443c11913'
for key in ['runner','input_gate','input_manifest']:bind(p[key])
assert p['runner']['sha256']=='06f64db20bba0554f570d4653f11fb7bccc7b98ec2e7de7085ab90fd8ba7333b'
for row in p['all_private_preexecution_files_and_preserved_originals']:bind(row)
bind(p['previous_held_v3_proposal']);bind(p['previous_independent_HOLD'])
floor=p['helpers_current_Git618_and_immutable_snapshots_exact']['floor'];bind(floor)
source=Path(floor['path']).read_text();floor_ast=ast.parse(source)
selector=next(n for n in floor_ast.body if isinstance(n,ast.FunctionDef) and n.name=='select_runtime_wheel')
selector_source=ast.get_source_segment(source,selector)
assert 'directory.glob("actions_runtime-*.whl")' in selector_source
assert '"-cp312-" not in wheel.name' in selector_source
assert 'len(candidates) != 1' in selector_source
wheel=Path(p['selected_cp312_wheel']['path']);parent=wheel.parent
original_artifact_owner=load(bind(p['artifact_data_ownerfinal'])['path'])
known={Path(row['path']).resolve():row for row in original_artifact_owner['evidence'] if Path(row['path']).suffix=='.whl'}
candidate_records=[];other_abi=0
for path in sorted(parent.glob('actions_runtime-*.whl')):
 assert path.resolve() in known;bind(known[path.resolve()])
 if '-cp312-' not in path.name:other_abi+=1;continue
 with zipfile.ZipFile(path) as z:
  metadata_paths=[name for name in z.namelist() if name.endswith('.dist-info/METADATA')]
  assert len(metadata_paths)==1;metadata=BytesParser().parsebytes(z.read(metadata_paths[0]))
  assert metadata.get('Name')=='actions-runtime' and metadata.get('Version')=='1.0.3'
 candidate_records.append({'filename':path.name,'bytes':path.stat().st_size,'sha256':known[path.resolve()]['sha256'],'platform':'Windows' if 'win_amd64' in path.name else 'Linux','ABI':'cp312'})
assert len(candidate_records)==2 and {r['platform'] for r in candidate_records}=={'Linux','Windows'}
assert other_abi==2
runner_source=Path(p['runner']['path']).read_text();runner_ast=ast.parse(runner_source)
supervisor=next(n for n in runner_ast.body if isinstance(n,ast.FunctionDef) and n.name=='supervisor')
selection=next(n for n in ast.walk(supervisor) if isinstance(n,ast.Assert) and 'select_runtime_wheel' in ast.unparse(n))
attempt_mkdir=next(n for n in ast.walk(supervisor) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='ATTEMPT' and n.func.attr=='mkdir')
temp=next(n for n in ast.walk(supervisor) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='mkdtemp')
process=next(n for n in ast.walk(supervisor) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='Popen')
assert selection.lineno==331 and selection.lineno<attempt_mkdir.lineno<temp.lineno<process.lineno
log=Path(d['original_gateway_log']['path']).read_text()
assert 'Expected exactly one cp312 actions-runtime 1.0.3 wheel in' in log and 'found 2' in log
assert 'installed-consumer-runner-v4.py", line 331, in supervisor' in log
assert 'select_runtime_wheel' in log and 'actual main robot run" was FAILURE' in log
assert not Path(d['attempt_namespace']).exists()
pre=load(p['harness']['complete_prehash']['path']);post=load(d['post_harness']['path'])
assert pre['tracked_sha256']==post['tracked_sha256'] and pre['tracked_executable_bits']==post['tracked_executable_bits'] and pre['count']==post['count']==1433
assert pre['head']==post['head']==p['harness']['head'] and pre['tree']==post['tree']==p['harness']['tree']
assert git('rev-parse','HEAD').decode().strip()==post['head'] and git('rev-parse','HEAD^{tree}').decode().strip()==post['tree'] and git('status','--porcelain')==b''
for path,digest in post['tracked_sha256'].items():
 assert sha((R/path).read_bytes())==digest
 assert bool((R/path).stat().st_mode&0o111)==post['tracked_executable_bits'][path]
proof={'schema':'current618-linux-consumer-original-v4-failure-independent-review/v1','status':'HOLD_ACTUAL_CONSUMER_UNQUALIFIED_SELECTOR_DIRECTORY_PRECONDITION_FAILED','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owner_final_failure':owner,'proposal':d['proposal'],'authorization':d['authorization'],'original_gateway_log':d['original_gateway_log'],'original_gateway_exit':d['gateway_exit'],'post_harness':d['post_harness'],'actual_gateway_exit':10,'actual_attempts_authorized':1,'verified_failure':{'exception':'ValueError','source_function':'verify_published_runtime_floor.select_runtime_wheel','runner_supervisor_line':331,'unchanged_floor_SHA256':floor['sha256'],'directory_contract':'Exactly one cp312 actions-runtime1.0.3 wheel; strict existing selector intentionally has no platform filter','actual_directory_original_qualified_candidates':candidate_records,'cp313_ignored_by_selector':other_abi,'before_attempt_mkdir_temporary_worker_install_CLI_cleanup':True,'attempt_namespace_absent':True,'no_consumer_worker_or_install_acceptance':True,'cleanup':'UNAVAILABLE: no owned worker or temp/attempt was created; no leak/natural/reaping claim inferred','consumer_phase_network_not_reached':'Source ordering only; no universal RCC gateway network census claim'},'source_retention':{'current_harness_head':post['head'],'tree':post['tree'],'all1433_prepost_current_FS_hash_execbits_clean':True,'v4_all60_refs_exact':True,'original_v3_proposal_and_HOLD_exact':True,'historical_v4_preexecution_GO':authorization['independent_GO'],'preexecution_GO_not_relabelled_actual_or_overwritten':True},'review_gap':'The preexecution review bound selectedwheel bytes and existing selector code but did not admit the actual WHEEL.parent candidate population. The authorized actual safely failed this unmet directory prerequisite. Preserve the preexecution-only review history and add a source-backed directory-exclusivity admission before any separately reviewed successor attempt.','next_source_or_proposal_scope':'Root-authorized writer may preserve the mixed original acquisition directory and make named private copies of the exact original Linuxcp312+cp313 pair. Meaningful read-only real selector RED on mixed originals, GREEN on isolated pair, and foreigncp312 injection rejection must bind a new immutable proposal. No weakened selector/platform fallback, no original archive/wheel deletion or automatic actual retry.','documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; accept root/owner upcoming exact directory-exclusivity lesson','Durable_learning':'A fixed wheel path/digest does not satisfy a selector that scans its parent directory. Qualify the directory candidate set using the real selector before installation; retain mixed original acquisitions and isolate exact selected platform bytes without weakening selection.','Evidence':'Immutable original gateway log and source line331; exact unchanged floor function; independent data-only two legitimate cp312 candidate inventories; actual attempt absent and1433 source posthashes unchanged. Prior5f08 independent-provenance lesson retained, but archive identity and directory uniqueness are separate prerequisites.','Stale_or_ambiguous_guidance_removed':'Preexecution byte/identity GO is not actual installed-consumer acceptance and does not implicitly prove the parent-directory selector contract.','Remaining_uncertainty':'No current installed consumer/cleanup/CLI result. Any successor requires frozen proposal review and distinct root execution authorization; OAuth/Windows/macro-platform/fullseven/private/native/tag/release HOLD.','Disposition':'Evidence-backed exact lesson supplied for root integration; no cosmetic source/document child by reviewer.'},'not_performed':['Selector or consumer reexecution','Tests/controls/gateway/installer/payload imports','Source/index/branch writes or downloads','Delete/copy/restore originals, push/merge/release'], 'upstream_disposition':'none'}
f=O/'independent-frozen-original-v4-consumer-failure-review.json';assert not f.exists();f.write_text(json.dumps(proof,indent=2)+'\n');f.chmod(0o444)
print(json.dumps({'path':str(f),'bytes':f.stat().st_size,'sha256':sha(f.read_bytes()),'status':proof['status']}))
