from pathlib import Path
import ast,hashlib,json
D=Path('/workspace/engineering/capacity-recovery-batch3-independent-review');initial=D/'independent-batch3-archive-preservation-review.json';d=json.loads(initial.read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def binding(p):return {'path':str(p),'bytes':Path(p).stat().st_size,'sha256':sha(p)}
firstpath=Path('/workspace/engineering/existing-workspace-scratch-capacity-recovery.json');assert sha(firstpath)=='bc18bca235d00e9d7ca0f618653ba1c004f6c27afbbf535894cf6d4977cc3c71';first=json.loads(firstpath.read_text());assert binding(first['complete_private_inventory']['path'])==first['complete_private_inventory']
for e in first['recovery_records']:
 p=Path(e['archive']);assert p.stat().st_size==e['archive_bytes'] and sha(p)==e['archive_sha256']
secondpath=Path('/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch2.json');assert sha(secondpath)=='30bcb73c25914e33eb0705cdb5367cc1a07cfba5f0890eaf8d365876186f3537';second=json.loads(secondpath.read_text());assert binding(second['private_inventory_binding']['path'])==second['private_inventory_binding']
for e in second['archives']:
 p=Path(e['archive']);assert p.stat().st_size==e['archive_bytes'] and sha(p)==e['archive_sha256']
secondreview=Path('/workspace/engineering/capacity-recovery-batch2-independent-review/independent-batch2-archive-preservation-review-v2.json');assert sha(secondreview)=='70951f62ce8ecab772976827522c64fd38f7eb2e469421a26256bc2723106ecd'
firstreview=Path('/workspace/engineering/capacity-recovery-independent-review/independent-archive-preservation-review-v2.json');assert sha(firstreview)=='918485892e6663cedd3bb595824ef181a1ac87f8172a0bc4f026065941b214f6';firstd=json.loads(firstreview.read_text())
assert binding('/tmp/actions-capacity-recovery.py')==firstd['source_recovery_script']
one=Path('/tmp/actions-capacity-recovery.py');two=Path('/tmp/actions-capacity-recovery-batch3.py');assert sha(two)=='2843727e9f9d7a48f39e1a6a64dc9ccbb7a0c38b22951b401d4781fcb0bc5b50'
def normalized(p):
 t=ast.parse(p.read_bytes());t.body=[n for n in t.body if not(isinstance(n,ast.Assign) and any(isinstance(a,ast.Name) and a.id in ['NAMES','DEST','STAGE'] for a in n.targets))];return ast.dump(t,include_attributes=False)
assert normalized(one)==normalized(two)
runner=Path('/workspace/actions-cloud/receipts/pr305-runner/canvas-native-public-runner-v5.py');assert sha(runner)=='09cdc6b19f5d3d9cc94fadca23373108868521e0378d33960146b1a8522e88ad'
root=Path('/workspace/actions-cloud/robocorp/temp');failed=list(root.glob('563d*'));assert len(failed)==1 and failed[0].is_dir()
canonical=Path('/workspace/engineering/capacity-recovery-independent-review/canonical-completed-scratch-preservation-proposed.patch');assert sha(canonical)=='7d07065b5bb7742698919997c8c6621cc20d00494741eb5365251ffb09f2d208';paragraph=''.join(line[1:] for line in canonical.read_text().splitlines(keepends=True) if line.startswith('+') and not line.startswith('+++'));guide=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md');assert paragraph in guide.read_text();excerpt=D/'canonical-existing-capacity-paragraph.md';excerpt.write_text(paragraph)
d['prior_first6_archive_and_privateindex_exact_hashes_preserved']={'first_summary':binding(firstpath),'first_private_inventory':first['complete_private_inventory'],'all6_archive_digest_and_size_match_prior_summary':True,'previous_independent_receipt':binding(firstreview)}
d['prior_batch2_archive_and_privateindex_exact_hashes_preserved']={'second_summary':binding(secondpath),'second_private_inventory':second['private_inventory_binding'],'both2_archive_digest_and_size_match_prior_summary':True,'previous_independent_receipt':binding(secondreview)}
d['algorithm_parity']={'batch3_tool':binding(two),'first_tool':binding(one),'AST_exact_except_names_and_private_output_dirs':True,'scope':'No recovery script executed by independent reviewer; exact namespace selection and existing outputdirs only'}
d['immutable_reference_spotchecks']={'V5runner':binding(runner),'failed563d_namespace_exists':True,'scope':'Only immutable frozen V5runner bytes and failed563d directory existence checked; no content hash or unchanged proof claimed for actively written305/282 or failed namespace without prior content baseline'}
d['original_archive_review_preserved']=binding(initial)
d['canonical_documentation']={'file':'docs/skills/repository-operations.md','accepted_original_exact_delta':binding(canonical),'current_root_integrated_exact_excerpt':binding(excerpt),'disposition':'Existing7d070 capacity paragraph already adapted verbatim to owning guide and sufficient; no new delta or duplicated instruction needed for algorithm-equivalent third batch','evidence':'33175 unique archive members and all internal hardlink payloads verified; original6 archives/index still exact old hashes; batch3 algorithm AST unchanged except two exact names/outputdirs; original controls/gates never relabeled','stale_ambiguity':'Recorded archive content metadata is distinct from unrecorded inode/rootmetadata/ACL/xattrs/mtime and retroactive handle state; capacity recovery does not admit old ENOSPC gates','remaining_uncertainty':'Expanded originals deliberately removed; correctness bounded to retained inventory, current archives and recorded metadata. No retroactive fullhandle census, unrecorded metadata, originalfailed563d-content baseline or current sourcewriter hash claims. Source/native/private/release gates remain separate','upstream':'none'}
p=D/'independent-batch3-archive-preservation-review-v2.json';p.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(binding(p)))
