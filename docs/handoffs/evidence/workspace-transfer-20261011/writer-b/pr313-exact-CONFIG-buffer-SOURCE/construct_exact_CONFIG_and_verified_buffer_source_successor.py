import ast,datetime,hashlib,json,os,stat,subprocess
from pathlib import Path
B=Path(__file__).resolve().parent;O=Path('/workspace/engineering/pr313-current2d86-private-cached-bounded-LIGHT-SOURCE-NOTRUN');R=Path('/workspace/engineering/captured-child-cleanup');I=Path('/workspace/engineering/pr313-current2d86-cached-bounded-LIGHT-independent-SOURCE-review');SOURCE='2d86c5cf92d3acb274a8ceb5d57bfb8b12c779b6';TREE='653a9e73e4d27641ec86de94b90f35d41e0f24f8'
def row(p):
 p=Path(p);m=p.lstat();assert stat.S_ISREG(m.st_mode) and not p.is_symlink();b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),mode=oct(stat.S_IMODE(m.st_mode)))
def exact(r):assert row(r['path'])==r;return Path(r['path']).read_bytes()
def put(n,v):
 p=B/n
 with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 p.chmod(0o400);return row(p)
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
assert git('rev-parse','HEAD').decode().strip()==SOURCE and git('rev-parse','HEAD^{tree}').decode().strip()==TREE and not git('status','--porcelain')
oldowner=row(O/'OWNERFINAL-current2d86-private-cached-bounded-LIGHT-SOURCE-and-external-parent-HOLD-NOTRUN.json');old=json.loads(exact(oldowner));cfg=json.loads(exact(old['config']));ind=row(I/'OWNERFINAL-independent-current2d86-private-cached-bounded-LIGHT-SOURCE-HOLD-and-external-parent-PREEXEC-HOLD.json');assert ind['sha256']=='2cb465a46bfe285f2fed33e52610ea72764f1f46512df8146d653e2f8b43f2b9'
for r in cfg['bindings']:exact(r)
helper='''def verified_buffer(path, expected_sha, mode, owner=False, expected_bytes=None):
    p=Path(path);m=p.lstat()
    assert stat.S_ISREG(m.st_mode) and not p.is_symlink() and stat.S_IMODE(m.st_mode)==mode
    if owner:assert m.st_uid==os.getuid() and m.st_gid==os.getgid()
    raw=p.read_bytes()
    assert len(raw)==m.st_size
    if expected_bytes is not None:assert len(raw)==expected_bytes
    assert hashlib.sha256(raw).hexdigest()==expected_sha
    return raw
'''
guardsource=exact(old['guard']).decode();guardchanges=[]
a="p=Path(sys.argv[1]);m=p.lstat();assert stat.S_ISREG(m.st_mode) and not p.is_symlink() and stat.S_IMODE(m.st_mode)==0o400\n assert digest(p)==sys.argv[2];c=json.loads(p.read_bytes());root=Path(c['source_root'])";b="c=json.loads(verified_buffer(sys.argv[1],sys.argv[2],0o400));root=Path(c['source_root'])";assert guardsource.count(a)==1;guardsource=guardsource.replace(a,b);guardchanges.append((a,b))
a="q=Path(path);s=q.lstat();assert stat.S_ISREG(s.st_mode) and not q.is_symlink() and stat.S_IMODE(s.st_mode)==mode and s.st_uid==os.getuid() and s.st_gid==os.getgid();assert digest(q)==sha;return json.loads(q.read_bytes())";b="return json.loads(verified_buffer(path,sha,mode,owner=True))";assert guardsource.count(a)==1;guardsource=guardsource.replace(a,b);guardchanges.append((a,b))
# Configuration-selected JSON source-data rows also parse exactly the buffer matched to their original byte/hash/mode binding.
for a,b in [("rows=json.loads(Path(c['source_inventory']['path']).read_bytes())","r=c['source_inventory'];rows=json.loads(verified_buffer(r['path'],r['sha256'],int(r['mode'],8),expected_bytes=r['bytes']))"),("baseline=json.loads(Path(c['native_baseline']['path']).read_bytes())","r=c['native_baseline'];baseline=json.loads(verified_buffer(r['path'],r['sha256'],int(r['mode'],8),expected_bytes=r['bytes']))")]:
 assert guardsource.count(a)==1;guardsource=guardsource.replace(a,b);guardchanges.append((a,b))
assert guardsource.count('def main():')==1;guardsource=guardsource.replace('def main():',helper+'\ndef main():');ast.parse(guardsource)
gp=B/'current_2d86_readonly_source_and_full_authority_guard_NOTRUN.py';gp.write_text(guardsource);gp.chmod(0o444);guard=row(gp)
newcfg=dict(cfg);newcfg['guard']=guard;refs=cfg['bindings']+[oldowner,old['config'],old['launcher'],old['guard'],old['ROOT_external_contract'],old['source_proof'],old['meaningful_controls_plan'],ind,guard];seen={}
for r in refs:
 exact(r)
 if r['path'] in seen:assert seen[r['path']]==r
 seen[r['path']]=r
newcfg['bindings']=list(seen.values());config=put('FROZEN-current2d86-private-cached-bounded-LIGHT-inputs-NOTRUN.json',newcfg)
launchsource=exact(old['launcher']).decode();launchchanges=[]
for a,b in [("CONFIG=BASE/'FROZEN-current2d86-private-bounded-LIGHT-inputs-NOTRUN.json'","CONFIG=BASE/'FROZEN-current2d86-private-cached-bounded-LIGHT-inputs-NOTRUN.json'"),(old['config']['sha256'],config['sha256'])]:
 assert launchsource.count(a)==1;launchsource=launchsource.replace(a,b);launchchanges.append((a,b))
a="raw=p.read_bytes();assert digest(raw)==expected;return json.loads(raw)";b="raw=verified_buffer(p,expected,0o600,owner=True);return json.loads(raw)";assert launchsource.count(a)==1;launchsource=launchsource.replace(a,b);launchchanges.append((a,b))
a="raw=p.read_bytes();assert digest(raw)==sha;return json.loads(raw)";b="raw=verified_buffer(p,sha,0o400,owner=True);return json.loads(raw)";assert launchsource.count(a)==1;launchsource=launchsource.replace(a,b);launchchanges.append((a,b))
a="cm=CONFIG.lstat();assert stat.S_ISREG(cm.st_mode) and not CONFIG.is_symlink() and stat.S_IMODE(cm.st_mode)==0o400 and digest(CONFIG.read_bytes())==CONFIG_SHA\n cfg=json.loads(CONFIG.read_bytes())";b="config_raw=verified_buffer(CONFIG,CONFIG_SHA,0o400,expected_bytes="+str(config['bytes'])+")\n cfg=json.loads(config_raw)";assert launchsource.count(a)==1;launchsource=launchsource.replace(a,b);launchchanges.append((a,b))
assert launchsource.count('def strict_review')==1;launchsource=launchsource.replace('def strict_review',helper+'\ndef strict_review');ast.parse(launchsource)
lp=B/'launch_current2d86_private_cached_bounded_LIGHT_once_NOTRUN.py';lp.write_text(launchsource);lp.chmod(0o444);launcher=row(lp)
# Inverse exact-text proof of declared narrow buffer/address corrections. No imported production/controller code is executed.
rev=guardsource.replace(helper+'\n','',1)
for a,b in reversed(guardchanges):rev=rev.replace(b,a)
assert rev==exact(old['guard']).decode()
rev=launchsource.replace(helper+'\n','',1)
for a,b in reversed(launchchanges):rev=rev.replace(b,a)
assert rev==exact(old['launcher']).decode()
assert newcfg['phases']==cfg['phases'] and newcfg['prefix_aliases']==cfg['prefix_aliases'] and newcfg['bounds']==cfg['bounds']
assert not Path(newcfg['outputs']['attempt']).exists() and not (B/'root-one-current2d86-private-LIGHT-release.json').exists()
contract=json.loads(exact(old['ROOT_external_contract']));contract.update(config=config,launcher=launcher,guard=guard,ROOTrelease_path=str(B/'root-one-current2d86-private-LIGHT-release.json'));contract['inner_command_argv']=[str(Path(cfg['cached_prefix'])/'bin/python'),str(lp),contract['ROOTrelease_path'],'ROOT_RELEASE_SHA256','REAL_PREEXEC_REVIEW_PATH','REAL_PREEXEC_REVIEW_SHA256'];rootcontract=put('required-external-all-outcome-parent-and-strict-ROOT-adoption-contract-NOTRUN.json',contract)
proof=put('exact-consumed-CONFIG-and-captured-buffer-parser-identity-source-proof-NOTRUN.json',{'schema':1,'source':SOURCE,'tree':TREE,'guard_original':old['guard'],'launcher_original':old['launcher'],'source1441_current30_native1192_alias5_historical118plus1':'UNCHANGED_BOUNDED_INPUT_MODEL','guard_exact_inverse_text_after_changes':guardchanges,'launcher_exact_inverse_text_after_changes':launchchanges,'shared_helper_SHA':hashlib.sha256(helper.encode()).hexdigest(),'buffer_contract':'Captureone raw, comparelength againstsameoriginalstat andoptionaldeclaredbytes, SHAexpectedtoken thenparseEXACTreturnedraw; no extraunverifiedJSONreread. Legacyregular/nonsymlink/mode andownerUIDGIDchecks preserved.','configuration_literal':'Exactcachedfilename matchesnewfrozenconfigrow/bytes/SHA, BASEnewprivatefolder','selected_JSON_rows':'Guardinventory/nativebaseline parsefromcapturedfullyboundrow too, preservingexistingexpectedbytes/hash/mode','all_phase_commands_outputs_cwd_cached_only':'EXACT_UNCHANGED','all_guardenv_childenv_capacity_and_clock':'EXACT_UNCHANGED nohard640primaryclaim','external_parent':'NOTAUTHORED_REQUIRED; controlsNOTRUN/floorFAIL stillHOLD','source_actual':'NOT_RUN','upstream_disposition':'none'})
controls=put('required-buffer-identity-and-nested-address-controls-plan-NOTRUN.json',{'schema':1,'status':'PLAN_ONLY_NOT_EXECUTED','original_plan':old['meaningful_controls_plan'],'additional_controls':['Correctbaselinebufferlength/sha/type/mode/UIDGID thenoneJSONparsedbuffer; swappedlaterreadcannotchangeadmittedparseddecision','Wrongsize/sha/mode/type/nonsymlink/UIDGIDbeforeparse; missingcachedCONFIGaddressrefusal','Correctlyrehashedstaleoutputcfg poison mustfailsemanticASTaddressauditdistinctfromcfgintegrityrejection','Changedauthorityafterprimarymustfailpost whileoriginalphaseexceptionretained','Actualprimary-only640parent/nativeownedprocess-tree/readers/lease/postcleanup remain NEXTcriticalexplicituseracceptance work; no metadata counts/NULLfacts asPASS'],'no_execution_authority':True})
canon=B/'canonical-verified-authority-buffer-and-consumed-CONFIG-proposed.txt';canon.write_text(json.loads(exact(ind))['documentation_improvement']['additional_exact_proposed_text']+'\n');canon.chmod(0o400)
allrefs=[row(p) for p in sorted(B.iterdir()) if p.is_file()]
owner=put('OWNERFINAL-current2d86-private-CONFIG-captured-buffer-minimal-SOURCE-successor-NOTRUN.json',{'schema':1,'status':'OWNER_FINAL_CURRENT2D86_PRIVATE_CONFIG_BUFFER_SOURCE_PREPARED_ALL_EXECUTION_HOLD','source':SOURCE,'tree':TREE,'source_count':1441,'source_clean':True,'app_source_HEAD_ref_env_delta':'NONE','original9b290_SOURCE_and_indHOLD':'Preservedbyteexact','original_source_owner':oldowner,'original_independent_SOURCE_HOLD':ind,'config':config,'launcher':launcher,'guard':guard,'ROOT_external_contract':rootcontract,'source_proof':proof,'control_plan':controls,'bindings':allrefs,'immutable_input_rows':len(newcfg['bindings']),'exact_corrective_scope':'CONFIGcachedbasename+verifiedsamebufferJSONparsing atconfig/release/reviews/source-data boundaries; sameauthorityschema/UIDGID/mode/source/native/prefix/phase/selectors/cached-only/outputpaths/budgets/floor','actual_controls_SOURCE_LIGHT_FULL_native':'NOT_RUN_HOLD','material_remaining':'Mandatoryexternalalloutcomeparent/controlproof/capacity andactualprimary-only640 boundedmechanism/completeownedtree-reader-lease-postcleanup acceptance; no SOURCEready/PREEXECGO selfclaim','floor':1288490189,'workspace_observation':os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize,'documentation':{'canonical_file_proposed':'docs/skills/repository-operations.md','exact_delta':row(canon),'evidence':'Ind2cb465 literaladdress+doubleJSONread findings; exactinverseSOURCEdiff captured-bufferhelper verifiedwithoutimports/tests; alloriginalbounds/inputmodels unchanged','stale_ambiguity':'Hashingonebufferdoesnotauthenticateanotherparsedread; filenamesmustmatchactualconsumedcfg; metadata640 isnotimplementedparent','remaining_uncertainty':'NewSOURCEind/control/parent/PREEXEC/resource and ROOTactualsource/native/cleanup requirements stillpending. No tests/imports/fixtures/gates/version/native execution.','upstream_disposition':'none'},'capture':datetime.datetime.now(datetime.timezone.utc).isoformat()})
for r in newcfg['bindings']+allrefs:exact(r)
assert not git('status','--porcelain')
print(json.dumps(owner))
