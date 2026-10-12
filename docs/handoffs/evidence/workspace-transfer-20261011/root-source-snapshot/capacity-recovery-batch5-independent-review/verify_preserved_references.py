from pathlib import Path
import ast,hashlib,json
D=Path('/workspace/engineering/capacity-recovery-batch5-independent-review');initial=D/'independent-batch5-archive-preservation-review.json'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def binding(p):return {'path':str(p),'bytes':Path(p).stat().st_size,'sha256':sha(p)}
prior_specs=[('existing-workspace-scratch-capacity-recovery.json','bc18bca235d00e9d7ca0f618653ba1c004f6c27afbbf535894cf6d4977cc3c71','complete_private_inventory','recovery_records','/workspace/engineering/capacity-recovery-independent-review/independent-archive-preservation-review-v2.json','918485892e6663cedd3bb595824ef181a1ac87f8172a0bc4f026065941b214f6'),('existing-workspace-scratch-capacity-recovery-batch2.json','30bcb73c25914e33eb0705cdb5367cc1a07cfba5f0890eaf8d365876186f3537','private_inventory_binding','archives','/workspace/engineering/capacity-recovery-batch2-independent-review/independent-batch2-archive-preservation-review-v2.json','70951f62ce8ecab772976827522c64fd38f7eb2e469421a26256bc2723106ecd'),('existing-workspace-scratch-capacity-recovery-batch3.json','3328b24d3ca8bcdc8998f44f5fe7463a9fadc14a4051b5172ea56312abb0d880','private_inventory_binding','archives','/workspace/engineering/capacity-recovery-batch3-independent-review/independent-batch3-archive-preservation-review-v2.json','82328cb7bc68c77b7e12392e1ad01e1b58cd48a536e8acbb75f0a2cfb1b85219')]
prior_specs.append(('existing-workspace-scratch-capacity-recovery-batch4.json','12e4d0ca481de54144088c824d6130301c650ada23bb647bfd1c96c030b0a431','private_inventory_binding','archives','/workspace/engineering/capacity-recovery-batch4-independent-review/independent-batch4-archive-preservation-review-v2.json','83d3ace6990571dc9b1e910fd7418e78c55748a4e8090caf2707074426117242'))
prior=[];count=0
for name,digest,inventory_key,archives_key,receipt,receipt_digest in prior_specs:
 p=Path('/workspace/engineering')/name;assert sha(p)==digest;old=json.loads(p.read_text());assert binding(old[inventory_key]['path'])==old[inventory_key]
 for e in old[archives_key]:
  a=Path(e['archive']);assert a.stat().st_size==e['archive_bytes'] and sha(a)==e['archive_sha256'];count+=1
 assert sha(receipt)==receipt_digest
 prior.append({'summary':binding(p),'private_inventory':old[inventory_key],'all_archive_bytes_size_SHA_preserved':True,'archive_count':len(old[archives_key]),'original_independent_review':binding(receipt)})
assert count==13
first=json.loads(Path(prior_specs[0][4]).read_text());one=Path('/tmp/actions-capacity-recovery.py');assert binding(one)==first['source_recovery_script']
two=Path('/tmp/actions-capacity-recovery-batch5.py');assert sha(two)=='00d2d46a37403b101261ebfafd32b087045ed41e2374b250965d7fe54a8432b7'
def normalized(p):
 t=ast.parse(p.read_bytes());t.body=[n for n in t.body if not(isinstance(n,ast.Assign) and any(isinstance(a,ast.Name) and a.id in ['NAMES','DEST','STAGE'] for a in n.targets))];return ast.dump(t,include_attributes=False)
assert normalized(one)==normalized(two)
runner=Path('/workspace/actions-cloud/receipts/pr305-runner/canvas-native-public-runner-v5.py');assert sha(runner)=='09cdc6b19f5d3d9cc94fadca23373108868521e0378d33960146b1a8522e88ad';failed=list(Path('/workspace/actions-cloud/robocorp/temp').glob('563d*'));assert len(failed)==1 and failed[0].is_dir()
canonical=Path('/workspace/engineering/capacity-recovery-independent-review/canonical-completed-scratch-preservation-proposed.patch');assert sha(canonical)=='7d07065b5bb7742698919997c8c6621cc20d00494741eb5365251ffb09f2d208';paragraph=''.join(line[1:] for line in canonical.read_text().splitlines(keepends=True) if line.startswith('+') and not line.startswith('+++'));guide=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md');assert paragraph in guide.read_text();excerpt=D/'canonical-existing-capacity-paragraph.md';excerpt.write_text(paragraph)
d=json.loads(initial.read_text());d['prior13_archives_4privateindices_summaries_and_reviews_exact_original_hashes_preserved']=prior
d['algorithm_parity']={'batch5_tool':binding(two),'first_tool':binding(one),'AST_exact_except_names_and_private_output_dirs':True,'scope':'No recovery script execution by independent reviewer; two exact namespace names and existing outputdirs only'}
d['immutable_reference_spotchecks']={'V5runner':binding(runner),'failed563d_namespace_exists':True,'scope':'Frozen externalrunner byteidentity and failed563d directory existence only; no unbaselined content equality or current sourcewriter hash claims'}
d['original_archive_review_preserved']=binding(initial)
d['canonical_documentation']={'file':'docs/skills/repository-operations.md','repository_instructions_read':binding('/workspace/actions/AGENTS.md'),'accepted_original_exact_delta':binding(canonical),'current_root_integrated_exact_excerpt':binding(excerpt),'disposition':'Existing7d070 capacity paragraph is verbatim integrated and sufficient for same-algorithm fifth batch; no new learning warrants duplicate/cosmetic guide changes','evidence':'29862 unique members with all internal hardlink payloads and recorded metadata verified; prior13 archive+4index+summary+review hashes unchanged; recovery AST same except2exact names/outputdirs; no original failedgates relabeled','stale_ambiguity':'A TAR hardlink header is not missing regular data; archived recorded metadata does not qualify unrecorded ACL/xattr/root/inode/mtime or retroactivehandle state; recovered capacity does not pass ENOSPC tests','remaining_uncertainty':'Expanded originals gone by design; byte proof bounded to retained pre-removal inventory. Full historical handle census and unrecorded metadata unavailable. No baseline content guarantee for failed563d or concurrent source writers. Source/native/private/backend/release gates remain separate','upstream':'none'}
p=D/'independent-batch5-archive-preservation-review-v2.json';p.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(binding(p)))
