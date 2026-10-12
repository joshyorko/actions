import hashlib,json,pathlib,stat
R=pathlib.Path('/workspace/engineering/pr221-current-e2-inner-v2-ACTUAL-independent-review');P=pathlib.Path('/workspace/engineering/pr221-current-e2-inner-data-executor-successor-v2-PREPARATION');OWN=pathlib.Path('/workspace/engineering/root-current-e2-one-inner-data-inspection-owned-v2')
def bind(p):
 p=pathlib.Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return dict(path=str(p),bytes=s.st_size,sha256=h.hexdigest(),mode=oct(stat.S_IMODE(s.st_mode)))
parent=pathlib.Path('/workspace/engineering/root-current-e2-one-inner-data-inspection-original-outer-owned-v2/OWNERFINAL-root-one-original-current-e2-inner-data-inspection-outer-terminal-v2.json');root=json.loads(parent.read_bytes());assert bind(parent)['sha256']=='60d63b42430bda3005527e6d445df7af7c0ea8ccc8d70d7a307738720472da76'
assert root['one_attempt'] is True and root['no_retry'] is True and root['returncode']==0 and 0<root['elapsed_seconds']<120
for row in [root['proposal'],root['review']]+root['outputs']:assert bind(row['path'])==row
proposal=json.loads(pathlib.Path(root['proposal']['path']).read_bytes());manifest=json.loads(pathlib.Path(proposal['manifest_binding']['path']).read_bytes())
for row in proposal['evidence']:assert bind(row['path'])==row
for row in manifest['bindings']:assert bind(row['path'])==row
assert bind(proposal['executor_binding']['path'])==proposal['executor_binding']
release=pathlib.Path(proposal['root_release']['path']);auth=json.loads(release.read_bytes());assert bind(release)['mode']=='0o600'
assert auth['schema']=='ROOT_ONE_CURRENT_E2_INNER_DATA_INSPECTION' and auth['execute'] is True and auth['proposal_binding']==root['proposal'] and auth['independent_review_binding']==root['review']
consumed=OWN/'consumed-one-root-release.json';assert json.loads(consumed.read_bytes())==auth and bind(consumed)['mode']=='0o600'
result=OWN/'OWNERFINAL-one-current-e2-inner-data-inspection-result.json';d=json.loads(result.read_bytes());assert d['status']=='PASS_STRUCTURAL_INNER_INTEGRITY_WITH_CONTENT_AUTHORITY_HOLDS' and d['protected_post']=='PASS';assert d['source']==proposal['source'] and d['tree']==proposal['tree'] and len(d['reports'])==7
expected={r['name']:r for r in manifest['outer_inventory']};source={r['path']:r for r in manifest['source_expectations']['rows']};assert len(source)==217
slots=set();summaries=[]
for row in d['reports']:
 assert bind(row['path'])==row
 x=json.loads(pathlib.Path(row['path']).read_bytes());ref=x['file'];outerrow=expected[ref['member']]
 assert ref['outer_original']==manifest['zip_binding'] and ref['filesystem_extraction']=='NOT_RUN' and ref['bytes']==outerrow['bytes'] and ref['sha256']==outerrow['sha256']
 inv=x['inventory'];assert len({i['path'] for i in inv})==len(inv) and len({i['path'].casefold() for i in inv})==len(inv)
 compare=x['source_comparison'];tracked=[r for r in compare['comparisons'] if 'git_blob' in r];generated=[r for r in compare['comparisons'] if 'classification' in r]
 assert len(tracked)==217 and {r['git_path'] for r in tracked}==set(source) and compare['tracked_source_files_absent_from_archive']==[]
 for r in tracked:
  e=source[r['git_path']];assert r['git_blob']==e['oid'] and r['git_mode']==e['mode'] and r['git_sha256']==e['sha256'] and r['git_bytes']==e['bytes']
  assert r['archive_sha256']==r['git_sha256'] and r['archive_bytes']==r['git_bytes'] and r['body_equal'] is True
  assert r['executable_bit_equal'] is (True if r['archive_unix_mode_available'] else None)
 assert compare['body_equal_count']==217 and compare['body_difference_count']==0
 assert x['generated_input_authority']=='HOLD'
 assert set(x['generated_oauth_categories'])=={'actions_config','default_user_config'}
 for v in x['generated_oauth_categories'].values():assert v==dict(category='EMPTY_STRING',sha256=hashlib.sha256(b'').hexdigest(),utf8_bytes=0)
 assert x['generated_static_assets']['index.html']['category']=='NONEMPTY_AUTHORITY_HOLD' and x['generated_static_assets']['index.html']['bytes']==987412
 assert x['tracked_html']['bytes']==933318 and x['tracked_html']['authority']=='HOLD'
 dirs=sum(i.get('directory',False) for i in inv);regular=len(inv)-dirs
 if 'platform' in x:
  slots.add((x['platform'],x['python_abi']));assert x['package_member_count']==219 and x['package_python_member_count']==203 and x['package_nonpython_member_count']==16
  assert x['record']==dict(all_member_hash_size_verified=True,hashed_rows=222,rows=223,self_unhashed_only=True) and regular==223
  assert x['other_payload_member_count']==4 and len(generated)==2
  assert dirs==(0 if x['platform']=='Windows' else 27)
  assert {r['git_path'] for r in generated}=={'action_server/src/actions/server/_oauth2_config.py','action_server/src/actions/server/bin/rcc-18.19.3'+('.exe' if x['platform']=='Windows' else '')}
  assert all(r['archive_unix_mode_available'] is (x['platform']!='Windows') for r in tracked)
  package_count=219;record=x['record'];python=203;platform=x['platform'];abi=x['python_abi']
 else:
  slots.add(('sdist',None));assert x['embedded_rcc_member_count']==0 and x['source_pyproject_equal'] is True and len(compare['comparisons'])==218 and len(generated)==1 and regular==223
  assert generated[0]['git_path']=='action_server/src/actions/server/_oauth2_config.py';package_count=218;record=None;python=sum(r['archive_path'].endswith('.py') for r in compare['comparisons']);platform='sdist';abi=None
 assert python==203
 summaries.append(dict(platform=platform,abi=abi,report_binding=row,original_member=ref['member'],original_member_sha256=ref['sha256'],package_regular_members=package_count,Python_members=python,directory_members=dirs,total_inventory_members=len(inv),RECORD=record,tracked_equal_bodies=217,tracked_body_differences=0,tracked_missing=0,tracked_mode_equal=217 if platform!='Windows' else None,Unix_modes_available=platform!='Windows',generated_allowed_members=len(generated),OAuth_required_fields=2,OAuth_empty_fields=2,static_index_bytes=987412,static_index_sha256=x['generated_static_assets']['index.html']['sha256'],tracked_HTML_bytes=933318,tracked_HTML_sha256=x['tracked_html']['sha256'],generated_content_authority='HOLD'))
assert slots=={(p,a) for p in ['Linux','Mac','Windows'] for a in ['cp312','cp313']}|{('sdist',None)}
assert sum(r['bytes'] for r in d['reports'])<8388608
for row in d['reports']:assert bind(row['path'])==row
proof=dict(parent_binding=bind(parent),child_result_binding=bind(result),root_release_binding=bind(release),consumed_release_binding=bind(consumed),parent_returncode=0,parent_elapsed_seconds=root['elapsed_seconds'],protected_post='PASS',executor_binding=proposal['executor_binding'],proposal_binding=root['proposal'],preexecution_independent_binding=root['review'],source=d['source'],tree=d['tree'],input_manifest_bindings_verified=17,proposal_evidence_bindings_verified=27,report_summary=summaries,no_inspector_replay_or_inner_archive_read_by_reviewer=True)
f=R/'independent-original-seven-report-count-source-and-authority-proof.json';f.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');f.chmod(0o400)
receipt=dict(schema='INDEPENDENT_ORIGINAL_CURRENT_E2_INNER_DATA_ACTUAL_REVIEW',decision='GO_CURRENT_E2_ORIGINAL_SEVEN_DISTRIBUTION_INNER_STRUCTURAL_INTEGRITY_ONLY',parent_binding=bind(parent),actual_child_result_binding=bind(result),proof_binding=bind(f),proposal_binding=root['proposal'],preexecution_independent_binding=root['review'],source=d['source'],tree=d['tree'],artifact_id=11708952448,original_zip_binding=manifest['zip_binding'],original_reports=d['reports'],actual_counts={'wheels':6,'sdist':1,'each_wheel_package_regular':219,'each_wheel_Python':203,'each_wheel_nonPython':16,'each_wheel_RECORD_rows':223,'each_wheel_RECORD_hashed':222,'Linux_Mac_directory_entries_each':27,'Windows_directory_entries_each':0,'sdist_package_regular':218,'sdist_inventory_regular':223,'tracked217_equal_in_each_distribution':True,'tracked_differences':0,'tracked_absences':0},qualification='Exact original result from approved frozen executor with50 real-function controls and runtime17 source/input pre/post checks. Reviewer rehashed reports and cross-checked source/reference/count invariants; did not rerun inspector or read inner archive payloads.',remaining_holds=['All seven generated OAuth modules have two empty required strings; required input/content authority remains HOLD.','Generated/static decoded index987412 and trackedHTML933318 are separately nonempty with distinct digests; no semantic equivalence or generated frontend authority admitted.','All217 tracked bodies match e2, with available Unix executable modes equal; Windows Unix modes unavailable remains UNKNOWN. This is packaged-body comparison, not builder checkout or compiler causation.','Linux original synthetic165c ordered[a709,e2]/treeafe separately authenticated; Mac/Windows/sdist builder checkout UNKNOWN. Do not substitute actuale2 for buildcheckout.','Original transfer6bf OSError9 FAIL retained; separate outer22eed and new innerPASS do not relabel transfer terminal.','No extracted package, import/install/cold registry/consumer/native/provider/private/code01f/frozenv6/issue or publication/release acceptance.','Other actual7 package payloads outside217 and generated exceptions include sdist buildmetadata; source authority remains bounded by explicit observed rows.'],documentation_improvement={'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; verified reuse of f797 entry/boundary lesson and existing per-platform RECORD/source/generated authority guidance.','Exact_delta':'Accept exact8-line f797 lesson already proposed: unoptimized typed ROOT admission, full ZIP-header preflight and restored real-function controls; retain source/generated/consumer authority separation. No new cosmetic paragraph required for this actual receipt.','Durable_learning_captured':'Current original distribution counts are now measured independently per platform; equal tracked bodies and valid RECORD do not establish builder checkout, generated OAuth/frontend authority or consumer/release acceptance.','Evidence':'Original0 parent5.197922s and protectedpostPASS; all7 hash-bound reports,223/222 wheel RECORD,217 body comparisons matching authentic Git rows; empty OAuth and separate HTML digests. Windows has zero directory entries and unavailable Unix modes, unlike Linux/Mac27.','Stale_or_ambiguous_guidance_removed':'Predicted219/203/223 labels are replaced by actual measured counts only for this original tuple; old215/full7 and transferFAIL remain historical. No body equality relabeled producer identity or empty content acceptance.','Remaining_uncertainty':'Generated-input/frontend source authority, other builder checkout and every installed/native/private/full release gate remain open.'},upstream_disposition='none')
g=R/'OWNERFINAL-independent-original-current-e2-seven-distribution-inner-ACTUAL-integrity-review.json';g.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');g.chmod(0o400);print(json.dumps(bind(g)));print(json.dumps(bind(f)))
