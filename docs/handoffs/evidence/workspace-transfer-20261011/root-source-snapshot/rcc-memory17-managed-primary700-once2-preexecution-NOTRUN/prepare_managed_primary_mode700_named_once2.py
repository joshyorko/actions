import ast, datetime, hashlib, json, os, stat, subprocess
from pathlib import Path
ROOT=Path('/workspace/engineering/rcc-memory17-managed-primary700-once2-preexecution-NOTRUN');os.umask(0o077)
def row(path):
 p=Path(path);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(s.st_mode))}
def put(name,data):
 p=ROOT/name
 if not isinstance(data,str):data=json.dumps(data,indent=2,sort_keys=True)+'\n'
 with p.open('x') as f:f.write(data);f.flush();os.fsync(f.fileno())
 p.chmod(0o400);return row(p)
oldbase=Path('/workspace/engineering/rcc-memory17-pure-controls-concrete-preexecution-NOTRUN')
oldowner=oldbase/'OWNERFINAL-memory17-concrete-pure-control-launcher-config-and-root-once-preexecution-NOTRUN-v2.json';old=json.loads(oldowner.read_bytes())
oldcfg=json.loads(Path(old['config']['path']).read_bytes());original=Path(old['launcher']['path']).read_text()
assert row(oldowner)['sha256']=='56d2b731ffcd6bcb3ebf5d752086e6bc30249f423279964d64271f8c8deb676f'
for r in old['original_bindings']+[old['config']]:assert row(r['path'])==r
new_owned=Path('/workspace/engineering/root-one-memory17-pure-controls-20261011-2')
new_release=Path('/workspace/engineering/root-one-memory17-pure-controls-managed700-once2-release.json')
assert not new_owned.exists() and not new_owned.is_symlink() and not new_release.exists() and not new_release.is_symlink()
newconfig=ROOT/'FROZEN-memory17-managed-primary700-once2-pure-config-NOTRUN.json'
text=original.replace("BASE=Path('/workspace/engineering/rcc-memory17-pure-controls-concrete-preexecution-NOTRUN')",f'BASE=Path({str(ROOT)!r})').replace("ROOT=Path('/workspace/engineering/root-one-memory17-pure-controls-20261011-1')",f'ROOT=Path({str(new_owned)!r})')
needle="    raw=Path(args.config).read_bytes();require(digest(raw)==args.config_sha256,'MEMORY17_CONFIG_HASH')\n    cfg=json.loads(raw);raw_release=Path(args.release).read_bytes()\n"
assert text.count(needle)==1
physical='''    require(Path(args.config) == BASE / 'FROZEN-memory17-managed-primary700-once2-pure-config-NOTRUN.json', 'MEMORY17_CONFIG_PATH')
    require(Path(args.release) == Path('/workspace/engineering/root-one-memory17-pure-controls-managed700-once2-release.json'), 'MEMORY17_RELEASE_PATH')
    for name, mode in ((args.config, 0o400), (args.release, 0o600), (__file__, 0o400)):
        path = Path(name)
        metadata = path.lstat()
        require(stat.S_ISREG(metadata.st_mode) and not path.is_symlink()
                and stat.S_IMODE(metadata.st_mode) == mode
                and metadata.st_uid == os.getuid() == 1000
                and metadata.st_gid == os.getgid() == 1000, 'MEMORY17_OPERATOR_FILE_PHYSICAL_IDENTITY')
    raw=Path(args.config).read_bytes();require(digest(raw)==args.config_sha256,'MEMORY17_CONFIG_HASH')
    cfg=json.loads(raw);raw_release=Path(args.release).read_bytes()
'''
text=text.replace(needle,physical)
oldmode="    rcc=Path(cfg['managed_rcc']['path']);require(digest(rcc.read_bytes())==cfg['managed_rcc']['sha256']\n         and stat.S_IMODE(rcc.stat().st_mode)==0o711,'MEMORY17_PRIMARY_RCC_PIN_NO_EXECUTION')\n"
assert text.count(oldmode)==1
text=text.replace(oldmode,'')
mode='''    rcc = Path(cfg['managed_rcc']['path'])
    metadata = rcc.lstat()
    require(rcc == Path('/workspace/actions-cloud/bin/rcc')
            and stat.S_ISREG(metadata.st_mode) and not rcc.is_symlink()
            and stat.S_IMODE(metadata.st_mode) == cfg['managed_rcc']['mode'] == 0o700
            and metadata.st_uid == cfg['managed_rcc']['uid'] == os.getuid() == 1000
            and metadata.st_gid == cfg['managed_rcc']['gid'] == os.getgid() == 1000
            and metadata.st_size == cfg['managed_rcc']['bytes'] == 22282402
            and digest(rcc.read_bytes()) == cfg['managed_rcc']['sha256'], 'MEMORY17_PRIMARY_RCC_PIN_NO_EXECUTION')
'''
assert text.count('def activation(cfg):\n')==1;text=text.replace('def activation(cfg):\n','def activation(cfg):\n'+mode)
new_launcher=put('root_release_one_memory17_managed_primary700_once2_NOTRUN.py',text)
newtree=ast.parse(text);compile(newtree,new_launcher['path'],'exec')
oldtree=ast.parse(original)
changed=[]
new_by={n.name:n for n in newtree.body if isinstance(n,ast.FunctionDef)}
for n in oldtree.body:
 if isinstance(n,ast.FunctionDef) and ast.dump(n,include_attributes=False)!=ast.dump(new_by[n.name],include_attributes=False):changed.append(n.name)
assert changed==['parse_arguments','activation']
assert ast.dump(new_by['guard'],include_attributes=False)==ast.dump(next(n for n in oldtree.body if isinstance(n,ast.FunctionDef) and n.name=='guard'),include_attributes=False)
assert ast.dump(new_by['run'],include_attributes=False)==ast.dump(next(n for n in oldtree.body if isinstance(n,ast.FunctionDef) and n.name=='run'),include_attributes=False)
managed=Path('/workspace/actions-cloud/bin/rcc');s=managed.lstat();m=row(managed)
assert m['sha256']=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428' and m['mode']=='0o700' and s.st_uid==s.st_gid==1000 and s.st_size==22282402
actual=Path('/workspace/engineering/rcc-memory17-original-mode-admission-failure-independent-review/OWNERFINAL-independent-original-memory17-managed-mode-admission-FAIL-and-source-preservation.json')
oldrootowner=Path('/workspace/engineering/root-memory17-reviewed-original-outer/OWNERFINAL-root-one-original-reviewed-memory17-outer.json')
canonical=Path('/workspace/engineering/rcc-memory17-original-mode-admission-failure-independent-review/canonical-measured-per-path-binary-mode-before-delegation-proposed.patch')
oldreview=Path('/workspace/engineering/rcc-memory17-concrete-independent-preexecution-review/OWNERFINAL-independent-memory17-concrete-config-launcher-and-ROOT-preflight-PREEXEC-review.json')
config=dict(oldcfg);config.update({'status':'MEMORY17_MANAGED_PRIMARY700_ONCE2_PREEXEC_PREPARED_NOTRUN','launcher':new_launcher,'managed_rcc':{'path':str(managed),'sha256':m['sha256'],'bytes':m['bytes'],'mode':0o700,'uid':s.st_uid,'gid':s.st_gid},'basetemp':str(new_owned/'basetemp'),'logger':str(new_owned/'logger'),'junit':str(new_owned/'junit.xml'),'root_release_path':str(new_release),'original_failed_mode_admission':row(actual),'original_root_failed_owner':row(oldrootowner),'original_consumed_release':row('/workspace/engineering/root-one-memory17-pure-controls-release.json'),'original_concrete_config':old['config'],'original_concrete_PREEXEC':row(oldreview),'physical_operator_admission':'New launcher checks exact fresh config/release paths regular nonsymlink400/600/currentUIDGID1000 before JSON; launcher400sameowner. ROOT also repeats external preflight.','managed_pin_rule':'Exact regularnonsymlinkPRIMARYpath0700UIDGID1000size22282402SHA7e588 before actualguard/tests; no mode repair/chmod.'})
config['pytest_argv']=[x.replace('20261011-1','20261011-2') for x in oldcfg['pytest_argv']]
config['frozen_bindings']=oldcfg['frozen_bindings']+[new_launcher,old['config'],row(oldowner),row(oldreview),row(actual),row(oldrootowner),row('/workspace/engineering/root-one-memory17-pure-controls-release.json'),row(canonical)]
configrow=put(newconfig.name,config)
original_refs=old['original_bindings']+[old['config'],row(oldreview),row(actual),row(oldrootowner),row('/workspace/engineering/root-one-memory17-pure-controls-release.json')]
for r in config['frozen_bindings']:assert row(r['path'])==r
assert config['expected_test_census']==oldcfg['expected_test_census'] and config['envelope']==oldcfg['envelope']
proof={'schema':1,'status':'STATIC_PARSED_NOT_EXECUTED','original_launcher':old['launcher'],'new_launcher':new_launcher,'original_config':old['config'],'new_config':configrow,'changed_functions_only':changed,'all_other_function_ASTs':'EXACT_INCLUDING_GUARD_RUN_BOUNDS_CAPTURE_JUNIT_PENDING','constants_changed_only':['BASE preparation location','ROOT output once-1 ->once-2'],'managed_primary_measured':{**m,'uid':1000,'gid':1000,'type':'REGULAR_NONSYMLINK'},'fixture_binary_unchanged':'Original711file/nochmod; samebytesdifferentpathmodes recordedinoriginalactual12177','tests_and_policy':{'test_source':oldcfg['frozen_bindings'][1],'policy_source':oldcfg['frozen_bindings'][2],'state':'BYTE_EXACT_ORIGINAL_NOT_RUN'},'config_delta_only':['Namedconfig/launcherhash/currentownpaths','Freshonce2 basetemp/logger/JUnit/rootrelease paths','Exactmeasuredmanagedmetadata','Add immutableoriginalfailure/preservation/canonical bindings','Internalphysicalconfig/releaseadmission text'],'default_budget':{'root':420,'before':120,'primary':120,'post':120,'kill_grace':10},'no_existing_originals_modified':True,'native':'NOT_RUN','memory_policy_adoption':'NONE'}
proofrow=put('named-managed-primary700-once2-exact-source-config-delta-proof-NOTRUN.json',proof)
expected_release={'schema':1,'status':'ROOT_RELEASE_ONE_MEMORY17_PURE_CONTROLS','config_sha256':configrow['sha256'],'launcher_sha256':new_launcher['sha256'],'source':config['source'],'tree':config['tree'],'root':str(new_owned),'serialized_no_other_heavy_or_storage_mutations':True,'independent_review':None}
argv=list(old['argv_template']);argv=[x.replace(str(oldbase/'root_release_one_memory17_pure_controls_NOTRUN.py'),new_launcher['path']).replace(old['config']['path'],configrow['path']).replace(old['config']['sha256'],configrow['sha256']).replace(oldcfg['root_release_path'],str(new_release)) for x in argv]
reviewfields=dict(old['independent_review_topfields_required']);reviewfields.update({'config_sha256':configrow['sha256'],'launcher_sha256':new_launcher['sha256']})
release_contract={'schema':1,'status':'TEMPLATE_ONLY_NOT_RUN_NOT_ROOTAUTH','expected_root_release':expected_release,'root_release_path':str(new_release),'release_mode':'0o600regularnonsymlinkUIDGID1000','compatible_independent_review_topfields':reviewfields,'exact_ROOT_argv_template':argv,'only_ROOT_placeholder_substitution':'ROOT_DISTINCT_HASH_REQUIRED_NOT_GRANTED ->measuredfreshROOTreleaseSHA','mandatory_ROOT_preflight':['Exact regular nonsymlink/currentUIDGID1000 config400/launcher400/release600 and allSHA; no chmod/physicalrepair.','Exact ROOTrelease typedkeys/source/tree/config/launcher/root/serializedTrue andREALcompatibleindrow.','Freshrootonce2+basetemp/logger/JUnitABSENT, originalfailedonce1 consumedandnotreused.','Root outer420TERM10 plus explicitparent450; no heavy/native/storageconcurrency.','Actualsuccess remainsprocess0PENDING original17JUnitcensus; memoryprofileNOTADOPTED.']}
release_row=put('named-managed-primary700-once2-compatible-root-release-contract-NOTRUN.json',release_contract)
owner={'schema':1,'status':'OWNER_FINAL_MEMORY17_MANAGED_PRIMARY700_ONCE2_CONCRETE_PREEXECUTION_NOTRUN','source':config['source'],'tree':config['tree'],'config':configrow,'launcher':new_launcher,'root_once':str(new_owned),'argv_template':argv,'root_release_expected':expected_release,'independent_review_topfields_required':reviewfields,'original_mode_admission_failure':row(actual),'original_root_failure':row(oldrootowner),'original_bindings':original_refs,'all_new_and_retained_binding_closure':config['frozen_bindings'],'exact_delta_proof':proofrow,'ROOT_release_contract':release_row,'physical_preflight':'Internallyenforcedexactregularnonsymlinkpaths400/600/400UIDGID1000plusROOTexternalrepeat; measuredprimary700strict beforebeforeguard/tests.','pure17':'NOT_RUN','policy_module':'UNCHANGED_NOT_ADOPTED','native':'NOT_RUN','product_source_edits':'NONE','managed_binary_edits':'NONE','ROOTrelease':'NOT_CREATED','source_scope':'Current8d49/1440 unchanged; existingV9readonly before/alwayspost enforces fullsource/originalnative1192+30+5+237aliases+temporal2.','documentation_improvement':{'canonical_file_proposed':'docs/skills/repository-operations.md','exact_delta':row(canonical),'durable_learning':'Permission admission is per owningpath, notbinarydigest; primary0700 andfixture0711 canbothbeexact. Pretestfailure consumesROOTrelease evenwithoutputrootABSENT.','evidence':'Original277e/ValueError+ind12177; directmanagedprimary andignoredfixtureexactbytes/size/UIDGID/perpathmodes; newmodepredicate preserves strictidentity ratherthanchmod.','stale_or_ambiguous_guidance_removed':'Incorrect primarymode711expectation fixedonlyinnewprivate launcher; originalincorrectguard andfailedattempt remainunchanged.','remaining_uncertainty':'Newlauncher/confignotindependentlyreviewed or executed; all17purecontrols andnative memorycalibration unqualified.'},'upstream_disposition':'none','capture':datetime.datetime.now(datetime.timezone.utc).isoformat()}
Path(__file__).chmod(0o444);owner['constructor']=row(__file__)
ownerrow=put('OWNERFINAL-memory17-measured-primary700-fresh-once2-concrete-PREEXEC-NOTRUN.json',owner)
print(json.dumps({'owner':ownerrow,'launcher':new_launcher,'config':configrow,'release_contract':release_row,'original_failure':row(actual)}))
