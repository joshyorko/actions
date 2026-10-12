import ast,datetime,hashlib,json,os,stat,subprocess
from collections import Counter,defaultdict
from pathlib import Path
D=Path('/workspace/engineering/root-failed300-default-cache-preservation-actual');O=Path(__file__).resolve().parent;SOURCE=Path('/home/agent/.robocorp/pkgs')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def check(v):assert bind(v['path'])=={k:v[k] for k in ('path','bytes','sha256')},v['path']
def info(p):
 s=p.lstat();return {'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,'mtime_ns':s.st_mtime_ns,'device':s.st_dev,'inode':s.st_ino,'nlink':s.st_nlink,'allocated_bytes':getattr(s,'st_blocks',0)*512}
def inventory(root):
 out={};pending=[root];assert root.is_dir() and not root.is_symlink()
 while pending:
  base=pending.pop()
  for p in sorted(base.iterdir()):
   s=p.lstat();v=info(p)
   if stat.S_ISDIR(s.st_mode):v.update(kind='directory');pending.append(p)
   elif stat.S_ISREG(s.st_mode):v.update(kind='file',bytes=s.st_size,sha256=sha(p));assert info(p)=={k:x for k,x in v.items() if k not in ('kind','bytes','sha256')}
   elif stat.S_ISLNK(s.st_mode):v.update(kind='symlink',target=os.readlink(p))
   else:raise AssertionError('unexpected type')
   out[str(p.relative_to(root))]=v
 return {'root':info(root),'entries':out}
def norm(i):
 ignored={'device','inode','allocated_bytes','nlink'}
 return {'root':{k:v for k,v in i['root'].items() if k not in ignored},'entries':{n:{k:v for k,v in r.items() if k not in ignored} for n,r in i['entries'].items()}}
def partition(i):
 groups=defaultdict(list)
 for n,r in i['entries'].items():
  if r['kind']=='file':groups[(r['device'],r['inode'])].append(n)
 for paths in groups.values():assert all(i['entries'][n]['nlink']==len(paths) for n in paths)
 return sorted(sorted(v) for v in groups.values() if len(v)>1)
ownerp=D/'OWNERFINAL-root-whole-default-cache-preservation-actual.json';owner=bind(ownerp);assert owner['bytes']==1521 and owner['sha256']=='fdbdc5705b6a15863d3a065e1e6821f4411d2297bb2268eb268946cecbb0ac6c';a=json.loads(ownerp.read_bytes());check(a['authorization']);check(a['private_complete_inventories'])
auth=json.loads(Path(a['authorization']['path']).read_bytes());private=json.loads(Path(a['private_complete_inventories']['path']).read_bytes())
for key in ('proposal','independent_review'):check(auth[key])
assert auth['one_copy'] and auth['preserve_all_existing_cache_bytes'] and auth['no_retry_or_install_or_other_cache_mutation']
originalpath=Path('/tmp/root-failed300-default-cache-readonly-preparation-20261011/complete-source-inventory-and-observed-handles.json');original=bind(originalpath);assert original['bytes']==329237 and original['sha256']=='60943726f5266defefd89dec0dcd7c604009251cf1e80dd5d211a11969e239b6';baseline=json.loads(originalpath.read_bytes());old=baseline['first_inventory'];assert old==baseline['second_inventory']==private['frozen_original']==private['source_before_switch']==private['backup_before_removal']
script=Path('/workspace/engineering/preserve-root-failed300-default-cache-once.py');tree=ast.parse(script.read_bytes());calls=[ast.unparse(n) for n in ast.walk(tree) if isinstance(n,ast.Call)];assert sum(n=='shutil.rmtree(BACKUP)' for n in calls)==1 and 'SOURCE.rename(BACKUP)' in calls and 'SOURCE.symlink_to(DEST, target_is_directory=True)' in calls
assert a['copy_events']==[{'copy_returncode':0,'elapsed_seconds':1.17353110100521}] and a['elapsed_seconds']==5.663243384005909 and a['elapsed_seconds']<600
assert (D/'copy.stdout.private.log').stat().st_size==(D/'copy.stderr.private.log').stat().st_size==0
DEST=Path(a['physical_destination']);BACKUP=Path(a['removed_only_verified_expanded_backup']);PARENT=DEST.parent
assert str(DEST)=='/dev/shm/actions-root-failed300-default-cache-preservation-20261011/pkgs' and str(BACKUP)=='/home/agent/.robocorp/pkgs.actions-failed300-preserved-backup-20261011'
assert SOURCE.is_symlink() and os.readlink(SOURCE)==str(DEST) and SOURCE.resolve(strict=True)==DEST.resolve(strict=True) and not os.path.lexists(BACKUP)
assert stat.S_IMODE(PARENT.stat().st_mode)==0o700 and stat.S_IMODE(Path(a['private_complete_inventories']['path']).stat().st_mode)==0o600
physical=inventory(DEST);logical=inventory(SOURCE.resolve(strict=True));assert norm(physical)==norm(logical)==norm(old)==norm(private['physical'])==norm(private['logical']) and partition(physical)==partition(logical)==partition(old)==[]
assert len(physical['entries'])==416 and Counter(r['kind'] for r in physical['entries'].values())=={'file':362,'directory':38,'symlink':16}
assert sum(r['bytes'] for r in physical['entries'].values() if r['kind']=='file')==1132159923
for h in [auth['pre_handles'],private['pre_handles'],private['post_copy_handles'],*private['last_handles'].values()]:assert not h['matches']
assert a['observed_handle_limits']=='Observed /proc cwd and fd symlink targets only; not a complete process/maps or historical handle census'
failed=Path('/workspace/engineering/pr300-current74-owner-full-contract-adoption/current74-one-reviewed-configured-full-terminal.json');terminal=json.loads(failed.read_bytes());check(terminal['log']);assert terminal['returncode']==4 and terminal['log']['sha256']=='38029425f98c3416b3dd8ad82a90f9ca96ba2e2f1818e9024286854a61bdf684'
assert sha(failed)=='27fcafcea7a3c1942717517ab97812b8586762bfa6cbeed701f7e12c549688fc'
R=Path('/workspace/engineering/pr300');g=lambda *argv:subprocess.check_output(['git',*argv],cwd=R)
assert g('rev-parse','HEAD').decode().strip()==terminal['head'] and g('rev-parse','HEAD^{tree}').decode().strip()==terminal['tree'] and not g('status','--porcelain')
sourceproof=Path('/workspace/engineering/pr300-issue86-assembled-transport-source-successor/immutable-current74-complete1423-Git-FS-mode-bindings.json');rows=json.loads(sourceproof.read_bytes())['all1423'];assert len(rows)==1423
for row in rows:
 p=R/row['path'];b=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'];assert row['mode']=='120000' or bool(p.stat().st_mode&0o111)==(row['mode']=='100755')
adoption=Path('/workspace/engineering/pr300-current74-owner-full-contract-adoption/OWNERFINAL-current74-reviewed-full-command-adoption-and-execution-HOLD.json');assert sha(adoption)=='17c61faa68cbdfe2daf6915335cc2a93ccd67328dbdf34c2cb2455963ad35eca';adopt=json.loads(adoption.read_bytes())
for v in adopt['all_distinct_original_and_LIGHT_reference_bindings_verified']:check(v)
prep=json.loads(Path(adopt['prepared_inputs']['record']['path']).read_bytes())
for n,h in prep['all30_current_inputs_exact_prepared_Git_bytes'].items():assert sha(R/n)==h
for n,r in prep['five_own_environment_configs'].items():assert sha(R/n/'.venv/pyvenv.cfg')==r['config_sha256'] and str((R/n/'.venv/bin/python').resolve())==r['python_resolved']
for v in adopt['prepared_inputs']['five_concrete_source_origins']:check(v)
fixture=adopt['prepared_inputs']['ignored_pinned_RCC'];assert sha(R/fixture['path'])==fixture['sha256'] and stat.S_IMODE((R/fixture['path']).stat().st_mode)==int(fixture['mode'],8)
check(adopt['prepared_inputs']['managed_gateway'])
# Do-not-touch paths have no complete historical inventory in this narrow move; report existence only.
protected_exists={n:Path(n).exists() for n in ['/home/agent/.robocorp/temp/dcdb2bb109728a05','/home/agent/.robocorp/holotree','/workspace/actions-cloud/robocorp','/workspace/engineering/pr282']}
assert protected_exists['/home/agent/.robocorp/temp/dcdb2bb109728a05'] and protected_exists['/workspace/actions-cloud/robocorp']
canonical=Path('/workspace/engineering/root-failed300-default-cache-readonly-preparation/canonical-exact-launcher-managed-RCC-home-preflight-proposed.patch');assert sha(canonical)=='811befd4b06df317ddfaee02dca3d5418568840183ecfb0ddc9e7d087fb89a6e'
proof_digest=hashlib.sha256(json.dumps(norm(physical),sort_keys=True,separators=(',',':')).encode()).hexdigest()
result={'verdict':'GO_ACTUAL_WHOLE_CACHE_PRESERVATION_AND_CAPACITY_RECOVERY_ONLY','owner':owner,'authorization':a['authorization'],'root_transaction_script':bind(script),'reviewed_at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_logical_symlink_exact':{'source':str(SOURCE),'target':str(DEST),'verified':True},'complete_current_physical_and_logical_inventory':{'entries':416,'files':362,'directories':38,'symlinks':16,'regular_bytes':1132159923,'root_and_all_member_mode_uid_gid_mtime_and_symlink_target_sha_sizes_exact':True,'normalized_complete_inventory_SHA256':proof_digest,'internal_hardlink_partitions':[],'external_hardlink_candidates':0,'private_actual_inventory_binding':a['private_complete_inventories'],'private_original_frozen_inventory_unchanged':original},'removed_backup':{'path':str(BACKUP),'absence_verified':True,'original_before_switch_and_backup_before_removal_exact_frozen':True,'only_one_named_shutil_rmtree_target_verified_in_script':True},'source1423_and_all_old_LIGHT_refs_prepared30_five_cfg_origins_managedRCC_preserved':True,'do_not_touch_observed_exists_only':protected_exists,'do_not_touch_limits':'No complete unbaselined historical unchanged claim for defaulttemp/holotree/managedhome; original source/input/ref contracts separately rehashed exactly. Root script mutates only revieweddefaultpkgspath, ownedphysicalcopy/privateproof and uniqueexpandedbackup.', 'actual_copy_returncode':0,'actual_transaction_seconds':a['elapsed_seconds'],'bound_scope':'Observed complete transaction5.663s within600; copy uses600TERM+10 and subprocess615. Verification has no separate universal walltime guarantee; do not transfer this actual timing to a future gate or move.','capacity':{'root_before_bytes':a['overlay_free_before'],'root_after_bytes':a['overlay_free_after'],'current_workspace_available_bytes_observation':os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize,'reservation_or_gate_release':False},'process_limits':'Recorded accessible cwd/fd matcheszero, with permissions/transient/maps/externalusers limitations. Root controlled known teamdefaultusersnone; no global quiescence, atomic directoryexchange or inode/device/allocatedblock/ACL/xattr/atime/ctime equality claim.','original300_full_FAILURE_preserved':{'terminal':bind(failed),'rawlog':terminal['log'],'returncode':4,'pytest_admission':False},'remaining_HOLD':['FutureRCC RED/corrected300 full each need concrete same-launcher managedhome preconditions plus distinctroot release/serialization; preservation GO alone authorizes no gate','No current300fullPASS/push/currentCI/sourcefix/native/private/provider/browser/publication admission','Existingdevshm retention is runtime workspace preservation; no new infrastructure or historicalownership/new-onlyGC claim'], 'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md','Exact_delta':bind(canonical),'Disposition':'Existing independently accepted exact7content-line811bef managedhome preflight correction remains sufficient; verified actualmove does not need duplicate transaction diary prose.','Durable_learning_captured':'Preserve entireunknown-history cache and logicalpath before capacityreuse; executableidentity and exactlauncherenvironmenthome remain separate gate prerequisites.','Evidence':'Originalwhole416 inventory rederived; actualphysical/logical/rootmetadata/body/topology exact; originalRCC4 log/current1423 refs unchanged.','Stale_or_ambiguous_guidance_removed':'Capacityrecovery doesnot convert setupfailure into testPASS; observedhandles/cross-mount physicalfacts remain qualified.','Remaining_uncertainty':'Futuremanagedsourcefull and private/native/platform/release gates still absent.'},'upstream_disposition':'none','review_actions':'Read-only stdlib AST/Git/hash/lstat/inventory; no copy/deletion/gate/download/source mutation','immutable_constructor':bind(__file__)}
out=O/'OWNERFINAL-independent-actual-whole-default-cache-preservation-review.json';assert not out.exists();out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');out.chmod(0o600);print(json.dumps(bind(out)))
