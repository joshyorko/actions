import hashlib,json,re,stat
from pathlib import Path
R=Path('/dev/shm/actions-rcc-compatibility-originals-20261011');O=Path('/workspace/engineering/rcc-original-acquisition-independent-review');Q=Path('/workspace/engineering/rcc-compatibility-next-wave-readonly')
def bind(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return {'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}
owner=R/'OWNERFINAL-three-original-RCC-acquisition-data-qualification.json';d=json.loads(owner.read_bytes());proof=O/'safe-independent-original-acquisition-readback.json'
assert bind(owner)['sha256']=='0da97bfc63a5e47de1c900e8d37ec55261d8b7ef6f68069a74167afc344c72ad'
assert all(bind(Path(b['path']))==b for b in d['bindings'])
run=json.loads((Q/'rcc-native-38105340592-run.private.json').read_bytes());api=json.loads((Q/'rcc-native-38105340592-artifacts.private.json').read_bytes());arts={a['id']:a for a in api['artifacts']}
assert arts[11689755940]['name']=='native-runtime-binaries' and arts[11689851536]['name']=='linux-amd64-native-runtime-receipt'
for aid in [11689755940,11689851536]:
 transport=json.loads((R/f'artifact-{aid}-original-transport.private.json').read_bytes());ref=json.loads((R/f'artifact-{aid}-returned-reference.private.json').read_bytes());status=json.loads((R/f'artifact-{aid}-original-acquisition-status.json').read_bytes())
 assert transport['status']==200 and ref['status']=='fulfilled' and ref['value']['isError'] is False
 assert status['artifact_id']==aid and status['status']=='ORIGINAL_BYTES_EXACT_METADATA_DIGEST' and status['bytes']==arts[aid]['size_in_bytes'] and status['sha256']==arts[aid]['digest'][7:]
assert json.loads((R/'released5-transport-status.json').read_bytes())['exit_code']==0
workflow=(Q/'rcc727-.github_workflows_rcc.yaml.source-original.txt').read_text()
for s in ['SHA256SUMS','_validate_receipt_commit(data, os.environ["RCC_CANDIDATE_SHA"])','robot_evidence, "binarySha256"','rcc-linux64','go-version: "1.26.9"']:
 assert s in workflow,s
assert 'v18.19.6' in (Q/'rcc727-version.source-original.txt').read_text()
patch=R/'canonical-embedded-Go-modified-source-provenance-proposed.patch';pb=bind(patch);assert pb['sha256']=='68cd85b007239dd49463c90a9ba3d07a43f810a5c3a46ed2c608da47206a0a96'
add=[l[1:] for l in patch.read_text().splitlines() if l.startswith('+') and not l.startswith('+++')];assert len(add)==7
identity=Q/'canonical-qualified-RCC-executable-identity-proposed.patch';assert bind(identity)['sha256']=='324d8c0b671e0e908ac1b881d127b7c70cf69fdcba45b5f97363065e5710d233'
refs=[bind(owner),bind(proof),bind(O/'complete-private-independent-byte-and-archive-proof.json'),bind(O/'read-originals-independent.py'),bind(O/'read-originals-independent-v2.py'),pb,bind(identity)]
receipt={
 'schema':'independent-original-RCC-acquisition-data-review-v1',
 'status':'GO_ORIGINAL_ACQUISITION_AND_DATA_IDENTITY_ONLY_FOR_SEPARATELY_APPROVED_ISOLATED_TESTS',
 'owner_final':refs[0],
 'independent_data_proof':refs[1],
 'review_scope':{'original_acquisitions':3,'bound_references_prepost':76,'ZIPs':2,'admitted_members':12,'full_member_CRC_size_SHA256_modes_unique_safe_nonlink_headers':True,'all_four_SHA256SUMS_binary_matches':True,'selected_native_bytes_match_original_member':True,'no_extraction_reconstruction_or_binary_invocation':True,'original_bytes':71634898,'streamed_expanded_bytes':86540625,'conservative_accounting_bytes':180560325,'owned_limit_bytes':209715200},
 'subjects':{
  'released5':{'version_subject':'v18.19.5','original_asset_id':549249380,'bytes':22360226,'sha256':'1a617ad7c736fa67c605e20e5ebe3c7d54b02cd548f733e05c809cf49a48db1e','ELF':'linux amd64','Go':'go1.26.5','embedded_revision':'d1aec7d0bb897a81274423c7a6bb747233f9c263','embedded_vcs_modified':True,'clean_D1_source_equivalence':'UNKNOWN; exact released executable bytes can be separately approved for isolated qualification, not relabeled a reproducible clean-D1 build'},
  'candidate727':{'version_subject':'v18.19.6','source':'727c1ff8b679cdbbe12836e53c87734a1edb0071','tree':'cfae5c5ee9df0e5031e8e9ae37040b5c98ac6152','ordered_parents':['07db6221a3540d227f2106eccf69fe0e7c11fee0','324524fffa4bd0f76c618f9fbb6ede30e733b2ff'],'original_successful_run':38105340592,'run_attempt':1,'native_artifact_id':11689755940,'native_ZIP_bytes':49089276,'native_ZIP_sha256':'88f406c654de1155e717ded1534fa058ca1c5375007109f2a06364d3a5036ac2','Linux_receipt_artifact_id':11689851536,'Linux_receipt_ZIP_bytes':185396,'Linux_receipt_ZIP_sha256':'ec8d7cc46646fcfca7a228392e1bc2cb53341d838563802abd7d306c1f07eaba','selected_Linux_bytes':22384802,'selected_Linux_sha256':'be55dadc391ae4ac7dd38356755a1698c595fdf41bd4a0141f8df7cc9d29f00e','ELF':'linux amd64','Go':'go1.26.9','embedded_vcs_modified':False,'data_chain':'Original member == selected binary == SHA256SUMS == native and JAT binary.sha256 == Robot binarySha256; native/JAT commitSha727/platformlinux_amd64/versionv18.19.6 match; native robotExactBinary full body == original Robot body'},
 },
 'producer_provenance':{'authenticated_retained_API_and_transport_originals':'Released asset549249380 and candidate artifacts11689755940/11689851536 authenticated and measured; both artifact APIs pin successful run38105340592/head727. Original transportHTTP200 retained privately. No reacquisition.', 'source_workflow_contract':'Exact727 source stages four native binaries, SHA256SUMS and hash checks before native receipt. Its source-owned validator invocation pins candidate SHA; original tasks.py validator implementation was not acquired or replayed. Native and JAT lifecycle payloads belong to different fixtures and are not asserted equal.', 'numeric_producing_job_id_and_original_job_log':'UNAVAILABLE within this acquisition review; no inferred numeric producer identity', 'publisher_signature_or_attestation':'UNKNOWN_NOT_SUPPLIED; API digest, checksum and embedded VCS metadata are not cryptographic publisher signatures or reproducible-build proof'},
 'preservation':{'all76_owner_bindings_exact_after_review':True,'managed_RCC3_and_activation_exact_bound_originals':True,'initial_owner_inspector_exit1_and_named_v2_exit0_retained':True,'historical097_b5aa_not_substituted_for727':True,'source_download_build_toolkit_pins_unmodified':True,'no_candidate_binary_execution_functional_test_gateway_install_source_edit_download_or_API_repoll':True},
 'reviewer_construction_observations':{'headers_probe':'Incorrect guessed filename failed before reading; correct bound original-artifact prefix inspected. No owner bytes changed.', 'initial_reader':'Own first reader wrongly demanded separate native/JAT lifecycle payload equality and failed after all archive checks. Original read-only reader retained; namedv2 removes only that invalid cross-fixture equality while preserving source/binary checks. No acquisition or product test was repeated.'},
 'limits':['Acquisition provenance permits the root to separately approve exact isolated binaries and preparation; this is not functional compatibility, provider recovery, persistent reuse, reload/drain, release or production-default admission.','Released5 dirty-source equivalence and cause remain UNKNOWN; candidate modified=false is data corroboration, not universal signing or reproducibility.','Original upstream lifecycle receipts are retained upstream evidence; no new Actions acceptance was executed.','Exact candidate727 only; no broad18.19.6 label, version-only allowlist, historical097 reuse, private01f reconstruction, native/otherplatform/full133/134/139/143/221 closure.','Capacity, frozen source/runner/helper/activation preflight and distinct root ONE-per-binary execution authority remain required.'],
 'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; exact owner proposed68cd85 and prior324d reused, no source guide mutation by reviewer','Durable_learning':'Embedded revision with vcs.modified=true cannot prove unchanged commit-tree source; retain dirty flag beside API and exact binary hashes, independently of functional qualification.','Exact_delta':{'embedded_provenance_patch':pb,'additions':7,'text_lines':6,'removals':0,'placement':'RCC Environment Artifact execution anchor'},'Existing_identity_delta_reused':bind(identity),'Evidence':'Independent data-only decoded original released5 D1/modifiedtrue and candidate727/modifiedfalse; all76 immutable refs and original source/member/receipt chain exact.','Stale_or_ambiguous_guidance_removed':'Exact proposed clarification excludes tag/checksum/embedded revision as clean-tree or signing proof. No cosmetic additions or session diary.','Remaining_uncertainty':'Released5 modified inputs/cause, numeric producer job/log, signatures/attestations, independent reproducibility and all new functional acceptance.'},
 'Upstream_disposition':'none; no confirmed upstream defect',
 'evidence':refs
}
out=O/'OWNERFINAL-independent-three-original-RCC-acquisition-data-review.json'
with out.open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
out.chmod(0o444)
print(json.dumps({'status':receipt['status'],'owner_final_review':bind(out)}))
