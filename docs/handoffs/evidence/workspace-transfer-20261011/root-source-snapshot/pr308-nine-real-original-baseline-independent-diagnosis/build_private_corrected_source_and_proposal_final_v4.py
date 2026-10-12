import ast, datetime, difflib, hashlib, json, os, stat
from pathlib import Path
ROOT=Path('/workspace/engineering/pr308-nine-real-private-catalog-lock-source-successor-final-v4-NOTRUN')
ROOT.mkdir(mode=0o700,exist_ok=False);os.umask(0o077)
def row(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(s.st_mode))}
def put(name,value,mode=0o444):
 p=ROOT/name
 if not isinstance(value,(str,bytes)):value=json.dumps(value,sort_keys=True,indent=2)+'\n'
 if isinstance(value,str):value=value.encode()
 with p.open('xb') as f:f.write(value);f.flush();os.fsync(f.fileno())
 p.chmod(mode);return row(p)
oldroot=Path('/workspace/engineering/pr308-current8d49-managed-reload-drain-private-preparation')
oldowner=oldroot/'OWNERFINAL-current8d49-managed-reload-drain-private-source-and-nine-real-controls-PREPARED-NOTRUN.json'
o=json.loads(oldowner.read_bytes()); original=Path(o['private_control_source']['path']).read_text()
assert row(o['private_control_source']['path'])==o['private_control_source']
helper='''def _catalog_identity_snapshot(catalog):
    """Freeze field structure, object identity and values without mutable aliases.

    A rollback may copy the outer catalog. Its original field containers and
    nested objects must remain exact, including their immutable value payloads.
    """
    seen = set()

    def freeze(value):
        if isinstance(value, (type(None), bool, int, float, str, bytes)):
            return ("value", type(value), id(value), value)
        identity = id(value)
        if identity in seen:
            return ("reference", type(value), identity)
        seen.add(identity)
        if isinstance(value, dict):
            contents = tuple((freeze(key), freeze(item)) for key, item in value.items())
            return ("dict", type(value), identity, contents)
        if isinstance(value, (list, tuple)):
            return ("sequence", type(value), identity, tuple(freeze(item) for item in value))
        if callable(value):
            return ("callable", type(value), identity)
        try:
            fields = vars(value)
        except TypeError as error:
            raise AssertionError("UNSUPPORTED_CATALOG_SNAPSHOT_LEAF") from error
        contents = tuple((name, freeze(item)) for name, item in fields.items())
        return ("object", type(value), identity, contents)

    return (type(catalog), tuple((name, freeze(value)) for name, value in vars(catalog).items()))


'''
needle='def assert_last_good(c):\n';assert original.count(needle)==1
new=original.replace(needle,helper+needle)
needle="        original=dict(generation=pool.generation,routes=list(app.router.routes),catalog=routes.mcp_server_setup_helper._catalog,source=(old_dir/'my_actions.py').read_bytes())\n"
assert new.count(needle)==1
new=new.replace(needle,needle+"        original['catalog_identity_snapshot'] = _catalog_identity_snapshot(original['catalog'])\n")
needle="    assert c.routes.mcp_server_setup_helper._catalog is c.original['catalog']\n";assert new.count(needle)==1
new=new.replace(needle,"    assert _catalog_identity_snapshot(c.routes.mcp_server_setup_helper._catalog) == c.original['catalog_identity_snapshot']\n")
needle="    def check():\n        assert c.pool.generation == c.original['generation']\n";assert new.count(needle)==1
new=new.replace(needle,"    def check():\n        assert c.pool._lock.locked(), 'WARMUP_CALLBACK_REQUIRES_EXISTING_POOL_LOCK'\n        assert c.pool._generation == c.original['generation']\n")
old_ast=ast.parse(original);new_ast=ast.parse(new)
names_old=[n.name for n in old_ast.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
assert '_catalog_identity_snapshot' not in names_old
changed=[];new_by={n.name:n for n in new_ast.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
for n in old_ast.body:
 if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and ast.dump(n,include_attributes=False)!=ast.dump(new_by[n.name],include_attributes=False):changed.append(n.name)
assert changed==['catalog_case','assert_last_good','test_candidate_warmup_precedes_generation_switch']
old_tests=[n.name for n in old_ast.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
new_tests=[n.name for n in new_ast.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
assert old_tests==new_tests and len(new_tests)==9
assert "assert routes.mcp_server_setup_helper._catalog is original['catalog']" in new
assert "assert c.routes.mcp_server_setup_helper._catalog is not c.original['catalog']" in new
assert 'assert c.pool.generation==c.original[\'generation\']+1' in new
standalone=put('test_current_managed_reload_sqlite_pool_barriers_successor_v2.py',new)
prospective_old=Path(o['prospective_existing_adapter_test_append']['path']).read_bytes()
assert prospective_old.endswith(original.encode())
prefix=prospective_old[:-len(original.encode())]
current_adapter=Path('/workspace/engineering/pr308/action_server/tests/action_server_tests/test_rcc_runtime_adapter.py').read_bytes()
assert prefix==current_adapter+b'\n\n' and len(current_adapter)==84689
prospective=put('prospective-current-test_rcc_runtime_adapter-with-corrected-nine-controls-v2.py',prefix+new.encode())
prefix_ast=ast.parse(prefix);whole_ast=ast.parse(prefix+new.encode())
assert len(prefix_ast.body)==82
assert [ast.dump(x,include_attributes=False) for x in whole_ast.body[:82]]==[ast.dump(x,include_attributes=False) for x in prefix_ast.body]
patch=put('private-original-nine-to-catalog-lock-successor-v2.patch',''.join(difflib.unified_diff(original.splitlines(True),new.splitlines(True),fromfile='a/test_current_managed_reload_sqlite_pool_barriers.py',tofile='b/test_current_managed_reload_sqlite_pool_barriers.py')))
append=put('prospective-current-adapter-corrected-nine-append-only-v2.patch',''.join(difflib.unified_diff(prefix.decode().splitlines(True),(prefix+new.encode()).decode().splitlines(True),fromfile='a/action_server/tests/action_server_tests/test_rcc_runtime_adapter.py',tofile='b/action_server/tests/action_server_tests/test_rcc_runtime_adapter.py')))
plan={'schema':1,'status':'NOT_RUN_REQUIRES_INDEPENDENT_SOURCE_REVIEW_AND_DISTINCT_ROOT_RELEASE','old_120s_baseline_budget':'UNCHANGED','outer_450s_ROOT_budget':'UNCHANGED','future_owned_root':'/workspace/engineering/pr308-current8d49-nine-real-source-control-root-once-2 MUST_BE_ABSENT','original_once_1':'PRESERVE_ALL_BYTES','baseline_first':['Exactly original nine named cases once against v2; genuine 9PASS0F0E0SKIP JUnit required before mutants.','Original early_generation mutant must fail exact generation-order assertion under held lock, not timeout.','Original omit_idle_restore and omit_restore_token mutants must fail their original restoration predicates before snapshot tolerance could accept.','Other six original private mutants still require genuine expected assertion failures; no collection/import failures count.'],'new_snapshot_sensitivity_controls_NOTRUN':['Exact outer shallow copy with all original nested objects and fields accepted.','Different outer wrapper of same type with copied/replaced equal-valued field container rejected.','Same field container with equal-valued replacement nested Tool/ActionInfo object rejected.','Same original nested object with mutated description/action docs rejected by frozen scalar payload.','Added/deleted catalog field key rejected.','Dict membership/key/object mutation and list membership/order change rejected.','Cycle/shared-reference topology changes rejected or unsupported leaf fails closed.','Snapshot holds no original mutable value/container aliases; post-snapshot mutation must not update oracle.'],'lock_control_NOTRUN':['Callback is invoked by actual on_reload under original threading.Lock: explicit locked() witness and direct private _generation read.','No lock acquisition or call to public generation in callback; public post-admit generation predicate retained.'],'positive_native':'NOT_RUN_NOT_IN_SCOPE','source_adoption':'NONE'}
planrow=put('corrected-nine-baseline-first-and-identity-sensitivity-plan-NOTRUN.json',plan,0o400)
base=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md');text=base.read_text()
anchor='until their call completes and the wrapper is reaped.\n'
assert text.count(anchor)==1
paragraph='''
Reload rollback controls must follow the implementation's identity boundaries.
The server snapshots private helper values with shallow copies, so restoration
may replace the outer MCP catalog while retaining its original field objects.
Capture field keys, nested object identities and immutable value contents before
the call; do not require outer catalog identity or keep a mutable oracle alias.
A warmup seam runs under the process pool's nonreentrant lock. Observe its held
lock and private generation token without calling the lock-taking public getter;
retain the public generation assertion after the reload returns. A timed-out
baseline with missing JUnit remains failed, even when its private oracle is fixed.
'''
newguide=text.replace(anchor,anchor+paragraph)
guide=put('canonical-reload-control-copy-and-lock-boundaries-proposed.patch',''.join(difflib.unified_diff(text.splitlines(True),newguide.splitlines(True),fromfile='a/docs/skills/repository-operations.md',tofile='b/docs/skills/repository-operations.md')))
actual=Path('/workspace/engineering/pr308-nine-real-original-baseline-independent-diagnosis/OWNERFINAL-independent-original-nine-baseline-failure-and-private-control-boundary.json')
origrows=[]
def walk(v):
 if isinstance(v,dict):
  if all(k in v for k in ('path','bytes','sha256','mode')):origrows.append(v)
  else:
   for z in v.values():walk(z)
 elif isinstance(v,list):
  for z in v:walk(z)
walk(o)
for r in origrows:assert row(r['path'])==r
proof={'schema':1,'original_private_source':o['private_control_source'],'original_prospective_append':o['prospective_existing_adapter_test_append'],'standalone_successor':standalone,'prospective_successor':prospective,'current_adapter_original_prefix':row('/workspace/engineering/pr308/action_server/tests/action_server_tests/test_rcc_runtime_adapter.py'),'original_byte_prefix_bytes':84689,'unchanged_original_append_separator_bytes':2,'original_whole_AST_prefix_statements':82,'original_named_cases_exact_order':new_tests,'changed_original_definitions_only':changed,'one_added_snapshot_helper':'_catalog_identity_snapshot','other_original_definition_ASTs':'EXACT','product_source_changes':'NONE','all_original_owner_rows_exact':len(origrows),'catalog_contract':'Outer object identity exempt; exact field keys, nested mutable objects/containers/callables/scalar identities and frozen values unchanged. Snapshot consists only of tuples/scalars/type references with no mutable payload alias. Unsupported leaf fails closed.','lock_contract':'Original locked() nonblocking witness; _generation read under held lock; public property read only after return.','source':'8d49d0865ad5ad27b2d4e325ec135212080625e8','tree':'a80600809d373038ca76e445ba0b7b79bb7eeaa6','tests':'NOT_RUN','native':'NOT_RUN'}
proofrow=put('private-corrected-source-structural-scope-proof-NOTRUN.json',proof,0o400)
owner={'schema':1,'status':'PRIVATE_CORRECTED_NINE_SOURCE_PREPARED_NOT_RUN_PENDING_INDEPENDENT_GO_AND_ROOT_RELEASE','original_actual_failure':row(actual),'original_prepared_owner':row(oldowner),'original_bound_rows':origrows,'new_bindings':[standalone,prospective,patch,append,planrow,proofrow,guide],'source':proof['source'],'tree':proof['tree'],'source_leaves':1440,'exact_scope':proof,'tests':'NOT_RUN','mutants':'NOT_RUN','native':'NOT_RUN','product_adoption':'NONE','ROOTrelease':'NONE','documentation_improvement':{'canonical_file_proposed':'docs/skills/repository-operations.md','exact_delta':guide,'durable_learning':'Copy-aware catalog identity/content oracle and lock-aware warmup control; immutable snapshot prevents alias masking; old timeout not upgraded.','evidence':'Original catalog identity traceback in two cases; original seventh warmup callback entry without return; exact server copy(value) and threading.Lock/on_reload/generation source.','stale_or_ambiguous_guidance_removed':'No previous specific oracle/lock boundary existed; no product rollback defect inferred from private control failure.','remaining_uncertainty':'Corrected baseline, snapshot sensitivity controls and all nine mutant assertions have not executed; real native reload/drain/provider remains unqualified.'},'upstream_disposition':'none','capture':datetime.datetime.now(datetime.timezone.utc).isoformat()}
ownerrow=put('OWNERFINAL-private-corrected-nine-catalog-identity-and-held-lock-source-successor-NOTRUN.json',owner,0o400)
print(json.dumps({'owner':ownerrow,'canonical':guide,'standalone':standalone,'prospective':prospective}))
