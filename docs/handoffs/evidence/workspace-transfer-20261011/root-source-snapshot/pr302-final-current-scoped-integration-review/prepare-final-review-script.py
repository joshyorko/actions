from pathlib import Path
old=Path('/workspace/engineering/pr302-full26-current-hosted-admission/freeze-full26-current-admission.py').read_text()
s=old.replace("'/workspace/engineering/pr302-full26-current-hosted-admission'","'/workspace/engineering/pr302-final-current-scoped-integration-review'")
s=s.replace("r/'original-current-API-metadata-private.json'","r/'original-terminal-API-metadata-private.json'")
s=s.replace("assert publisher['name']=='publish (3.12)' and publisher['status']=='queued'","assert publisher['name']=='publish (3.12)' and publisher['status']=='completed' and publisher['conclusion']=='success'\nassert all(x['status']=='completed' and x['conclusion']=='success' for x in jobs)\nassert all(x['status']=='completed' and x['conclusion']=='success' for x in runs['workflow_runs'])")
s=s.replace("'HOLD_FINAL_SCOPED_INTEGRATION_LATE_PUBLISHER_QUEUED'","'GO_FINAL_SCOPED_NORMAL_INTEGRATION_EXACT_774_A346_TUPLE_ONLY'")
s=s.replace("'Pending PR-canary artifact validation is not authorized publication; tag/credentials/release-source conditions stay unchanged.'","'Terminal PR-canary artifact validation succeeded; it is not authorized publication. Tag/credentials/release-source conditions stay unchanged.'")
s=s.replace("'Earlier25registered/23SUCCESS/2pending cannot substitute for current26; current25SUCCESS leaves dependentpublisher pending.'","'Earlier25registered/23SUCCESS/2pending and later26registered25SUCCESS/publisherqueued are historical. Current26SUCCESS includes terminalpublisher.'")
s=s.replace("'Natural terminal completion of publish(3.12) job114414257399 then one bounded exacttuple26checks/26jobs/10flows/status/review/threads/policy reconciliation. No busy polling/manual rerun. No final integrationGO now.'","'Root may mark current draft ready separately and perform expected-head normal integration only while namedtarget774/headA346 and testedtreeA1c4 remain exact; preserve ordered ordinarymerge/tree validation. If target advances first, refresh and requalify the changed union. This source integrationGO does not authorize artifact release/publication.'")
s=s.replace("'Publisher terminalvalidation pending; OAuth authority/content, release/platform/coldregistry/native/privatefull134 gates open.'","'Publisher artifactvalidation terminalSUCCESS; OAuth authority/content, release/platform/coldregistry/native/privatefull134 gates remain open.'")
s=s.replace("p=r/'safe-full26-current-hosted-admission-HOLD.json';", "p=r/'safe-final-current-scoped-integration-GO.json';")
# Use the accepted integrated root adaptation, preserving original external proposal and all old HOLD receipts.
anchor="p=r/'safe-final-current-scoped-integration-GO.json';"
extra='''
# Original publisher step terminal semantics are source-bound; these skips are expected for pull_request.
assert flow['event']=='pull_request'
steps={x['name']:x for x in publisher['steps']}
expected_skips=['Verify merged tag provenance and version','Check Runtime publish credential','Publish verified artifacts']
assert [x['name'] for x in publisher['steps'] if x['conclusion']=='skipped']==expected_skips
for name in expected_skips:
 start=wf.index('name: '+name);segment=wf[start:start+250];assert "if: github.event_name == 'push'" in segment
for name in ['Verify exact Runtime artifact inventory','Verify Runtime artifacts','Canary local Runtime verifier','Upload artifact: action_server/dist/*']:
 assert steps[name]['status']=='completed' and steps[name]['conclusion']=='success'
receipt['late_publisher']['started_at']=publisher['started_at'];receipt['late_publisher']['completed_at']=publisher['completed_at']
receipt['late_publisher']['artifact_validation_steps_success']=['Verify exact Runtime artifact inventory','Verify Runtime artifacts','Canary local Runtime verifier','Upload artifact: action_server/dist/*']
receipt['late_publisher']['expected_PR_event_skipped_steps']={name:"Source guard push-only; current event pull_request. Retained skipped, not treated as successful release gate." for name in expected_skips}
receipt['normal_integration_scope']='Exact current source/control/target/tested-tree normal integration admission only. Draftready/merge mutation owned by root. No actual release/provider/native/private qualification.'
held=pathlib.Path('/workspace/engineering/pr302-full26-current-hosted-admission/safe-full26-current-hosted-admission-HOLD.json');assert sha(held.read_bytes())=='76d6379f4a85dba7e3d64689436542731533a08386d29fd73b16988acbaa32b4'
receipt['previous_full26_queued_HOLD_immutable']={'path':str(held),'sha256':sha(held.read_bytes())}
patch=pathlib.Path('/workspace/engineering/pr302-full26-current-hosted-admission/exact-dependent-job-registration-canonical-proposal.patch');assert sha(patch.read_bytes())=='d7a0a7b9452553bb609084acdf71bb7ace68f152b5bdd419a8817e151ddeb93b'
rootguide=pathlib.Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md');roottext=rootguide.read_text();begin=roottext.index('Derive the expected CI job set');end=roottext.index('Retain complete terminal logs',begin);paragraph=roottext[begin:end]
assert 'paginated endpoint covers currently registered jobs, not completion of the' in paragraph and 'queued publisher as pending.' in paragraph
snap=r/'accepted-root-canonical-adaptation.md';snap.write_text(paragraph);snap.chmod(0o444)
receipt['Documentation_improvement']['Canonical_file_changed_or_proposed']='docs/skills/repository-operations.md; accepted late-registration proposal d7a0a7b9 integrated by root in existing Derive CI paragraph. Current candidate canonical fef375 remains retained byte-exact.'
receipt['Documentation_improvement']['exact_proposed_patch']={'path':str(patch),'sha256':sha(patch.read_bytes()),'disposition':'ADAPTED_AND_INTEGRATED_BY_ROOT; actual owning paragraph independently inspected, no duplicate checkout edit.'}
receipt['Documentation_improvement']['accepted_root_adaptation_snapshot']={'path':str(snap),'sha256':sha(snap.read_bytes()),'root_guide_sha256_at_review':sha(rootguide.read_bytes())}
receipt['Documentation_improvement']['Evidence'].append('Final exact26SUCCESS/10flowSUCCESS includes114414257399; source-event guarded3release steps skipped, inventory/Twine/canary/upload4stepsSUCCESS.')
receipt['Documentation_improvement']['prior_fef375_disposition']='Accepted source/control/nine sample/testedmerge boundaries retained and supported by unchanged fresh54a. Late registration lesson separately accepted/adapted in root owningguide; no cosmetic duplicate.'
'''
s=s.replace(anchor,extra+'\n'+anchor)
# This lane does not create a second identical external proposal.
s=s.replace("pp.write_text(patch);pp.chmod(0o444)","pass")
s=s.replace("'size':pp.stat().st_size,'sha256':sha(pp.read_bytes())","'size':len(patch.encode()),'sha256':sha(patch.encode())")
s=s.replace("'canonical_proposal_sha256':sha(pp.read_bytes())","'canonical_proposal_sha256':receipt['Documentation_improvement']['exact_proposed_patch']['sha256']")
p=Path('/workspace/engineering/pr302-final-current-scoped-integration-review/verify-final-current-admission.py');p.write_text(s)
