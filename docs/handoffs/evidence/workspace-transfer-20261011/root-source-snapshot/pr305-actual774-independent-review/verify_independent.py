from pathlib import Path,PurePosixPath
import subprocess,json,hashlib,stat,os,re
R=Path('/workspace/engineering/pr305');D=Path('/workspace/engineering/pr305-actual774-independent-review');S=Path('/workspace/engineering/pr305-actual774-refresh');H='723397b748b48282e13480b0ab7e4cb4c7e10c8c';A='1e9c462fc16534f1a6153ef666ae60a9ac9560d6';B='774438b130afb2ead9bbc1c1b76cb6f91e72150a';T='a58412bc551d5927580d9d9d6f5fb8989c67ffc2';V='3ec9d0acbe30ad94d02e4c24fef2587127964495';N='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def leaves(c):return {n.decode():meta.decode().split() for row in git('ls-tree','-rz',c).split(b'\0') if row for meta,n in [row.split(b'\t',1)]}
receipt=S/'frozen-source-receipt.json';assert sha(receipt)=='0d21c19c364d2529dcccec9fd967ee467d3928cbfb8aa8929d884d1c2c2533c7';v=json.loads(receipt.read_text());refs=[]
def inspect(x):
 if isinstance(x,dict):
  if {'path','sha256','bytes'}<=x.keys() and isinstance(x['path'],str):assert bind(x['path'])=={k:x[k] for k in ('path','bytes','sha256')};refs.append(bind(x['path']))
  for z in x.values():inspect(z)
 elif isinstance(x,list):
  for z in x:inspect(z)
inspect(v)
assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse',H+'^{tree}').decode().strip()==T and git('show','-s','--format=%P',H).decode().split()==[A,B];assert git('status','--porcelain')==b''
a,b,c,n,h=map(leaves,(A,B,H,N,V));assert len(c)==1410 and a.keys()<=c.keys() and b.keys()<=c.keys();novel={p for p in c if c[p] not in (a.get(p),b.get(p))};assert novel<={'docs/skills/repository-operations.md'}
for p,e in c.items():
 if e[1]=='blob' and e[0]!='120000':assert (R/p).read_bytes()==git('show',H+':'+p)
 elif e[0]=='120000':assert os.readlink(R/p).encode()==git('show',H+':'+p)
assert all(c[p]==b[p] for p in b if p.startswith('.github/'))
proof=json.loads((S/'source-union-proof.json').read_text());inp=proof['producer_inputs'];five=proof['five'];assert len(inp)==268 and len(five)==5 and not (inp.keys()&five.keys())
for p,e in {**inp,**five}.items():assert e==c[p]==a[p]==b[p]==n[p]==h[p]
frontend=json.loads((S/'named-frontend-wrapper-source-retention.json').read_text());assert frontend['count']==85 and len(frontend['entries'])==85
for p,e in frontend['entries'].items():assert c[p]==a[p]==h[p]==n[p]==e
for p,e in v['owned_Canvas_fixtures_and_authoring_exact_original1e9'].items():assert c[p]==a[p]==e
reuse=json.loads((S/'bootstrap-reuse.json').read_text());assert reuse['input_count']==24 and len(reuse['inputs'])==24
for p,e in reuse['inputs'].items():assert sha(R/p)==e
own=json.loads((S/'own-env-origin-proof.json').read_text());assert len(own['records'])==5
for e in own['records']:
 assert e['own_prefix'] is True and e['own_source'] is True and Path(e['prefix'])==R/e['package']/'.venv';assert Path(e['source']).is_relative_to(R/e['package']/'src');assert sha(e['source'])==e['source_sha256'];assert sha(Path(e['prefix'])/'pyvenv.cfg')==e['venv_config_sha256']
patch=git('diff',A,H,'--','docs/skills/repository-operations.md','docs/skills/work-items.md');assert patch==(S/'canonical-imported-delta.patch').read_bytes();(D/'canonical-reviewed-imported-delta.patch').write_bytes(patch)
assert '1200 passed, 12 skipped' in (S/'full-source.log').read_text() and '46 passed, 2 deselected' in (S/'scoped.log').read_text() and '69 passed' in (S/'toolkit.log').read_text();static=(S/'static.log').read_text();assert 'Success: no issues found in 338 source files' in static and '302 files already formatted' in static
retained=json.loads((S/'retained-native-helper-browser-and-V5-proof.json').read_text());inspect(retained);inventory=json.loads(Path(retained['original_inventory']['path']).read_text());root=Path('/workspace/engineering/pr310-runner-qualification-owned/dist/action-server');entries=[]
for p in sorted(root.rglob('*'),key=lambda z:z.relative_to(root).as_posix()):
 kind='symlink' if p.is_symlink() else 'directory' if p.is_dir() else 'file' if p.is_file() else 'UNSUPPORTED';assert kind!='UNSUPPORTED';entries.append({'path':p.relative_to(root).as_posix(),'kind':kind,'mode':stat.S_IMODE(p.lstat().st_mode),'link_target':p.readlink().as_posix() if p.is_symlink() else None,'content_sha256':sha(p) if p.is_file() else None})
assert len(entries)==1192 and entries==inventory;assert retained['historical_V5_source']['head']==V and retained['historical_V5_source']['native_producer']==N
for e in retained['frozen_helper_original_and_snapshot_bindings'].values():assert e['original']['sha256']==e['snapshot']['sha256'] and stat.S_IMODE(Path(e['snapshot']['path']).stat().st_mode)==0o444
roundtrip=json.loads((S/'generator-roundtrip.json').read_text());assert roundtrip['before']==roundtrip['after'] and len(roundtrip['before'])==26
result={'head':H,'tree':T,'ordered_parents':[A,B],'clean':True,'leaves':len(c),'novel_leafs_only_docs':sorted(novel),'complete_current_working_blob_bytes_exact_frozen_Git':True,'all_old_target_leaves_present':True,'whole_github_exact_target':True,'production268_selected5_combined273_exact1e9_774_3ec_92498':True,'frontend_wrapper85_named_inputs_exact1e9_3ec_92498':True,'three_owned_fixture_authoring_Gitblobs_exact1e9':True,'own24_prepared_inputs_and_five_concrete_source_prefix_bindings_exact':True,'nested_receipt_reference_bindings':refs,'original1192_tree_entries_modes_hashes_symlink_targets_exact':True,'original_helpers_snapshots_readonly_exact':True,'V5historical_tuple_unchanged_notcurrent_actual':True,'canonical_imported_delta':bind(D/'canonical-reviewed-imported-delta.patch'),'fresh_recorded_full1200_12_scoped46_2deselect_Toolkit69_static338_gen8_26outputs_30trackedYAML_source_only':True,'no_native_browser_provider_actual_run_or_push':True};p=D/'independent-complete-source-and-retained-byte-proof.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'nested_bindings':len(refs)},indent=2))
