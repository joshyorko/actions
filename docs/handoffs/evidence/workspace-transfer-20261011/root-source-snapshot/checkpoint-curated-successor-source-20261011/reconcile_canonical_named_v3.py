import datetime,difflib,hashlib,json,stat,subprocess
from pathlib import Path
OUT=Path(__file__).parent;REPO=Path('/workspace/engineering/campaign-checkpoint');ENG=Path('/workspace/engineering');TARGET='a54c982462d1e7ad011d8152bfc299d997503fb3'
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(REPO),*args],timeout=30)
def sha(x):return hashlib.sha256(x).hexdigest()
def save(p,d):p.open('x').write(json.dumps(d,indent=2)+'\n');p.chmod(0o600)
before={name:(OUT/('original-dirty-'+Path(name).name)).read_bytes() for name in ['docs/skills/repository-operations.md','docs/skills/provenance-observability.md']}
assert all((REPO/name).read_bytes()==raw for name,raw in before.items())
manifest=REPO/'docs/program/evidence/wave11/current-engineering-successor-20261011/curated-safe-manifest.json';rows=json.loads(manifest.read_bytes())['rows']
for r in rows:assert sha((REPO/r['proposed_successor_relative_path']).read_bytes())==r['sha256']
operations=before['docs/skills/repository-operations.md'].decode();provenance=before['docs/skills/provenance-observability.md'].decode();dispositions=[]
def added_blocks(patch):
 blocks=[];current=[]
 for line in Path(patch).read_text().splitlines():
  if line.startswith('+') and not line.startswith('+++'):current.append(line[1:])
  elif current:blocks.extend('\n'.join(current).strip().split('\n\n'));current=[]
 if current:blocks.extend('\n'.join(current).strip().split('\n\n'))
 return [b for b in blocks if b]
def insert_block(block,anchor,code):
 global operations
 if block in operations:dispositions.append(dict(code=code,status='DUPLICATE_ALREADY_EXACT_RETAINED'));return
 assert operations.count(anchor)==1,(code,'ANCHOR_UNAVAILABLE')
 operations=operations.replace(anchor,block+'\n\n'+anchor,1);dispositions.append(dict(code=code,status='CONTEXT_ADAPTED_EXACT_BLOCK_INSERTED'))
incoming=git('show',TARGET+':docs/skills/provenance-observability.md').decode();section=incoming[incoming.index('## Private common Run-output boundary'):incoming.index('## Verification matrix')]
denial=next(b for b in added_blocks(ENG/'pr305-current-e3c-source-LIGHT/exact-imported-e3-canonical-guide-delta.patch') if b.startswith('For assembled output-transport denials'))
assert denial in provenance and denial in section;section=section.replace(denial+'\n\n','');assert '## Private common Run-output boundary' not in provenance
provenance=provenance.replace('## Verification matrix',section+'## Verification matrix',1);dispositions.append(dict(code='OUTPUT_TRANSPORT',status='ACTUAL_A54_COHERENT_SECTION_IMPORTED_DIRTY_DENIAL_PARAGRAPH_EXACT_ONCE'))
for code,name in [('CACHE','pr308-owned-package-cache-independent-private-patch-review/exact-accepted-owned-package-cache-canonical-delta.patch'),('CACHE_RUNNER','rcc-compatibility-owned-cache-runner-successor-preparation/canonical-current-cache-runner-proposed-delta.patch'),('NATIVE_HOME_MODE','rcc-current-e4ff-cache-mode-private-v8-proposal/canonical-native-managed-home-mode-boundary-exact-proposed.patch')]:insert_block('\n\n'.join(added_blocks(ENG/name)),'Managed spec-v2 Action packages use the provisional RCC runtime adapter only',code)
for code,name in [('ARCHIVE_ALIAS','pr308-cache-current-e3c-SOURCEFULL-preexecution/canonical-exact-historical-receipt-archive-alias-proposed.patch'),('COPY_SCOPE','curated-successor-handoff-plan-after62f4/canonical-safe-curated-successor-proposed.patch'),('CONFIG_PATH_CLOSURE','pr305-current5306-SOURCEFULL-preexecution-executable-v4/canonical-config-consumed-path-dependency-closure-proposed.patch'),('PYTEST_STORAGE','pytest38-completed-preservation-readonly-proposal/canonical-pytest-root-origin-and-bounded-preservation-proposed.patch'),('PYTEST_RETENTION','pytest38-completed-preservation-private-source/canonical-pytest-retention-evidence-root-protection-proposed.patch'),('SCOPED_RELEASE','pr313-current12dd-bound-FULL-independent-preexecution-review/exact-scoped-execution-review-decision-canonical-proposed.patch')]:insert_block('\n\n'.join(added_blocks(ENG/name)),'## Pull Request Triage',code)
target_ops=git('show',TARGET+':docs/skills/repository-operations.md').decode();a=target_ops.index('separately from RCC wrapper receipts.');a=target_ops.rfind('\n\n',0,a)+2;b=target_ops.index('The bounded retirement result',a);shutdown=target_ops[a:b].strip();insert_block(shutdown,'The bounded process-tree result distinguishes wrapper reaping, observed live','SHUTDOWN_RESPONSE_AND_NATURAL_EXIT')
for name in ['pr305-current-e3c-source-LIGHT/exact-imported-e3-canonical-guide-delta.patch','pr282-current-a54-source-LIGHT/exact-imported-a54-canonical-guide-delta.patch']:
 for block in added_blocks(ENG/name):
  if block in operations or block in provenance:dispositions.append(dict(code=Path(name).name,block_sha256=sha(block.encode()),status='EXACT_DUPLICATE_RETAINED'))
  elif block.startswith(('wiring, adapters and Canvas execution','explicit `/api/shutdown/`')):dispositions.append(dict(code=Path(name).name,block_sha256=sha(block.encode()),status='COVERED_BY_COHERENT_ACTUAL_A54_CONTEXT_IMPORT'))
  else:raise RuntimeError('UNRECONCILED_ACCEPTED_CANONICAL_BLOCK:'+sha(block.encode()))
for name,new in [('docs/skills/repository-operations.md',operations),('docs/skills/provenance-observability.md',provenance)]:
 assert all(tag in {'equal','insert'} for tag,*_ in difflib.SequenceMatcher(a=before[name].decode().splitlines(keepends=True),b=new.splitlines(keepends=True),autojunk=False).get_opcodes())
 (REPO/name).write_text(new)
save(OUT/'exact-canonical-reconciliation-dispositions-v3.json',dispositions)
print(json.dumps(dict(copied=len(rows),canonical_dispositions=len(dispositions),dirty_guides_addition_only=True,commit='NOT_RUN')))
