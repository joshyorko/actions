import ast,datetime,difflib,hashlib,json,os,re,stat,subprocess
from pathlib import Path
OUT=Path(__file__).parent;REPO=Path('/workspace/engineering/campaign-checkpoint');ENG=Path('/workspace/engineering')
PLAN=ENG/'curated-successor-handoff-plan-after62f4/OWNERFINAL-safe-curated-successor-handoff-plan-after62f4.json'
BASE='62f4e180f6c894777ebc8ed3a729e88d2f6531d6';TARGET='a54c982462d1e7ad011d8152bfc299d997503fb3'
DEST=REPO/'docs/program/evidence/wave11/current-engineering-successor-20261011'
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(REPO),*args],timeout=30)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def bind(p):
 p=Path(p);r=p.read_bytes();return dict(path=str(p),bytes=len(r),sha256=sha(r),mode=oct(stat.S_IMODE(p.stat().st_mode)))
def save(p,d,mode=0o600):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.open('x').write(json.dumps(d,indent=2)+'\n');p.chmod(mode);return bind(p)
assert git('rev-parse','HEAD').decode().strip()==BASE
assert git('branch','--show-current').decode().strip()=='handoff/actions-swarm-mk3-wave8-20261010'
assert git('status','--porcelain').decode().splitlines()==[' M docs/skills/provenance-observability.md',' M docs/skills/repository-operations.md']
plan=json.loads(PLAN.read_bytes());before={}
for name,row in plan['dirty_canonical_guides_preserved'].items():
 assert bind(REPO/name)==row
 raw=(REPO/name).read_bytes();p=OUT/('original-dirty-'+Path(name).name);p.open('xb').write(raw);p.chmod(0o600);before[name]=raw
assert sha((ENG/'checkpoint-current-engineering-after299-0938.py').read_bytes())=='0319f50eaa81800c7edf3bc75b80182bbfc5721ba0ef86d45c199e3bc0a6d4d1'
rows=plan['curated_rows'][:]
additional=[
('current308','pr308-native-home-mode-current-a54-SOURCE-LIGHT/OWNERFINAL-current396925-public-native-home-mode-and-a54-union-SOURCE_LIGHT.json'),
('current308','pr308-current3969-independent-SOURCE-LIGHT-review/OWNERFINAL-independent-current3969-SOURCE-LIGHT-review.json'),
('current308','pr308-current3969-independent-source-union-review/OWNERFINAL-independent-current3969-static-source-union-review.json'),
('mode_failure','rcc-current-e4ff-control3-actual-independent-review/OWNERFINAL-independent-original-current-e4ff-control3-cache-mode-actual-failure-review.json'),
('mode_failure','rcc-current-e4ff-control3-mode-source-diagnosis-owned/OWNERFINAL-independent-source-supported-current-control3-home-mode-diagnosis-and-minimal-proposal.json'),
('mode_failure','rcc-current-e4ff-cache-mode-private-v8-proposal/OWNERFINAL-PUBLIC-current-e4ff-native-managed-home-mode-fixture-and-guide-patch.json'),
('current308','root-pr308-public-home-mode-patch-ordinary-a54-adoption/OWNERFINAL-root-exact-public-home-mode-patch-and-ordinary-a54-adoption.json'),
('current282','root-pr282-current1299-one-configured-sourcefull/OWNERFINAL-root-current1299-configured-SOURCEFULL-PASS.json'),
('current282','pr282-current1299-independent-actual-SOURCEFULL-review/OWNERFINAL-independent-current1299-original-configured-SOURCEFULL-review.json'),
('current282','root-pr282-current1299-one-normal-draft-source-push/OWNERFINAL-root-one-current1299-normal-source-push.json'),
('current305','pr305-current-a54-source-LIGHT/OWNERFINAL-current5306-ordinary-a54-source-LIGHT-source-HOLD.json'),
('current305','pr305-current5306-SOURCEFULL-preexecution-executable-v4/OWNERFINAL-current5306-managed-configured-SOURCEFULL-preexecution-proposal.json'),
('current305','pr305-current5306-independent-executable-v4-review/OWNERFINAL-independent-current5306-executable-v4-static-preexecution-review.json'),
('capacityB27','root-B27-one-existing-tmp-recovery-named-v2/OWNERFINAL-root-one-B27-named-metadata-existing-tmp-terminal.json'),
('capacityB27','capacity-recovery-batch27-independent-actual-review/OWNERFINAL-independent-original-B27-existing-tmp-actual-byte-preservation-review.json'),
('current221','pr221-currenta54-metadata-source-artifact-review/OWNERFINAL-current-a54-PR221-metadata-source-artifact-readiness-review.json'),
('current221','pr221-currenta54-one-original-aggregate-acquisition-preparation/OWNERFINAL-current-a54-one-original-aggregate-acquisition-PREPARATION-v2.json'),
('pytest38','pytest38-completed-preservation-private-source/OWNERFINAL-exact-pytest38-storage-archiver-preexecution-SOURCE-HOLD.json'),
('pytest38','pytest38-completed-preservation-private-source/safe-source-absence-and-installed-retention-mechanism.json'),
('currentCI','root-current-engineering-heads-CI-20261011-1641/safe-current-heads-CI-summary.json'),
('canonical','rcc-current-e4ff-cache-mode-private-v8-proposal/canonical-native-managed-home-mode-boundary-exact-proposed.patch'),
('canonical','pr305-current5306-SOURCEFULL-preexecution-executable-v4/canonical-config-consumed-path-dependency-closure-proposed.patch'),
('canonical','pytest38-completed-preservation-readonly-proposal/canonical-pytest-root-origin-and-bounded-preservation-proposed.patch'),
('canonical','pytest38-completed-preservation-private-source/canonical-pytest-retention-evidence-root-protection-proposed.patch'),
('canonical','curated-successor-handoff-plan-after62f4/canonical-safe-curated-successor-proposed.patch')]
# Resolve the exact worker-announced current305 LIGHT path; never create a copied subject filename.
additional=[(g,n.replace('OWNERFINAL-current5306-ordinary-a54-source-LIGHT-source-HOLD.json','OWNERFINAL-current5306-ordinary-a54-source-LIGHT-full-and-actual-HOLD.json')) for g,n in additional]
for group,name in additional:
 p=ENG/name;r=bind(p);r.update(group=group,proposed_successor_relative_path=str(DEST.relative_to(REPO)/f'{group}--{p.name}'));rows.append(r)
for row in rows:
 p=Path(row['path']);assert bind(p)=={k:row[k] for k in ('path','bytes','sha256','mode')}
# Read every body; keep an explicit field-level diagnostic private. No recursive binding copy.
def scan(x,p=()):
 issues=[]
 if isinstance(x,dict):
  for k,v in x.items():
   if k.lower() in {'access_token','client_secret','api_key','signed_url','raw_response','raw_body','environment_dump'} and isinstance(v,str) and v:issues.append('.'.join((*p,k)))
   if k.lower() in {'stdout','stderr'} and isinstance(v,str) and v and not (v.endswith('.log') or v in {'PIPE','DEVNULL','CAPTURED_PRIVATE'}):issues.append('.'.join((*p,k)))
   issues+=scan(v,(*p,k))
 elif isinstance(x,list):
  for v in x:issues+=scan(v,p)
 elif isinstance(x,str):
  if re.search(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|X-Amz-Signature=|sig=[A-Za-z0-9%]{30,})',x):issues.append('.'.join(p)+':credential-pattern')
 return issues
privacy=[]
for row in rows:
 p=Path(row['path']);raw=p.read_bytes()
 if p.suffix=='.json':
  value=json.loads(raw);issues=scan(value);privacy.append(dict(path=str(p),issues=issues,body_inspected=True))
  row['original_declared_status']=value.get('status',value.get('decision',value.get('admission','NO_SINGLE_STATUS_FIELD')))
 else:privacy.append(dict(path=str(p),issues=[],exact_patch_only=True))
save(OUT/'private-safe-payload-field-inspection.json',privacy)
assert not any(r['issues'] for r in privacy), 'PRIVACY_CLASSIFICATION_HOLD'
assert not DEST.exists();DEST.mkdir(parents=True)
for row in rows:
 p=Path(row['path']);dest=REPO/row['proposed_successor_relative_path'];assert not dest.exists();dest.open('xb').write(p.read_bytes());dest.chmod(0o644);assert sha(dest.read_bytes())==row['sha256'];row['copied_Git_mode']='100644'
manifest=dict(schema=1,status='CURATED_SAFE_SUCCESSOR_COPY_SOURCE_REVIEW_REQUIRED_NOT_COMMITTED',
 predecessor=BASE,named_target=TARGET,original_curated40_count=40,original_curated40_bytes=345772,
 additional_exact_rows=len(additional),total=len(rows),total_bytes=sum(r['bytes'] for r in rows),
 private_reference_payload_copy='NOT_AUTHORIZED_NOT_PERFORMED',collector0319_rerun='NOT_RUN',
 rows=rows,sourcegraph54_regeneration='NOT_RUN',prior1180_manifest='RETAINED_UNCHANGED')
save(DEST/'curated-safe-manifest.json',manifest,0o644)
# Reconcile exact existing accepted paragraphs; preserve every pre-existing dirty byte.
operations=before['docs/skills/repository-operations.md'].decode();provenance=before['docs/skills/provenance-observability.md'].decode();dispositions=[]
def added_blocks(patch):
 blocks=[];current=[]
 for line in Path(patch).read_text().splitlines():
  if line.startswith('+') and not line.startswith('+++'):current.append(line[1:])
  elif current:blocks.append('\n'.join(current).strip());current=[]
 if current:blocks.append('\n'.join(current).strip())
 return [b for b in blocks if b]
def insert_block(block,anchor,code):
 global operations
 if block in operations:dispositions.append(dict(code=code,status='DUPLICATE_ALREADY_EXACT_RETAINED'));return
 assert operations.count(anchor)==1,(code,'ANCHOR_UNAVAILABLE')
 operations=operations.replace(anchor,block+'\n\n'+anchor,1);dispositions.append(dict(code=code,status='CONTEXT_ADAPTED_EXACT_BLOCK_INSERTED'))
# Source-bound private service/transport contract has a coherent owning section in actuala54.
incoming=git('show',TARGET+':docs/skills/provenance-observability.md').decode()
section=incoming[incoming.index('## Private common Run-output boundary'):incoming.index('## Verification matrix')]
# Existing dirty denial paragraph is retained at its original verification location; no duplicate.
denial=next(b for b in added_blocks(ENG/'pr305-current-e3c-source-LIGHT/exact-imported-e3-canonical-guide-delta.patch') if b.startswith('For assembled output-transport denials'))
assert denial in provenance;assert denial in section;section=section.replace(denial+'\n\n','')
assert '## Private common Run-output boundary' not in provenance
provenance=provenance.replace('## Verification matrix',section+'## Verification matrix',1)
dispositions.append(dict(code='OUTPUT_TRANSPORT',status='ACTUAL_A54_CANONICAL_SECTION_IMPORTED_DIRTY_DENIAL_PARAGRAPH_RETAINED_ONCE'))
for code,name in [('CACHE','pr308-owned-package-cache-independent-private-patch-review/exact-accepted-owned-package-cache-canonical-delta.patch'),('CACHE_RUNNER','rcc-compatibility-owned-cache-runner-successor-preparation/canonical-current-cache-runner-proposed-delta.patch'),('NATIVE_HOME_MODE','rcc-current-e4ff-cache-mode-private-v8-proposal/canonical-native-managed-home-mode-boundary-exact-proposed.patch')]:
 block='\n\n'.join(added_blocks(ENG/name));insert_block(block,'Managed spec-v2 Action packages use the provisional RCC runtime adapter only',code)
for code,name in [('ARCHIVE_ALIAS','pr308-cache-current-e3c-SOURCEFULL-preexecution/canonical-exact-historical-receipt-archive-alias-proposed.patch'),('COPY_SCOPE','curated-successor-handoff-plan-after62f4/canonical-safe-curated-successor-proposed.patch'),('CONFIG_PATH_CLOSURE','pr305-current5306-SOURCEFULL-preexecution-executable-v4/canonical-config-consumed-path-dependency-closure-proposed.patch'),('PYTEST_STORAGE','pytest38-completed-preservation-readonly-proposal/canonical-pytest-root-origin-and-bounded-preservation-proposed.patch'),('PYTEST_RETENTION','pytest38-completed-preservation-private-source/canonical-pytest-retention-evidence-root-protection-proposed.patch'),('SCOPED_RELEASE','pr313-current12dd-bound-FULL-independent-preexecution-review/exact-scoped-execution-review-decision-canonical-proposed.patch')]:
 block='\n\n'.join(added_blocks(ENG/name));insert_block(block,'## Pull Request Triage',code)
# Accepted large imported patches: classify duplicate paragraphs and import missing shutdown contract as source text.
for name in ['pr305-current-e3c-source-LIGHT/exact-imported-e3-canonical-guide-delta.patch','pr282-current-a54-source-LIGHT/exact-imported-a54-canonical-guide-delta.patch']:
 for block in added_blocks(ENG/name):
  if block in operations or block in provenance:dispositions.append(dict(code=Path(name).name,block_sha256=sha(block.encode()),status='EXACT_DUPLICATE_RETAINED'))
  elif block.startswith(('wiring, adapters and Canvas execution','explicit `/api/shutdown/`','The assembled route')):dispositions.append(dict(code=Path(name).name,block_sha256=sha(block.encode()),status='COVERED_BY_COHERENT_ACTUAL_A54_CONTEXT_IMPORT'))
  else:raise RuntimeError('UNRECONCILED_ACCEPTED_CANONICAL_BLOCK:'+sha(block.encode()))
target_ops=git('show',TARGET+':docs/skills/repository-operations.md').decode()
a=target_ops.index('separately from RCC wrapper receipts.')
a=target_ops.rfind('\n\n',0,a)+2;b=target_ops.index('The bounded retirement result',a)
shutdown=target_ops[a:b].strip();insert_block(shutdown,'The bounded process-tree result distinguishes wrapper reaping, observed live','SHUTDOWN_RESPONSE_AND_NATURAL_EXIT')
# Before dirty operations is a byte-preserving subsequence: additions only.
matcher=difflib.SequenceMatcher(a=before['docs/skills/repository-operations.md'].decode(),b=operations,autojunk=False)
assert all(tag in {'equal','insert'} for tag,*_ in matcher.get_opcodes())
# Provenance is addition-only too: no pre-existing dirty sentences discarded.
matcher=difflib.SequenceMatcher(a=before['docs/skills/provenance-observability.md'].decode(),b=provenance,autojunk=False)
assert all(tag in {'equal','insert'} for tag,*_ in matcher.get_opcodes())
(REPO/'docs/skills/repository-operations.md').write_text(operations);(REPO/'docs/skills/provenance-observability.md').write_text(provenance)
save(OUT/'exact-canonical-reconciliation-dispositions.json',dispositions)
print(json.dumps(dict(copied=len(rows),bytes=sum(r['bytes'] for r in rows),canonical_dispositions=len(dispositions),commit='NOT_RUN')))
