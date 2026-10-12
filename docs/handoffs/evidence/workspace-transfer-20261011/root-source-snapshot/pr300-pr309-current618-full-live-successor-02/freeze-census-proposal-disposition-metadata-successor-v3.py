from pathlib import Path
import hashlib,json
B=Path('/workspace/engineering/pr300-pr309-current618-full-live-successor-02')
def bind(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
p=B/'OWNERFINAL-one-current300-309-complete-CI-census.json';assert bind(p)['sha256']=='4196767b137dc9f6d334cabda3afbccbd61d8d2c872b33464021755754256b8b';d=json.loads(p.read_text());old=d['documentation_improvement'];doc=dict(old)
for k,v in list(doc.items()):
 if isinstance(v,str):doc[k]=v.replace('exact accepted original-checkout50ad proposal reused pending root integration','exact owner-proposed original-checkout50ad source-backed delta pending independent review and root integration').replace('exact accepted50ad laterref distinction','exact owner-proposed50ad laterref distinction')
items=[]
for row in old['Exact_reused_deltas']:
 if row['exact_accepted_delta']['sha256'].startswith('50ad'):
  items.append({'exact_owner_proposed_delta':row['exact_accepted_delta'],'verbatim_present_in_current_root_guide':False,'disposition':'Owner-proposed source-backed50ad exactbytes only; independent review and root application pending. Currentguide has general actualcheckout/orderedparents lesson, not this specific laterref distinction. No claim alreadyintegrated or independentlyadmitted.'})
 else:items.append(row)
doc['Exact_reused_deltas']=items;d['documentation_improvement']=doc;d['original_owner_census_before_proposal_disposition_correction']=bind(p);d['original_census_constructor']=d['immutable_constructor'];d['immutable_constructor']=bind(Path(__file__));d['metadata_only_correction']='Root clarified50ad ownerproposal not yet independentlyadmitted/rootintegrated. Correct only documentation disposition; all original current API queries/source/CI/jobs/status/policy/reviews/closures remain unchanged, no additional reads or rerun.'
p=B/'OWNERFINAL-one-current300-309-complete-CI-census-metadata-successor-v3.json';assert not p.exists();p.write_text(json.dumps(d,indent=2)+'\n');p.chmod(0o600);print(json.dumps({'OWNER_FINAL_CENSUS':bind(p),'constructor':bind(Path(__file__)),'source_API_CI_receipts_unchanged':True,'original4196_preserved':True,'no_API_repetition':True,'50ad_proposed_only_not_admitted_integrated':True}))
