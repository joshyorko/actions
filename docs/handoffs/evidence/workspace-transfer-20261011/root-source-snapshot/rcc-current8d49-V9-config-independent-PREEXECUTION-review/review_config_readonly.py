import ast,hashlib,json,os,pathlib,stat,subprocess,copy
P=pathlib.Path('/workspace/engineering/rcc-current8d49-qualified-V9-entry-bootstrap-preparation');R=pathlib.Path('/workspace/engineering/rcc-current8d49-V9-config-independent-PREEXECUTION-review');owner=P/'OWNERFINAL-current8d49-qualified-V9-entry-config-and-managed-PREEXECUTION-proposal.json'
def digest(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):
 p=pathlib.Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();return dict(path=str(p),bytes=s.st_size,sha256=digest(p),mode=oct(stat.S_IMODE(s.st_mode)))
def check(row):assert bind(row['path'])==row
check(dict(path=str(owner),bytes=7708,sha256='a68a1536079388ba03721f976982f3772bc5387d15d2403c0e736baa24be592d',mode='0o400'));d=json.loads(owner.read_bytes());check(d['config']);c=json.loads(pathlib.Path(d['config']['path']).read_bytes())
for row in [d['source_V9_proposal'],d['source_V9_independent']]+d['constructors']+[d['data_only_real_package_all_entry_plan_control']['code']]:check(row)
oldpath=pathlib.Path('/workspace/engineering/rcc-current8d49-qualified-V8-config-preparation/FROZEN-current8d49-control3-qualified-V8-config-v2.json');assert digest(oldpath)=='a209cc117db4d17a7383ba519abdff064211960aa0b8a88ddf32569fef322f9f';old=json.loads(oldpath.read_bytes())
allow={'owned_root','owned_package_cache','pytest_argv','bindings','actual_status','launch_disposition'};assert set(c)==set(old) and all(c[k]==old[k] for k in set(c)-allow)
assert len(old['bindings'])==291 and len(c['bindings'])==308 and c['bindings'][:291]==old['bindings']
assert len({(x['path'],x['sha256']) for x in c['bindings']})==308
r3='/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-3';r4='/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-4';assert old['owned_root']==r3 and c['owned_root']==r4
assert [x for x in old['pytest_argv'] if x.startswith(r3+'/')]==[r3+'/pytest',r3+'/pytest-logging',r3+'/junit.xml']
assert c['pytest_argv']==[r4+x[len(r3):] if x.startswith(r3+'/') else x for x in old['pytest_argv']]
def encoded(v):return (json.dumps(v,sort_keys=True,separators=(',',':'))+'\n').encode()
m={'schema':1,'runtime_source_sha':c['source'],'runtime_source_tree':c['tree'],'label':'control3','binary_sha256':c['binary']['sha256'],'state_root':r4,'package_cache_root':r4+'/actions-home/pkgs'};ms=hashlib.sha256(encoded(m)).hexdigest();plan={'schema':1,'marker':m,'marker_sha256':ms,'marker_path':r4+'/rcc-package-cache-owner.json','child_config':dict(m,state_marker_sha256=ms),'environment_key':'ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG','cold_publication_then_warm_staged_pkgs_only':True}
assert encoded(c['owned_package_cache'])==encoded(plan);assert hashlib.sha256(encoded(plan)).hexdigest()==d['cache_plan_sha256']=='1d0af9c61e34ed5e9ed20fb1a21a7240f59974ba8102c7de57141cfccae0da18'
assert c['budgets']==[600,10,645,660,10] and c['source_count']==1440 and len(c['source_body_modes'])==1440 and len(c['native_original_members'])==1192 and len(c['prepared_inputs'])==30 and len(c['concrete_own_origins'])==5
assert c['binary']=={'path':'/workspace/actions-cloud/bin/rcc','sha256':'7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428','selector':None,'version':'v18.19.3'}
root=pathlib.Path(c['source_root']);env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'}
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(root),*args],env=env)
assert git('rev-parse','HEAD').decode().strip()==d['source'] and git('rev-parse','HEAD^{tree}').decode().strip()==d['tree'] and git('status','--porcelain')==b''
tracked={}
for row in git('ls-tree','-rz','--full-tree','HEAD').split(b'\0'):
 if row:
  a,path=row.split(b'\t');mode,typ,obj=a.decode().split();tracked[path.decode()]=(mode,typ,obj)
assert len(tracked)==1440 and set(tracked)=={r['path'] for r in c['source_body_modes']}
for r in c['source_body_modes']:
 p=root/r['path'];assert tracked[r['path']]==(r['mode'],'blob',r['object']) and digest(p)==r['sha256'] and stat.S_IMODE(p.lstat().st_mode)==r['fs_mode']
for p,h in c['prepared_inputs'].items():assert digest(root/p)==h
for r in c['native_original_members']:
 p=pathlib.Path(c['native_original_root'])/r['path'];s=p.lstat();assert stat.S_IMODE(s.st_mode)==r['mode']
 if r['kind']=='file':assert stat.S_ISREG(s.st_mode) and digest(p)==r['content_sha256']
 elif r['kind']=='directory':assert stat.S_ISDIR(s.st_mode)
 elif r['kind']=='symlink':assert stat.S_ISLNK(s.st_mode) and os.readlink(p)==r['link_target']
 else:raise AssertionError('UNSUPPORTED_NATIVE_KIND')
# Preserve historical fixture row against immutable Git body/snapshot, separate from live fixture.
h=c['historical_fixture_binding'];snapshot=pathlib.Path('/workspace/engineering/rcc-current8d49-private-V8-real-fixture-mode-successor/historical-e4ff-staged-fixture-exact-Git-blob.snapshot.py');assert snapshot.stat().st_size==h['bytes'] and digest(snapshot)==h['sha256'] and stat.S_IMODE(snapshot.stat().st_mode)==0o444
raw=git('show','e4ff080375a8422bb656e52d218f198521dda078:action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py');assert len(raw)==h['bytes'] and hashlib.sha256(raw).hexdigest()==h['sha256'];check(c['current_fixture_binding'])
missing=[];verified_physical=0
for r in c['bindings']:
 if r==h:continue
 if pathlib.Path(r['path']).exists():check(r);verified_physical+=1
 else:missing.append(r)
assert len(missing)==1 and missing[0]['sha256']=='8dc25bb1b99503af386d12d32c0637aa3503617c6f97d66a83f4643969934d4c'
mp=pathlib.Path('/workspace/engineering/root-failed-control3-one-byte-preservation-v4/root-exact-historical-failed-member-archive-mapping.json');assert digest(mp)=='cc73027ce86ea0965f3bdd88ed3398c322dcf012b337a4ca161966f19ffee6c7' and stat.S_IMODE(mp.stat().st_mode)==0o600;mapping=json.loads(mp.read_bytes());assert mapping['original_binding']==missing[0] and mapping['original_status']=='FAIL' and mapping['original_cleanup']=='FAIL_UNCHANGED' and mapping['original_path_absent'] is True
for k in ['archive','complete_index','expanded_removal','root_original_terminal']:check(mapping[k])
# Exact compressed archive hash binds prior approved1696-byte member proof; no repeated full TAR replay.
for k in ['source_FULL','source_independent','source_FULL_independent']:check(c[k])
for row in c['temporal_shared_outputs']:
 p=pathlib.Path(row['path']);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and digest(p)==row['sha256'];assert all(row[k]==v for k,v in {'bytes':s.st_size,'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,'device':s.st_dev,'inode':s.st_ino,'mtime_ns':s.st_mtime_ns}.items())
for row in c['concrete_own_origins']:
 assert pathlib.Path(row['prefix']).is_dir() and pathlib.Path(row['origin']).is_file() and pathlib.Path(row['origin']).is_relative_to(root)
for p in [r3,r4,'/workspace/engineering/root-rcc-owned-cache-one-current8d49-control3-v9-1']:assert not pathlib.Path(p).exists() and not pathlib.Path(p).is_symlink()
# Bootstrap and all wrapper/dependency paths are present in the exact config inventory.
source=json.loads(pathlib.Path(d['source_V9_proposal']['path']).read_bytes());rows={(r['path'],r['sha256']):r for r in c['bindings']}
for r in source['original_four_modules_unchanged']+source['named_V9_bindings']:assert rows[(r['path'],r['sha256'])]==r
review=json.loads(pathlib.Path(d['source_V9_independent']['path']).read_bytes());assert review['decision']=='GO_CURRENT8D49_NAMED_V9_ENTRY_BOOTSTRAP_SOURCE_ONLY'
proof=dict(schema='INDEPENDENT_EXACT_V9_CONFIG_POLICY_STATE_AND_ALL_BINDING_CLOSURE',proposal_binding=bind(owner),config_binding=d['config'],cache_plan_sha256=d['cache_plan_sha256'],top_fields_preserved_except_declared=sorted(set(c)-allow),old291_bindings_exact_prefix=True,final308_unique_binding_rows=True,physical_bindings_rehashed=verified_physical,historical_fixture_original_Git_and_snapshot_equal=True,historical_missing_receipt_fixed_alias_archive_and_index_rehashed=True,historical_missing_receipt_prior_member_proof_reused_no_TAR_replay=True,current_source1440_Git_tree_FS_body_fullmode=True,native1192_body_kind_mode_link=True,prepared30=True,own5_prefix_origin_metadata_only=True,temporal2_exact_metadata_and_bodies=True,cache_marker_plan_fully_reconstructed=True,sole_root3_to4_and_three_pytest_paths=True,original_transport_file_binding_preserved=True,budgets=c['budgets'],source=d['source'],tree=d['tree'],fresh_capacity_snapshot={p:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize for p in ['/workspace','/dev/shm','/tmp']},operation='NOT_RUN',native_acceptance='HOLD_UNTIL_ROOT_DISTINCT_RELEASE_AND_ORIGINAL_ACTUAL_RESULT')
f=R/'independent-V9-config-source-native-binding-and-root-policy-closure-proof.json';f.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');f.chmod(0o400);print(json.dumps(bind(f)))
