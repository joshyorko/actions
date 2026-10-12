import ast,hashlib,json,os,pathlib,stat,subprocess
B=pathlib.Path('/workspace/engineering/pr307-currente2-concrete-LIGHT-PREEXECUTION')
OUT=pathlib.Path('/workspace/engineering/pr307-current2314-concrete-LIGHT-independent-review')
ROOT=pathlib.Path('/workspace/engineering/pr307')
def sha(b):return hashlib.sha256(b).hexdigest()
def binding(p):
 p=pathlib.Path(p);m=p.lstat();assert stat.S_ISREG(m.st_mode) and not p.is_symlink();b=p.read_bytes()
 return {'path':str(p),'bytes':len(b),'sha256':sha(b),'mode':oct(stat.S_IMODE(m.st_mode))}
def exact(r):
 a=binding(r['path']);assert all(a[k]==r[k] for k in ('bytes','sha256','mode'));return a
owner=binding(B/'OWNERFINAL-current2314-concrete-LIGHT-PREEXECUTION.json');assert owner['sha256']=='6d1ad9685a70707b18b059be186a383eb49893fd35824e6cbaee729f855ba9eb'
d=json.loads(pathlib.Path(owner['path']).read_bytes());refs=[owner]
for k in ('launcher','config','controlled_staged_Invoke','constructor','activation','source_union_owner'):refs.append(exact(d[k]))
cfg=json.loads(pathlib.Path(d['config']['path']).read_bytes());refs.extend(exact(r) for r in cfg['bindings'])
proof=json.loads(pathlib.Path(cfg['source_proof']['path']).read_bytes());typed=proof['all_git_FS_body_and_exec_mode_exact'];assert len(typed)==1442
for r in typed:
 p=ROOT/r['path'];m=p.lstat()
 if r['mode']=='120000':assert stat.S_ISLNK(m.st_mode);raw=os.readlink(p).encode()
 else:assert stat.S_ISREG(m.st_mode);raw=p.read_bytes();assert bool(m.st_mode&0o111)==(r['mode']=='100755')
 assert len(raw)==r['bytes'] and sha(raw)==r['sha256']
for r in proof['prepared30_exact_original307_head']:
 raw=(ROOT/r['path']).read_bytes();assert len(raw)==r['bytes'] and sha(raw)==r['sha256']
assert len(proof['prepared30_exact_original307_head'])==30
for r in proof['five_existing_venvs_config_only']:refs.append(exact(r['pyvenv_config']))
assert len(proof['five_existing_venvs_config_only'])==5
refs.extend(exact(r) for r in proof['retained_original_evidence'])
for r in cfg['forbidden_generated_outputs']:
 p=pathlib.Path(r['path'])
 if r['exists']:refs.append(exact(r['binding']))
 else:assert not p.exists() and not p.is_symlink()
env=os.environ.copy();env['GIT_OPTIONAL_LOCKS']='0'
def git(*args):return subprocess.check_output(['git','--no-optional-locks',*args],cwd=ROOT,env=env).decode().strip()
assert git('rev-parse','HEAD')==d['source'];assert git('rev-parse','HEAD^{tree}')==d['tree'];assert not git('status','--porcelain=v1')
assert not pathlib.Path('/workspace/engineering/pr307-current2314-light-once-owned').exists()
for k in ('launcher','controlled_staged_Invoke'):ast.parse(pathlib.Path(d[k]['path']).read_bytes())
launcher=ast.parse(pathlib.Path(d['launcher']['path']).read_bytes());guard=next(n for n in launcher.body if isinstance(n,ast.FunctionDef) and n.name=='guard');guardcode=ast.unparse(guard)
assert 'CONFIG_SHA' not in guardcode and '__file__' not in guardcode
assert len(cfg['managed_activation_expected'])==18
assert not list(pathlib.Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/lib/python3.12/site-packages').glob('*log*pytest*'))
proofout={'schema':'INDEPENDENT_CURRENT2314_CONCRETE_LIGHT_ORIGINAL_STATIC_SOURCE_PROOF','original_owner':owner,'current_source':d['source'],'current_tree':d['tree'],'typed_source_rows_verified':1442,'prepared_inputs':30,'own_five_configs':5,'old_owned_evidence':len(proof['retained_original_evidence']),'bindings_verified':refs,'all_selected_ignored_generated_outputs_exact':True,'attempt_root_absent':True,'managed_keys_declared':18,'cached_Toolkit_log_plugin_namespace_absent':True,'syntax_parsed_only':True,'launcher_modules_imported':False,'tests_native_gates_executed':False,'concrete_gap':'guard(cfg) lacks config selfbinding and authorized launcher selfbinding before/finally; checks exist at initial entry only','git_optional_locks_disabled':True}
pp=OUT/'independent-original-concrete-LIGHT-static-source-proof.json';pp.write_bytes((json.dumps(proofout,indent=2,sort_keys=True)+'\n').encode());pp.chmod(0o400)
proposal='For a reviewed once-only launcher, include its immutable configuration and root-authorized launcher byte hash in the same before/finally guard as external inputs. Entry-only selfbinding does not establish that those inputs stayed unchanged during execution; preserve an original HOLD and use a named successor without replaying gates.\n'
p=OUT/'proposed-canonical-launcher-selfbinding-before-finally.txt';p.write_text(proposal);p.chmod(0o400)
receipt={'schema':'INDEPENDENT_CURRENT2314_CONCRETE_LIGHT_PREEXECUTION_ORIGINAL_REVIEW','decision':'HOLD_CURRENT2314_LIGHT_PREEXECUTION_SELF_BINDINGS_MISSING_FROM_ALWAYS_POST','source':d['source'],'tree':d['tree'],'owner':owner,'static_source_proof':binding(pp),'execution_authorized':False,'static_verified_scope':['1442 complete tracked filesystem bodies and executable modes','30 prepared input bytes and five existing environment configurations','15 old evidence refs and fixed ignored outputs unchanged','managed 18 exports and PATH prefix required before commands','Toolkit uses cached pytest without Runtime plugin flags; distinct absent ALL basetemp/JUnit/private stdio','Runtime 41-control focus uses absolute plugin logging','unchanged task/helper staged under own root, existing own venv/Poetry, controlled gh only; paired success then second exit17 preserves prior module','per-phase timeout with primary sequence780 and outer900TERM10; failures sealed before assertions','always-finally external/source postguard with primary error retained separately'],'required_named_successor_delta':['guard config file bytes/mode/hash before and finally','guard root-authorized launcher self bytes/mode/hash before and finally','preserve original owner/config/launcher/stage code and HOLD; no gate replay or command/output/budget changes'],'limits':['All LIGHT gates NOT_RUN','No actual OAuth acquisition/content authority/native/full/fresh CI/release acceptance','Five actual import origins remain proposed checks; current independent verification is existing metadata only','Outer hard kill can prevent finally and remains incomplete HOLD','No complete process cleanup or reader-join claim from timeout wrapper fallback'],'documentation_improvement':{'canonical_file_proposed':'docs/skills/repository-operations.md','exact_delta':proposal,'proposal_binding':binding(p),'durable_learning':'Entry-only selfbinding is distinct from all-input before/finally preservation','evidence':'f650 launcher guard AST and initial config/root-authorized selfSHA entry checks','stale_or_ambiguous_guidance_removed':'Initial binding must not be described as always-post coverage','remaining_uncertainty':'Named successor not yet announced; no execution or preservation outcome measured'},'upstream_disposition':'none','read_only':True}
rp=OUT/'OWNERFINAL-independent-current2314-original-concrete-LIGHT-PREEXECUTION-HOLD.json';rp.write_bytes((json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode());rp.chmod(0o400);print(json.dumps(binding(rp),sort_keys=True))
