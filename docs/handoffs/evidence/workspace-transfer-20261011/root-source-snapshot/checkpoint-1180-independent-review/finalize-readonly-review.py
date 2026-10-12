import collections
import datetime
import hashlib
import json
import pathlib
import re
import subprocess

R=pathlib.Path('/workspace/engineering/checkpoint-1180-independent-review')
W=pathlib.Path('/workspace/engineering/campaign-checkpoint')
PFX='docs/program/evidence/wave11/current-engineering-20261011/'
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):
    p=pathlib.Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def write(name,obj):
    p=R/name
    with p.open('x') as f:json.dump(obj,f,indent=2,sort_keys=True);f.write('\n')
    p.chmod(0o444);return ref(p)
def git(*a):return subprocess.check_output(['git','--no-optional-locks',*a],cwd=W)
manifest=json.loads((W/(PFX+'manifest.json')).read_bytes())
parent=json.loads(git('show','HEAD:'+PFX+'manifest.json'))
new={k:v for k,v in manifest.items() if k not in parent}
readback=json.loads((R/'new536-nested-original-binding-readback.json').read_bytes())
priorpath=pathlib.Path('/workspace/engineering/checkpoint-644-independent-review/verified-stage-and-historical-binding-proof.json')
prior=json.loads(priorpath.read_bytes())
priorclass={(x['path'],x['expected_sha256']):x for x in prior['nested_noncurrent_classified']}
classified=[]
for x in readback['results']:
    if x['status']=='EXACT':continue
    key=(x['path'],x['expected_sha256'])
    y={k:x[k] for k in ('path','expected_bytes','expected_sha256','status','payloads')}
    if key in priorclass:
        y['disposition']='inherited_prior644_reviewed_historical_scope_unchanged'
        y['prior_specific_disposition']=priorclass[key].get('disposition')
        if x['expected_sha256']=='6c5367796b853a77cca55f0256d71ba0d42deb1e9abade55cff063a37e0622f7':
            recovery=pathlib.Path('/workspace/engineering/pr306-actual776-refresh/original-constructor-content-recovery/freeze-source-receipt-initial-exact-recovered.py')
            assert sha(recovery.read_bytes())==x['expected_sha256'];y['retained_distinct_exact_recovery']=ref(recovery)
    elif x['path'].startswith('/workspace/engineering/pr300/'):
        relative=x['path'].split('/workspace/engineering/pr300/',1)[1]
        body=subprocess.check_output(['git','--no-optional-locks','show','7840057a8b055576d11d339d8c0fbb738927a491:'+relative],cwd='/workspace/engineering/pr300')
        assert sha(body)==x['expected_sha256'] and len(body)==x['expected_bytes']
        y['disposition']='historical_issue86_proposal784_source_Git_blob_exact_successor_worktree_is_separate_not_old_actual'
        y['immutable_source']='7840057a8b055576d11d339d8c0fbb738927a491'
    elif x['path'].endswith('/input-and-source-admission.json'):
        q=pathlib.Path('/workspace/engineering/pr221-current618-linux-consumer-preflight/input-manifest-before-dist-info-wording-correction.json')
        assert sha(q.read_bytes())==x['expected_sha256'];y['disposition']='construction_prewording_alias_distinct_retained_original_exact_not_final_execution_pin';y['retained_original']=ref(q)
    elif x['path'].endswith('/installed-consumer-runner-v3.py'):
        if x['expected_sha256']=='e2be54c502e730030e94f3d444742a96871146bfcef7d479180416b77595908c':
            q=pathlib.Path('/workspace/engineering/pr221-current618-linux-consumer-preflight/runner-before-dist-info-wording-correction.py');assert sha(q.read_bytes())==x['expected_sha256'];y['retained_original']=ref(q)
            y['disposition']='construction_prewording_alias_distinct_retained_original_exact_not_final_execution_pin'
        else:
            assert x['expected_sha256']=='ade8a64f77069af3327140eee6732cba3cc43cb46547f6fe40849773a5fd150e'
            y['disposition']='pre_Ruff_constructor_observation_not_frozen_execution_identity_initial_bytes_not_recovered'
        y['explicit_preserved_disposition']=ref('/workspace/engineering/pr221-current618-linux-consumer-preflight/constructor-and-prewording-receipt-disposition.json')
    elif x['expected_bytes']==0 and x['expected_sha256']==sha(b'') and x['path'].endswith('.log'):
        y['disposition']='zero_byte_construction_logger_observation_subsequently_appended_not_current_immutable_terminal_log_no_reconstruction'
    else:raise AssertionError((x['path'],x['expected_sha256']))
    classified.append(y)
assert len(classified)==222
classification=write('precise-historical-nested-alias-and-measurement-dispositions.json',{'current_nested_exact':5370,'historical_removed_installed_member_measurements':196,'noncurrent_aliases':26,'unclassified_aliases':0,'prior644_review':ref(priorpath),'records':classified,'unrecovered22524B_manifest_alias':'a48328d0c9b3e4758dbea148663dabe2ab07a4812f0fcdf0ccb476d01de95b12 remains historical unknown original; no reconstructed bytes or predecessor construction GO','scope':'All1180 selected originals themselves are exact. Nested mutable source paths, construction logger observations and cleaned installed files retain the stated historical limits, separately from later exact actual bindings.'})
privacy=[];urls=collections.Counter();patchtargets=collections.Counter();content_fields=[]
token=re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|[?&](?:X-Amz-Signature|sig)=|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
def scan(o,n,loc=''):
    if isinstance(o,dict):
        for k,v in o.items():
            if k.lower() in {'stdout','stderr','raw','raw_body','raw_response','api_key','access_token','secret','password','content','body'} and isinstance(v,str) and v:
                assert n=='pr300-issue86-next-proposal-OWNERFINAL-current784-issue86-bounded-assembled-transport-next-proposal.json' and loc+'/'+k=='/expected_semantic_cells/8/body' and v=='Output storage unavailable'
                content_fields.append({'payload':n,'field':loc+'/'+k,'classification':'public_fixed_error_literal_expected_contract_not_raw_response'})
            scan(v,n,loc+'/'+str(k))
    elif isinstance(o,list):
        for i,v in enumerate(o):scan(v,n,loc+'/'+str(i))
for n,record in new.items():
    b=(W/(PFX+n)).read_bytes();assert len(b)==record['bytes'] and sha(b)==record['sha256']
    assert pathlib.Path(record['source']).read_bytes()==b
    text=b.decode();assert not token.search(text)
    for host in re.findall(r'https?://([^/\s\"<>]+)',text):urls[host]+=1
    if n.endswith('.json'):scan(json.loads(text),n)
    else:
        for target in re.findall(r'^\+\+\+ (.+)$',text,re.M):patchtargets[target]+=1
assert set(urls)=={'github.com','files.pythonhosted.org','docs.github.com'}
privacyproof=write('new536-safe-content-and-declared-scope-proof.json',{'new536_formats':{'json':488,'patch':48},'direct_standalone_raw_logs_ZIPs_source_modules_artifact_payloads':0,'credential_signed_URL_private_key_pattern_hits':[],'URL_hosts':dict(urls),'nonempty_sensitive_raw_fields':content_fields,'patch_target_summary':dict(patchtargets),'patch_scope':'Canonical guidance and bounded public EOL/workflow/test deltas; two retained consumer parameter-only delta patches reference immutable paths/pins and preserve previously accepted mechanisms, not private implementation payloads. Older644 selected content remains exact and keeps prior admitted privacy scope.','README':'Appends accepted actuala0d/source83119checks/original012cd8 API identity; keeps active312/300 future waves excluded, old failed Windows gates, partial consumers/OAuth/private/full graph holds and unrecovered historical alias; no inaccurate acceptance upgrade found.','upstream_disposition':'none'})
owner=json.loads(pathlib.Path('/workspace/engineering/checkpoint-1180-staged-identity.json').read_bytes())
assert sha(git('ls-files','-s','-z'))==owner['index_sha256']
assert sha(git('diff','--cached','--name-status','-z'))==owner['staged_names_sha256']
assert not git('diff','--name-only')
proofs=[ref(R/n) for n in ['all1180-original-copy-typed-staged-byte-proof-v3.json','new536-nested-original-binding-readback.json','canonical74-and-README-scope-proof.json','exact-staged-canonical74-delta.patch','verify-staged-readonly.py','verify-staged-readonly-reader-successor-v2.py','verify-staged-readonly-reader-successor-v3.py','initial-reader-staged-name-encoding-diagnostic.json','reader-nullable-size-sort-diagnostic.json']]+[classification,privacyproof,ref(__file__)]
result={'schema':'independent_readonly_ownerfinal_staged_checkpoint_review','status':'GO_STAGED_1180_NORMAL_EXISTING_HANDOFF_COMMIT_PUSH_ONLY_NO_ENGINEERING_GATE_WAIVER','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owner':ref('/workspace/engineering/checkpoint-1180-staged-identity.json'),'subject':{'worktree':str(W),'branch':owner['branch'],'base':owner['base'],'frozen_staged_tree':owner['tree'],'semantic_index_sha256':owner['index_sha256'],'semantic_index_encoding':'SHA256(git --no-optional-locks ls-files -s -z output)','staged_names_sha256':owner['staged_names_sha256'],'staged_names_encoding':'SHA256(git --no-optional-locks diff --cached --name-status -z output)','staged_paths':539},'admission':{'all1180_staged_blobs_originals_copies_SHA_sizes_typed_modes':True,'prior644_records_blobs_modes_unchanged':True,'new536_bytes':27405588,'new536_frozen_plan_exact':True,'all_other_parent_entries_unchanged':True,'staged_tree_object_entries_exact':True,'unstaged_clean':True,'no_unclassified_nested_aliases':True,'nested_current_exact':5370,'historical_installed_members_absent_after_owned_cleanup':196,'historical_noncurrent_aliases':26,'privacy_safe_selection':True,'canonical_exact_additions':74,'canonical_removed_lines':0},'historical_limits':{'unrecovered22524B_alias':'Original22524/a483 remains unrecovered; no new reconstruction or predecessor admission.','initial_pre_Ruff_renderer':'One19364/ade8 constructor identity observation is not a frozen execution pin; original bytes not recovered. Named prewording originals and final v3/v4/v5 wrappers remain distinct and exact.','zero_byte_log_observations':'Three binding occurrences across two construction logger files subsequently appended; not immutable terminal log originals.','historical_issue86_source':'Two784 Git blobs independently exact; current authorized source writer changes do not relabel historical proposal as current actual proof.','removed_installed_tree':'196 inherited installed-file hashes remain measured historical receipts, not fresh installed tree reread.','inherited_policy_index':'Historical physical-index HOLD and named semantic644 successor remain preserved; current comparison uses entry serialization only.'},'documentation_improvement':{'Canonicalfilechanged/proposed':'docs/skills/repository-operations.md staged root-owned exact74 added lines,0removals','Durablelearning':'Nine verified blocks: ignored RCC fixture assets, bounded xdist worker environment, early captured cleanup versus wrapper reap, original checkout versus later merge ref, PR versus push changed-file filters, concatenated verbose SKIPPED census, tracked/generated embedded checkout bytes, independently anchored archive provenance labels, and selector directory exclusivity.','Evidence':ref(R/'canonical74-and-README-scope-proof.json'),'Exactdelta':ref(R/'exact-staged-canonical74-delta.patch'),'Staleguidanceremoved':'No prior guidance removed; exact accepted clauses inserted at source-appropriate existing anchors, preserving old canonical blocks.','Remaininguncertainty':'Historical checkout/hosted cleanup causality, semantic frontend equivalence, private/native/all-platform/release scope remain explicitly unqualified; documentation does not change acceptance gates.'},'allowed_next':'Root normal commit/push on the existing handoff branch after this GO; independent committed/remote readback remains separate.','remaining_holds':['No issue closure or full54-contract graph closure','No current-head CI carry to later source','No native or private acceptance upgrade','No OAuth/sourceauthority/platform/registry/tag/Runtime release admission','No unimplemented cleanup improvement or hosted timeout cause established'],'no_source_index_git_ref_collector_gate_actual_download_mutation':True,'proof_bindings':proofs,'upstream_disposition':'none'}
final=write('OWNERFINAL-independent-staged1180-checkpoint-review.json',result)
print(json.dumps(final,sort_keys=True))
