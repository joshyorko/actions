"""Read-only source/AST/identity inventory; writes only new private proposal files."""
import ast, difflib, hashlib, json, os, stat, subprocess
from pathlib import Path
BASE=Path(__file__).resolve().parent
CP=Path('/workspace/engineering/campaign-checkpoint')
REPO=Path('/workspace/engineering/pr308')
SOURCE='8d49d0865ad5ad27b2d4e325ec135212080625e8'
PRIVATE=Path('/workspace/engineering/rcc-current8d49-private-V8-real-fixture-mode-successor')
SHARED=Path('/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation')
QUALIFIED=Path('/workspace/engineering/rcc-current8d49-qualified-V8-config-preparation')
RELOAD=Path('/workspace/engineering/pr308-current8d49-managed-reload-drain-private-preparation')
def digest(b): return hashlib.sha256(b).hexdigest()
def binding(p):
 p=Path(p); m=p.lstat(); assert stat.S_ISREG(m.st_mode) and not p.is_symlink()
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':digest(b),'mode':oct(stat.S_IMODE(m.st_mode))}
def git(*args): return subprocess.check_output(['git','-C',str(REPO),*args])
def save(name, j):
 p=BASE/name;assert not p.exists();b=(json.dumps(j,indent=2,sort_keys=True)+'\n').encode();p.write_bytes(b);p.chmod(0o400);return binding(p)
oldmanifest=CP/'docs/program/evidence/wave11/current-engineering-successor-20261011/curated-safe-manifest-v7.json'
old=json.loads(oldmanifest.read_bytes());assert len(old['rows'])==84
oldverified=[]
for r in old['rows']:
 p=CP/r['proposed_successor_relative_path'];b=p.read_bytes();assert len(b)==r['bytes'] and digest(b)==r['sha256']
 oldverified.append({'sha256':r['sha256'],'bytes':r['bytes'],'durable_path':str(p.relative_to(CP))})
prior=Path('/workspace/engineering/private-handoff-current1935-successor-PREPARATION')
priorfiles=[prior/'OWNERFINAL-private-current1935-additive-handoff-PROPOSAL.json',prior/'proposed-additive-safe-reference-manifest.json',prior/'proposed-1935Z-engineering-handoff-successor.md']
prior_bindings=[binding(p) for p in priorfiles]
assert [(x['bytes'],x['sha256']) for x in prior_bindings]==[(5606,'d5fe68a6346bc0be49b429886be0274906ea4091b43046116180d9cfb6f65de8'),(22481,'4bd2e8ea96b0062b21c2c3b23571d59e067b11ebd6a5eb65a488de114c9524e9'),(3837,'4edb3381a10a99e05afed665261f9571dcc7613bfa056983008835d506ef2cce')]
current=json.loads(priorfiles[1].read_bytes())
# Match all frozen prior payload SHA tuples; names/extensions are not evidence.
known={r['sha256'] for r in oldverified}
for r in current['selected_rows']:
 def walk(x):
  if isinstance(x,dict):
   if 'sha256' in x: known.add(x['sha256'])
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(r)
modules=[PRIVATE/x for x in ['owned_cache_policy_v8.py','actual_transport_v8.py','historical_binding_current8d49_v8.py','fixture_records_v8.py']]+[SHARED/x for x in ['runner_contracts_v3.py','owned_monitor_v1.py','historical_binding_v1.py','historical_failed_receipt_archive_v1.py']]
reloadsource=RELOAD/'test_current_managed_reload_sqlite_pool_barriers.py'
adapterpath='action_server/tests/action_server_tests/test_rcc_runtime_adapter.py'
original=git('show',SOURCE+':'+adapterpath)
prospective=(RELOAD/'prospective-current-test_rcc_runtime_adapter-with-nine-servicefree-controls.py').read_bytes()
newsource=reloadsource.read_bytes();assert prospective==original+b'\n\n'+newsource
original_ast=ast.parse(original.decode());future_ast=ast.parse(prospective.decode())
assert ast.dump(ast.Module(body=future_ast.body[:len(original_ast.body)],type_ignores=[]),include_attributes=False)==ast.dump(original_ast,include_attributes=False)
patch=''.join(difflib.unified_diff(original.decode().splitlines(True),prospective.decode().splitlines(True),fromfile='a/'+adapterpath,tofile='b/'+adapterpath,n=3)).encode()
patchfile=BASE/'proposed-current8d49-adapter-nine-controls-append-only.patch';assert not patchfile.exists();patchfile.write_bytes(patch);patchfile.chmod(0o400)
extras=[reloadsource,patchfile,RELOAD/'nine-real-SQLite-pool-barrier-baseline-and-private-mutant-RED-plan-NOTRUN.json',RELOAD/'current8d49-reload-drain-recontext-implementation-and-admission.md',RELOAD/'canonical-current-source-reload-drain-transaction-scope-proposed.patch']
rows=[]
for i,p in enumerate(modules+extras,1):
 r=binding(p);assert r['sha256'] not in known
 r.update({'proposed_durable_path':'docs/handoffs/evidence/actions-swarm-mk3-20261011-1935Z-source-closure/'+f'{i:02d}-'+p.name,'content_class':'PUBLIC_SOURCE_OR_TEST_OR_BOUNDED_PATCH_NO_PRIVATE_PAYLOAD','copied_Git_mode':'100644','execution':'NOT_RUN_BY_THIS_PREPARATION'})
 rows.append(r)
assert len({r['sha256'] for r in rows})==len(rows)
assert sum(r['bytes'] for r in rows)<=150000
snapshot=PRIVATE/'historical-e4ff-staged-fixture-exact-Git-blob.snapshot.py'
oldsource='e4ff080375a8422bb656e52d218f198521dda078';histpath='action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'
hist=git('show',oldsource+':'+histpath);assert hist==snapshot.read_bytes()
assert len(hist)==48314 and digest(hist)=='af2f79ccd395c088076381f6681860cf8160f8fd0d9169e122634fe684c37c35'
ancestor=subprocess.run(['git','-C',str(REPO),'merge-base','--is-ancestor',oldsource,SOURCE],check=False).returncode;assert ancestor==0
imports=[]
for p in modules+[QUALIFIED/x for x in ['build_qualified_current8d49_config_v8_FINAL.py','managed_one_version_entry_v8.py','launch_one_version_v8.py','readonly_current_input_guard_v8.py','gateway_entry_v8.py']]+[reloadsource]:
 tree=ast.parse(p.read_text()); rowsimp=[]
 for n in ast.walk(tree):
  if isinstance(n,ast.Import):rowsimp.extend(a.name for a in n.names)
  elif isinstance(n,ast.ImportFrom) and n.module:rowsimp.append(n.module)
 imports.append({'source':binding(p),'imports':sorted(set(rowsimp))})
# Explicit dynamic ownership loader, source-buffer import and self-launch path.
helper=Path('/workspace/actions-cloud/receipts/pr305-runner/frozen-helpers/verify_dakota_rcc_acceptance.py')
helperbinding=binding(helper);assert helperbinding['sha256']=='60acf72569c2dfe5748f45ac6c3bf4cc8621e28955a4afa3dbf2f417d7290659'
manifest={
 'schema':'PRIVATE_ADDITIVE_EXACT_SOURCE_CLOSURE_PROPOSAL_ONLY',
 'status':'PREPARED_NOT_COPIED_NOT_ADOPTED_NOT_EXECUTED',
 'source':SOURCE,'tree':git('rev-parse',SOURCE+'^{tree}').decode().strip(),
 'original1935_immutable':prior_bindings,'old84_manifest':binding(oldmanifest),'old84_exact_copied_rows_verified':84,
 'old84_coverage_sha256':digest(json.dumps(oldverified,sort_keys=True).encode()),
 'additional_rows':rows,'additional_original_bytes':sum(r['bytes'] for r in rows),'additional_unique_count':len(rows),
 'existing_constructor_and_four_entry_guard_modules':'Exact five bodies already selected by original1935; not duplicated here',
 'direct_import_graph':imports,
 'historical_fixture_reconstruction':{'source':oldsource,'ancestor_of_current_source':True,'tree':git('rev-parse',oldsource+'^{tree}').decode().strip(),'git_path':histpath,'blob_entry':git('ls-tree',oldsource,'--',histpath).decode().strip(),'bytes':len(hist),'sha256':digest(hist),'existing_private_snapshot':binding(snapshot),'new_copy_required':False,'proposed_later_reconstruction':['git -C /workspace/engineering/pr308 show '+oldsource+':'+histpath+' > <exclusive-private-snapshot-path>','Require48314bytes/af2f79... exactSHA; chmod0444; preserve required exact accepted snapshot filename/parent mapping'],'executed_here':False},
 'reload_application':{'baseline':{'source':SOURCE,'path':adapterpath,'bytes':len(original),'sha256':digest(original)},'standalone':binding(reloadsource),'prospective_full_module':binding(RELOAD/'prospective-current-test_rcc_runtime_adapter-with-nine-servicefree-controls.py'),'reconstruction':'original tracked adapter bytes + two LF bytes + exact standalone source bytes','whole_original_AST_prefix':'EXACT','compact_append_patch':binding(patchfile),'three_paths':'Combine already-selected ec231 persistent staging+guide patch with this adapter-only append patch and scoped1021 reload canonical; source adoption/new controls need distinct root authorization','nine_controls':'PREPARED_NOT_RUN'},
 'ownership_frozen_loader':{'required_external_public_helper':helperbinding,'loader':'actual_transport_v8 load_verified_helper hashes original bytes then compile/exec verified buffer; observer identifies existing Linux helper self-launch path; __file__ remains immutable original path','snapshot_or_helper_copies_here':False},
 'external_required_inputs_not_committed':['Original absolute-path private config and ROOT release; no caller-generated/relabelled approval','Approved binary3/5/7276 exactbytes and original provenance/managedactivation19/prepared Python+toolkit/pytest/psutil','Current8d49 tracked Runtime source and real fixtures; prior source/control tuples remain separate','Historical raw receipt archives/indices/maps referenced by hashed bindings, external-only','Distinct root capacity/serialization and reviewed actual execution release; no native permission implied'],
 'limitations':['This is source closure, not a standalone executable package or fresh functional qualification','Original absolute imports/paths unchanged; durable copies need explicitly reviewed staging to immutable original namespace or equivalent exact-path plan','Latest FIVE48capFAIL preserved; mutable V5storage preparation excluded','NativefirstnewerNONE; nine reloadcontrolsNOTRUN; production/currentPR308 unchanged'],
 'privacy_review':'Source AST/text only; no rawconfig/index/ZIP/binary/log/APIresponse/signedURL/memberpayload copied. Fixed path/hash admission constants and controlled test data are retained.',
 'documentation_improvement':{'canonical_file':'docs/skills/repository-operations.md','delta':'Reuse existing config-consumed-path dependency closure and temporal historical-alias/source-identity guidance; zero new canonical lines','evidence':'c39564ff existing source-closure canonical in old84 + exact AST import graph/af2f Git blob + prospective adapter reconstruction','stale_ambiguity_removed':'Owner receipts alone do not contain their imported executable source; source reuse must bind body SHA rather than filename','remaining_uncertainty':'Separate root source/actual grants, private inputs and all release/native/wholegraph holds remain'},
 'upstream_disposition':'none','worktree_index_Git_product_mutations':False,'tests_or_native_or_imported_payload_execution':False}
manifestbinding=save('proposed-unique-safe-source-closure-manifest.json',manifest)
for before in prior_bindings:assert binding(before['path'])==before
owner={'schema':'OWNERFINAL_PRIVATE_SOURCE_CLOSURE_PROPOSAL','status':'FROZEN_SOURCE_ONLY_PREPARATION_NO_APPLICATION_OR_EXECUTION','manifest':manifestbinding,'constructor':binding(__file__),'source':SOURCE,'tree':manifest['tree'],'additional_unique_files':len(rows),'additional_bytes':manifest['additional_original_bytes'],'historical48314_fixture':'Exact existing Git blob/ancestry proved; no redundant copy; original mode0444 required for later reviewed reconstruction','original1935_immutable':prior_bindings,'source_runtime_closure':'Eight additional modules plus existing five1935 constructor/entry/guard modules; historical snapshot and external immutable helper privately required','reload':'Exact standalone nine-control source plus compact append-only patch; testsNOT_RUN; current adapter unchanged','root_adoption_required':True,'nativefirstnewer':'NONE','canonical_delta':'Existing sourceclosure guidance reused; no additional canonical prose','upstream_disposition':'none'}
ob=save('OWNERFINAL-private-current1935-unique-safe-source-closure-PROPOSAL.json',owner)
print(json.dumps({'owner':ob,'manifest':manifestbinding,'additional_files':len(rows),'additional_bytes':manifest['additional_original_bytes'],'old84_verified':84},sort_keys=True))
