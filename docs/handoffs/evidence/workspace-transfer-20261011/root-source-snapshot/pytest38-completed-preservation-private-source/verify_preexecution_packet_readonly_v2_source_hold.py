import ast,hashlib,importlib.util,json,os,stat,shutil,subprocess
from pathlib import Path
OUT=Path(__file__).parent
p=OUT/'preserve_exact_pytest38_once_v5.py';spec=importlib.util.spec_from_file_location('storage_definitions_readonly',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
cfgp=OUT/'private-current396-data-only-guard-and-exact-pytest38-inputs.json';cfg=json.loads(cfgp.read_bytes())
assert not m.DEST.exists() and not m.DEST.is_symlink() and not m.STAGE.exists() and not m.STAGE.is_symlink()
entries=m.baseline_entries(cfg['original_inventory']['path']);root_available=m.ROOT.exists()
if root_available:m.root_admission(entries[''])
for rel,row in entries.items():
 m.safe_name(m.ROOT.name+('/'+rel if rel else ''))
 if row['kind']=='file':m.safe_name(m.ROOT.name+'/'+row['hardlink_first'])
checks=m.global_guard(cfg);before=m.accessible_handles()
parent=Path('/workspace/engineering/rcc-control3-failed-owned-preservation-proposal/preserve_failed_control3_once_v4.py');old=ast.parse(parent.read_text());new=ast.parse(p.read_text())
unchanged=[]
for name in ['need','sha','meta','inventory','create_archive']:
 a=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name==name);b=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name==name)
 assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False);unchanged.append(name)
assert not m.DEST.exists() and not m.STAGE.exists()
result=dict(schema=1,status='HOLD_SOURCE_ROOT_UNAVAILABLE' if not root_available else 'READ_ONLY_PREEXECUTION_DEPENDENCY_AND_GUARD_PASS',
 current=checks,baseline_entries_including_root=len(entries),original_root_metadata_exact='UNAVAILABLE' if not root_available else True,source_root_currently_available=root_available,source_root_disappearance_cause='UNKNOWN',
 all_expected_archive_names_safe=True,exact_parent_AST_reused=unchanged,
 fresh_tmp_available=shutil.disk_usage('/tmp').free,required_tmp=469762048,
 accessible_reference_observation=before,DEST_STAGE_absent=True,
 current_source_clean=True,archive_remove_restore_extract_execution='NOT_RUN',
 complete15683_body_current_replay='NOT_RUN_AT_PREPARATION; two complete frozen original snapshots retained; actual operation requires full fresh equality twice',
 owner_UID_GID=[os.geteuid(),os.getegid()],upstream='none')
p=OUT/'private-readonly-current-guard-dependency-and-archive-name-proof-v2-source-HOLD.json';p.open('x').write(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n');p.chmod(0o600)
print(json.dumps(dict(status=result['status'],current_rows=1426,historical_rows=1423,native=1192,retained_files=checks['retained'],entries=len(entries),tmp_free=result['fresh_tmp_available'],archive_remove='NOT_RUN')))
