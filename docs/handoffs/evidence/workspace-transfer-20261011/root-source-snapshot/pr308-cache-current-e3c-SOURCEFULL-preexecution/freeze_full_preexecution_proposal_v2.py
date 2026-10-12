import ast,copy,hashlib,json,os,stat
from pathlib import Path
O=Path('/workspace/engineering/pr308-cache-current-e3c-SOURCEFULL-preexecution')
def row(p):
 p=Path(p);h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return {'path':str(p),'sha256':h.hexdigest(),'bytes':p.stat().st_size,'mode':oct(stat.S_IMODE(p.stat().st_mode))}
original=O/'OWNERFINAL-current-e4ff-managed-configured-SOURCEFULL-preexecution-proposal.json';assert row(original)['sha256']=='bacae1a9c4998816b4422abf35686a49524c9f73669a7f739cc7c084ac140e96'
old=json.loads(original.read_text());new=copy.deepcopy(old);new['status']='OWNERFINAL_NAMED_V2_CURRENT_SOURCEFULL_PREEXECUTION_REVIEW_REQUIRED_NOT_RUN'
new['configured_full_argv'][-1]=str(O/'current_source_full_body_v2.py')
new['outer_managed_command']=['source /workspace/actions-cloud/activate.sh','unset PYTHONOPTIMIZE','PATH primary/bin then exact cached toolkit/bin preserved',old['outer_managed_command'][-1].replace('launch_current_source_full_once.py','launch_current_source_full_once_v2.py')]
new['one_attempt']['owned_output_directory']=str(O/'one-configured-full-once-owned-v2')
new['predecessor']={'binding':row(original),'disposition':'HISTORICAL_HOLD_0b902_DUE_TO_VERIFIED_EXPANDED_REMOVAL_NOT_NEW_SOURCE_FAILURE','unchanged':True}
maprow=row('/workspace/engineering/root-failed-control3-one-byte-preservation-v4/root-exact-historical-failed-member-archive-mapping.json');assert maprow['sha256']=='cc73027ce86ea0965f3bdd88ed3398c322dcf012b337a4ca161966f19ffee6c7'
mapping=json.loads(Path(maprow['path']).read_text());proof=O/'named-v2-readonly-historical-member-resolution-proof.json';measured=json.loads(proof.read_text());assert measured['original_binding']==mapping['original_binding'];assert measured['original_status']=='FAIL'
new['historical_binding_alias']={'mapping':maprow,'archive':mapping['archive'],'complete_index':mapping['complete_index'],'expanded_removal':mapping['expanded_removal'],'root_original_terminal':mapping['root_original_terminal'],'original_binding':mapping['original_binding'],'member':mapping['member'],'member_uid':1000,'member_gid':1000,'member_mode':'0o600','verified_readonly_proof':row(proof),'readonly_resolution_seconds':measured['readonly_resolution_seconds'],'checks':'Stream compressed SHA, exact archive size/mode/nosymlink, all mapped metadata bindings; unique safe regular member/1696bytes/SHA/mode/uidgid/original FAIL and cleanup FAIL; gzip EOF/CRC/ISIZE; no path restoration or acceptance transfer.'}
new['optimization_guard']='unset PYTHONOPTIMIZE; fail before assert-dependent gate if sys.flags.optimize !=0 or PYTHONOPTIMIZE nonempty'
new['strict_before_after_guards']['historical_removed_receipt']='ONLY original8dc path/hash may resolve exact verified archived member; all other rows unchanged'
new['current_capacity_observation']={'workspace_bytes':os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize,'devshm_bytes':os.statvfs('/dev/shm').f_bavail*os.statvfs('/dev/shm').f_frsize,'status':'FRESH_FLOOR_AND_SERIALIZED_ROOT_RELEASE_STILL_REQUIRED'}
new['documentation_improvement']={'canonical_file_proposed':'docs/skills/repository-operations.md','exact_new_alias_delta':row(O/'canonical-exact-historical-receipt-archive-alias-proposed.patch'),'durable_learning':'Exact archive member can satisfy historical byte preservation after verified removal, without recreating receipt paths or changing failed acceptance.','evidence':'Operator mapcc73027, original1696/8dc bytes and FAIL/cleanupFAIL found in ca557 gzip with exact uidgid/mode and stream/gzipEOF checks.','stale_or_ambiguous_guidance_removed':'Do not mistake an intentionally absent expanded path for lost preserved bytes; never waive missing-row checks or infer actual qualification from an alias.','remaining_uncertainty':'Independent complete preservation review and current configuredFULL/ROOT serialized release remain pending; historical RCC failure unchanged.'}
files=['current_source_full_body_v2.py','current_source_prepost_guard_v2.py','launch_current_source_full_once_v2.py','historical_failed_receipt_archive_v1.py']
for f in files:compile((O/f).read_bytes(),str(O/f),'exec')
# Commands and timing envelope remain exactly their predecessor except named body path.
assert new['execution_bounds']==old['execution_bounds']
assert new['configured_full_argv'][:-1]==old['configured_full_argv'][:-1]
for f in ['current_source_full_body.py','launch_current_source_full_once.py']:
 before=(O/f).read_text();after=(O/(Path(f).stem+'_v2.py')).read_text()
 after=after.replace("'frozen-current-source-full-inputs-v2.json'","'frozen-current-source-full-inputs.json'").replace("'OWNERFINAL-current-e4ff-managed-configured-SOURCEFULL-preexecution-proposal-v2.json'","'OWNERFINAL-current-e4ff-managed-configured-SOURCEFULL-preexecution-proposal.json'").replace("'current_source_prepost_guard_v2.py'","'current_source_prepost_guard.py'").replace("'one-configured-full-once-owned-v2'","'one-configured-full-once-owned'")
 after=after.replace("if sys.flags.optimize != 0 or os.environ.get('PYTHONOPTIMIZE'):\n raise RuntimeError('PYTHON_OPTIMIZE_MUST_BE_CLEARED_BEFORE_MANAGED_GATE')\n",'')
 assert ast.dump(ast.parse(before),include_attributes=False)==ast.dump(ast.parse(after),include_attributes=False)
new['named_body_parent_AST_preservation']='EXACT after filename and early optimize guard normalization; commands/waits/pre60/full640/post60/outer900/600TERM10 unchanged'
new['resolver_module_interface']={'binding':row(O/'historical_failed_receipt_archive_v1.py'),'call':'verify_exact_historical_receipt(original_row, mapping_binding)','returns':'safe original/archive/member bindings plus FAIL and historical-preservation-only scope; no raw JSON returned'}
new['frozen_input_bindings']=[row(O/f) for f in files]+[row(O/'frozen-current-source-full-inputs-v2.json'),row(Path(__file__)),row(original),row(proof),row(O/'v2-readonly-historical-member-resolution.private.log'),row(O/'canonical-exact-historical-receipt-archive-alias-proposed.patch'),maprow]+[mapping[key] for key in ['complete_index','expanded_removal','root_original_terminal']]+[r for r in old['frozen_input_bindings'] if r['path'] not in [str(O/f) for f in ['current_source_full_body.py','current_source_prepost_guard.py','launch_current_source_full_once.py','frozen-current-source-full-inputs.json','freeze_full_preexecution_proposal.py']]]
p=O/'OWNERFINAL-current-e4ff-managed-configured-SOURCEFULL-preexecution-proposal-v2.json';assert not p.exists();p.write_text(json.dumps(new,indent=2,sort_keys=True)+'\n');p.chmod(0o600);print(json.dumps(row(p)))
