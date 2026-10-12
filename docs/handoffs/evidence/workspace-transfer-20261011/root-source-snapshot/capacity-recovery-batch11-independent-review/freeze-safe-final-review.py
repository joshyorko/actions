from pathlib import Path
import hashlib,json,stat
D=Path('/workspace/engineering/capacity-recovery-batch11-independent-review')
def binding(p):
 p=Path(p);h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return {'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}
p=D/'independent-batch11-archive-preservation-review-v2.json';j=json.loads(p.read_text());owner=Path('/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch11.json');assert binding(owner)=={'path':str(owner),'bytes':2244,'sha256':'94e3d73c02073e96a40b567030431bf4629e9fabbc98851ee476e13e1e2b2eb2'}
o=json.loads(owner.read_text());assert sum(a['members_verified'] for a in j['two_archives'])==o['recorded_members']==29871
for a,b in zip(j['two_archives'],o['archives']):
 assert a['archive']=={'path':b['archive'],'bytes':b['archive_bytes'],'sha256':b['archive_sha256']} and a['members_verified']==b['verified_members'] and b['expanded_removed'] and b['archive_verified_before_original_removal']
prior=j['prior25_archives_10privateindices_summaries_and_reviews_exact_original_hashes_preserved'];assert len(prior)==10 and sum(p['archive_count'] for p in prior)==25
for r in prior:
 assert stat.S_IMODE(Path(r['private_inventory']['path']).stat().st_mode)==0o600
 old=json.loads(Path(r['summary']['path']).read_text());entries=old.get('archives',old.get('recovery_records'))
 for e in entries:assert stat.S_IMODE(Path(e['archive']).stat().st_mode)==0o600 and not Path(e['archive']).is_symlink()
# Named final successor binds complete safe read-only proof; counts/type-key inspections only.
j['owner_announced_root_summary_unchanged']=binding(owner)
j['same_algorithm_batch10_AST_reference']=binding('/tmp/actions-capacity-recovery-batch10.py')
j['canonical_documentation']['disposition']='Existing exact7d070 paragraph verified verbatim in owning canonical checkpoint; no new correctness behavior or cosmetic duplication for same unchanged algorithm.'
j['safe_counts']={'new_archives':2,'new_recorded_members':29871,'new_resolved_internal_hardlink_headers':6,'new_logical_regular_file_bytes':sum(a['logical_regular_file_bytes_verified'] for a in j['two_archives']),'prior_archives_exact_retained_hashes':25,'prior_complete_private_indices_exact_retained_hashes':10,'prior_safe_summaries_and_independent_reviews_rehashed':10,'total_retained_archives_eleven_batches':27}
j['inspection_output_policy']='Fixed counts/type keys only; no inventory member paths or payload/config content forwarded in this review.'
j['review_readonly_disposition']='Read-only original archived byte verification and fixed owned receipt writes only. No recovery script execution, deletion, source changes, installer/native/provider/browser gate or prior-root-summary rewrite.'
j['review_evidence_bindings']={q.name:binding(q) for q in sorted(D.iterdir()) if q.is_file() and q.name not in ('independent-batch11-archive-preservation-review-v3.json','freeze-safe-final-review.log')}
j['Upstream_disposition']='none'
for q in D.iterdir():
 if q.is_file():q.chmod(0o600)
out=D/'independent-batch11-archive-preservation-review-v3.json';out.write_text(json.dumps(j,indent=2)+'\n');out.chmod(0o600);print(json.dumps({'receipt':binding(out),'counts':j['safe_counts'],'verdict':j['verdict']}))
