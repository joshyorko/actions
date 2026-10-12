"""One independently reviewed, root-released DATA_ONLY operation. Inert import."""
from pathlib import Path
import hashlib,json,os,stat,subprocess,sys,traceback
OWNED=Path('/workspace/engineering/root-one-completed-FULL-single-copy-storage-owned-v2');RELEASE=Path('/workspace/engineering/root-one-completed-FULL-single-copy-storage-release-v2.json');PROPOSAL=Path('/workspace/engineering/completed-current8d49-FULL-storage-single-copy-fallback-PREPARATION-v2/OWNERFINAL-one-completed-FULL-single-copy256-storage-PREEXECUTION-v2.json');PHASE='single_copy_FULL'
BINDINGS={'guard': {'path': '/workspace/engineering/completed-current8d49-FULL-storage-single-copy-fallback-PREPARATION-v2/guard_readonly.py', 'bytes': 7448, 'sha256': '583e4aff39009b0dce28e25687fe20a270d97540407a778d88f878f97ef628ce', 'mode': '0o444'}, 'config': {'path': '/workspace/engineering/completed-current8d49-FULL-scratch-storage-PREEXECUTION-v1/private-exact-one-completed-FULL-scratch-inputs.json', 'bytes': 9378479, 'sha256': '1ef448b2ee0b2b00462c516a096c858287f5d117d2f43171b9f679c75b9206ee', 'mode': '0o444'}, 'relocation_plan': {'path': '/workspace/engineering/completed-current8d49-FULL-storage-single-copy-fallback-PREPARATION-v2/private-exact-original-partial-relocation-plan.json', 'bytes': 1408, 'sha256': 'e2ca10cd9b5604940edf35ed1d41003a2a146f439dddc1734c7babe5a4112742', 'mode': '0o444'}, 'relocation_module': {'path': '/workspace/engineering/completed-current8d49-FULL-storage-single-copy-fallback-PREPARATION-v2/exact_failed_partial_relocation_v2.py', 'bytes': 6232, 'sha256': '9058cfc3e86ebbc7f8e765d8853a4883f27cebc068f4b08d25e7104c8be3a2bc', 'mode': '0o444'}, 'capture_helper': {'path': '/workspace/engineering/completed8d49-four-root-storage-PREPARATION-v3/guard_capture.py', 'bytes': 3010, 'sha256': '7ce1b282a002fbf03371ba0b1c5ba1684253ee68ffcf234f16e58e7902860c2a', 'mode': '0o444'}, 'existing_alias_resolver': {'path': '/workspace/engineering/completed8d49-five-root-storage-PREPARATION-v4/exact_original_row_archive_aliases.py', 'bytes': 4922, 'sha256': 'fdbe4493f59c0256c4ca63f0da390c71d2a1d6c98dfc9f8d4cc0b5187561712e', 'mode': '0o444'}, 'existing_alias_plan': {'path': '/workspace/engineering/completed8d49-five-root-storage-PREPARATION-v5/private-fixed-nine-original-row-future-archive-member-plan.json', 'bytes': 6966, 'sha256': 'ce099428e2647c6793d3f1d2bc541d5b864c58ebffe40371007cc7d7ac3236e8', 'mode': '0o444'}, 'child': {'path': '/workspace/engineering/completed-current8d49-FULL-storage-single-copy-fallback-PREPARATION-v2/archive_exact_one_completed_FULL_single_copy_once.py', 'bytes': 21276, 'sha256': 'e717faae8a9e5f7a1ccea85c17df928a728216e43bf77256c487e685d9971771', 'mode': '0o444'}, 'promotion_helper': {'path': '/workspace/engineering/completed-current8d49-FULL-storage-single-copy-fallback-PREPARATION-v2/exclusive_single_copy_archive_promotion.py', 'bytes': 1491, 'sha256': '63c8d00d5830672ad4e03d5e5dd811d4735f32bd7ca865ff4c6f63d3c2587a09', 'mode': '0o444'}};CHILD_ARGV=['/usr/bin/timeout', '--signal=TERM', '--kill-after=10s', '600s', '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python', '/workspace/engineering/completed-current8d49-FULL-storage-single-copy-fallback-PREPARATION-v2/archive_exact_one_completed_FULL_single_copy_once.py'];CONFIG=Path('/workspace/engineering/completed-current8d49-FULL-scratch-storage-PREEXECUTION-v1/private-exact-one-completed-FULL-scratch-inputs.json')
MANAGED=Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python');EXPECTED_REVIEW='GO_EXACT_ONE_COMPLETED_FULL_SINGLE_COPY256_STORAGE_PREEXECUTION_V2';EXPECTED_RELEASE='ROOT_ONE_EXACT_COMPLETED_FULL_SINGLE_COPY_STORAGE_RELEASE_V2'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 return {'path':str(p),'bytes':s.st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(s.st_mode))}
def check(row):assert bind(row['path'])==row
def sources():
 for row in BINDINGS.values():check(row)
def write(p,data):
 with Path(p).open('xb') as f:os.fchmod(f.fileno(),0o600);f.write((json.dumps(data,indent=2,sort_keys=True)+'\n').encode());f.flush();os.fsync(f.fileno())
 fd=os.open(Path(p).parent,os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def namespaces():
 check(BINDINGS['guard']);check(BINDINGS['relocation_module'])
 guard={'__name__':'verified_data_guard'};exec(compile(Path(BINDINGS['guard']['path']).read_bytes(),BINDINGS['guard']['path'],'exec'),guard)
 reloc={'__name__':'verified_data_relocation'};exec(compile(Path(BINDINGS['relocation_module']['path']).read_bytes(),BINDINGS['relocation_module']['path'],'exec'),reloc)
 return guard,reloc

def main():
 assert not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE')
 assert sys.argv[1:]==['--root-execute-reviewed-'+PHASE,str(RELEASE)]
 assert Path(sys.prefix).resolve()==MANAGED.parent.parent.resolve()
 os.umask(0o077);assert bind(RELEASE)['mode']=='0o600'
 release=json.loads(RELEASE.read_bytes());assert release['schema']==EXPECTED_RELEASE and release['one_attempt'] is True and release['no_retry'] is True
 assert release['serialized_no_other_selected_root_source_native_or_heavy_mutations'] is True
 assert release['proposal_binding']==bind(PROPOSAL);check(release['independent_review_binding'])
 independent=json.loads(Path(release['independent_review_binding']['path']).read_bytes())
 assert independent['decision']==EXPECTED_REVIEW and independent['proposal_binding']==release['proposal_binding']
 assert release['driver_binding']==bind(Path(__file__)) and release['child_argv']==CHILD_ARGV
 assert release['parent_envelope']=={'timeout_seconds':900,'TERM_kill_after_seconds':10}
 assert release['source']=='8d49d0865ad5ad27b2d4e325ec135212080625e8' and release['tree']=='a80600809d373038ca76e445ba0b7b79bb7eeaa6'
 if PHASE=='relocation':assert release['relocation_plan_binding']==BINDINGS['relocation_plan'] and release['relocation_module_binding']==BINDINGS['relocation_module']
 else:
  row=release['required_relocation_actual_binding'];assert row['path']=='/workspace/engineering/root-one-original-FULL-partial-relocation-owned-v1/original-one-attempt-terminal.json';check(row)
  actual=json.loads(Path(row['path']).read_bytes());assert actual['status']=='PASS_DATA_RELOCATION_ONLY' and actual['protected_post']=='PASS' and actual['child_returncode']==0
 assert not OWNED.exists();OWNED.mkdir(mode=0o700);write(OWNED/'consumed-exact-release.json',release)
 result={'schema':EXPECTED_RELEASE+'_ORIGINAL_TERMINAL','phase':PHASE,'status':'NOT_STARTED','child_returncode':None,'protected_post':'NOT_RUN','native':'NOT_RUN','one_attempt':True,'no_retry':True}
 primary=None;guard=reloc=None
 try:
  sources();guard,reloc=namespaces();config=guard['load_config'](CONFIG)
  before=guard['protected'](config,phase='before',capture_parent=OWNED);write(OWNED/'protected-before.json',before)
  plan=json.loads(Path(BINDINGS['relocation_plan']['path']).read_bytes());reloc['validate_plan'](plan)
  original=reloc['verify_original_or_alias'](plan);write(OWNED/'original-partial-state-before.json',original)
  capacities={m:os.statvfs(m).f_bavail*os.statvfs(m).f_frsize for m in ['/workspace','/tmp','/dev/shm']}
  assert capacities['/workspace']>=16777216
  if PHASE=='relocation':
   assert original['status']=='ORIGINAL_PHYSICAL_EXACT' and not Path(plan['destination_root']).exists()
   assert capacities['/dev/shm']>=plan['original']['bytes']+16777216+134217728
   assert capacities['/tmp']>=16777216+134217728
  else:
   assert original['status']=='EXACT_ORIGINAL_PARTIAL_PHYSICAL_ALIAS_VERIFIED'
   assert capacities['/tmp']>=419430400
   assert not Path('/tmp/actions-completed-current8d49-FULL-scratch-preserved-single-v2').exists() and not Path('/tmp/actions-completed-current8d49-FULL-scratch-stage-single-v2').exists()
   selected=guard['selected_roots'](config);write(OWNED/'selected-FULL-before.json',selected)
  write(OWNED/'fresh-capacity-before.json',capacities);sources()
  with (OWNED/'original-child.stdout.private.log').open('xb') as stdout,(OWNED/'original-child.stderr.private.log').open('xb') as stderr:
   completed=subprocess.run(CHILD_ARGV,cwd='/workspace',env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=stdout,stderr=stderr,check=False,timeout=615)
   stdout.flush();os.fsync(stdout.fileno());stderr.flush();os.fsync(stderr.fileno())
  result['child_returncode']=completed.returncode;write(OWNED/'original-child-terminal.json',{'returncode':completed.returncode,'argv':CHILD_ARGV})
  if completed.returncode:raise subprocess.CalledProcessError(completed.returncode,CHILD_ARGV)
  if PHASE=='single_copy_FULL':assert all(not Path(p).exists() for p in config['roots'].values())
 except BaseException as exc:
  primary=exc;result['status']='FAIL';result['primary_exception_type']=type(exc).__name__
  with (OWNED/'original-primary-traceback.private.log').open('x') as f:os.fchmod(f.fileno(),0o600);f.write(traceback.format_exc());f.flush();os.fsync(f.fileno())
 finally:
  try:
   sources()
   if guard is None:guard,reloc=namespaces()
   config=guard['load_config'](CONFIG);after=guard['protected'](config,phase='after',capture_parent=OWNED);write(OWNED/'protected-after.json',after)
   state=reloc['verify_original_or_alias'](json.loads(Path(BINDINGS['relocation_plan']['path']).read_bytes()));write(OWNED/'original-partial-state-after.json',state)
   result['protected_post']='PASS'
  except BaseException as secondary:
   result['status']='FAIL';result['protected_post']='FAIL';result['secondary_exception_type']=type(secondary).__name__
   with (OWNED/'original-postguard-traceback.private.log').open('x') as f:os.fchmod(f.fileno(),0o600);f.write(traceback.format_exc());f.flush();os.fsync(f.fileno())
   if primary is None:primary=secondary
   elif hasattr(primary,'add_note'):primary.add_note('Protected postguard also failed: '+type(secondary).__name__)
  if primary is None:result['status']='PASS_DATA_RELOCATION_ONLY' if PHASE=='relocation' else 'PASS_DATA_FULL_STORAGE_PRESERVATION_ONLY'
  result['capacity_after']={m:os.statvfs(m).f_bavail*os.statvfs(m).f_frsize for m in ['/workspace','/tmp','/dev/shm']}
  write(OWNED/'original-one-attempt-terminal.json',result)
 if primary is not None:raise primary

if __name__=='__main__':main()
