from pathlib import Path
import ast,copy,difflib,hashlib,json,os,stat,subprocess
O=Path(__file__).resolve().parent;OLD=Path('/workspace/engineering/pr305-current5306-SOURCEFULL-preexecution');L=Path('/workspace/engineering/pr305-current-a54-source-LIGHT');R=Path('/workspace/engineering/pr305')
os.umask(0o077)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def check(row):
 observed=bind(row['path'])
 for key in ['bytes','sha256','mode']:assert observed[key]==row[key]
def save(name,d):
 p=O/name;assert not p.exists();p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');p.chmod(0o600);return bind(p)
def git(*args,cwd=R):return subprocess.check_output(['git','-C',str(cwd),*args],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),stderr=subprocess.PIPE)
original=OLD/'OWNERFINAL-current5306-managed-configured-SOURCEFULL-preexecution-proposal.json';metadata=OLD/'OWNERFINAL-current5306-managed-configured-SOURCEFULL-preexecution-subject-metadata-v2.json';full=json.loads(original.read_text());meta=json.loads(metadata.read_text());cfgold=json.loads((OLD/'frozen-current-source-full-inputs.json').read_text());assert sha(original)=='fbdaba2989e187ad11547f56ff0107092a479d4592aaa48b9170cc7a2339e553'and sha(metadata)=='0993125d3ea8c732a7f851e5d3c20df5f71aa1e318bc887c449c1bfd1f9ee623'
for row in full['frozen_input_bindings']:check(row)
original_bindings=[bind(original),bind(metadata),bind(OLD/'frozen-current-source-full-inputs.json')]+[bind(OLD/n)for n in ['current_source_full_body.py','current_source_prepost_guard.py','launch_current_source_full_once.py']]
assert cfgold['head']=='5306eeb26595da4ce571b99812eb50f047cfc903'and cfgold['tree']=='8418e9ffeeaaf2446771e34b5b4602bab3d357a5';assert not Path(cfgold['source_inventory']).exists()and not (OLD/'one-configured-full-once-owned').exists()
correct=L/('private-current-'+cfgold['head'][:4]+'-complete-source-body-mode-inventory.json');assert correct.is_file()and not correct.is_symlink()
implementation=[]
for name in ['current_source_full_body.py','current_source_prepost_guard.py','launch_current_source_full_once.py']:
 p=O/name;assert not p.exists();p.write_bytes((OLD/name).read_bytes());p.chmod(0o600);compile(p.read_bytes(),str(p),'exec');assert p.read_bytes()==(OLD/name).read_bytes();implementation.append(bind(p))
cfg=copy.deepcopy(cfgold);cfg['source_inventory']=str(correct);cfg['implementation_bindings']=implementation
comparison=copy.deepcopy(cfg);comparison['source_inventory']=cfgold['source_inventory'];comparison['implementation_bindings']=cfgold['implementation_bindings'];assert comparison==cfgold
source=cfg['head'];tree=cfg['tree'];assert git('rev-parse','HEAD','HEAD^{tree}').decode().splitlines()==[source,tree]and git('status','--porcelain')==b''
# Validate all file/directory dependencies consumed by launcher/before/after/body,
# including configuration-only paths that are absent from top-level binding lists.
closure=[]
def existing(p,kind):
 p=Path(p);assert p.is_dir()if kind=='directory'else p.is_file();closure.append({'path':str(p),'kind':kind,'resolved':str(p.resolve())})
existing(cfg['source_root'],'directory');existing(R/'developer','directory');existing(R/'developer/toolkit.py','file');existing(R/'action_server','directory');existing(R/'action_server/.venv/bin/python','file');existing(Path(cfg['cached_toolkit_prefix'])/'bin/python','file')
for row in [cfg['source_LIGHT'],*cfg['implementation_bindings'],*cfg['prepared_environment_and_RCC_bindings'],*cfg['retained_actual_files_and_helpers']]:check(row);existing(row['path'],'file')
light=json.loads(Path(cfg['source_LIGHT']['path']).read_text());assert light['source']['commit']==source and light['source']['tree']==tree
for row in light['frozen_bindings']:check(row);existing(row['path'],'file')
rows=json.loads(correct.read_text());assert len(rows)==1427;assert len({row['path']for row in rows})==1427
tracked={}
for entry in git('ls-tree','-rz','HEAD').split(b'\0'):
 if entry:
  header,path=entry.split(b'\t');mode,kind,blob=header.decode().split();tracked[path.decode()]=(mode,kind,blob)
assert set(tracked)=={row['path']for row in rows}
for row in rows:
 p=R/row['path'];body=os.readlink(p).encode()if row['mode']=='120000'else p.read_bytes();assert hashlib.sha256(body).hexdigest()==row['sha256']and stat.S_IMODE(p.lstat().st_mode)==row['fs_mode'];assert tracked[row['path']]==(row['mode'],row['kind'],row['blob']);assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==row['blob']
for path,digest in cfg['prepared30_inputs'].items():assert sha(R/path)==digest;existing(R/path,'file')
assert len(cfg['prepared30_inputs'])==30
origins=[]
for package,module in cfg['concrete_origin_packages']:
 p=L/('own-origin-'+package+'.json');existing(p,'file');measured=json.loads(p.read_text());assert measured['module']==module and Path(measured['prefix']).resolve()==(R/package/'.venv').resolve()and Path(measured['origin']).resolve().is_relative_to((R/package/'src').resolve());existing(measured['origin'],'file');existing(measured['python'],'file');existing(R/package/'.venv','directory');existing(R/package/'src','directory');origins.append({'package':package,'module':module,'origin_evidence':bind(p),'scope':'Existing LIGHT-measured origin/prefix and current path existence; no fresh import/gateway executed.'})
for row in cfg['historical_original_Git_bodies']:
 existing(row['repository'],'directory');body=git('show',row['source']+':'+row['Git_path'],cwd=Path(row['repository']));assert len(body)==row['bytes']and hashlib.sha256(body).hexdigest()==row['sha256']
existing(cfg['original_native_config'],'file');baseline=json.loads(Path(cfg['original_native_config']).read_text());native=Path(baseline['native_original_root']);existing(native,'directory');assert len(baseline['native_original_members'])==1192
for row in baseline['native_original_members']:
 p=native/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert p.is_file()and not p.is_symlink()and sha(p)==row['content_sha256']
 elif row['kind']=='directory':assert p.is_dir()and not p.is_symlink()
 else:assert p.is_symlink()and os.readlink(p)==row['link_target']
assert {p.relative_to(native).as_posix()for p in native.rglob('*')}=={r['path']for r in baseline['native_original_members']}
assert len(cfg['expected_activation_exports'])==18 and cfg['expected_activation_exports']['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2';assert full['execution_bounds']==meta['execution_bounds'];assert cfg['capacity_floor_bytes']==1288490188
configbinding=save('frozen-current-source-full-inputs.json',cfg)
# Existing scripts dynamically read their own directory; literal packet filenames
# are checked before freezing the proposal. Body/configured task remains untouched.
for name in ['current_source_full_body.py','current_source_prepost_guard.py','launch_current_source_full_once.py']:
 literals={n.value for n in ast.walk(ast.parse((O/name).read_bytes()))if isinstance(n,ast.Constant)and isinstance(n.value,str)};assert 'frozen-current-source-full-inputs.json'in literals
assert 'OWNERFINAL-current5306-managed-configured-SOURCEFULL-preexecution-proposal.json'in {n.value for n in ast.walk(ast.parse((O/'launch_current_source_full_once.py').read_bytes()))if isinstance(n,ast.Constant)}
assert not (O/'one-configured-full-once-owned').exists()and not (O/'one-configured-full-once-owned').is_symlink()
proofbinding=save('typed-config-consumed-path-and-complete-source-native-dependency-closure-v3.json',{'status':'READ_ONLY_TYPED_CONSTRUCTOR_GUARD_PASS_NO_EXECUTION','source':source,'tree':tree,'only_config_semantic_delta':'source_inventory: nonexistent copied1299 filename replaced by exact measured5306 inventory; implementation binding paths follow named copied identical scripts.','wrong_original_inventory':cfgold['source_inventory'],'wrong_original_inventory_still_absent':True,'correct_inventory':bind(correct),'all1427_current_source_typed_Git_FS_hash_modes_exact':True,'all1192_original_native_body_mode_member_set_exact':True,'prepared30_exact':True,'five_existing_LIGHT_origin_prefix_path_evidence':origins,'file_directory_closure':list({row['path']:row for row in closure}.values()),'scripts_all_original_bytes_exact':implementation,'activation_exports':18,'primary_PATH_guard':19,'execution_bounds':full['execution_bounds'],'existing_original_once_directory_absent':True,'new_once_directory_absent':True,'scope':'No pre/post/body or launcher execution; no package/module imports, gateways, tests, installer or native execution. Root must recheck current source/origins/capacity at actual release.'})
# Proposed durable lesson; no canonical source write in this private correction.
guide=R/'docs/skills/repository-operations.md';text=guide.read_text();anchor='after a gate starts from evidence checked before that gate.\n';assert text.count(anchor)==1
addition='\nBefore adopting a frozen command packet, verify every file path consumed by its\nconstructor, launcher, guards and body, including paths stored only in its\nconfiguration. Hashing the listed bindings does not prove that a separately\nnamed source inventory exists or belongs to the intended commit and tree.\nPreserve a rejected packet and use a named successor with a checked dependency\nclosure; do not backfill a copied filename or relabel the earlier packet.\n'
patch=''.join(difflib.unified_diff(text.splitlines(True),text.replace(anchor,anchor+addition).splitlines(True),fromfile='a/docs/skills/repository-operations.md',tofile='b/docs/skills/repository-operations.md'));patchpath=O/'canonical-config-consumed-path-dependency-closure-proposed.patch';assert not patchpath.exists();patchpath.write_text(patch);patchpath.chmod(0o600)
proposal=copy.deepcopy(meta);proposal.pop('subject_metadata_correction');proposal['status']='OWNERFINAL_CURRENT5306_NAMED_SOURCE_INVENTORY_CORRECTED_EXECUTABLE_PREEXECUTION_READY_FOR_REVIEW_NOT_RUN';proposal['configured_full_argv']=[str(O/'current_source_full_body.py')if x==str(OLD/'current_source_full_body.py')else x for x in proposal['configured_full_argv']];proposal['outer_managed_command']=[s.replace(str(OLD),str(O))for s in proposal['outer_managed_command']];proposal['one_attempt']['owned_output_directory']=str(O/'one-configured-full-once-owned');proposal['frozen_input_bindings']=[configbinding,cfg['source_LIGHT'],bind(__file__),*implementation,*cfg['prepared_environment_and_RCC_bindings'],bind('/workspace/actions-cloud/activate.sh'),proofbinding,bind(patchpath),*original_bindings]
proposal['inventory_path_correction']={'original_executable_HOLD':bind(original),'original_metadata_only_HOLD':bind(metadata),'original_config_binding':original_bindings[2],'original_scripts_preserved':original_bindings[3:],'unchanged_current_SOURCE_LIGHT_subject_successor':bind(L/'OWNERFINAL-current5306-ordinary-a54-source-LIGHT-subject-metadata-v2.json'),'exact_change':'Only source_inventory corrected to measured source5306 filename plus named-directory self-binding paths/metadata. Scripts copied byte-exact; source/control/pins/commands/tasks/guards/bounds unchanged.','original_missing1299_inventory':'NOT_BACKFILLED','no_original_attempt_consumed':True,'dependency_closure_proof':proofbinding,'new_launcher_root_release_hash':'This new OWNERFINAL digest, distinct ROOTrelease after independent GO and serialization/capacity; old fbdaba hash remains old rejected contract only.'}
proposal['documentation_improvement']={'canonical_file_proposed':'docs/skills/repository-operations.md','exact_delta':bind(patchpath),'durable_learning':'Resolve every configuration-consumed file path against the exact current source tuple; a list of valid hash-bound files does not validate omitted dependency strings.','evidence':{'original_wrong_inventory':cfgold['source_inventory'],'correct_inventory':bind(correct),'typed_dependency_closure':proofbinding},'stale_ambiguity_removed':'Copied1299 source inventory could remain unchecked despite correct5306 header/argv/top-level file bindings. Original rejected metadata stays unchanged; named executable successor is explicit.','remaining_uncertainty':'No full gate, pre/post/body command or fresh origin import executed; independent review, distinct ROOTrelease/serialization/fresh capacity remain required.'}
proposal['retained_unannounced_v3_constructor_draft']={'proposal':bind('/workspace/engineering/pr305-current5306-SOURCEFULL-preexecution-executable-v3/OWNERFINAL-current5306-managed-configured-SOURCEFULL-preexecution-proposal.json'),'constructor':bind('/workspace/engineering/pr305-current5306-SOURCEFULL-preexecution-executable-v3/construct_and_validate_named_inventory_successor_v3.py'),'status':'HOLD_CONSTRUCTOR_REVIEW_BEFORE_ANNOUNCEMENT_NO_EXECUTION','reason':'Final constructor-only ternary assertion inadvertently constant-true; earlier complete typed/source/native checks passed but namedV4 replaces this with explicit inventory-path and proof-binding equality. No launcher/guard/body or source change.'}
p=O/'OWNERFINAL-current5306-managed-configured-SOURCEFULL-preexecution-proposal.json';ownerbinding=save(p.name,proposal)
for row in proposal['frozen_input_bindings']:check(row)
assert cfg['source_inventory']==str(correct)
assert bind(correct)==json.loads(Path(proofbinding['path']).read_text())['correct_inventory']
for row in original_bindings:check(row)
assert not Path(cfgold['source_inventory']).exists()and git('status','--porcelain')==b''
print(json.dumps({'OWNERFINAL':ownerbinding,'source':source,'tree':tree,'source_leaves':1427,'native_members':1192,'closure_paths':len(closure),'scripts_copied_byte_exact':3,'source_inventory':bind(correct),'execution':'NOT_RUN','workspace_available_bytes':os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize}))
