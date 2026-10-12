from pathlib import Path
import json,hashlib,time
O=Path('/workspace/engineering/capacity-recovery-batch13-independent-review');O.mkdir(mode=0o700,exist_ok=True);start=time.monotonic()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def exact(v):p=Path(v['path']);assert p.is_file() and p.stat().st_size==v['bytes'] and sha(p)==v['sha256'];return v
old=Path('/workspace/engineering/capacity-recovery-batch12-independent-review/independent-batch12-archive-preservation-review-v2.json');assert old.stat().st_size==17008 and sha(old)=='0eb075fdeede4d818bec4dfc7d05e8230d2eccddc9ec226d8d836288e37b83a0';x=json.loads(old.read_bytes());batches=x['prior27_archives_11privateindices_summaries_and_reviews_exact_original_hashes_preserved'];assert len(batches)==11
summaries=[];reviews=[];indices=[];archives=[]
for b in batches:
 summaries.append(exact(b['summary']));indices.append(exact(b['private_inventory']));reviews.append(exact(b['original_independent_review']));s=json.loads(Path(b['summary']['path']).read_bytes())
 for a in s['archives']:
  p=Path(a['archive']);assert p.stat().st_size==a['archive_bytes'] and sha(p)==a['archive_sha256'];archives.append({'archive_bytes':a['archive_bytes'],'archive_sha256':a['archive_sha256']})
assert len(archives)==27
last=Path('/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch12.json');s=json.loads(last.read_bytes());summaries.append(bind(last));indices.append(exact(s['private_inventory_binding']))
for a in s['archives']:
 p=Path(a['archive']);assert p.stat().st_size==a['archive_bytes'] and sha(p)==a['archive_sha256'];archives.append({'archive_bytes':a['archive_bytes'],'archive_sha256':a['archive_sha256']})
for name in ['independent-batch12-archive-preservation-review.json','independent-batch12-archive-preservation-review-v2.json','independent-batch12-archive-preservation-review-final.json','independent-safe-batch12-summary.json']:
 p=old.parent/name;reviews.append(bind(p))
assert len(archives)==29 and len(indices)==12
V5=exact(x['immutable_reference_spotchecks']['V5runner']);assert V5['sha256']=='09cdc6b19f5d3d9cc94fadca23373108868521e0378d33960146b1a8522e88ad';failed=Path('/workspace/actions-cloud/robocorp/temp/563d');matches=list(failed.parent.glob('563d*'));assert len(matches)==1 and matches[0].is_dir()
doc=x['canonical_documentation'];accepted=exact(doc['accepted_original_exact_delta']);assert accepted['sha256']=='7d07065b5bb7742698919997c8c6621cc20d00494741eb5365251ffb09f2d208'
result={'prior_authoritative_independent_v2':bind(old),'prior_archives29_exact_retained_original_hashes':archives,'prior_complete_private_indices12_exact_retained_original_hashes':indices,'prior_safe_summaries_exact_retained_hashes':summaries,'prior_review_binding_checks':reviews,'original_V5runner09cdc_exact':V5,'failed563d_namespace_current_exists_only':True,'failed_namespace_scope':'No content/member/state/hash inference;existence only','canonical_accepted_original_exact_delta':accepted,'canonical_prior_review_disposition':doc['disposition'],'prior29_archives_not_extracted_or_replayed':True,'check_seconds':round(time.monotonic()-start,3),'no_GC_restore_removals_source_gateway_actual_or_download':True,'upstream_disposition':'none'}
p=O/'independent-prior29-archives12-indices-and-original-reference-proof.json';p.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');p.chmod(0o600);print(json.dumps({'proof':bind(p),'prior_archives':29,'prior_indices':12,'safe_summaries':len(summaries),'reviews_rehashed':len(reviews),'check_seconds':result['check_seconds']}))
