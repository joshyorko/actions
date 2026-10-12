import hashlib,json,os,stat,shutil,datetime
from pathlib import Path
OUT=Path(__file__).parent
READ=Path('/workspace/engineering/pytest38-completed-preservation-readonly-proposal')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=Path(p);s=p.lstat();return dict(path=str(p),bytes=s.st_size,sha256=sha(p),mode=oct(stat.S_IMODE(s.st_mode)))
def save(n,d):
 p=OUT/n;p.open('x').write(json.dumps(d,indent=2)+'\n');p.chmod(0o600);return bind(p)
for p in OUT.iterdir():
 if p.is_file() and not p.is_symlink():p.chmod(0o600)
installed=Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/lib/python3.12/site-packages/_pytest')
root=Path('/tmp/pytest-of-agent/pytest-38');assert not root.exists() and not root.is_symlink()
trace=save('safe-source-absence-and-installed-retention-mechanism.json',dict(schema=1,
 decision='HOLD_SOURCE_ROOT_UNAVAILABLE',observed_at_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 root=str(root),root_exists=False,parent_real_directory=True,
 observed_current_numbered_roots=[39,40,41],default_control_numbered_root=39,
 installed_source_bindings=[bind(installed/'tmpdir.py'),bind(installed/'pathlib.py')],
 installed_defaults=dict(tmp_path_retention_count=3,tmp_path_retention_policy='all'),
 source_lines=dict(tmpdir_defaults=[227,233],tmpdir_default_directory=[184,187],
  pathlib_candidate_threshold=[344,347,352],pathlib_exit_registration=[398,403]),
 mechanism='Default numbered-root cleanup is registered at exit; candidate number <= max_existing-keep. With max_existing41 and keep3,38 is eligible. Lock/deletion logic must also admit it.',
 actual_default39_command=['/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python','-m','pytest','-q',str(OUT/'test_pytest38_archiver_controls.py')],
 actual_default39_log=bind(OUT/'controls-serial-successor.private.log'),
 effective_settings_for40_41='UNAVAILABLE',responsible_cleanup_invocation='UNKNOWN',
 original_root_bytes='UNAVAILABLE_NO_ARCHIVE_PROOF_NO_RECONSTRUCTION',
 archiver_operation_parent_or_remove_execution='NOT_RUN',
 exact_preexecution_source_guard_failed_before_archive_destination_created=True,
 original_inventory_retained=bind(READ/'private-complete-two-stable-pytest38-body-metadata-inventory.json')))
patch='''--- a/docs/skills/repository-operations.md
+++ b/docs/skills/repository-operations.md
@@
+Before running synthetic storage controls, choose a new, explicit owned
+`--basetemp` and verify that it is absent. Pytest may delete a supplied existing
+base directory, and its default numbered-root retention may reclaim older roots
+that another task has only inventoried. An inventory does not reserve its bytes.
+Serialize against retention-triggering tests until evidence roots are preserved;
+if a root vanishes, retain the failed admission and report its bodies unavailable
+without reconstructing them or attributing a particular cleanup invocation from
+directory numbers alone.
'''
p=OUT/'canonical-pytest-retention-evidence-root-protection-proposed.patch';p.open('x').write(patch);p.chmod(0o600)
cfg=OUT/'private-current396-data-only-guard-and-exact-pytest38-inputs.json';d=json.loads(cfg.read_bytes());proof=OUT/'private-readonly-current-guard-dependency-and-archive-name-proof-v2-source-HOLD.json';check=json.loads(proof.read_bytes());assert check['status']=='HOLD_SOURCE_ROOT_UNAVAILABLE'
controls=['original-mechanisms-red.private.log','final-v3-controls-green.private.log','final-v6-controls-green.private.log']
assert '3 failed' in (OUT/controls[0]).read_text() and '1 failed, 33 passed' in (OUT/controls[1]).read_text() and '34 passed' in (OUT/controls[2]).read_text()
files=[p for p in OUT.iterdir() if p.is_file() and p.name!='OWNERFINAL-exact-pytest38-storage-archiver-preexecution-SOURCE-HOLD.json']
owner=dict(schema=1,owner_announced_at_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 decision='HOLD_SOURCE_ROOT_UNAVAILABLE_PREEXECUTION_IMPLEMENTATION_ONLY',
 script=bind(OUT/'preserve_exact_pytest38_once_v6.py'),configuration=bind(cfg),
 readonly_original_proposal=bind(READ/'OWNERFINAL-exact-completed-pytest38-bounded-storage-preservation-proposal.json'),
 original_root=str(root),original_root_current_exists=False,
 destination='/tmp/actions-completed-pytest38-preservation-one-owned',stage='/tmp/actions-completed-pytest38-preservation-one-owned-stage',
 destinations_currently_absent=not Path('/tmp/actions-completed-pytest38-preservation-one-owned').exists() and not Path('/tmp/actions-completed-pytest38-preservation-one-owned-stage').exists(),
 operation_archive_remove_restore_extract_or_native='NOT_RUN',
 original15683_members_current_bytes='UNAVAILABLE',original_root_disappearance_cause='UNKNOWN',
 original_frozen_inventory_and_correlation_retained=True,original_known_inaccessible2_and241_pointer_scope='FINITE_UNKNOWN_GLOBAL_OR_UNREADABLE_SCOPE',
 implementation_contract=dict(exact_root_fixed=True,root_UID_GID=[1000,1000],root_mode='0o700',
  expected_members_excluding_root=15683,expected_archive_members_including_root=15684,
  expected_types=dict(directory=3424,file=11756,symlink=495,fifo=8),internal_hardlink_groups=4,
  root_and_worker_lock_absence_required=True,two_fresh_complete_body_metadata_inventory_equalities_required=True,
  PAX_mtime_ns_exact_integer_decimal=True,complete_private_index_file_and_parent_directory_fsynced_before_remove=True,
  unique_safe_names_and_single_gzip_CRC_ISIZE_EOF_required=True,compressed_ceiling_bytes=335544320,
  every_compressed_write_including_footer_checked_before_write=True,reserved_free_bytes=134217728,
  required_fresh_tmp=469762048,operation_seconds=600,kill_grace_seconds=10,outer_seconds=900,outer_kill_grace=10,
  failed_admission_preserves_original_and_partial_output=True,after_every_started_outcome_current_source_native_prior_archive_guards_attempted=True,
  root_markers_before_after_all_started_outcomes=True,no_restore_or_extractall=True),
 pure_control_evidence=dict(original_imported_mechanisms_RED='3FAIL',
  tightened_desired_index_directory_durability_RED='1FAIL33PASS',
  final_v6_GREEN='34PASS0SKIP',final_command=['env','-u','PYTHONOPTIMIZE','timeout','--signal=TERM','--kill-after=10s','60s','/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python','-m','pytest','-q','--basetemp='+str(OUT/'synthetic-final-v6-green-once'),str(OUT/'test_pytest38_archiver_controls_v6.py')],
  initial_cached_pytest_n_option_SETUPFAIL_retained=True,
  intermediate_test_expectation_5FAIL27PASS_retained=True,
  synthetic_small_archives_only_not_actual_source=True,covered=['ceiling before write','reserve','gzip footer overflow retains partial','unsafe names','duplicate/missing members','CRC/ISIZE/truncation/trailing/concatenation','mode/uid/gid/nsmtime/sub-ns','resolved body','hardlink target/external link','FIFO type','complete index before removal','failed index/revalidation never remove','directory fsync']),
 actual_readonly_data_guards=dict(current_HEAD=d['current_head'],current_tree=d['current_tree'],current_Git_FS_body_modes=1426,
  current_SOURCE_LIGHT_FULL_qualification='NOT_INFERRED',historical_e4_Git_body_modes=1423,
  old_native_complete_members=1192,retained_files=386,prior_archives=61,prior_indices=27,
  failed_control3_original_status='FAIL_UNCHANGED',failed563='EXISTENCE_ONLY',
  complete_known_dependency_readback='PASS_EXCEPT_ORIGINAL_SOURCE_ROOT_UNAVAILABLE',proof=bind(proof)),
 release_required_but_not_granted=dict(root_exact_hash_bound_once=True,independent_script_config_review=True,
  no_concurrent_source_native_tmp_retention_writes=True,source_root_exact_original_identity_and_bytes_available=True,
  current_DATAONLY_guard_head_must_match_or_named_reviewed_successor_required=True,
  actual_status='HOLD_NO_RELEASE_SOURCE_UNAVAILABLE',outer_argv=['env','-u','PYTHONOPTIMIZE','timeout','--signal=TERM','--kill-after=10s','900s','/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python',str(OUT/'preserve_exact_pytest38_once_v6.py'),'--config',str(cfg),'--config-sha256',sha(cfg),'--release','<distinct-root-release0600>','--release-sha256','<root-release-SHA256>']),
 safe_retention_trace=trace,all_authored_top_level_files_preserved=[bind(p) for p in sorted(files)],
 Documentation_improvement=dict(Canonical_file_changed_or_proposed='docs/skills/repository-operations.md; original8line a76b reused plus concrete retention-root-protection successor proposed, no source/docs changes here',
  Exact_delta_or_verified_reuse=[bind(READ/'canonical-pytest-root-origin-and-bounded-preservation-proposed.patch'),bind(OUT/'canonical-pytest-retention-evidence-root-protection-proposed.patch')],
  Durable_learning_captured='Bound archive writes and preserve exact ns metadata/index durability; inventoring an evidence root does not reserve it from default pytest retention. Synthetic tests need absent, explicitly owned basetemp.',
  Evidence=[trace,bind(proof),*[bind(OUT/n) for n in controls]],
  Stale_or_ambiguous_guidance_removed='No exact launch origin from correlation; no inventory-to-reservation claim; no directory numbering-to-responsible invocation or unavailable-body reconstruction.',
  Remaining_uncertainty='Original root bytes and precise responsible cleanup invocation unavailable. Compression and archival/removal remain NOT_RUN. Code/controls do not prove actual storage preservation.'),Upstream_disposition='none',constructor=bind(__file__))
p=OUT/'OWNERFINAL-exact-pytest38-storage-archiver-preexecution-SOURCE-HOLD.json';p.open('x').write(json.dumps(owner,indent=2)+'\n');p.chmod(0o400)
print(json.dumps(dict(owner=bind(p),script=owner['script'],configuration=owner['configuration'],status=owner['decision'],GREEN='34PASS',actual_archive_remove='NOT_RUN')))
