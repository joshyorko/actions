"""Read-only Git/filesystem/privacy review; emits external receipts only."""
import datetime,hashlib,json,os,re,stat,subprocess
from pathlib import Path
R=Path('/workspace/engineering/campaign-checkpoint');B=Path('/workspace/engineering/control-memory-checkpoint-independent-application-review')
D='docs/handoffs/evidence/actions-swarm-mk3-20261011-control-memory-continuation'
M=R/D/'exact-safe-original-source-and-owner-copy-manifest.json'
G=R/'docs/skills/repository-operations.md'
PARENT='843cb16dc071fc764f11f1e0b3b07432dcd04a7d'

def row(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();raw=p.read_bytes()
 return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'mode':oct(stat.S_IMODE(s.st_mode))}
def put(n,j):
 p=B/n
 with p.open('x') as f:json.dump(j,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 p.chmod(0o400);return row(p)
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
assert git('rev-parse','HEAD').decode().strip()==PARENT
assert not git('diff','--cached','--name-only')
manifest_binding=row(M);assert manifest_binding['sha256']=='91703bb9cdd4cf616f00bd8e506b6dd9bc8228b10c707f142ef872575cfafeed'
m=json.loads(M.read_text());assert m['parent']==PARENT and m['files']==len(m['copies'])==36 and sum(x['bytes'] for x in m['copies'])==m['bytes']==303157
assert len({x['path'] for x in m['copies']})==36
copies=[]
for x in m['copies']:
 p=R/x['path'];src=Path(x['source']);assert p.parent==M.parent
 a=row(p);b=row(src);assert (a['bytes'],a['sha256'])==(x['bytes'],x['sha256'])==(b['bytes'],b['sha256']) and b['mode']==x['source_mode']
 assert p.read_bytes()==src.read_bytes();assert x['scope']=='Exact original historical owner or private source checkpoint; no runtime adoption or evidence promotion'
 copies.append({'copy':a,'original':b})
assert {p.name for p in M.parent.iterdir()}=={Path(x['path']).name for x in m['copies']}|{M.name}
grow=row(G);assert grow['bytes']==254108 and grow['sha256']=='15e988c9bb0e7ce9930a849a7daaef04b42ee24a924b39683d60986ecb9097aa'
oldguide=git('show',PARENT+':docs/skills/repository-operations.md');newguide=G.read_bytes();assert newguide.startswith(oldguide)
append=newguide[len(oldguide):];assert len(append.splitlines())==77
assert git('diff','--numstat','--','docs/skills/repository-operations.md').decode().strip()=='77\t0\tdocs/skills/repository-operations.md'
oldpaths={}
for part in git('ls-tree','-rz','HEAD').split(b'\0'):
 if part:
  meta,path=part.split(b'\t',1);mode,kind,objectid=meta.decode().split();oldpaths[path.decode()]=(mode,kind,objectid)
preserved=0
for path,(mode,kind,objectid) in oldpaths.items():
 assert kind=='blob';p=R/path;s=p.lstat();assert ('120000' if stat.S_ISLNK(s.st_mode) else '100755' if stat.S_IMODE(s.st_mode)&0o111 else '100644')==mode
 if path=='docs/skills/repository-operations.md':continue
 raw=os.readlink(p).encode() if stat.S_ISLNK(s.st_mode) else p.read_bytes();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==objectid
 preserved+=1
allowed={x['path'] for x in m['copies']}|{str(M.relative_to(R)),'docs/skills/repository-operations.md'}
status=git('status','--porcelain=v1','--untracked-files=all').decode().splitlines();changed={line[3:] for line in status};assert changed==allowed
assert git('diff','--check')==b''
# Full selected byte scan, not an assertion that global external storage lacks secrets.
patterns={'signed_query':r'(?:X-Amz-Signature|X-Goog-Signature|[?&](?:sig|se|sv|token|signature)=)',
 'credential_literal':r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)',
 'bearer_literal':r'Bearer\s+[A-Za-z0-9_-]{20,}'}
urls=[];jsonrows=0;sourcerows=0
for x in m['copies']:
 raw=(R/x['path']).read_bytes();text=raw.decode('utf-8')
 assert not any(re.search(pattern,text,re.I) for pattern in patterns.values())
 for u in re.findall(r'https?://[^\s\"<>]+',text):assert u.split('/')[2]=='github.com';urls.append('PUBLIC_GITHUB_EXISTING_UPSTREAM_COORDINATION_URL')
 if x['path'].endswith('.json'):
  j=json.loads(text);assert type(j) is dict;jsonrows+=1
 else:
  assert x['path'].endswith('.py');sourcerows+=1
 # No signed urls/private payload packages/logfile bytes were selected. Historical path/hash references are allowed.
 assert not Path(x['path']).name.endswith(('.zip','.gz','.tar','.log','.robolog','.xml','.whl','.bin'))
# Scope decisions verified from the original copied receipt bodies.
def copyj(n):return json.loads((R/m['copies'][n-1]['path']).read_text())
assert copyj(5)['decision']=='FAIL_STOP_CONTROL3_V9_NATIVE_NOT_QUALIFIED_NEWER5_7276_NOTRUN'
assert copyj(9)['decision']=='HOLD_ORIGINAL_MEMORY17_PRE_TEST_MODE_ADMISSION_FAILED_NO_PURE_TEST_CENSUS'
assert copyj(10)['decision']=='GO_ACTUAL_MEMORY17_PURE_CONTROLS_ONLY_NO_NATIVE_POLICY_ADOPTION'
assert copyj(13)['decision']=='HOLD_ORIGINAL_GATE_UNCHANGED_MINIMAL_JUNIT_PROTOCOL_SUCCESSOR_PROPOSED_ONLY'
assert copyj(14)['decision']=='GO_ORIGINAL_KNOWN_NINE18_SEMANTIC_RED_RESTORED_GREEN_SOURCE_ONLY_ACTUAL'
assert copyj(16)['decision']=='GO_ACTUAL_CURRENT8D49_READER_OBSERVER28_SYNTHETIC_CONTROLS_ONLY'
assert copyj(19)['decision']=='GO_EXACT_ORIGINAL_FAILED_FULL_PARTIAL_RELOCATION_ACTUAL_DATA_PRESERVATION_ONLY'
assert copyj(20)['decision']=='GO_ACTUAL_EXACT_COMPLETED_FULL_SINGLE_COPY_DATA_STORAGE_PRESERVATION_ONLY'
append_binding={'bytes':len(append),'sha256':hashlib.sha256(append).hexdigest(),'added_lines':77,'deleted_lines':0}
index=git('ls-files','--stage','-z');indexfp=hashlib.sha256(index).hexdigest()
proof=put('independent-all36-exact-original-copies-parent-preservation-and-scope-proof.json',{'schema':1,'status':'READONLY_EXACT_APPLICATION_PROOF','parent':PARENT,'manifest_binding':manifest_binding,'copies':copies,'copied_files':36,'copied_bytes':303157,'copied_JSON_receipts':jsonrows,'copied_public_source_files':sourcerows,'all_prior_tracked_body_modes_preserved_except_guide':preserved,'prior_tracked_paths':len(oldpaths),'guide_binding':grow,'exact_guide_append':append_binding,'allowed_changed_paths':sorted(allowed),'staged_changes':'NONE','unchanged_index_stage_listing_SHA256':indexfp,'selected_privacy_scan':'No signed query/bearer/credential literals or raw log/config/index/archive/binary payloads; only2public GitHub upstream coordination links; private path/hash references retained','public_GitHub_URLs':len(urls),'author_tracked_diffcheck':'PASS_77APPEND_ONLY','scope':'Owner receipts/source closure historical additive provenance only, not executable/config/profile/consumer/release/native acceptance. No raw secret/whole private inventory or failed receipt promotion','reviewer_activity':'READONLY_GIT_AND_BYTES_NO_TESTS_PRODUCT_IMPORTS_OR_STAGE'})
dispositions=[
 {'delta':'per-child fixed bootstrap/import boundary; path-owned700 vs711 and consumed pre-root release','evidence':'copies01/02/09 preserve original V8 import and memory17 admission failures; copies10 pure17 successor actual only','decision':'ACCEPT_SOURCE_BACKED'},
 {'delta':'Original subprocess tuple, primary/secondary publication and null cleanup scope','evidence':'copies05/06 retain control3 FAIL; signal:killed sourceUNKNOWN and missing publication; no5/7276 execution','decision':'ACCEPT_SOURCE_BACKED'},
 {'delta':'8c28 shared memory/headroom/profile and d6 self identity/read caps/join/interval attribution','evidence':'copies15/16/33/34/35/36 preserve pure/synthetic-only policy and observer; no full backend/native/headroom calibration','decision':'ACCEPT_WITH_EXISTING_BACKEND_ADOPTION_HOLD'},
 {'delta':'5584 catalog immutable nested snapshot/held-lock boundary and37c observed omitted JUnit type','evidence':'copies11/12/13/14/32 retain original failures, corrected baseline and specific known18 source-only sensitivity scope','decision':'ACCEPT_SOURCE_BACKED_NO_NATIVE_OR_COMPLETE_ORACLE_CLAIM'},
 {'delta':'Exact fallback enclosure, actual baseline first and no stale correction carry','evidence':'copies11/13/14 original baseline/protocol FAIL preserved alongside named source-only successors','decision':'ACCEPT_SOURCE_BACKED'},
 {'delta':'Progress writer dispatch, capped index/executableaddresses/budgets/single hardlink copy and typed failed partial alias','evidence':'copies17/18/19/20 scope lossless storage only, original failed partial remainsFAIL; no gzip completion upgrade or native qualification','decision':'ACCEPT_SOURCE_BACKED_REUSE_CURRENT_SOURCE_LESSONS_NO_NEW_WIRING_CLAIM'},
 {'delta':'Unique device/inode recovery bytes, distinct environment/restoration dependency subject and disk versus RAM','evidence':'copy28 is explicit readonly environment capacity proposal, no removal; source dependencies/prefix/symlinks remain obligations','decision':'ACCEPT_PLAN_SCOPE_NO_COMPLETED_RECOVERY_OR_NATIVE_CLAIM'}]
receipt=put('OWNERFINAL-independent-control-memory-continuation-safe-copy-canonical-application-GO.json',{'schema':1,'status':'INDEPENDENT_EXACT_SAFE_CHECKPOINT_APPLICATION_GO','decision':'GO_NORMAL_DOCUMENTATION_COMMIT_PUSH_EXISTING_CHECKPOINT_BRANCH_ONLY_AFTER_ROOT_OWN_STAGE_COMMITTED_HASH_READBACK','parent':PARENT,'manifest_binding':manifest_binding,'guide_binding':grow,'independent_proof':proof,'files':36,'bytes':303157,'allowed_changed_paths_count':len(allowed),'old_tracked_preserved_except_append':preserved,'index_stage_listing_SHA256':indexfp,'documentation':{'exact_delta':append_binding,'canonical_dispositions':dispositions,'accepted_existing_source_lessons':'Exact root77line append sufficient; no cosmetic extra proposal or session diary','stale_ambiguity_removed':'Prepared source and synthetic/pure/data-preservation receipts cannot qualify backend/native/release or erase original failure; per-path modes and protocol emitters are measured independently','remaining_uncertainty':'This is WORKING application and unchanged index review. ROOT must stage exact allowed paths then verify staged/committed originals and actual remote; private external references/full archives not bundled or newly admitted; backend/native/current campaign release holds remain'},'privacy':'SELECTED_COPY_BYTES_INSPECTED_NO_CREDENTIAL_SIGNED_URL_RAW_PRIVATE_PAYLOAD_FOUND','reviewer_tests_source_stage_commit_push':'NONE','upstream_disposition':'none','capture':datetime.datetime.now(datetime.timezone.utc).isoformat()})
assert row(M)==manifest_binding and row(G)==grow and hashlib.sha256(git('ls-files','--stage','-z')).hexdigest()==indexfp
print(json.dumps(receipt))
