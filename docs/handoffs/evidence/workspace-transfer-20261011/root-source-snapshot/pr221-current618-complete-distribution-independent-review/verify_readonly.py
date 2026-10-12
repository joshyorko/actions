from pathlib import Path,PurePosixPath
import ast,base64,configparser,csv,email.parser,gzip,hashlib,io,json,re,stat,subprocess,tarfile,tomllib,zipfile
D=Path('/workspace/engineering/pr221-current618-complete-distribution-independent-review');O=Path('/workspace/engineering/pr221-current618-complete-distribution-integrity-owned');R=Path('/workspace/actions')
SOURCE='6181b044c75de35386f1ae30e71725398b6a7feb';BUILD='e7666eacf2687f65050b97a88e791f8d0ce4cd20';BASE='a70993fafc99a9f94041485542d5a720797ca394';TREE='99ac5309add45af65049546dd3a99f357884cf3b'
def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def binding(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def check(e):assert binding(e['path'])=={k:e[k] for k in ['path','bytes','sha256']};return e

def git(*args):return subprocess.check_output(['git','-C',str(R),*args],stderr=subprocess.PIPE)
def load(p):return json.loads(Path(p).read_text())
owner=O/'OWNERFINAL-current618-complete-original-distribution-integrity.json';assert owner.stat().st_size==24118 and sha(owner)=='75757b7de4162b6e8afd739fd983b99325cd18ea2a368a279d4f233197c4314a';v=load(owner)
assert len(v['evidence'])==17
for e in v['evidence']:check(e)
priorCount=0
for p in v['previous_owners_and_all_binding_bytes_unchanged']:
 check(p['owner']);old=load(p['owner']['path']);assert len(old['evidence'])==p['all_existing_bindings_unchanged']
 for e in old['evidence']:check(e);priorCount+=1
assert priorCount==217
assert git('rev-parse',SOURCE+'^{tree}').decode().strip()==git('rev-parse',BUILD+'^{tree}').decode().strip()==TREE
assert git('show','-s','--format=%P',SOURCE).decode().split()==['77647484b3cdd8e18aabf344a4018ea8ed8e3ea0','3155fc55ea7d47afbc547fddc963b5860462924b']
assert git('show','-s','--format=%P',BUILD).decode().split()==[BASE,SOURCE]
project=tomllib.loads(git('show',SOURCE+':action_server/pyproject.toml').decode())['tool']['poetry'];assert project['name']=='actions-runtime' and project['version']=='1.0.3'
# Pure standard-library constraint parsing, no package imports or source execution.
def ver(s):
 p=[int(x) for x in s.split('.')]
 while len(p)>1 and p[-1]==0:p.pop()
 return tuple(p)
def spec(s):
 if s.startswith('^'):
  x=s[1:];p=[int(x) for x in x.split('.')];i=next((i for i,n in enumerate(p) if n),len(p)-1);upper=p[:i+1];upper[-1]+=1;s='>='+x+',<'+'.'.join(map(str,upper))
 elif re.fullmatch(r'\d+(?:\.\d+)*',s):s='=='+s
 out=[]
 for term in s.split(','):
  m=re.fullmatch(r'(>=|<=|==|!=|>|<)\s*(\d+(?:\.\d+)*)',term.strip());assert m;out.append((m[1],ver(m[2])))
 return sorted(out)
def canon(n):return re.sub(r'[-_.]+','-',n).lower()
expectedDeps={canon(k):{'extras':sorted(x.get('extras',[])) if isinstance(x,dict) else [],'constraints':spec(x['version'] if isinstance(x,dict) else x)} for k,x in project['dependencies'].items() if k!='python'}
def metadata(b):
 m=email.parser.BytesParser().parsebytes(b);assert m.get_all('Name')==[project['name']] and m.get_all('Version')==[project['version']] and spec(m['Requires-Python'])==spec(project['dependencies']['python']);deps={}
 for s in m.get_all('Requires-Dist',[]):
  z=re.fullmatch(r'([A-Za-z0-9_.-]+)(?:\[([^\]]+)\])?\s+\(([^)]+)\)',s);assert z;n=canon(z[1]);assert n not in deps;deps[n]={'extras':sorted(z[2].split(',')) if z[2] else [],'constraints':spec(z[3])}
 assert deps==expectedDeps
 return {'name':m['Name'],'version':m['Version'],'dependency_count':len(deps),'source_python_dependencies_exact':True,'sha256':digest(b)}
allLeaves={}
for row in git('ls-tree','-rz',SOURCE).split(b'\0'):
 if row:
  meta,p=row.split(b'\t',1);allLeaves[p.decode()]=meta.decode().split()
sourceFiles={p[len('action_server/src/'):]:e for p,e in allLeaves.items() if p.startswith('action_server/src/')};assert len(sourceFiles)==215
sourceBodies={p:git('cat-file',e[1],e[2]) for p,e in sourceFiles.items()}
def safeName(n):
 assert n and '\x00' not in n and '\\' not in n and ':' not in n and not n.startswith('/')
 p=PurePosixPath(n);assert '..' not in p.parts and '.' not in p.parts and str(p)==n.rstrip('/')
def unzip(b):
 payload={};infos={}
 with zipfile.ZipFile(io.BytesIO(b)) as z:
  lst=z.infolist();assert len(lst)<=5000 and len({i.filename for i in lst})==len(lst) and sum(i.file_size for i in lst)<=512*1024*1024
  for i in lst:
   safeName(i.filename);assert not i.flag_bits&1 and not stat.S_ISLNK(i.external_attr>>16) and i.file_size<=128*1024*1024
   body=z.read(i);assert len(body)==i.file_size
   infos[i.filename]=i
   if not i.is_dir():payload[i.filename]=body
 return payload,infos
report=load(v['complete_data_only_proof']['path']);assert len(report['wheels'])==6
platform={};originals={};distributionBodies={}
for a in report['original_platform_archives']:
 check(a['file']);payload,info=unzip(Path(a['file']['path']).read_bytes());assert len(payload)==(1 if a['platform']=='sdist' else 2)
 for item in a['inventory']:
  name=item['path'];body=payload[name];i=info[name];assert len(body)==item['bytes'] and digest(body)==item['sha256'] and f'{i.CRC:08x}'==item['crc32'] and oct(i.external_attr>>16)==item['unix_mode'] and i.create_system==item['create_system']
 for name,body in payload.items():assert name not in distributionBodies;distributionBodies[name]=body;platform[name]=a['platform']
 originals[a['platform']]=a['file']
assert len(distributionBodies)==7 and {a['id'] for a in v['new_original_artifacts']}=={11698787320,11698838081}
aggregate,aggInfo=unzip(Path(report['aggregate']['file']['path']).read_bytes());assert len(aggregate)==len(aggInfo)==8 and set(aggregate)==set(distributionBodies)|{'actions-runtime-manifest.sha256'}
for name,b in distributionBodies.items():assert aggregate[name]==b
publisher=git('show',SOURCE+':action_server/scripts/publish_verified_runtime.py');assert publisher==Path(v['separately_typed_aggregate_manifest']['publisher_source_snapshot']['path']).read_bytes();pubAST=ast.parse(publisher)
man=next(n for n in pubAST.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MANIFEST_NAME' for t in n.targets));assert ast.literal_eval(man.value)=='actions-runtime-manifest.sha256'
write=next(n for n in pubAST.body if isinstance(n,ast.FunctionDef) and n.name=='write_manifest');names=next(n for n in pubAST.body if isinstance(n,ast.FunctionDef) and n.name=='_artifact_names')
assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='sorted' for n in ast.walk(names)) and any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_artifact_names' for n in ast.walk(write))
constants=[n.value for n in ast.walk(write) if isinstance(n,ast.Constant)];assert '  ' in constants and '\n' in constants
expectedManifest=''.join(digest(b)+'  '+n+'\n' for n,b in sorted(distributionBodies.items())).encode();assert aggregate['actions-runtime-manifest.sha256']==expectedManifest==Path(v['separately_typed_aggregate_manifest']['file']['path']).read_bytes() and len(expectedManifest)==939 and len(expectedManifest.splitlines())==7

def oauth(b):
 t=ast.parse(b);rows=[n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(z,ast.Name) and z.id=='FILE_CONTENTS' for z in n.targets)];assert len(rows)==1 and isinstance(rows[0].value,ast.Dict);d=ast.literal_eval(rows[0].value);assert set(d)=={'actions_config','default_user_config'} and all(isinstance(x,str) and x=='' for x in d.values());return {'entries':2,'category':'BOTH_EMPTY_STRINGS','module_sha256':digest(b),'authority':'HOLD'}

def compare(payload,info,prefix=''):
 matched=0;modeMatches=0;pyCRLF=0;textCRLF=0;staticOther=0;unknownMode=0
 for name,e in sourceFiles.items():
  archive=prefix+name;assert archive in payload;b=payload[archive];original=sourceBodies[name]
  i=info[archive];mode=i.external_attr>>16 if isinstance(i,zipfile.ZipInfo) else i.mode;available=i.create_system==3 if isinstance(i,zipfile.ZipInfo) else True
  if available:assert mode&0o777==int(e[0][-3:],8);modeMatches+=1
  else:unknownMode+=1
  if b==original:matched+=1
  elif b.replace(b'\r\n',b'\n')==original:
   assert b.count(b'\r\n')>0
   if name.endswith('.py'):pyCRLF+=1
   else:textCRLF+=1
  else:
   assert name=='actions/server/_static_contents.py';staticOther+=1
 return {'tracked':215,'body_equal':matched,'CRLF_only_Python':pyCRLF,'CRLF_only_other_text':textCRLF,'generated_static_additional_difference':staticOther,'recorded_full_Unix_permission_equal':modeMatches,'Unix_permission_unavailable':unknownMode}
wheelRows=[]
for record in report['wheels']:
 name=Path(record['file']['path']).name;b=distributionBodies[name];assert Path(record['file']['path']).read_bytes()==b;payload,info=unzip(b);assert len(payload)==221
 root='actions_runtime-1.0.3.dist-info/';m=metadata(payload[root+'METADATA']);w=email.parser.BytesParser().parsebytes(payload[root+'WHEEL']);cp=record['python_abi'];plat=record['platform'];assert cp in ['cp312','cp313']
 tags=['manylinux_2_5_x86_64','manylinux1_x86_64','manylinux_2_17_x86_64','manylinux2014_x86_64'] if plat=='Linux' else ['win_amd64'] if plat=='Windows' else ['macosx_12_0_arm64'];assert w['Root-Is-Purelib']=='false' and w.get_all('Tag')==[cp+'-'+cp+'-'+tag for tag in tags] and name=='actions_runtime-1.0.3-'+cp+'-'+cp+'-'+'.'.join(tags)+'.whl'
 ep=configparser.ConfigParser();ep.read_string(payload[root+'entry_points.txt'].decode());assert ep.sections()==['console_scripts'] and dict(ep['console_scripts'])==project['scripts']
 rows=list(csv.reader(io.StringIO(payload[root+'RECORD'].decode())));assert len(rows)==221 and all(len(x)==3 for x in rows) and len({x[0] for x in rows})==221 and {x[0] for x in rows}==set(payload)
 for path,h,size in rows:
  if path==root+'RECORD':assert h==size==''
  else:
   data=payload[path];assert h=='sha256='+base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=') and size==str(len(data))
 package=[n for n in payload if n.startswith('actions/')];assert len(package)==217 and sum(n.endswith('.py') for n in package)==202 and sum(not n.endswith('.py') for n in package)==15
 counts=compare(payload,info)
 if plat=='Windows':
  assert counts=={'tracked':215,'body_equal':36,'CRLF_only_Python':173,'CRLF_only_other_text':5,'generated_static_additional_difference':1,'recorded_full_Unix_permission_equal':0,'Unix_permission_unavailable':215}
  t=ast.parse(payload['actions/server/_static_contents.py']);sourceT=ast.parse(sourceBodies['actions/server/_static_contents.py']);decodedCR=sum(n.value.count(b'\r' if isinstance(n.value,bytes) else '\r') for n in ast.walk(t) if isinstance(n,ast.Constant) and isinstance(n.value,(str,bytes)));sourceCR=sum(n.value.count(b'\r' if isinstance(n.value,bytes) else '\r') for n in ast.walk(sourceT) if isinstance(n,ast.Constant) and isinstance(n.value,(str,bytes)));assert decodedCR==13 and sourceCR==0
 else:assert counts['body_equal']==counts['recorded_full_Unix_permission_equal']==215 and counts['Unix_permission_unavailable']==0
 category=oauth(payload['actions/server/_oauth2_config.py'])
 # All original inner central-directory inventories including modes/CRC/hash must agree.
 assert len(record['inventory'])==len(info)
 for e in record['inventory']:
  i=info[e['path']];data=payload.get(e['path'],b'');assert e['path'] in payload or i.is_dir();assert len(data)==e['bytes'] and digest(data)==e['sha256'] and f'{i.CRC:08x}'==e['crc32'] and oct(i.external_attr>>16)==e['unix_mode'] and i.create_system==e['create_system']
 wheelRows.append({'filename':name,'platform':plat,'ABI':cp,'bytes':len(b),'sha256':digest(b),'metadata':m,'RECORD_files':221,'RECORD_hashes':220,'Python_members':202,'nonPython_members':15,'entrypoints_exact_source':True,'tags_exact_filename_and_source_matrix':True,'source_comparison':counts,'generated_OAuth':category,'generated_static_decoded_CR':13 if plat=='Windows' else 0,'consumer_native_execution':'NOT_RUN'})
assert len({(w['platform'],w['ABI']) for w in wheelRows})==6
sdist=report['sdist'];sdname=Path(sdist['file']['path']).name;sdb=distributionBodies[sdname];assert Path(sdist['file']['path']).read_bytes()==sdb
payload={};infos={}
with tarfile.open(fileobj=io.BytesIO(sdb),mode='r:gz') as tf:
 members=tf.getmembers();assert len(members)==221 and len({m.name for m in members})==221
 for m in members:
  safeName(m.name);assert m.name.startswith('actions_runtime-1.0.3/') and m.isfile() and m.size<=128*1024*1024;data=tf.extractfile(m).read();assert len(data)==m.size;payload[m.name]=data;infos[m.name]=m
for e in sdist['inventory']:
 m=infos[e['path']];data=payload[e['path']];assert len(data)==e['bytes'] and digest(data)==e['sha256'] and oct(m.mode)==e['mode'] and m.uid==e['uid'] and m.gid==e['gid'] and not e['directory']
with gzip.GzipFile(fileobj=io.BytesIO(sdb)) as gf:
 while gf.read(1048576):pass
prefix='actions_runtime-1.0.3/';sdmeta=metadata(payload[prefix+'PKG-INFO']);assert tomllib.loads(payload[prefix+'pyproject.toml'].decode())['tool']['poetry']==project
sdcounts=compare(payload,infos,prefix+'src/');assert sdcounts['body_equal']==sdcounts['recorded_full_Unix_permission_equal']==215 and not any('/bin/rcc' in n for n in payload);sdoauth=oauth(payload[prefix+'src/actions/server/_oauth2_config.py'])
# Original builder checkout identities in the owned decoded logs; no raw text output.
logRows=[]
for e in v['old_original_three_builder_logs_reused']+[v['new_original_Mac_builder_log']['file']]:
 check(e);assert stat.S_IMODE(Path(e['path']).stat().st_mode)==0o600;lines=Path(e['path']).read_text().splitlines();hits=[]
 for i,line in enumerate(lines):
  if 'git' in line and 'log -1' in line and '--format' in line:
   for j in range(i+1,min(i+4,len(lines))):
    if BUILD in re.findall(r'\b[0-9a-f]{40}\b',lines[j]):hits.append({'command_line':i+1,'SHA_line':j+1});break
 assert len(hits)==1;logRows.append({'file':e,'authenticated_decoded_checkout':BUILD,'checkout_observation':hits[0],'scope':'Original decoded text bytes, not compressed server log archive'})
mac=Path(v['new_original_Mac_builder_log']['file']['path']).read_text();marker='Verified uncached PyPI Runtime dependency artifacts: ';floors=[json.loads(line.split(marker,1)[1]) for line in mac.splitlines() if marker in line];assert len(floors)==1
fixed={k:{'version':x['version'],'sha256':x['sha256']} for k,x in floors[0].items()};assert fixed==v['new_original_Mac_builder_log']['existing_builder_cp312_published_floor_marker'][0]['allowlisted_package_versions_and_digests']
# Preserve original v4 inputs and failed-before-worker facts separately from v5 preparation.
for e in [v['Linux_v4_consumer_input_preservation']['unchanged_frozen_v4_input_manifest'],v['Linux_v4_consumer_input_preservation']['unchanged_original_Linux_cp312_input']]:check(e)
assert v['Linux_v4_consumer_input_preservation']['unchanged_frozen_v4_input_manifest']['sha256']=='798f11c5416e57d6d0fa39c79c9524fc52e2e022496c1c3f12b3c902facc61d3' and v['Linux_v4_consumer_input_preservation']['unchanged_original_Linux_cp312_input']['sha256']=='90a785d81ca1158ab58a3feb0eabc1b3b3dabb6e395f2f503337c2cf53e986d6'
doc=load(v['Documentation_improvement']['path']);guide=Path(doc['canonical_file']).read_text()
for e in doc['exact_deltas']:check(e['exact_patch']);assert e['exact_delta'] in guide
trace=load(v['previous_owners_and_all_binding_bytes_unchanged'][2]['owner']['path']);refs=trace['confirmed']['encoder_source_refs'];taskbody=git('show',SOURCE+':'+refs['public_source_path']);taskAST=ast.parse(taskbody)
assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='read_bytes' and n.lineno==refs['read_bytes_line'] for n in ast.walk(taskAST));assert any(isinstance(n,ast.keyword) and n.arg=='newline' and isinstance(n.value,ast.Constant) and n.value.value=='\n' for n in ast.walk(taskAST))
for e in v['evidence']:check(e)
proof={'schema':'independent-data-only-complete-seven-distribution-integrity/v1','owner_final':binding(owner),'actual_source':SOURCE,'actual_source_tree':TREE,'actual_ordered_parents':v['actual_integration_Git']['ordered_parents'],'original_producer':{'checkout':BUILD,'ordered_parents':[BASE,SOURCE],'tree':TREE,'run':38126987514,'identity_scope':'Synthetic build e766 remains distinct from actual integration618 despite fulltree equality'},'bindings':{'new':17,'prior':217,'all_hash_size_exact':True},'original_archive_count':{'new':2,'prior':3,'total':5,'aggregate_outer_members':8,'distributions':7,'manifest':1},'all_outer_and_inner_ZIP_paths_unique_safe_bounded_CRC_bytes_complete':True,'all_seven_platform_distributions_byteequal_aggregate':True,'six_wheel_slots':wheelRows,'sdist':{'filename':sdname,'sha256':digest(sdb),'bytes':len(sdb),'members':221,'allmember_hash_size_mode_UID_GID_recorded_exact':True,'gzip_EOF_CRC_ISIZE':True,'METADATA':sdmeta,'project_exact_source':True,'tracked_source':sdcounts,'generated_OAuth':sdoauth,'embedded_RCC_members':0},'aggregate_manifest':{'bytes':939,'rows':7,'sha256':digest(expectedManifest),'source_sha256':digest(publisher),'sorted_original_digests_doubleSpace_filename_LF_exact':True,'publisher_AST_source_authority_observed_only_NOT_RUN':True},'four_original_builder_decoded_logs':logRows,'new_Mac_floor_marker':{'sample':'EXISTING_BUILDER_CP312_ONLY','allowlisted_versions_and_SHA':fixed,'not_cp313_or_new_installed_consumer_qualification':True},'Linux_v4_input_exact_unchanged':True,'Windows_scope':{'perwheel_raw_source_matches':36,'perwheel_Python_CRLF_only':173,'perwheel_other_text_CRLF_only':5,'perwheel_static_additional_difference':1,'perwheel_decoded_static_CR':13,'Unix_permission_identity':'UNAVAILABLE','semantic_equivalence':'NOT_ESTABLISHED','historical_checkout_vs_compiler_cause':'UNKNOWN'},'generated_OAuth_authority':'HOLD_BOTH_FIXED_ENTRIES_EMPTY_ALL_SIX_WHEELS_AND_SDIST','installed_consumer_native_private_registry_tag_release':'HOLD_NOT_RUN_BY_REVIEWER','canonical_exact_source_backed_reuse':doc,'no_download_metadata_poll_package_import_install_build_source_control_execution_native_provider_browser_push_merge':True,'upstream_disposition':'none'}
p=D/'independent-complete-original-distribution-data-proof.json';assert not p.exists();p.write_text(json.dumps(proof,indent=2)+'\n');p.chmod(0o600)
final={'schema':'actions.independent-current618-seven-distribution-ownerfinal-review/v1','verdict':'GO_COMPLETE_ORIGINAL_DISTRIBUTION_INVENTORY_AND_INTEGRITY_ONLY','owner_final':binding(owner),'independent_data_proof':binding(p),'subject':{'actual_source':SOURCE,'actual_tree':TREE,'original_synthetic_producer':BUILD,'producer_ordered_parents':[BASE,SOURCE],'run':38126987514,'new_artifact_IDs':[11698787320,11698838081],'new_Mac_log_job':114433293230},'verified':{'new17_prior217_binding_SHA_sizes':True,'six_wheels_plus_sdist':True,'aggregate8_members_seven_exact_original_distributions_plus939B7row_manifest':True,'all_CRC_and_wheel_RECORD220hash221file_source_metadata_deps_tags_entrypoints':True,'Mac_Linux_all215_tracked_source_bodies_and_fullrecorded_modes':True,'sdist_all215_tracked_source_bodies_and_modes':True,'four_original_decoded_builder_logs_e766_not_relabeled_actual618':True,'original_v4_90a_wheel_and798f_manifest_retained':True},'findings':[],'holds':['Allsix wheels/sdist OAuth two fixed entries empty; approved source/content authority HOLD','Windows173Python+5othertextCRLF and1additionalstatic/13decodedCR differences; semantic equivalence NOT_ESTABLISHED, historical causation UNKNOWN, Unix mode unavailable','Current installed-platform consumers/native/browser/provider/private/backend/registry/tag/fullrelease acceptance remain separate; failed Linux gateway-before-worker/install and v5 preparation do not constitute actual PASS'],'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md','Exact_delta_disposition':'Accept verified existing9744 policy/snapshot, bf95 partialplatform/syntheticidentity, and1306 generatedstatic/completecheckout lessons verbatim in owning guide; no cosmetic addition','Durable_learning_captured':'Complete seven distribution/aggregate integrity is distinct from source-body identity, generated-input authority and actual platform consumer qualification; eighth manifest typed separately; syntheticproducer remains distinct from equal-tree actual integration','Evidence':'Allseven originalplatform distribution bytes equal aggregate, manifest exactsourcepublisherAST format, sixRECORD/metadata/tags/deps, all215Mac/Linux/sdistGitbodies+modes; Windows rawdifferences andemptyOAuth measured separately; fouroriginalcheckout logs','Stale_or_ambiguous_guidance_removed':'Seven distributions are not eight outermembers or seven consumers; CR-removal diagnostic comparison is not semantics/source waiver; LF module writing does not normalize embedded assets','Remaining_uncertainty':'Windows historicalcause/semantics, Unixmodeunavailable, approved generatedOAuth source/content, actualcurrentinstalledconsumers and private/native/releasegraph'},'upstream_disposition':'none'}
f=D/'OWNERFINAL-independent-current618-seven-distribution-integrity-review.json';assert not f.exists();f.write_text(json.dumps(final,indent=2)+'\n');f.chmod(0o600);print(json.dumps({'OWNERFINAL':binding(f),'proof':binding(p)}))
