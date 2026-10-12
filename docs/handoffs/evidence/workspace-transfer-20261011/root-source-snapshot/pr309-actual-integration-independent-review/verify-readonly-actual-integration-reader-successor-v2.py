import datetime
import hashlib
import json
from pathlib import Path
import subprocess

R=Path('/workspace/engineering/pr309')
B=Path('/workspace/engineering')
O=B/'pr309-actual-integration-independent-review'
ACTUAL='a0d258a16095b95b1bf9000cb1201cddfaff4779'
SOURCE='83123ff42c21587e3eb944e20af89f1a9e9ff0ea'
BASE='6181b044c75de35386f1ae30e71725398b6a7feb'
TESTED='012cd8fd70cecbf53e236ca35ede0ffcb35297b5'
TREE='1181b35b11e4904405ca1a9a3a398e6c1c3abfd0'
def sha(body):return hashlib.sha256(body).hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
verified={}
def bind(row):
    p=Path(row['path']);body=p.read_bytes();assert len(body)==row['bytes'] and sha(body)==row['sha256'],str(p)
    verified[str(p)]=row;return row
def refs(value):
    if isinstance(value,dict):
        if {'path','bytes','sha256'}<=value.keys() and str(value['path']).startswith('/'):bind(value)
        for v in value.values():refs(v)
    elif isinstance(value,list):
        for v in value:refs(v)
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*a])
owner=bind({'path':str(B/'pr309-actual-integration.json'),'bytes':1353,'sha256':'cc14479336e95bc5cafe2795bc796a7d1e3b5f6dd70d4bc66096ad5cd7850046'})
d=load(owner['path']);refs(d)
authref=bind({'path':str(B/'pr309-current618-root-normal-merge-authorization.json'),'bytes':4927,'sha256':'11216299b207fd3c7c7473959745f07aa3b1963511e9596de1822eeadfe8ec7a'})
auth=load(authref['path']);refs(auth)
finalref=auth['independent_final_scoped_GO'];final=load(finalref['path']);refs(final)
assert finalref['sha256']==d['final_independent_scoped_GO_sha256']=='8d834b13a663e6768090963ef8a62860155b31b2c9b1aebbf5b11b5c3f70ab7e'
source=load(final['source_owner']['path']);refs(source)
indsource=load(final['independent_source_GO']['path']);refs(indsource)
metadata=load(final['complete_metadata_owner']['path']);refs(metadata)
windows=load(final['owner']['path']);refs(windows)
assert final['source_owner']['sha256']=='e00bf1644c432c14da0b71fe79ffe58373cc1df3325163127cca780bd2120d01'
assert final['independent_source_GO']['sha256']=='1f0537ee03da972e181e39868ad47a28feac48aba8dee08b5448e4211feed005'
assert d['actual']==ACTUAL and d['source']==SOURCE and d['tested_synthetic']==TESTED and d['tree']==TREE
assert d['ordered_parents']==[BASE,SOURCE] and git('show','-s','--format=%P',ACTUAL).decode().strip().split()==[BASE,SOURCE]
for commit in [ACTUAL,SOURCE]:assert git('rev-parse',commit+'^{tree}').decode().strip()==TREE
tested_commit_path=B/'pr300-pr309-current618-full-live-successor-02/pr309/merge-commit.raw.private.json'
tested_tree_path=B/'pr300-pr309-current618-full-live-successor-02/pr309/complete-tree.raw.private.json'
assert str(tested_commit_path) in verified and str(tested_tree_path) in verified
tested_commit=load(tested_commit_path);tested_tree=load(tested_tree_path)
assert tested_commit['sha']==TESTED and tested_commit['commit']['tree']['sha']==TREE
assert [row['sha'] for row in tested_commit['parents']]==[BASE,SOURCE]
assert tested_tree['sha']==TREE and tested_tree['truncated'] is False
assert windows['original_actual_checkout']['local_Git_object_absent_no_fetch_needed_same_SHA_API_complete_tree_authenticated'] is True
original_checkout_line=Path(windows['original_decoded_log']['path']).read_text().splitlines()[windows['original_actual_checkout']['original_log_checkout_line']-1]
assert TESTED in original_checkout_line

actual_entries=git('ls-tree','-rz',ACTUAL)
assert actual_entries==git('ls-tree','-rz',SOURCE)
api_rows=sorted((row['path'],row['mode'],row['sha']) for row in tested_tree['tree'] if row['type']=='blob')
git_rows=[]
for raw in actual_entries.split(b'\0'):
    if raw:
        header,path=raw.split(b'\t',1);mode,kind,blob=header.decode().split();git_rows.append((path.decode(),mode,blob))
assert sorted(git_rows)==api_rows and len(api_rows)==1421

assert sha(actual_entries)==d['typed_inventory_sha256']=='1ed74906c693217b500f2e3795298de283edd04dbc86f1db216fe2af861924fc'
rows=[entry for entry in actual_entries.split(b'\0') if entry];assert len(rows)==1421
assert source['head']==indsource['head']==final['source']==SOURCE
assert source['tree']==indsource['tree']==final['source_tree']==TREE
assert git('rev-parse','HEAD').decode().strip()==SOURCE and git('status','--porcelain')==b''
for entry in rows:
    header,path=entry.split(b'\t',1);mode,kind,blob=header.decode().split();assert kind=='blob'
    p=R/path.decode();assert p.read_bytes()==git('cat-file','blob',blob)
    assert bool(p.stat().st_mode&0o111)==(mode=='100755')
api=load(d['private_API_binding']['path'])
assert api['number']==309 and api['merged'] is True and api['state']=='closed' and api['draft'] is False
assert api['merge_commit_sha']==ACTUAL and api['merged_at']==d['merged_at']
assert api['head']['sha']==SOURCE and api['base']['sha']==BASE and api['base']['ref']=='integration/community-release-20261008'
assert auth['head']==SOURCE and auth['target']==BASE and auth['tested_checkout']==TESTED and auth['tree']==TREE
assert auth['normal_API_policy_enforcement_required'] is True and auth['force_or_waiver'] is False
assert auth['mergeable']=='MERGEABLE' and auth['mergeStateStatus']=='CLEAN'
assert auth['complete_current_reviews_threads_closures']==[0,0,0]
checks=auth['complete_current_checks'];assert len(checks)==19
assert all(row['status']=='COMPLETED' and row['conclusion']=='SUCCESS' for row in checks)
ci=final['complete_current_CI'];assert ci['declared_PR_workflows']==6 and ci['declared_PR_jobs']==19 and ci['auxiliary_PUSH_jobs']==0
assert ci['materialized_checks']==ci['materialized_jobs']==len(ci['jobs'])==19 and ci['all_completed_success'] is True
assert all(row['conclusion']=='success' for row in ci['jobs'])
assert len({row['id'] for row in ci['jobs']})==19 and ci['late_publisher_id']==114444748187
assert any(row['id']==114444748187 and row['name']=='publish (3.12)' for row in ci['jobs'])
assert ci['registry_publication_qualified'] is False
named=O/'single-named-integration-ref-readback.txt';body=named.read_bytes()
assert body.decode().strip()==ACTUAL+'\trefs/heads/integration/community-release-20261008'
named_ref={'path':str(named),'bytes':len(body),'sha256':sha(body)};bind(named_ref)
doc=final['Documentation_improvement'];refs(doc)
application=load(doc['Exact_root_application']['path']);refs(application)
guide=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text()
assert 'Classify a merge against the PR\'s named target.' in guide
assert 'Record the target branch, merge commit and tree separately' in guide
proof={'schema':'pr309-actual-normal-integration-independent-readback/v1',
 'status':'GO_ACTUAL_NORMAL309_INTEGRATION_ONLY_NO_WHOLE_ISSUE_RELEASE_ADMISSION',
 'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'root_actual_owner':owner,'root_normal_authorization':authref,'final_independent_scoped_GO':finalref,
 'accepted_source_owner':final['source_owner'],'accepted_independent_source_GO':final['independent_source_GO'],
 'source':{'actual':ACTUAL,'tree':TREE,'ordered_actual_parents':[BASE,SOURCE],'accepted_source':SOURCE,'tested_synthetic':TESTED,'ordered_tested_parents':[BASE,SOURCE]},
 'verified':{'all1421_typed_mode_type_blob_path_entries_equal_actual_source_tested':True,
  'typed_inventory_encoding':'git ls-tree -rz exact NUL-delimited mode/type/blob/path output',
  'typed_inventory_sha256':sha(actual_entries),'source_worktree1421_FS_Git_body_execbits_clean':True,
  'authenticated_original_API_merged_true_closed_nondraft_exact_actual_head_base':True,
  'single_named_branch_readback_exact_actual':True,'all_bound_receipt_files_rehashed':len(verified),
  'recorded_complete_current19SUCCESS_six_PRflows_no_auxpush_latepublisher_included':True,
  'normal_ready_expected_head_authority_force_or_waiver_false':True,'no_issue_closures':True},
 'authenticated_API':d['private_API_binding'],'single_named_ref':named_ref,
 'original_tested_checkout_proof':'Original log checkout line113 and retained authenticated commit/complete recursive API1421 tree; historical tested012cd8 commit object absent locally, not fetched. Actual/source verified from commonGit.',
 'CI_scope':'Retained exact831/618 complete19 success and original tested012cd8 source identity only; no new CI sampling or later-source gate carry. Publisher status is not registry publication qualification.',
 'remaining_HOLDs':['Whole issues152/196 and retained graph closures','Native/private/provider/Workspace/ChatGPT/full backend/public identity/platform acceptance','Tag/publication/Runtime release/OAuth authority','Dependent branches require ordinary exact-target refresh plus fresh source/CI gates; historical tuples stay original'],
 'documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md',
  'Exact_accepted_reuse':doc,'Durable_learning':'Bind normal integration to ordered actual parents and complete typed tree; keep original runner checkout identity distinct from API head and later merge refs, while preserving event-specific complete late-job inventory.',
  'Evidence':'Authenticated original merged API, single current named branch and commonGit actual/source/tested1421 typed equality; normal authority and final19-job admission receipts rehashed.',
  'Stale_or_ambiguous_guidance_removed':'No new text/duplicate diary; accepted checkout/tree/event/late-publisher lessons reused. Merge is scoped integration, not issue closure or registry publication.',
  'Remaining_uncertainty':'Broad issues/native/private/provider/release remain unqualified; this review performs no new CI or actual acceptance.'},
 'not_performed':['CI repoll/log or ZIP acquisition/download','Tests/gateway/installer/native/provider/browser/consumer','Source/index/ref mutations or new push/PR/merge/issue closure'],
 'upstream_disposition':'none'}
dest=O/'OWNERFINAL-independent-actual309-normal-integration-readback.json';assert not dest.exists()
dest.write_text(json.dumps(proof,indent=2)+'\n');dest.chmod(0o444)
print(json.dumps({'path':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest.read_bytes()),'status':proof['status']}))
