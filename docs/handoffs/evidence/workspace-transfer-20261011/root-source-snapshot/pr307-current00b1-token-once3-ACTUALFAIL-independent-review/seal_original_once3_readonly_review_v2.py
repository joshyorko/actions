import ast, hashlib, json, os, re, stat, subprocess, tomllib, xml.etree.ElementTree as ET
from pathlib import Path
D=Path('/workspace/engineering/pr307-current00b1-token-once3-ACTUALFAIL-independent-review'); R=Path('/workspace/engineering/pr307-current00b1-token-light-once3-owned'); W=Path('/workspace/engineering/pr307'); P=Path('/workspace/engineering/pr307-current00b1-token-light-once3-PREEXECUTION-NOTRUN'); O=Path('/workspace/engineering/root-pr307-current00b1-reviewed-token-light-once3-outer')
S='00b1bb9974b73f2da65e49c9048774c84df286ba'; T='2663e86b2344f9e056c3259653cb905a6d195599'; OLD='c97edfd10edb5b1c63f8a6371bfd2905996a2da2'
def sha(b):return hashlib.sha256(b).hexdigest()
def bind(p):
 p=Path(p); st=p.lstat(); assert stat.S_ISREG(st.st_mode) and not p.is_symlink(); b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b),'mode':oct(stat.S_IMODE(st.st_mode))}
def load(p):return json.loads(Path(p).read_text())
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(W),*a],env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
owner=bind(O/'OWNERFINAL-root-one-original-reviewed-current00b1-token-light-once3-outer.json');assert owner['bytes']==1164 and owner['sha256']=='9449bf7a824b018d2b860ea0a6681af584f35a79df37d8e1cfe94b111e81c2c9'
root=load(owner['path']);assert root['source']==S and root['tree']==T and root['outer_returncode']==1
cfg=load(P/'immutable-one-TOKEN-LIGHT-once3-inputs.json'); refs=[]
for row in cfg['bindings']:
 b=bind(row['path']);assert all(b[k]==row[k] for k in ['bytes','sha256','mode']);refs.append(b)
assert len(refs)==85
assert git('rev-parse','HEAD').decode().strip()==S and git('rev-parse',S+'^{tree}').decode().strip()==T
assert git('show','-s','--format=%P',S).decode().strip()==OLD
assert not git('status','--porcelain','--untracked-files=no')
entries=git('ls-tree','-r','-z',S).split(b'\0'); source_count=0
for record in entries:
 if not record:continue
 meta,path=record.split(b'\t',1); mode,kind,oid=meta.split(); rel=path.decode(); p=W/rel; blob=git('cat-file','blob',oid.decode());st=p.lstat()
 if mode==b'120000':assert p.is_symlink() and os.readlink(p).encode()==blob
 else:assert stat.S_ISREG(st.st_mode) and p.read_bytes()==blob and bool(st.st_mode&0o111)==(mode==b'100755')
 source_count+=1
assert source_count==1442
before=load(R/'before-guard.json');post=load(R/'always-post-guard.json');external=[]
for item in [before,post]:assert item['status']=='PASS' and item['source']==S and item['tree']==T and item['typed_FS_rows']==1442 and item['prepared_inputs']==30 and item['five_configs']==5
for n in ['external-before-envelope.json','external-always-post-envelope.json']:
 p=O/n; v=load(p);assert v['status']=='PASS' and v['exact_binding_count']==96; external.append(bind(p))
censuses={};evidence=[owner,bind(R/'original-terminal.json'),bind(R/'before-guard.json'),bind(R/'always-post-guard.json'),*external]
for ph,counts in [('toolkit',(179,0,0,0)),('token-release-line-GREEN',(99,0,0,0)),('guard-focus',(41,0,0,0)),('token-RED-parent2314',(2,2,0,0))]:
 p=R/ph/'junit.xml';cases=list(ET.parse(p).getroot().iter('testcase'));ids=[(c.get('classname'),c.get('name')) for c in cases];c=(len(cases),sum(c.find('failure') is not None for c in cases),sum(c.find('error') is not None for c in cases),sum(c.find('skipped') is not None for c in cases));assert c==counts and len(set(ids))==c[0]
 terminal=load(R/ph/'terminal.json');assert terminal['returncode']==terminal['expected_returncode'];censuses[ph]={'unique_cases':c[0],'passed':c[0]-sum(c[1:]),'failures':c[1],'errors':c[2],'skips':c[3],'gateway_returncode':terminal['returncode']};evidence.extend(bind(R/ph/f) for f in ['junit.xml','terminal.json','stdout.bin','stderr.bin'])
redstderr=(R/'token-RED-parent2314/stderr.bin').read_text(errors='replace');assert 'returned non-zero exit status 1' in redstderr and 'toolkit.py' in redstderr
static=load(R/'configured-static/terminal.json');assert static['returncode']==10 and static['expected_returncode']==0
stdout=(R/'configured-static/stdout.bin').read_text(errors='replace');stderr=(R/'configured-static/stderr.bin').read_text(errors='replace');assert 'returned non-zero exit status 1' in stderr and 'toolkit.py' in stderr
leaves=[x.removeprefix(str(W)+'/') for x in re.findall(r'^ERROR: (.+) Imports are incorrectly sorted and/or formatted\.$',stderr,re.M)]
expected=['devutils/src/devutils/fixtures.py','devutils/tests/test_http_helper_tests_workflow.py','devutils/tests/test_runtime_conformance.py','devutils/tests/test_invoke_utils.py'];assert leaves==expected
failed=[]
for rel in leaves:
 b=bind(W/rel); assert (W/rel).read_bytes()==git('show',OLD+':'+rel);failed.append(b)
evidence.extend(bind(R/'configured-static'/f) for f in ['terminal.json','stdout.bin','stderr.bin'])
pkg=W/'devutils'; lock=tomllib.loads((pkg/'poetry.lock').read_text());assert [p['version'] for p in lock['package'] if p['name']=='isort']==['5.13.2']
metadata=pkg/'.venv/lib/python3.12/site-packages/isort-5.13.2.dist-info/METADATA';assert metadata.exists() and '\nVersion: 5.13.2\n' in metadata.read_text()
config_sources=[]
for base in [pkg/'src',pkg,pkg.parent]:
 for n in ['.isort.cfg','pyproject.toml','setup.cfg','tox.ini','.editorconfig']:
  p=base/n
  if p.is_file():config_sources.append(bind(p)); assert n=='.editorconfig' or '[tool.isort]' not in p.read_text()
config_sources.extend(bind(p) for p in [pkg/'poetry.lock',metadata,pkg/'.venv/bin/isort',pkg/'ruff.toml'])
proposal='''After an owning-package Isort failure, retain the exact reported file scope and settings-search context. A package without an Isort profile does not inherit another package's Black profile. Preserve import bindings in each lexical scope and non-import bodies when sorting imports; verify the same files with both the owning Ruff formatter and Isort before accepting a formatting-only successor. A newly reached failing tool does not invalidate earlier completed phases or qualify phases that never ran.\n'''
doc=D/'canonical-owning-isort-settings-and-sequential-static-scope-proposed.txt'; assert not doc.exists();doc.write_text(proposal);doc.chmod(0o400)
result={'construction_history':{'original_constructor':'seal_original_once3_readonly_review.py','failure':'TypeError: guard capture fields are fixed integer counts, not lists; corrected only reviewer parsing before receipt seal','no_tests_or_source_mutation':True},'schema':1,'status':'INDEPENDENT_ORIGINAL_CURRENT00B1_ONCE3_ACTUALFAIL_CONFIRMED','decision':'HOLD_SOURCE_PUSH_AND_FULL_NATIVE_AUTHORITY','source':S,'tree':T,'parent':OLD,'original_root':owner,'outer_returncode':1,'outer_elapsed_seconds':root['elapsed_seconds'],'current_source_at_review':{'clean':True,'full_typed_Git_FS_body_exec_mode_count':1442},'original_actual_censuses':censuses,'primary_failure':{'phase':'configured-static','gateway_returncode':10,'checked_inner_returncode':1,'tool':'Isort','installed_and_locked_version':'5.13.2','command_from_original':'poetry run isort --check src tests','cwd':str(pkg),'reported_four_leaf_bindings':failed,'all_four_unchanged_from_c97':True,'preceding_static_results':{'Runtime_format_files':317,'Runtime_mypy_files':354,'OAuth_helper_format_files':2,'OAuth_helper_mypy_files':1,'Devutils_Ruff_format_files':20,'Ruff_checks':'PASS'},'failure_scope':'import sorting/formatting; exact required text transform NOT_RUN by reviewer','cleanup_final_readers_and_descendant_census':'UNKNOWN'},'remaining_phases':{'Devutils_mypy_after_Isort':'NOT_RUN','workflow_generation':'NOT_RUN','controlled_Invoke':'NOT_RUN'},'guards':{'child_before_and_alwayspost':'PASS','consumed_exact_bindings':85,'ROOT_external_before_and_alwayspost_exact_binding_count':96,'prepared_inputs':30,'own_environment_configs':5},'settings_provenance':{'installed_Metadata_and_package_lock_confirm':'5.13.2','Devutils_pyproject_Isort_profile':'ABSENT','Runtime_Isort_profile':'black; distinct owning package','static_settings_search':'first directory src -> Devutils -> repository .editorconfig; indent4 and package defaults79/GRID/profile empty','actual_show_config':'NOT_RUN/NOT_PRINTED; settings are source-derived, not a new tool observation','bindings':config_sources},'minimal_authorized_source_proposal':{'existing_branch_parent':S,'only_four_import_sort_leaves':expected,'procedure':'Use owning locked Isort5.13.2 from Devutils with same settings search context; explicitly --settings-path src if necessary to preserve actual src/tests search. Sort only these four reported leaves. Keep configs, gates, imports/aliases/names and all non-import executable/assertion bodies unchanged. Verify own Ruff0.1.15 formatter and Isort on the same leaves, then full configured scopes. If incompatible output is measured, stop and preserve diagnostics; do not borrow Runtime Black profile or silently alter gates.','proof':'Compare import binding multisets per lexical scope and all non-import AST; import-order AST itself may legitimately change. All other typed body/modes remain exact. Preserve once3 FAIL and prior once1/once2; fresh descendant and separate ROOT once4 authorization required.','full_gate':'MANDATORY_NOT_RUN; no source push until accepted LIGHT and later full source gate'},'evidence_bindings':evidence,'consumed_85_bindings':refs,'Documentation improvement':{'Canonical file changed or proposed':'docs/skills/repository-operations.md; proposed insertion adjacent to owning formatter/package-scope guidance','Durable learning captured':proposal.strip(),'Evidence':[str(R/'configured-static/terminal.json'),str(R/'configured-static/stderr.bin'),str(pkg/'poetry.lock'),str(pkg/'pyproject.toml'),str(pkg.parent/'.editorconfig')],'Stale or ambiguous guidance removed':'Do not infer cross-package Isort profile, whole-module AST equality after import sorting, or successful later tools from a partially completed static phase.','Remaining uncertainty':'No reviewer formatting execution; exact edits and simultaneous Ruff/Isort compatibility await bounded writer checks; FULL/native/OAuth/release remain HOLD.','Exact proposed delta':bind(doc)},'Upstream disposition':'none','review_operations':'Read-only source/Git/stdlib parsing and hashing; wrote owned review outputs only. No tests/imports/helper replay/source/ref/index/push/ready/merge/download/native operation.'}
out=D/'OWNERFINAL-independent-original-current00b1-token-once3-ACTUALFAIL-and-owning-Isort-four-leaf-proposal.json';assert not out.exists();out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');out.chmod(0o400);print(json.dumps(bind(out)));print(json.dumps(bind(doc)))
