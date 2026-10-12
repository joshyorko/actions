import ast, collections, hashlib, json, os, shutil, stat, subprocess, time
from pathlib import Path
OUT=Path('/workspace/engineering/capacity-recovery-batch25-proposal')
BASE=Path('/workspace/actions-cloud/robocorp/temp')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def save(n,x):
 p=OUT/n
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
 p.chmod(0o600);return bind(p)
census=json.loads((OUT/'private-complete-completed-candidate-metadata-census.json').read_text());assert census['prior_archive_count']==50
name=census['selected']['name'];root=BASE/name;assert name!='563d911e4172f035' and name not in census['excluded_names_private']
parent=Path('/tmp/actions-capacity-recovery-batch19.py');assert sha(parent)=='48fd7e4c79e55b80ceda0b63c1d1da87feeb368cefee265d5c12bad6ad940840'
script=Path('/tmp/actions-capacity-recovery-batch25.py');text=parent.read_text().replace("actions-completed-scratch-recovery-batch19","actions-completed-scratch-recovery-batch25").replace("['c3b676a701cf3ae2']",repr([name]));assert script.read_text()==text;script.chmod(0o600)
def norm(s):
 return [ast.dump(x,include_attributes=False) for x in ast.parse(s).body if not(isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'DEST','STAGE','NAMES'} for t in x.targets))]
assert norm(text)==norm(parent.read_text()) and len(norm(text))==16
assert not Path('/dev/shm/actions-completed-scratch-recovery-batch25').exists() and not Path('/tmp/actions-completed-scratch-recovery-batch25-stage').exists()
# Load only original pure definitions, never imports/config/main or any archival/removal code.
ns={'hashlib':hashlib,'stat':stat,'os':os,'Path':Path};defs=[x for x in ast.parse(parent.read_text()).body if isinstance(x,ast.FunctionDef) and x.name in {'sha','inventory'}];exec(compile(ast.Module(body=defs,type_ignores=[]),'accepted-pure-inventory-only','exec'),ns)
def handles():
 x={'processes':0,'accessible_links_read':0,'unreadable_or_transient':0,'candidate_path_matches_private':[]}
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  x['processes']+=1;links=[proc/'cwd']
  try:links+=list((proc/'fd').iterdir())
  except (OSError,PermissionError):x['unreadable_or_transient']+=1
  for l in links:
   try:t=os.readlink(l);x['accessible_links_read']+=1
   except OSError:x['unreadable_or_transient']+=1;continue
   if t==str(root) or t.startswith(str(root)+'/'):x['candidate_path_matches_private'].append({'pid':proc.name,'link':str(l),'target':t})
 assert not x['candidate_path_matches_private'];return x
assert root.is_dir() and not root.is_symlink() and (root/'recycle.now').read_text().strip()=='True'
firsth=handles();first=ns['inventory'](root);second=ns['inventory'](root);secondh=handles();assert first==second
assert (root/'recycle.now').read_text().strip()=='True'
invbind=save('private-complete-candidate-two-stable-inventories-v2.json',{'original_namespace':str(root),'first':first,'second':second,'two_full_body_mode_mtime_uidgid_type_link_snapshots_equal':True})
handlebind=save('private-accessible-process-cwd-FD-before-after-v2.json',{'first':firsth,'second':secondh,'scope':'Only no observed accessible cwd/FD matches; permission/transient errors remain UNKNOWN, no universal quiescence or historical reader/reaping claim.'})
# Current prior originals independently rehash against complete recorded recovery indices; do not extract archives.
idxs=sorted(set(Path('/tmp').glob('actions-completed-scratch-recovery*/private-complete-inventory-and-recovery.json'))|set(Path('/dev/shm').glob('actions-completed-scratch-recovery*/private-complete-inventory-and-recovery.json')))
assert len(idxs)==24
prior=[];ibs=[]
for idx in idxs:
 ibs.append(bind(idx));x=json.loads(idx.read_text())
 for r in x['records']:
  p=Path(r['archive']);assert p.is_file() and p.stat().st_size==r['archive_bytes'] and sha(p)==r['archive_sha256']
  assert stat.S_IMODE(p.stat().st_mode)==0o600
  assert r['expanded_removed'] is True and not Path(r['original_namespace']).exists()
  prior.append({'archive':str(p),'bytes':r['archive_bytes'],'sha256':r['archive_sha256'],'mode':0o600,'prior_original_expanded_removed_record_retained':True})
assert len(prior)==50
priorbind=save('private-prior50-original-archives24-indices-current-hash-retention-v2.json',{'archives':prior,'indices':ibs,'no_archive_extraction_or_recovery_execution':True})
# Parent/terminal/current source proof boundaries; all raw logs remain private.
ownerpath=Path('/workspace/engineering/pr312-actual300-refresh-configured-full-once-owned-v2/OWNERFINAL-root-current312-ec70-configured-SOURCEFULL.json');owner=json.loads(ownerpath.read_text());assert owner['all_primary_and_postguard_returncodes']==0 and owner['counts']=={'PASSED':1335,'SKIPPED':13,'FAILED':0,'ERROR':0}
ownerbindings=[]
for b in owner['bindings']:
 assert bind(b['path'])==b;ownerbindings.append(b)
rawpath=Path('/workspace/engineering/pr312-actual300-refresh-configured-full-once-owned-v2/original-configured-full.private.log');raw=rawpath.read_bytes();assert len(raw)==346188 and sha(rawpath)=='2e2da108608f75625f88a7328ed7be1cfa166b85f76203697f48dbfab6588762'
assert str(root).encode() not in raw
work=Path('/workspace/engineering/runtime-checkout-eol');head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=work,text=True).strip();tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=work,text=True).strip();assert head==owner['head'] and tree==owner['tree'];assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=work)
source=[]
for line in subprocess.check_output(['git','ls-tree','-r','-z','HEAD'],cwd=work).split(b'\0'):
 if not line:continue
 prefix,p=line.split(b'\t',1);mode,kind,oid=prefix.decode().split();assert kind=='blob';relative=os.fsdecode(p);body=subprocess.check_output(['git','cat-file','blob',oid],cwd=work);f=work/relative
 if mode=='120000':assert f.is_symlink() and os.fsencode(os.readlink(f))==body
 else:assert f.is_file() and f.read_bytes()==body and bool(f.stat().st_mode&0o111)==(mode=='100755')
 source.append({'path':relative,'mode':mode,'git_blob':oid,'sha256':hashlib.sha256(body).hexdigest()})
sourcebind=save('private-current312-source-Git-FS-complete-body-and-exec-modes.json',{'head':head,'tree':tree,'entries':source})
failed=BASE/'563d911e4172f035';assert failed.is_dir()
v5=Path('/workspace/actions-cloud/receipts/pr305-runner/published-core-rcc-consumer-v5.py')
# Resolve the previously frozen V5 runner binding from original scoped proof, never invent pathname or baseline.
failedinputs=Path('/workspace/engineering/rcc-control3-failed-owned-preservation-proposal/frozen-preservation-inputs-v3.json');fi=json.loads(failedinputs.read_text())
fi_binding=bind(failedinputs)
patch=Path('/workspace/engineering/capacity-recovery-independent-review/canonical-completed-scratch-preservation-proposed.patch');assert sha(patch)=='7d07065b5bb7742698919997c8c6621cc20d00494741eb5365251ffb09f2d208'
# The canonical paragraph is already imported; check its literal added content still exists.
added=[l[1:] for l in patch.read_text().splitlines() if l.startswith('+') and not l.startswith('+++') and l[1:].strip()]
guide=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text();assert all(l in guide for l in added)
meta={'schema':'capacity-batch25-owner-preexecution-proposal-v1','decision':'SCRIPT_PREPARATION_ONLY_INDEPENDENT_REVIEW_AND_ROOT_ONE_RELEASE_REQUIRED','script':bind(script),'algorithm_parent':bind(parent),'all16_nonconfiguration_AST_exact_parent':True,'only_configuration_changes':['DEST','STAGE','NAMES'],'names_exact_allowlist':[name],'destination':'/dev/shm/actions-completed-scratch-recovery-batch25','unused_new_stage':'/tmp/actions-completed-scratch-recovery-batch25-stage','destination_stage_absent':True,'completed_marker_True_before_after':True,'largest_completed_by_fresh_measured_allocated_blocks':census['selected'],'completed_candidates_measured':len(census['completed_candidates_private']),'all_prior50_archive_names_and_failed563_excluded':True,'complete_candidate_recorded_members':len(first),'two_full_candidate_body_mode_mtime_uidgid_type_symlink_inventories_equal':True,'fresh_accessible_handle_observations':[firsth,secondh],'source_origin':'UNREPORTED','original_current312_log_exact_owned_namespace_occurrences':0,'source_origin_scope':'No newest/mtime or marker attribution; ROOT1335/13 source-full is separately retained, not an origin proof or native qualification.','root_current312_source_full_owner':bind(ownerpath),'root_current312_original_full_bindings':ownerbindings,'current312_Git_FS_source_entries':len(source),'current312_head':head,'current312_tree':tree,'current312_tracked_clean':True,'prior50_archives24_indices_current_recorded_SHA_size_mode_exact':True,'failed563_original_exists_excluded':True,'frozen_failed_control3_native1192_helpers0444_sourceguard_inputs_reference_only':fi_binding,'failed_control3_original_status':'FAIL_HOLD_UNCHANGED; v3 failed preservation remains separate NOT_RUN proposal','private_proof_bindings':[bind(OUT/'private-complete-completed-candidate-metadata-census.json'),invbind,handlebind,priorbind,sourcebind],'workspace_free_bytes_observation':shutil.disk_usage('/workspace').free,'existing_shm_free_bytes_observation':shutil.disk_usage('/dev/shm').free,'root_proposed_exact_argv':['timeout','--signal=TERM','--kill-after=10s','600s','/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python',str(script)],'execution_prerequisites':['Independent immutable proposal/script review followed by distinct ROOT ONE release; no other heavy/shared scratch mutation active','Fresh markerTrue and no observed accessible cwd/FD matches before original full inventory and after verified archive/full reinventory before only named expanded removal','Exact original complete index saved0600 before removal; archive0600; all member bodies/sizes/modes/UIDGID/type/links resolved and full inventory unchanged','All original prior50 archives/24 indices and source/native/helper/failed roots preserved; root before/after guards separately required','Post capacity is freshly measured, never presumed: source-full floor1200000000B; cold floor1288490189B; separate release and strict policies apply'],'NOT_RUN':True,'limitations':['Only accessible /proc cwd/FD observations; unreadable/transient/map/external actor scope UNKNOWN, not universal quiescence','Complete archive verification/removal belongs future root execution and separate actual reviewer; proposal is not recovered capacity','Accepted exact profile records expanded mtime_ns but does not verify precise TAR ns mtime, ACL/xattrs/inode/rootmetadata','No source suite/native/provider/browser/consumer/issue/release acceptance or failed state relabeling','Current source-volume increase cannot be guaranteed from allocated-block estimate'],'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md exact imported 7d070 paragraph accepted unchanged','Exact_delta_or_reuse':bind(patch),'Durable_learning_captured':'Recorded body/mode/UIDGID/link archive evidence and a repeated full inventory and accessible handle check precede only the explicitly named completed scratch removal. Capacity and source origin remain separate evidence.','Evidence':[bind(script),bind(parent),invbind,handlebind,priorbind],'Stale_or_ambiguous_guidance_removed':'No source-origin inference from mtime/marker or cleanup/acceptance claim from fresh accessible-handle absence. Existing verified paragraph already carries the durable rule; no cosmetic duplicate.','Remaining_uncertainty':'No archive/removal executed; independent review and root release required, universal handle scope unknown, recovered capacity unmeasured.'},'Upstream_disposition':'none','retained_metadata_construction_failure':{'constructor':bind(OUT/'finalize-readonly-proposal.py'),'reason':'Guessed nonexistent /workspace/engineering/pr312 failed after read-only inventory/retention proofs, before OWNERFINAL. Corrected v2 derives existing cwd from authenticated root proposal. No archive or expanded removal executed.'},'constructor':bind(__file__)}
p=OUT/'OWNERFINAL-batch25-exact-one-completed-preexecution-proposal.json';assert not p.exists();p.write_text(json.dumps(meta,indent=2)+'\n');p.chmod(0o400)
print(json.dumps({'proposal':bind(p),'script':bind(script),'members':len(first),'prior_archive_count':len(prior),'prior_indices':len(idxs),'source_entries':len(source),'first_accessible_match_count':len(firsth['candidate_path_matches_private']),'second_accessible_match_count':len(secondh['candidate_path_matches_private']),'workspace_free':meta['workspace_free_bytes_observation'],'shm_free':meta['existing_shm_free_bytes_observation'],'decision':meta['decision']}))
