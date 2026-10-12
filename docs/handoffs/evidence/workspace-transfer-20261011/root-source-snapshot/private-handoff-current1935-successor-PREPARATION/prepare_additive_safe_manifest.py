"""Read-only checkpoint/source curation. No copies or Git mutations."""
import hashlib,json,os,re,subprocess
from pathlib import Path
O=Path(__file__).resolve().parent
E=Path('/workspace/engineering');C=E/'campaign-checkpoint'
def sha(b):return hashlib.sha256(b).hexdigest()
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b),'mode':oct(p.stat().st_mode&0o777)}
def put(name,d):
 p=O/name;b=d.encode() if isinstance(d,str) else (json.dumps(d,indent=2,sort_keys=True)+'\n').encode();fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o400)
 with os.fdopen(fd,'wb') as f:f.write(b)
 return bind(p)
head=subprocess.check_output(['git','-C',str(C),'rev-parse','HEAD']).decode().strip();assert head=='d55ed399a5b6ba67e88002dd6d490ac9366c2130'
assert subprocess.check_output(['git','-C',str(C),'status','--porcelain'])==b''
old=subprocess.check_output(['git','-C',str(C),'ls-tree','-rz',head,'--','docs/handoffs'])
existing={};counts={}
for row in old.split(b'\0'):
 if not row:continue
 header,path=row.split(b'\t',1);mode,kind,oid=header.decode().split();assert kind=='blob';p=C/path.decode();data=p.read_bytes();assert subprocess.check_output(['git','-C',str(C),'hash-object','--stdin'],input=data).decode().strip()==oid
 existing.setdefault(sha(data),[]).append(path.decode())
 for key in ['1830Z','1853']:
  if key in path.decode():counts[key]=counts.get(key,0)+1
paths=[
('source-light-owner','pr308-expectedEDF-fresh-gates-preparation/OWNERFINAL-current8d49-configured-SOURCE_LIGHT-PASS.json'),
('source-light-independent','pr308-current8d49-independent-SOURCE-LIGHT-review/OWNERFINAL-independent-current8d49-configured-SOURCE_LIGHT-review.json'),
('source-full-independent-retained-rootpost','pr308-current8d49-independent-SOURCEFULL-actual-review/OWNERFINAL-independent-current8d49-original-configured-SOURCEFULL-and-retained-ROOTpost-supplement-review.json'),
('Windows-original-diagnosis','pr308-current8d49-original-Windows-one-owned/OWNERFINAL-current8d49-one-original-Windows-source-and-static-failure-diagnosis.json'),
('Windows-private-patch-source-owner','pr308-current8d49-Windows-private-portability-successor/OWNERFINAL-private-current8d49-Windows-portability-source-PROPOSAL.json'),
('Windows-private-patch','pr308-current8d49-Windows-private-portability-successor/proposed-two-path-assertions-and-cache-owner-features.patch'),
('Windows-private-source-independent','pr308-current8d49-Windows-private-portability-independent-review/OWNERFINAL-independent-private-current8d49-Windows-portability-SOURCE-proposal-review.json'),
('reload-drain-NOTRUN','pr308-current8d49-managed-reload-drain-private-preparation/OWNERFINAL-current8d49-managed-reload-drain-private-source-and-nine-real-controls-PREPARED-NOTRUN.json'),
('persistent-source-patch','pr308-current8d49-persistent-two-path-private-recontext/frozen-current8d49-two-path-persistent-fixture-source.patch'),
('persistent-source-independent','pr308-current8d49-persistent-recontext-independent-review/OWNERFINAL-independent-private-current8d49-persistent-recontext-SOURCE_ONLY-and-logging-HOLD.json'),
('Runtime-seven-inner-actual-independent','pr221-current-e2-inner-v2-ACTUAL-independent-review/OWNERFINAL-independent-original-current-e2-seven-distribution-inner-ACTUAL-integrity-review.json'),
('Runtime-original-outer-independent','pr221-current-e2-original-outer-inspection-independent-review/OWNERFINAL-independent-current-e2-original-outer-inspection-ACTUAL-data-integrity-review-v2.json'),
('Runtime-original-transfer-FAIL','root-current-e2-one-aggregate-adoption/OWNERFINAL-root-original-one-current-e2-aggregate-transfer-failure-and-exact-retained-ZIP.json'),
('Runtime-Mac-Windows-source-checkout-owner-review-pending','pr221-currente2c-Mac-Windows-original-producer-log-owned/OWNERFINAL-currente2-original-Mac-Windows-producer-checkout-build-identity-only.json'),
('V8-qualified-config-owner-NOTRUN','rcc-current8d49-qualified-V8-config-preparation/OWNERFINAL-current8d49-qualified-V8-control3-config-and-managed-PREEXEC.json'),
('V8-qualified-config-independent-PREEXEC','rcc-current8d49-qualified-V8-independent-preexecution-review/OWNERFINAL-independent-current8d49-qualified-V8-control3-config-managed-PREEXEC-review.json'),
('V8-qualified-constructor-source','rcc-current8d49-qualified-V8-config-preparation/build_qualified_current8d49_config_v8_FINAL.py'),
('V8-managed-entry-source','rcc-current8d49-qualified-V8-config-preparation/managed_one_version_entry_v8.py'),
('V8-launcher-source','rcc-current8d49-qualified-V8-config-preparation/launch_one_version_v8.py'),
('V8-readonly-guard-source','rcc-current8d49-qualified-V8-config-preparation/readonly_current_input_guard_v8.py'),
('V8-gateway-source','rcc-current8d49-qualified-V8-config-preparation/gateway_entry_v8.py'),
('FIVE-storage-PREEXEC-review-pending','completed8d49-five-root-storage-PREPARATION-v4/OWNERFINAL-five-completed8d49-roots-capped-storage-PREEXECUTION-v4.json'),
('canonical-native-logger','rcc-current8d49-private-V8-fixture-logger-successor/canonical-private-actual-fixture-history-and-pytest-logger-proposed.patch'),
('canonical-Windows-feature-guard','pr308-current8d49-Windows-private-portability-successor/canonical-native-path-and-POSIX-feature-proposed.txt'),
('canonical-Poetry-capture','completed8d49-four-root-storage-PREPARATION-v3/proposed-canonical-managed-Poetry-and-guard-capture-lesson.txt'),
('canonical-ZIP-vs-TAR','pr221-current-e2-inner-data-executor-successor-v2-PREPARATION/canonical-real-data-inspector-entry-and-boundary-controls-proposed-v2.patch'),
('canonical-platform-checkout','pr221-currente2c-Mac-Windows-original-producer-log-owned/canonical-original-platform-checkout-identity-proposed.md')]
rows=[]
for n,(role,rel) in enumerate(paths,1):
 p=E/rel;r=bind(p);assert r['bytes']<50000
 text=p.read_text();assert not re.search(r'https?://\S*[?&](?:sig|X-Amz-Signature|access_token|token)=',text,re.I)
 if p.suffix=='.json':json.loads(text)
 destination='docs/handoffs/evidence/actions-swarm-mk3-20261011-1935Z/'+f'{n:02d}-'+p.name
 r.update({'role':role,'proposed_destination':destination,'already_copied_at_checkpoint':existing.get(r['sha256'],[]),'copy_needed':r['sha256'] not in existing,'privacy':'Safeowner/patch/public-source orchestration only; nestedreferences are scopes not copies. No rawlog/API/member/index/config/binary content admitted.'})
 rows.append(r)
new=[r for r in rows if r['copy_needed']];assert sum(r['bytes'] for r in new)<=200000
manifest=put('proposed-additive-safe-reference-manifest.json',{'schema':'PRIVATE_PROPOSED_ADDITIVE_SAFE_HANDOFF_REFERENCE_MANIFEST','checkpoint_base':head,'checkpoint_tree':subprocess.check_output(['git','-C',str(C),'rev-parse',head+'^{tree}']).decode().strip(),'checkpoint_branch':subprocess.check_output(['git','-C',str(C),'branch','--show-current']).decode().strip(),'original_handoff_subtree_serialization_sha256':sha(old),'original_handoff_files_verified':len([r for r in old.split(b'\0') if r]),'original_1830_1853_counts':counts,'selected_rows':rows,'new_copy_count':len(new),'new_original_bytes':sum(r['bytes'] for r in new),'no_copy_or_checkpoint_mutation':True,'private_exclusions':['rawlogs/API/MCP responses/signedURLs','fullmember/source/preparedinventories','binaries/artifactZIP/wheelmemberbodies','OAuth/provider/userconfiguration','private760Kqualifiedconfig','privatecurrentraws/rootstdio/native outputs'],'source_current':'8d49d0865ad5ad27b2d4e325ec135212080625e8','source_tree':'a80600809d373038ca76e445ba0b7b79bb7eeaa6','integration_current_at_capture':'e2c81adce7858d5a952991ba9a8b7f72e902038a','scope':'Proposedimmutable1935snapshot, notlivepolledCI/currentexecutionrelease','upstream_disposition':'none'})
lead='''# Engineering handoff successor proposal — captured 2026-10-11 19:35Z

This is a private additive proposal on the existing checkpoint branch. Preserve
checkpoint d55ed399a5b6ba67e88002dd6d490ac9366c2130 and all older1830Z/1853/8f
handoffs, original copied evidence and construction/failure scopes unchanged.
No checkpoint file, index, branch, commit or remote changed in this preparation.

PR308 remains draft at8d49d0865ad5ad27b2d4e325ec135212080625e8,
treea80600809d373038ca76e445ba0b7b79bb7eeaa6. Linux LIGHT and original configured
FULL1470PASS13SKIP are independently accepted. Preserve the separate ROOT post
environment failure and named read-only supplement; it did not rerun the suite.
Current Windows remains source/static HOLD: two expected-Path-string failures
and seven POSIX UID/GID stub errors. The independently accepted private patch
093cb/3cb is NOTADOPTED to keep the native qualification tuple immutable.
Captured current CI25SUCCESS/1FAIL is metadata, not a native compatibility result.

Runtime current-e2 original aggregate inner integrity is independently accepted
291686: all six wheels and the sdist bind217 tracked source files. Measured wheel
layout219package/203Python/223RECORD/222hashed remains distribution-only evidence.
Original transfer6bf079 FAIL and independent outer22eed remain distinct. OAuth
contains two empty config values per report; HTML/generated-input authority,
installed consumers, other-platform source authority and publication remain HOLD.
The Mac/Windows literal-checkout owner is acquired, with its independent review
pending at this capture. No new original log or artifact acquisition is proposed.

Native control3, released5 and exactcandidate7276 remain NOT_RUN for this successor;
no newer binary has a functional result. Qualified V8 constructor/launchers and
independent PREEXEC3860 are frozen. The FIVE-root storage a133 proposal is still
review-pending at capture. Only after its actual preservation/independent result,
fresh workspace>=1288490189B and shm>=3865470567B, ROOT may bind a real typed
release SHA and authorize exactly one control3 command. The frozen argv template
is retained in the manifest's V8 owners; its root-SHA slot is not executable approval.
Stop on failure. Released5 then7276 each need predecessor actualPASS, independently
qualified same-source config and a distinct one-attempt ROOT release; no loops/retries.
Managed activation18exports+PATH, unchanged3defaults/buildpins and scoped budgets
remain required. No provider credentials, new infrastructure or runtime rebuild.

Private persistentec231/source-only and reloadfaf0/nine-control-NOTRUN packets remain
unadopted. After baseline native qualification, ROOT can decide their smallest
existing-branch adoption, retaining real handlers, ownership/lifecycle assertions and
provider-recovery HOLD. The Windows portability patch requires its own reviewed
source adoption and fresh configured/Windows gates; existing1470Linux results cannot
qualify changed tests. Existing PR305/313 successor work retains its own source/gate
identities and is not promoted by this handoff.

The retained54-contract graph is not closed:53remain open and accepted210 remains
closed;221 is draft/release HOLD. Full private/native/consumer/provider/backend,
Workspace/ChatGPT/product-epic acceptance and publication remain separate. This
proposal closes no issue and does not declare campaign completion.

The proposed manifest records exact original bytes/hashes, scope and existing-copy
reuse. Copy only safe owners, patches and reviewed orchestration modules. Keep raw
logs/API/index/member bodies/binaries/signed URLs/OAuth values and the private760K
configuration outside Git. ROOT may integrate reviewed contextual canonical lessons
and append this lead only when a later actual milestone is owner-announced.
'''
leadrow=put('proposed-1935Z-engineering-handoff-successor.md',lead)
canonical=[]
guide=(C/'docs/skills/repository-operations.md').read_text()
for role in ['canonical-native-logger','canonical-Windows-feature-guard','canonical-Poetry-capture','canonical-ZIP-vs-TAR','canonical-platform-checkout']:
 row=next(r for r in rows if r['role']==role);text=Path(row['path']).read_text();canonical.append({'binding':{k:row[k] for k in ['path','bytes','sha256','mode']},'disposition':'ROOT contextual integration/reuse only; do not apply patch headers blindly or duplicate already accepted paragraphs','already_copied':row['already_copied_at_checkpoint']})
owner=put('OWNERFINAL-private-current1935-additive-handoff-PROPOSAL.json',{'schema':'OWNERFINAL_PRIVATE_CURRENT1935_ADDITIVE_HANDOFF_PROPOSAL','status':'PREPARATION_ONLY_CHECKPOINT_UNTOUCHED','checkpoint_base':head,'manifest_binding':manifest,'lead_binding':leadrow,'evidence':[manifest,leadrow,bind(__file__)],'copy_budget':{'new_selected_original_bytes':sum(r['bytes'] for r in new),'new_selected_originals':len(new),'all_selected_rows':len(rows),'maximum':200000},'canonical_candidates':canonical,'source_paths_and_nextcommands':'Exact qualifiedV8 argv/rootrelease/capacity and sourceownerpaths in manifest; rootSHAunfilled meansNOTAUTHORIZED. Smallestnextstep independentstorage thenactualcontrol3 ROOTonce; otherversions/privatefixtures/Windowspatch separate.','preservation':'AlltrackedhandoffsubtreefileGitbytes rehashed; currentcheckpoint cleanandunchanged. No mutablealiascurrentclaim; references retainhistoricalscope.','documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; precise queued d21d/3169/f46d/f797/7418 lessons contextual adoption or explicit reuse only','Durable_learning':'Historicalfixture/bodyidentity, ownedpytestlogger, POSIXfeatures, capturedPoetryresult, ZIPheader-vsTAR and per-platformcheckout are separate trust boundaries','Evidence':'Selectedindependentowners/originalfailure and actual7distributionreports exactsourcebindings; no testreplay','Stale_or_ambiguous_guidance_removed':'1935append distinguishes1830pending from lateracceptedFULL/inner; no overwrittenoldlead/currentnativeinference','Remaining_uncertainty':'FIVEactual/indreview and native3/5/7276pending, Windowspatchnotadopted, generatedcontent/consumer/sourceauthority/releaseHOLD'},'upstream_disposition':'none'})
assert subprocess.check_output(['git','-C',str(C),'status','--porcelain'])==b''
for r in rows:assert bind(r['path'])=={k:r[k] for k in ['path','bytes','sha256','mode']}
print(json.dumps({'owner':owner,'manifest':manifest,'lead':leadrow,'new_copy_count':len(new),'new_bytes':sum(r['bytes'] for r in new),'old_handoff_files':len([r for r in old.split(b'\0') if r]),'checkpoint_mutation':'NONE'}))
