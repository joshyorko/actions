import ast
import hashlib
import json
import subprocess
from pathlib import Path

root = Path('/workspace/engineering/rcc-public')
out = Path('/workspace/engineering/rcc-public-parent-deadline-source')
old = '44afd960ad01f83eeef7773b334ccde3683c022d'
first_target = '1c7585fe8bb3cb9476c3997570bd3f04466f2bbc'
first_merge = '5ce38be8e4ab735d33784eef3ed4cd88abb1741a'
source = '27e5939be0d6932b06bae233a7758d1bbcc9bf1a'
target = '774438b130afb2ead9bbc1c1b76cb6f91e72150a'
current_merge = '99e64a1c926f52f42698c4a5bc9f39d946827654'
native = '92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'
owned = {'action_server/scripts/verify_dakota_rcc_acceptance.py','action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py','docs/skills/repository-operations.md'}

def git(*args):
    return subprocess.check_output(['git','-C',str(root),*args])

def leaves(ref):
    return {name.decode():meta.decode().split() for row in git('ls-tree','-rz',ref).split(b'\0') if row for meta,name in [row.split(b'\t',1)]}

def body(ref, path):
    return git('show',ref+':'+path)

def merge_proof(left, right, result):
    a,b,c=map(leaves,(left,right,result))
    assert git('show','-s','--format=%P',result).decode().split()==[left,right]
    assert not (a.keys()-c.keys()) and not (b.keys()-c.keys())
    combined=[p for p in c if c[p] not in (a.get(p),b.get(p))]
    assert set(combined)<={'docs/skills/repository-operations.md'}
    return {'head':result,'tree':git('rev-parse',result+'^{tree}').decode().strip(),'ordered_parents':[left,right],'leaves':{'left':len(a),'right':len(b),'union':len(c)},'no_parent_leaf_deleted':True,'only_combined_parent_leaf':combined}

unions=[merge_proof(old,first_target,first_merge),merge_proof(source,target,current_merge)]
assert set(git('diff-tree','--no-commit-id','--name-only','-r',source).decode().splitlines())==owned
final=git('rev-parse','HEAD').decode().strip()
a,t,c,n=map(leaves,(old,target,final,native))
assert set(git('diff','--name-only',current_merge,final).decode().splitlines())<={p for p in owned if p.endswith('.py')}
proposal=json.loads(Path('/workspace/engineering/rcc-public-checkpoint-preparation/public-parent-deadline-source-proposal-v2.json').read_text())
eleven={}
for row in proposal['public_source']['original11_body_blob_identities']:
    p=row['path'];assert a[p][2]==row['git_blob'] and hashlib.sha256(body(old,p)).hexdigest()==row['sha256']
    if p not in owned:assert c[p]==a[p]
    eleven[p]={'original_mode_type_blob':a[p],'original_sha256':row['sha256'],'current_mode_type_blob':c[p],'unchanged':c[p]==a[p]}
assert all(c[p]==t[p] for p in t if p.startswith('.github/'))
script='action_server/scripts/verify_dakota_rcc_acceptance.py'
old_ast=ast.parse(body(old,script));current_ast=ast.parse((root/script).read_bytes())
new_functions={'_private_deadline_receipt_file','record_supervisor_deadline_failure'}
normalized=[]
for node in current_ast.body:
    if isinstance(node,ast.FunctionDef) and node.name in new_functions:continue
    if isinstance(node,ast.FunctionDef) and node.name=='main':
        outer=next(n for n in ast.walk(node) if isinstance(n,ast.Try) and any(isinstance(h.type,ast.Name) and h.type.id=='ProcessTreeCleanupError' for h in n.handlers))
        before=len(outer.handlers)
        outer.handlers=[h for h in outer.handlers if not (isinstance(h.type,ast.Attribute) and h.type.attr=='TimeoutExpired')]
        assert len(outer.handlers)==before-1
    normalized.append(node)
assert ast.dump(ast.Module(body=normalized,type_ignores=[]))==ast.dump(old_ast)
test='action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py'
old_test=ast.parse(body(old,test));new_test=ast.parse((root/test).read_bytes())
old_functions={n.name:n for n in old_test.body if isinstance(n,ast.FunctionDef)}
new_test_functions={n.name:n for n in new_test.body if isinstance(n,ast.FunctionDef)}
assert all(ast.dump(node)==ast.dump(new_test_functions[name]) for name,node in old_functions.items())
deps={f'{p}/{q}' for p in ('actions','action_server','actions-http-helper') for q in ('pyproject.toml','poetry.lock')}
producer=lambda entries:sorted(p for p in entries if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps)
baseline=producer(n);current=producer(c);changed=[p for p in baseline if c.get(p)!=n[p]];added=sorted(set(current)-set(baseline));removed=sorted(set(baseline)-set(current))
assert len(baseline)==268 and len(current)==269 and not removed
assert changed==['action_server/src/actions/server/_action_package_handler.py','action_server/src/actions/server/_actions_import.py','action_server/src/actions/server/_actions_process_pool.py','action_server/src/actions/server/_rcc_runtime_adapter.py']
assert added==['action_server/src/actions/server/rcc_trust_profile.py']
assert all(c[p]==a[p] for p in changed+added)
assert all(c[p]==t[p]==n[p] for p in baseline if p not in changed)
five=sorted(p for p in t if p.endswith(('/test_cli_mcp_catalog_rollback.py','/test_cli_live_reload_multi_package.py','/test_cli_successful_generation_drain.py','/test_cli_multi_package_sync.py','/test_cli_mcp_resource_history.py')))
assert len(five)==5 and all(c[p]==t[p]==n[p] for p in five)
allowed_mutation={test,script}
assert all((root/p).read_bytes()==body(current_merge,p) for p in c if c[p][1]=='blob' and p not in allowed_mutation)
bootstrap=json.loads((out/'bootstrap-preflight.json').read_text());assert len(bootstrap['inputs_sha256'])==24
assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==digest for p,digest in bootstrap['inputs_sha256'].items())
assert all((root/p/'.venv/pyvenv.cfg').is_file() and not (root/p/'.venv').is_symlink() for p in ('actions','action_server','actions-http-helper','devutils','work-items'))
proof={'status':'PASS','final_head':final,'final_tree':git('rev-parse','HEAD^{tree}').decode().strip(),'source_refreshes':unions,'source_checkpoint':{'head':source,'tree':git('rev-parse',source+'^{tree}').decode().strip(),'parent':first_merge,'only3_owned_paths':sorted(owned)},'original11':eleven,'whole_github_exact_current_actual_target':True,'original_verifier_AST_exact_after_removing2newfunctions_and1timeout_handler':True,'all_original_acceptance_test_functions_AST_unchanged':True,'new_acceptance_test_functions':sorted(new_test_functions.keys()-old_functions.keys()),'unchanged_owner_helpers':['run_owned_process','record_supervisor_cleanup_failure'],'watchdog':2465,'producer':{'native_source':native,'baseline_count':len(baseline),'current_count':len(current),'matches':len(baseline)-len(changed),'changed_original_public_inputs':changed,'added_original_public_inputs':added,'removed':removed,'qualification':'NOT_QUALIFIED_COMPLETE_PRODUCER_INVENTORY_DIFFERS','inventory':{p:c[p] for p in current}},'five290_selectors':{p:c[p] for p in five},'prepared24_inputs_exact_own_envs':True}
proof['producer']['inventory_sha256']=hashlib.sha256(json.dumps(proof['producer']['inventory'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
(out/'source-union-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
print('COMPLETE_UNION_ORIGINAL11_OWNER_AST_ALL269_INVENTORY_FIVE_SELECTOR_OWN_PREPARED24=PASS')
