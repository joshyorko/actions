import ast,difflib,hashlib,json,os,re,stat,subprocess
from pathlib import Path
R=Path('/workspace/engineering/pr282');D=Path('/workspace/engineering/pr282-current-c35e-independent-LIGHT-review');O=Path('/workspace/engineering/pr282-actual309-refresh')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for v in iter(lambda:f.read(1048576),b''):h.update(v)
 return h.hexdigest()
def bind(p):
 p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def check(row):
 b=bind(row['path']);assert b['bytes']==row['bytes'] and b['sha256']==row['sha256'];assert int(b['mode'],8)==int(str(row['mode']),8) if 'mode' in row else True
 return b
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def inv(ref):
 out={}
 for rec in git('ls-tree','-rz',ref).split(b'\0'):
  if rec:
   m,p=rec.split(b'\t',1);out[p.decode()]=m.decode().split()
 return out
ownerp=O/'OWNERFINAL-current-c35e-ordinary-a0d-source-LIGHT-full-and-actual-HOLD.json';assert sha(ownerp)=='79513104c6a9b9bc67d6b1d58ce2993bead4cc8db156dee99ab0dada3ecd12b8';v=json.loads(ownerp.read_bytes());refs=[check(row) for row in v['evidence_bindings']];assert len(refs)==39
assert git('rev-parse','HEAD').decode().strip()==v['head'];assert git('rev-parse','HEAD^{tree}').decode().strip()==v['tree'];assert not git('status','--porcelain');assert git('branch','--show-current').decode().strip()==v['branch'];assert git('show','-s','--format=%P','HEAD').decode().split()==v['ordered_parents']
a,b=[inv(p) for p in v['ordered_parents']];current=inv(v['head']);assert len(a)==1433 and len(current)==1435 and set(current)==set(a)|set(b)
novel=[p for p,row in current.items() if row not in [a.get(p),b.get(p)]];assert novel==['docs/skills/repository-operations.md']
for p,row in a.items():assert p in current and (row==current[p] or p=='docs/skills/repository-operations.md')
for p,row in b.items():assert p in current and (row==current[p] or p=='docs/skills/repository-operations.md')
proof=json.loads((O/'FROZEN-staged-automatic-a0d-union-proof.json').read_bytes());assert current==proof['typed_union']
old=git('show',v['ordered_parents'][0]+':docs/skills/repository-operations.md').decode().splitlines(keepends=True);new=git('show','HEAD:docs/skills/repository-operations.md').decode().splitlines(keepends=True);ops=list(difflib.SequenceMatcher(a=old,b=new,autojunk=False).get_opcodes());assert all(tag in ('equal','insert') for tag,*_ in ops);assert sum(j2-j1 for tag,i1,i2,j1,j2 in ops if tag=='insert')==58
post=json.loads((O/'FROZEN-post-LIGHT-complete-source-original-bytes-modes.json').read_bytes());pre=json.loads((O/'FROZEN-before-source-original-e736-bindings.json').read_bytes());oldmodes={row['path']:row['current_FS_mode'] for row in pre['source_FS_rows']}
for row in post['source_FS_rows']:
 p=R/row['path'];mode=stat.S_IMODE(p.lstat().st_mode);body=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes();assert len(body)==row['bytes'] and hashlib.sha256(body).hexdigest()==row['sha256'];assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==row['blob'];assert oct(mode)==row['current_FS_mode'];assert row['path'] not in oldmodes or oldmodes[row['path']]==oct(mode)
ref441=[check(row) for row in pre['all_bound_refs_current_bytes_modes']];assert len(ref441)==441
historical=json.loads(Path('/workspace/engineering/pr282-actual618-refresh/frozen-source-receipt.json').read_bytes());native=json.loads(Path(historical['retained_owned_artifacts']['original1192_native_helper0444_browser_V5']['after']['path']).read_bytes());proposal=json.loads(Path(native['immutable_proposal']['path']).read_bytes());layout=Path(proposal['native']['layout'])/'dist/action-server';inventory=json.loads(Path(native['original_inventory']['path']).read_bytes());assert len(inventory)==1192 and {p.relative_to(layout).as_posix() for p in layout.rglob('*')}=={r['path'] for r in inventory}
for row in inventory:
 p=layout/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert sha(p)==row['content_sha256'] and not p.is_symlink()
 elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert p.is_symlink() and os.readlink(p)==row['link_target']
for group in native['frozen_helper_original_and_snapshot_bindings'].values():
 for key in ('original','snapshot'):assert sha(group[key]['path'])==group[key]['sha256']
 assert stat.S_IMODE(Path(group['snapshot']['path']).stat().st_mode)==0o444
v5=json.loads(Path(native['historical_V5_checkpoint']['path']).read_bytes());assert len(v5['raw_receipts_private_do_not_commit'])==18 and len(v5['frozen_posthashes'])==50
for row in v5['raw_receipts_private_do_not_commit']:assert sha(row['path'])==row['sha256']
for row in v5['frozen_posthashes']:
 if sha(row['path'])!=row['sha256']:
  rel=Path(row['path']).relative_to('/workspace/engineering/pr305').as_posix();body=subprocess.check_output(['git','-C','/workspace/engineering/pr305','show','3ec9d0acbe30ad94d02e4c24fef2587127964495:'+rel]);assert hashlib.sha256(body).hexdigest()==row['sha256']
gen='.github/workflows/_gen_workflows.py';original='9c8f1c95caeded6495877280ed1465fd9850b254'
def method(raw):return next(n for n in ast.walk(ast.parse(raw)) if isinstance(n,ast.FunctionDef) and n.name=='published_canvas_acceptance')
assert ast.dump(method(git('show',original+':'+gen)))==ast.dump(method(git('show','HEAD:'+gen)))
# Whole tracked workflow files are identical to e736, a stronger check than a
# parser-only equality of the Canvas step. No generator execution in review.
assert all(current[p]==row for p,row in a.items() if p.startswith('.github/'))
prep=json.loads((O/'own-Bootstrap-reuse-inputs-and-origins.json').read_bytes());assert len(prep['inputs_exact_prepared_git_bytes_sha256'])==30 and len(prep['own5actual_prefix_and_source_origin_assertions'])==5
for p,h in prep['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/p)==h
assert sha(prep['original_bootstrap_log'])==prep['original_bootstrap_log_sha256'] and prep['new_Bootstrap_executed'] is False
terminal=json.loads((O/'one-root-released-LIGHT-final-terminal.json').read_bytes());assert len(terminal['records'])==8 and all(row['returncode']==0 for row in terminal['records'])
counts=[]
for row in terminal['records']:
 check(row['original_log']);raw=Path(row['original_log']['path']).read_text();assert 'SUCCESS' in raw;counts.append({'scope':row['scope'],'returncode':0,'pytest_terminal_summaries':re.findall(r'\d+ passed[^\r\n]*',raw),'ruff_format_file_counts':re.findall(r'\d+ files? (?:left unchanged|already formatted)',raw),'mypy_source_counts':re.findall(r'Success: no issues found in \d+ source files?',raw)})
y=json.loads((O/'generator-roundtrip.json').read_bytes());assert len(y['generated_workflows'])==8 and len(y['before'])==26 and y['before']==y['after'];assert len(y['additional_yaml_parsed_and_bytes_preserved'])==4 and y['all_tracked_yaml_count']==30
for p,h in {**y['after'],**y['additional_yaml_parsed_and_bytes_preserved']}.items():assert sha(R/p)==h
assert historical['current_producer']['current']==275 and proof['oldmatches']==259 and proof['changed']==9 and proof['added']==7 and proof['selected_tests_separate']==5
result={'status':'GO_SOURCE_LIGHT_ONLY_FULL_ACTUAL_PUSH_HOLD','head':v['head'],'tree':v['tree'],'ordered_parents':v['ordered_parents'],'source_owner':bind(ownerp),'independent_checks':{'owner_direct_refs':39,'retained_current_refs':441,'current_leaf_count':1435,'old_leaf_count':1433,'no_deletions':True,'only_novel_blob':'docs/skills/repository-operations.md','guide_addition_lines':58,'whole_GitHub_original_body_mode_exact':True,'Canvas_entire_method_AST_exact_original9c':True,'all_current_source_FS_body_mode_exact':True,'old_source_modes_preserved':True,'native_original_inventory_members':1192,'helper_snapshots_0444':True,'historical_raw_V5_receipts':18,'historical_V5_posthashes':50,'prepared_inputs':30,'recorded_concrete_own_origins':5,'configured_LIGHT_scopes':8,'generated_roundtrips':8,'all_tracked_YAML':30},'gates_read_only_log_evidence':counts,'production_scope':{'production':275,'old268_match':259,'changed':9,'added':7,'selected_tests_separate':5,'native_qualification':'UNQUALIFIED'},'remaining_hold':['Current full configured source gate NOT_RUN','Distinct root capacity/serialized full release','Fresh hosted CI and normal push review','All native/browser/provider/private actual historical scope retained; no actual run in this review','10 unavailable historical workspace refs remain UNAVAILABLE; source original scope retained by immutable Git where recorded'],'documentation_improvement':v['documentation_improvement'],'exact_imported_guide_patch':bind(O/'exact-both-parent-canonical-import.patch'),'upstream_disposition':'none','evidence_refs':refs,'reviewer_script':bind(__file__)}
p=D/'OWNERFINAL-independent-c35e-SOURCE-LIGHT-review.json';assert not p.exists();p.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');p.chmod(0o600);print(json.dumps(bind(p),sort_keys=True))
