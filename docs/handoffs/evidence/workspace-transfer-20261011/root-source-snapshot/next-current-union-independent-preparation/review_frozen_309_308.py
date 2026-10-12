from pathlib import Path
import hashlib
import json
import subprocess

TARGET='1c7585fe8bb3cb9476c3997570bd3f04466f2bbc'
GUIDE='docs/skills/repository-operations.md'
CONFIGS={
 309:{'head':'0d947f839628cc902bd409a7be93dcb49bc0aa02','tree':'ec4d3d4e6ad9fc0dc9450254698b4827c7f734d5','merge':'51392cfcb6e8e09968e359e45a9ace3b4c6afbc0','old':'41d4ee41190d7d3f3969212471863c70852295ba','merge_tree':'65b4ed6efe2b26e7192fe8981a84d4fc0050d7fb','receipt_sha':'7654ba25146baecf37b18423183ef3609c5fd231ecc19f81d0d6393fdd258906','scoped':80,'full':1153,'types':338,'numstat':'5\t1','owned':['action_server/tests/action_server_tests/test_auth_route_inventory.py']},
 308:{'head':'9025a1e44bb05992e9f220842bfaf16a99ebd04f','tree':'b658453c78785aaaf5b998ef1e1aaade4174377d','merge':'87962e6214f502948d2cc2df442167cdd02509d2','old':'483e3e735c268b08acba1fd3930a9a34e0deaa91','merge_tree':'391daa0d048a701ae25d5c4b8b6522930b389338','receipt_sha':'804e7de01f982a3d4901c52b9ac765c3e3491a98f135792287bc4a9220252b20','scoped':37,'full':1152,'types':337,'numstat':'7\t0','owned':['action_server/scripts/verify_dakota_rcc_acceptance.py','action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py']},
}
def binding(p):
 b=p.read_bytes();return{'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def git(n,*args):return subprocess.check_output(['git','-C',f'/workspace/engineering/pr{n}',*args])
def tree(n,x):
 d={}
 for row in git(n,'ls-tree','-rz',x).split(b'\0'):
  if row:
   meta,path=row.split(b'\t',1);d[path.decode()]=tuple(v.decode()for v in meta.split())
 return d

producer=json.loads(Path('/workspace/engineering/native292-owned/producer-input-inventory.json').read_text())
selected=json.loads(Path('/workspace/engineering/native292-owned/selected-test-inventory.json').read_text())
for n,c in CONFIGS.items():
 h,m,o=c['head'],c['merge'],c['old'];owned=Path(f'/workspace/engineering/pr{n}-actual311-refresh');out=Path(f'/workspace/engineering/pr{n}-actual311-independent-review');repo=Path(f'/workspace/engineering/pr{n}')
 receipt=owned/'frozen-source-receipt.json';assert binding(receipt)['sha256']==c['receipt_sha'];r=json.loads(receipt.read_text())
 assert git(n,'log','-1','--format=%H %T %P',h).decode().strip()==f"{h} {c['tree']} {m}"
 assert git(n,'show','-s','--format=%P',m).decode().strip()==f'{o} {TARGET}'
 assert git(n,'rev-parse',m+'^{tree}').decode().strip()==c['merge_tree']
 assert not git(n,'status','--porcelain')and git(n,'rev-parse','HEAD').decode().strip()==h
 old,target,merge,current=map(lambda x:tree(n,x),[o,TARGET,m,h])
 assert set(old)<=set(merge)and set(target)<=set(merge)
 assert {p for p in current if current[p]!=merge.get(p)}=={GUIDE}
 unchanged=sum(current[p]==merge[p]for p in merge)
 assert unchanged==len(current)-1
 ancestor=git(n,'merge-base',o,TARGET).decode().strip();base=tree(n,ancestor);checked=0;both=[]
 for p in set(base)|set(old)|set(target):
  s,t,b=old.get(p),target.get(p),base.get(p)
  if s==t:e=s
  elif s==b:e=t
  elif t==b:e=s
  else:both.append(p);continue
  assert merge.get(p)==e,p;checked+=1
 assert both==[GUIDE]
 beforeguide=git(n,'show',m+':'+GUIDE).decode()
 for sha in [o,TARGET]:
  additions=[line[1:]for line in git(n,'diff','--unified=0',ancestor,sha,'--',GUIDE).decode().splitlines()if line.startswith('+')and not line.startswith('+++')and line[1:].strip()]
  assert all(line in beforeguide for line in additions)
 for p in c['owned']:assert current[p]==merge[p]==old[p]and(repo/p).read_bytes()==git(n,'show',h+':'+p)
 assert all(current[p]==target[p]for p in current if p.startswith('.github/'))
 assert all(current[p]==target[p]for p in target if p not in set(c['owned'])|{GUIDE})
 for inv in [producer,selected]:
  for p,e in inv.items():
   assert current[p]==old[p]==target[p]
   assert current[p][0]==e['mode']and current[p][1]==e['kind']and current[p][2]==e['blob']
   assert hashlib.sha256(git(n,'show',h+':'+p)).hexdigest()==e['sha256']
 assert len(producer)==268and len(selected)==5
 for e in r['gate_logs'].values():assert binding(Path(e['path']))==e
 for key in ['source_proof','source_inspector','bootstrap_reuse','original_bootstrap','generator_roundtrip']:
  e=r[key];assert binding(Path(e['path']))==e
 for e in r['old_receipts_own_original_identities']:assert binding(Path(e['path']))==e
 cached=r['cached_GitHub_control']['receipt'];assert binding(Path(cached['path']))==cached
 reuse=json.loads(Path(r['bootstrap_reuse']['path']).read_text());assert reuse['input_count']==len(reuse['inputs'])==24and reuse['own_five_package_environments_present']and reuse['no_installer']
 for path,sha in reuse['inputs'].items():
  raw=git(n,'show',h+':'+path);assert hashlib.sha256(raw).hexdigest()==sha and raw==git(n,'show',reuse['prepared_source']+':'+path)and(repo/path).read_bytes()==raw
 assert all((repo/p/'.venv/pyvenv.cfg').exists()for p in ['actions','action_server','actions-http-helper','devutils','work-items'])
 original=Path(reuse['original_log']);assert binding(original)['sha256']==reuse['sha256']and 'actual main robot run" was SUCCESS'in original.read_text()
 full=(owned/'full-source.log').read_text()
 assert f"{c['full']} passed, 13 skipped, 15 warnings"in full and '+ poetry run invoke test-not-integration'in full and 'actual main robot run" was SUCCESS'in full
 assert f'/workspace/engineering/pr{n}/action_server/.venv/bin/python'in full
 assert "'-m', 'not integration_test'"in full
 assert f"{c['scoped']} passed, 1 deselected"in(owned/'scoped.log').read_text()
 assert '69 passed'in(owned/'toolkit.log').read_text()
 static=(owned/'static.log').read_text()
 for needle in ['+ poetry run invoke lint','poetry run isort --check src tests','+ poetry run invoke typecheck',f"Success: no issues found in {c['types']} source files",'actual main robot run" was SUCCESS']:assert needle in static
 roundtrip=json.loads((owned/'generator-roundtrip.json').read_text());assert roundtrip['before']==roundtrip['after']and len(roundtrip['before'])==26
 for path,sha in roundtrip['before'].items():assert hashlib.sha256(git(n,'show',h+':'+path)).hexdigest()==sha
 patch=out/'canonical-integrated-actual311-delta.patch';patch.write_bytes(git(n,'diff',m,h,'--',GUIDE));e=r['documentation_improvement']['Exact_delta'];assert binding(Path(e['path']))==e and patch.read_bytes()==Path(e['path']).read_bytes()
 assert git(n,'diff','--numstat',m,h).decode().strip()==c['numstat']+'\t'+GUIDE
 subprocess.check_call(['git','-C',str(repo),'diff','--check',m,h])
 if n==309:
  text=git(n,'show',h+':'+c['owned'][0]).decode()
  for needle in ['actual = Counter(identities)','expected = Counter(policy.keys())','unexpected = actual - expected','missing = expected - actual','route_pattern = getattr(route, "path_format", route.path)','methods = tuple(sorted(getattr(route, "methods", ()) or ()))','test_auth_route_inventory_rejects_new_uncategorized_route']:
   assert needle in text
  behavior='Unchangedrealroute graph captured at before_start returnsFalse beforepool/Uvicorn; Counter ofrouteclass/Starlettepath_format/complete_sortedmethodtuple recordsmultiplicity/hiddenroute/terminalmount andrejectsextraormissingidentity. Existingstartupbarrier anduncategorizednegative controls meaningful; handwrittenclassification isnotrequestcredentialenforcement oroptionaltransport coverage.'
  holds=['Full#152 missing/wrong/validcredential, GETHEAD/download/WebSocket/streaming/sideeffect rejection and trusted optionaltransport/requestmatrix remainseparateHOLD.']
 else:
  text=git(n,'show',h+':'+c['owned'][0]).decode()
  for needle in ['def validate_candidate_wheel_metadata(','if len(metadata_members) != 1:', 'metadata_text = archive.read(metadata_members[0]).decode("utf-8")','actual_distribution != expected_distribution','actual_version != expected_version','"sha256": sha256_file(wheel.path)']:
   assert needle in text
  behavior='Unchangedcandidateverifier reads pinnedPoetry checkedsource versions, selects expectedwheel filename, requiresoneMETADATAmember/UTF8andexpectedNameVersion; separatewholewheel digest recordsbytes. Source/mockbaseline andmetadata-poison controls remainmeaningful but no actualnewPoetrywheel/provider execution. No claim of unique metadataheaderkeys beyondimplemented .get behavior.'
  holds=['Full#134 originalprivate01f/fafb/frozenv6spec-runner absent; currentmetadata/public RCC scopes notwholeacceptance.','37servicefreecontrols/1realRCCdeselect do notproveactualcandidatewheelbuild/RCC/provider/warmcache/native; historical67e82/e339failedwrapperexit-1 andactualsourceversionidentities retained.']
 result={
  'verdict':f'GO_NORMAL_GUARDED_EXISTING_REF_PUSH_EXACT_{h}_ACTUAL311_SOURCE_REFRESH; HOLD_FRESH_HOSTED_MERGE_AND_FULL'+('152'if n==309else'134'),
  'scope':'independentread-only frozen source/evidence/doc acceptance; no source/gate/native/provider/browser execution or push',
  'source':{'head':h,'tree':c['tree'],'parent':m,'ordinary_merge_tree':c['merge_tree'],'ordered_ordinary_parents':[o,TARGET],'actual_target_tree':'35a5168a3904ba41e29047fec2a4cd3b50880a78','same_existing_branch':r['branch'],'clean':True},
  'independent_preservation':{'old_and_target_leaf_sets_retained':True,'old_leaves':len(old),'target_leaves':len(target),'final_leaves':len(current),'ordinarynonconflicting_threeway_paths_checked':checked,'onlyboth_changedguide':both,'both_parent_guide_addedblocks_retained':True,'ownedimplementation_modes_blobs_unchanged':{p:current[p]for p in c['owned']},'all_other_nonowned_modes_blobs_exact_target':True,'final_only_delta':'canonicalguide5add1remove'if n==309else'canonicalguide7add','final_all_other_modes_blobs_equal_tested_union':unchanged,'native268_mode_blob_SHA_exact_old_target_reference':True,'selected5_mode_blob_SHA_exact_old_target_reference':True,'whole_github_generator_workflows_exact_actualtarget':True},
  'behavior_and_negative_control_review':behavior,
  'fresh_actual_source_checks':{'Doctor':'PASS','Bootstrap':'verified24input_sourcebyteequalprepared/fiveownpyvenvconfigs_present; existingownedBootstraplogPASS;noinstaller','Toolkit':69,'scoped_pass':c['scoped'],'integration_or_real_RCC_deselected':1,'source_pass':c['full'],'source_skips':13,'warnings':15,'full_configured_lint':'Ruffcheck/format/IsortPASS','configured_typecheck_files':c['types'],'all_YAML_dependabot_roundtrip':26,'actual_source_python':f'/workspace/engineering/pr{n}/action_server/.venv/bin/python','gate_source':'ordinaryunion with finalguide workingtext; frozenchild changesonlyguide andallotherleafpairs match','canonicaldiffcheck':'PASS'},
  'original_worker_receipt':binding(receipt),'verified_raw_log_bindings':r['gate_logs'],'verified_source_proof':r['source_proof'],'verified_source_inspector':r['source_inspector'],'verified_Bootstrap_reuse':r['bootstrap_reuse'],'original_Bootstrap_binding':r['original_bootstrap'],'historical_original_receipts_retained':r['old_receipts_own_original_identities'],'cached_old_control_retained':r['cached_GitHub_control'],
  'held_gates':['Fresh exactnewhead/source/control/actualtarget19declaredhostedjobs/reviews/threads/draft/policy beforemerge; earlierfbde/sourceheadCI ishistorical, no oldgreen carry.','If actualtargetadvancesbeforeintegration recomputeordinaryunionandrequiredgates; sourceparity alone notadmissionoflaterbase.','268+5trackedinputparityis scopedproducer sourceevidence, not newactualwheel/frozen/platform/managedCore/lifecycle/releaseexecution.']+holds+['Private metadata/fullRuntime1.0.3publication andremaining retainedacceptancegraph remainHOLD.'],
  'canonical_documentation':{'canonical_file':GUIDE,'exact_integrated_delta':binding(patch),'disposition':'GO_INTEGRATED currentfrozen guideclarification; originalimplementation/test assertionsunchanged; no duplicatedsourceproposalneeded','durable_learning':r['documentation_improvement']['Durable_learning'],'evidence':'directunchangedsource semanticinspection/currentrawscoped+fullconfigured sourcegates/24inputreuse/268+5sourceparity/26YAMLroundtrip','stale_ambiguity':r['documentation_improvement']['Stale_or_ambiguous_guidance_removed'],'remaining_uncertainty':r['documentation_improvement']['Remaining_uncertainty'],'upstream':'none'},
 }
 p=out/'independent-frozen-source-review.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(binding(p)))
