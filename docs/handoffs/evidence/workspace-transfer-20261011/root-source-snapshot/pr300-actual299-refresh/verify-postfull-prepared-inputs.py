from pathlib import Path
import hashlib, json, stat
R=Path('/workspace/engineering/pr300')
O=Path('/workspace/engineering/pr300-actual299-refresh')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
j=json.loads((O/'own-Bootstrap-reuse-inputs-and-origins.json').read_text())
assert len(j['all30_current_inputs_exact_prepared_Git_bytes'])==30
for name,h in j['all30_current_inputs_exact_prepared_Git_bytes'].items():assert sha(R/name)==h,name
for name, row in j['five_own_environment_configs'].items():
 assert sha(R/name/'.venv/pyvenv.cfg')==row['config_sha256'],name
 assert str((R/name/'.venv/bin/python').resolve())==row['python_resolved']
for row in j['five_actual_concrete_module_origins_and_prefixes']:
 assert Path(row['prefix']).is_relative_to(R)
 assert Path(row['origin']).is_relative_to(R)
 assert Path(row['origin']).is_file()
c=json.loads((O/'five-own-prepared-environment-copy-and-path-rebinding.json').read_text())
count=0
for env in c['environments']:
 for row in env['path_only_rebindings']:
  assert sha(Path(env['source'])/row['relative'])==row['original_sha256']
  assert sha(Path(env['own_destination'])/row['relative'])==row['rebound_sha256']
  count+=1
fixture=json.loads((O/'existing-prepared-runtime-inputs-copy-successor-v2.json').read_text())['copied_ignored_fixture_input']
for p in (Path(fixture['source']),R/fixture['path']):
 assert sha(p)==fixture['sha256']
 assert p.stat().st_size==fixture['bytes']
 assert stat.S_IMODE(p.stat().st_mode)==int(fixture['mode'],8)
assert sha('/workspace/actions-cloud/bin/rcc')==fixture['sha256']
assert not (R/'action_server/src/actions/server/_oauth2_config.py').exists()
assert sha(j['original_Bootstrap_log'])==j['original_Bootstrap_log_sha256']
light=json.loads((O/'owner-light-ready-prehash-capacity-FULL-HOLD.json').read_text())
for row in light['evidence']:
 assert Path(row['path']).stat().st_size==row['bytes']
 assert sha(row['path'])==row['sha256']
result={'all30_prepared_input_bytes_unchanged':True,'five_own_configs_and_Python_resolved_paths_unchanged':True,'five_original_concrete_module_origin_records_remain_valid_paths':True,'original_and_own_rebound_environment_metadata_bytes_unchanged':True,'rebound_path_count':count,'pinned_Rcc_source_destination_and_gateway_digest_exact':fixture['sha256'],'pinned_Rcc_fixture_mode_exact':fixture['mode'],'all_light_original_evidence_refs_exact':len(light['evidence']),'generated_OAuth_still_absent_content_authority_HOLD':True,'no_complete_environment_tree_or_process_reaping_claim':True}
(O/'after-authorized-full-prepared-inputs-and-original-receipts-proof.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
