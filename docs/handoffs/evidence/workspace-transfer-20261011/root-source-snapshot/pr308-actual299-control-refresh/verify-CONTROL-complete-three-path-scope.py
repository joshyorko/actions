from pathlib import Path
import ast,hashlib,json,subprocess,zipfile,os,re
R=Path('/workspace/engineering/pr308');O=Path('/workspace/engineering/pr308-actual299-control-refresh');S='c10380a4d2ebc6f0aca63eb85c8f84a337da4962';T='21676c626a933c2d55761ec85ecf26fe0eef26bb';oldS='7eb5bce946750555ab009f77592862920a901506';oldT='3ff76037779763d0461ff3a755b900c9ed83dcf8'
P=['.github/workflows/_gen_workflows.py','.github/workflows/actions_runtime_rcc_provider_rollback.yml','developer/tests/test_rcc_provider_rollback_workflow.py']
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def sha(b):return hashlib.sha256(b).hexdigest()
def bind(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
base=json.loads((O/'before-CONTROL-complete-source-and-original-ref-proof.json').read_text());rows=[];delta=[]
assert git('branch','--show-current').decode().strip()=='fix/rcc-candidate-wheel-identities-20261010'
changed=git('diff',S,'--name-only').decode().splitlines();assert set(changed)==set(P)
for x in base['all1419']:
 p=x['path'];b=(R/p).read_bytes();source=git('show',S+':'+p);assert bool((R/p).stat().st_mode&0o111)==(x['mode']=='100755'),p
 if p in P:
  normalized=b.replace(S.encode(),oldS.encode()).replace(T.encode(),oldT.encode());assert normalized==source,p
  if p.endswith('.py'):assert ast.dump(ast.parse(normalized))==ast.dump(ast.parse(source))
  delta.append({'path':p,'mode':x['mode'],'source_blob':x['blob'],'CONTROL_blob':git('hash-object','--',str(R/p)).decode().strip(),'source_bytes':len(source),'source_sha256':sha(source),'CONTROL_bytes':len(b),'CONTROL_sha256':sha(b),'candidate_sha_occurrences':b.count(S.encode()),'candidate_tree_occurrences':b.count(T.encode()),'whole_bytes_normalization_exact':True,'whole_AST_normalization_exact':p.endswith('.py')})
 else:assert sha(b)==x['sha256'] and len(b)==x['bytes'],p
 rows.append({'path':p,'mode':x['mode'],'blob':git('hash-object','--',str(R/p)).decode().strip(),'bytes':len(b),'sha256':sha(b)})
assert len(rows)==1419 and len(delta)==3
for x in base['all147_frozen_refs']:assert bind(x['path'])==x,x['path']
source_owner=Path('/workspace/engineering/pr308-actual299-source-refresh/SOURCE-frozen-owner-final-checkpoint.json');source_ind=Path('/workspace/engineering/pr308-actual299-independent-source-review/independent-frozen-current-SOURCE-review.json');assert bind(source_owner)['sha256']=='de231c011ee899c8e3ce6c6de4f2448136350758231f3f873f760d30600f4678';assert bind(source_ind)['sha256']=='9480a381d5be565b70c34c7b1672cecbb651159dad4595021e74fa5ff9836f25'
actual_root=Path('/workspace/engineering/pr308-current776-fresh-threecase-owned');actual=json.loads((actual_root/'frozen-original-threecase-proof.json').read_text());assert bind(actual['acquisition']['ZIP']['path'])==actual['acquisition']['ZIP']
with zipfile.ZipFile(actual['acquisition']['ZIP']['path']) as z:
 assert len(z.infolist())==7
 for x in actual['archive_members']:
  i=z.getinfo(x['member']);b=z.read(i);assert len(b)==x['bytes'] and sha(b)==x['sha256'];assert oct(i.external_attr>>16)==x['zip_recorded_mode'];p=actual_root/'original-members'/x['member'];assert p.read_bytes()==b and p.stat().st_mode&0o777==0o600
rcc=R/'action_server/src/actions/server/bin/rcc-18.19.3';assert sha(rcc.read_bytes())=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428' and rcc.stat().st_mode&0o777==0o711
assert re.search(r'55 passed',(O/'GREEN55-static.log').read_text());assert re.search(r'96 passed',(O/'ToolkitTest.log').read_text())
assert json.loads((O/'generator-roundtrip-successor-v2-receipt.json').read_text())['all_tracked_GitHub_YAML_count']==30
assert json.loads((O/'after-full-own-Bootstrap-reuse-inputs-and-origins.json').read_text())==json.loads(Path('/workspace/engineering/pr308-actual299-source-refresh/after-full-own-Bootstrap-reuse-inputs-and-origins.json').read_text())
assert json.loads((O/'branch-RED-actual-successor-v2-result.json').read_text())['actual_failed']==2
oldguide=git('show',S+':docs/skills/repository-operations.md');assert (R/'docs/skills/repository-operations.md').read_bytes()==oldguide;assert b'fix/rcc-candidate-wheel-identities-20261010' in oldguide
receipt={'SOURCE':S,'SOURCE_tree':T,'actual_target':'6181b044c75de35386f1ae30e71725398b6a7feb','only_three_CONTROL_path_delta':delta,'all1416_other_paths_body_modes_exact_SOURCE':True,'all1419_current_typed_body_modes_execbits':rows,'all147_original_frozen_refs_exact':base['all147_frozen_refs'],'SOURCE_owner':bind(source_owner),'SOURCE_independent_GO':bind(source_ind),'seven_original_actual_ZIP_members_and_recorded_modes_private0600_exact':True,'own30_inputs_five_concrete_origins_exact_SOURCE':True,'owned_ignored_RCC_SHA0711_exact':True,'guide_exact_SOURCE_three_reviewed_branch_correction':True,'source_full_not_repeated_or_misbound_CONTROL':True,'initial_branch_collector_failure_and_launch_order_retained':True,'current_native_producer_inventory':json.loads(source_owner.read_text())['production_and_selected_native_inventory'],'Upstream_disposition':'none'}
p=O/('postcommit-CONTROL-all-source-and-original-input-proof.json' if git('rev-parse','HEAD').decode().strip()!=S else 'precommit-CONTROL-all-source-and-original-input-proof.json');assert not p.exists();p.write_text(json.dumps(receipt,indent=2)+'\n');p.chmod(0o600);print(json.dumps({'proof':bind(p),'all1419_typed':True,'only_three_paths':True,'all147_original_refs':True,'original7members':True}))
