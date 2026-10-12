from pathlib import Path
import hashlib,json,stat
D=Path('/workspace/engineering/capacity-recovery-batch10-independent-review')
def binding(p):
 p=Path(p);h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return {'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}
p=D/'independent-batch10-archive-preservation-review-v2.json';j=json.loads(p.read_text());owner=Path('/workspace/engineering/existing-workspace-scratch-capacity-recovery-batch10.json');assert binding(owner)=={'path':str(owner),'bytes':2243,'sha256':'2a486f9c002844a7ded6159ce7c552badba60afdd095407ea5eb04b57dba4ac9'}
o=json.loads(owner.read_text());assert sum(a['members_verified'] for a in j['two_archives'])==o['recorded_members']==29707
for a,b in zip(j['two_archives'],o['archives']):
 assert a['archive']=={'path':b['archive'],'bytes':b['archive_bytes'],'sha256':b['archive_sha256']} and a['members_verified']==b['verified_members'] and b['expanded_removed'] and b['archive_verified_before_original_removal']
prior=j['prior23_archives_9privateindices_summaries_and_reviews_exact_original_hashes_preserved'];assert len(prior)==9 and sum(p['archive_count'] for p in prior)==23
for r in prior:
 assert stat.S_IMODE(Path(r['private_inventory']['path']).stat().st_mode)==0o600
 old=json.loads(Path(r['summary']['path']).read_text());entries=old.get('archives',old.get('recovery_records'))
 for e in entries:assert stat.S_IMODE(Path(e['archive']).stat().st_mode)==0o600 and not Path(e['archive']).is_symlink()
# New named final successor retains announced drafts and records the inspection exception honestly.
j['owner_announced_root_summary_unchanged']=binding(owner)
j['same_algorithm_batch9_AST_reference']=binding('/tmp/actions-capacity-recovery-batch9.py')
j['canonical_documentation']['disposition']='Existing exact7d070 paragraph verified verbatim in owning canonical checkpoint; no new correctness behavior or cosmetic duplication for same unchanged algorithm.'
j['inspection_output_exception']='A schema inspection accidentally forwarded the private inventory key list (member paths); no payload bytes or config values were printed. Output was oversized/truncated. Subsequent inspection fixed to allowlisted counts/type keys; safe receipts contain no member names or payload.'
j['limitations']=[x for x in j['limitations'] if not x.startswith('No private archive contents/member names')]+['No member payload/configuration was admitted to Git. The member-name forwarding inspection exception is retained candidly; safe summary and final receipt exclude individual member names.']
j['safe_counts']={'new_archives':2,'new_recorded_members':29707,'new_resolved_internal_hardlink_headers':6,'new_logical_regular_file_bytes':sum(a['logical_regular_file_bytes_verified'] for a in j['two_archives']),'prior_archives_exact_retained_hashes':23,'prior_complete_private_indices_exact_retained_hashes':9,'prior_safe_summaries_and_independent_reviews_rehashed':9,'total_retained_archives_ten_batches':25}
j['review_readonly_disposition']='Read-only original archived byte verification and fixed owned receipt writes only. No recovery script execution, deletion, source changes, installer/native/provider/browser gate or prior-root-summary rewrite.'
j['review_evidence_bindings']={q.name:binding(q) for q in sorted(D.iterdir()) if q.is_file() and q.name not in ('independent-batch10-archive-preservation-review-v3.json','freeze-safe-final-review.log')}
j['Upstream_disposition']='none'
for q in D.iterdir():
 if q.is_file():q.chmod(0o600)
out=D/'independent-batch10-archive-preservation-review-v3.json';out.write_text(json.dumps(j,indent=2)+'\n');out.chmod(0o600);print(json.dumps({'receipt':binding(out),'counts':j['safe_counts'],'verdict':j['verdict']}))
