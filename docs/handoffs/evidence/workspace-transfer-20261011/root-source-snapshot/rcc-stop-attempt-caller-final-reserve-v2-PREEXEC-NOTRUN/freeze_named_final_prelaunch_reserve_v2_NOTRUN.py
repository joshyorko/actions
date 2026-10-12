"""Stdlib-only named literal/block successor. Never imports or runs callers."""
import ast
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

B=Path('/workspace/engineering/rcc-stop-attempt-caller-final-reserve-v2-PREEXEC-NOTRUN')
OLD=Path('/workspace/engineering/rcc-stop-attempt-concrete-ROOT-caller-PREEXEC-NOTRUN')

def row(path):
    p=Path(path);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();raw=p.read_bytes()
    return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),mode=oct(stat.S_IMODE(s.st_mode)))

def put(name,value):
    p=B/name;raw=value if type(value) is bytes else (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o400)
    with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    return row(p)

ownerold=row(OLD/'OWNERFINAL-stop-attempt-concrete-inner-external-parent-PREEXEC-NOTRUN.json')
assert ownerold['sha256']=='9fd59226cf8ac1a5d3f7e084010acf39f72fdc9b3224062b0f9cd17e2e098ff0'
oldowner=json.loads(Path(ownerold['path']).read_text());oldcfgrow=oldowner['config_binding'];assert row(oldcfgrow['path'])==oldcfgrow
cfg=json.loads(Path(oldcfgrow['path']).read_text())
hold=row('/workspace/engineering/rcc-stop-attempt-concrete-caller-independent-PREEXEC-review/OWNERFINAL-independent-original-stop-attempt-concrete-caller-PREEXEC-shared-deadline-HOLD.json')
assert hold['sha256']=='532eae986a87ba8a1597444af6c5d464f216d3777c6fac4b21bbfcce8aba0a59'
h=json.loads(Path(hold['path']).read_text());assert h['caller_config_binding']==oldcfgrow
oldcommon=Path(cfg['implementation_bindings']['caller_contract']['path']).read_text()
first="""        term_seconds=min(120,remaining-15)
        argv[argv.index('120s')]=f'{term_seconds:.6f}s'
"""
firstnew="""        term_seconds=min(120,remaining-15)
        timeout_token_index=argv.index('120s')
        argv[timeout_token_index]=f'{term_seconds:.6f}s'
"""
final="""            if primary_deadline is not None:
                parent_seconds=min(parent_seconds,primary_deadline-time.monotonic())
                need(parent_seconds>0,'STOP_CALLER_PRIMARY_DEADLINE_EXHAUSTED_NO_LAUNCH')
"""
finalnew="""            if primary_deadline is not None:
                remaining=primary_deadline-time.monotonic()
                need(remaining>15,'STOP_CALLER_PRIMARY_DEADLINE_EXHAUSTED_NO_LAUNCH')
                term_seconds=min(120,remaining-15)
                argv[timeout_token_index]=f'{term_seconds:.6f}s'
                parent_seconds=min(parent_seconds,remaining)
"""
assert oldcommon.count(first)==oldcommon.count(final)==1
newcommon=oldcommon.replace(first,firstnew).replace(final,finalnew).replace(str(OLD),str(B)).replace('FROZEN-stop-attempt-concrete-ROOT-config-NOTRUN.json','FROZEN-stop-attempt-final-reserve-v2-ROOT-config-NOTRUN.json')
inverse=newcommon.replace(firstnew,first).replace(finalnew,final).replace(str(B),str(OLD)).replace('FROZEN-stop-attempt-final-reserve-v2-ROOT-config-NOTRUN.json','FROZEN-stop-attempt-concrete-ROOT-config-NOTRUN.json')
assert inverse==oldcommon and ast.dump(ast.parse(inverse),include_attributes=False)==ast.dump(ast.parse(oldcommon),include_attributes=False)
implementations={}
for role,oldrow in cfg['implementation_bindings'].items():
    body=newcommon.encode() if role=='caller_contract' else Path(oldrow['path']).read_bytes()
    ast.parse(body);implementations[role]=put(Path(oldrow['path']).name,body)
    if role!='caller_contract':assert implementations[role]['sha256']==oldrow['sha256']
patch=put('exact-final-prelaunch-reserve-and-named-address-common-only.patch',''.join(difflib.unified_diff(oldcommon.splitlines(True),newcommon.splitlines(True),fromfile=cfg['implementation_bindings']['caller_contract']['path'],tofile=implementations['caller_contract']['path'])).encode())
proof=put('exact-final-prelaunch-reserve-common-block-inverse-proof-NOTRUN.json',dict(schema=1,status='STDLIB_TEXT_AST_DATA_ONLY_NO_EXECUTION',original_owner=ownerold,original_PREEXEC_HOLD=hold,old_implementation_bindings=cfg['implementation_bindings'],named_implementation_bindings=implementations,exact_common_delta=patch,whole_inverse_text_AST_exact=True,inner_external_bodies_exact=True,only_common_regions=['BASE/CONFIG namespaced addresses','save exact timeouttoken index before120s replacement','finalprePopen freshremaining>15; TERMtoken andparentfallback recomputed fromsamefreshmeasurement'],old_stale_arithmetic_witness=h['blocking_finding']['static_arithmetic_witness_NOT_RUNTIME_OBSERVATION'],corrected_static_arithmetic_NOT_RUNTIME=[dict(final_remaining=10,launch='REFUSED',predicate='remaining>15'),dict(final_remaining=30,TERM=15,KILL=10,fallback_margin=5,parent_at_most=30),dict(final_remaining=150,TERM=120,KILL=10,fallback_margin=5,parent_at_most=135)],immutable_phase_config_helper=[cfg['phase_config'],cfg['phase_helper']],phase_order=cfg['phase_order'],census_frames_caps_and_bounds_unchanged=True,shareddeadline_scope='765primary+135innerpost under900; uncapped1215 not810, no allphasecompletion guarantee. External135+930+135=1200/parent1230 unchanged.',tests_imports_native='NOT_RUN'))
refs=cfg['frozen_bindings']+oldowner['all_local_bindings']+[ownerold,hold,proof,patch]
refs+=list(cfg['implementation_bindings'].values())
unique={}
for r in refs:
    assert row(r['path'])==r
    if r['path'] in unique:assert unique[r['path']]==r
    unique[r['path']]=r
cfg['status']='CONCRETE_STOP_ATTEMPT_FINAL_RESERVE_V2_PREPARED_NOTRUN'
cfg['implementation_bindings']=implementations
cfg['ROOT_release_template']['implementation_bindings']=implementations
cfg['frozen_bindings']=list(unique.values())
cfg['final_prelaunch_reserve_successor_proof']=proof
cfg['original_prelaunch_HOLD']=hold
config=put('FROZEN-stop-attempt-final-reserve-v2-ROOT-config-NOTRUN.json',cfg)
contractold=json.loads(Path(oldowner['root_contract']['path']).read_text());contract=dict(contractold)
contract['config_binding']=config;contract['implementation_bindings']=implementations
contract['ROOT_release_template']=dict(cfg['ROOT_release_template']);contract['ROOT_release_template']['caller_config_sha256']=config['sha256']
req=dict(contractold['compatible_independent_PREEXEC_required_fields'])
req.update(caller_config_sha256=config['sha256'],external_parent_sha256=implementations['external_parent']['sha256'],inner_caller_sha256=implementations['inner_caller']['sha256'],caller_contract_sha256=implementations['caller_contract']['sha256'])
contract['compatible_independent_PREEXEC_required_fields']=req
contract['ROOT_exact_argv']=[v.replace(cfg['implementation_bindings']['external_parent']['path'],implementations['external_parent']['path']) for v in contractold['ROOT_exact_argv']]
# Use original addresses for the literal inverse replacement, not the updatedcfg.
contract['ROOT_exact_argv']=[v.replace(oldowner['implementation_bindings']['external_parent']['path'],implementations['external_parent']['path']).replace(oldcfgrow['sha256'],config['sha256']) for v in contractold['ROOT_exact_argv']]
contract['status']='NAMED_FINAL_RESERVE_V2_TEMPLATE_NOT_EXECUTION_RELEASE'
contract['original_HOLD']=hold
contract['final_prelaunch_measurement']='Selectedtimeout index saved; justbefore subprocess.run freshremaining>15 and bothTERM andparentfallback updated. No guard/helper/predicate/budget/ROOTgrant schema change.'
contract=put('ROOT-final-reserve-v2-distinct-release-and-exact-argv-contract-NOTRUN.json',contract)
assert not Path(cfg['root_once']).exists() and not Path(cfg['root_once']).is_symlink() and not Path(cfg['root_release_path']).exists() and not Path(cfg['root_release_path']).is_symlink()
source=Path('/workspace/engineering/pr308');git=lambda *a:subprocess.check_output(['git','-C',str(source),*a]).decode().strip()
assert git('rev-parse','HEAD')==cfg['source'] and git('rev-parse','HEAD^{tree}')==cfg['tree'] and not git('status','--porcelain','--untracked-files=no')
doc=put('canonical-final-process-launch-shared-deadline-reserve-proposed.json',dict(schema=1,status='EXACT_SOURCE_BACKED_DELTA_PROPOSED_NOT_PRODUCT_GUIDE_EDIT',canonical_file='docs/skills/repository-operations.md',exact_addition=h['documentation']['canonical_delta_proposal_only'],evidence=[hold,proof],remaining='Staticpreparation only; no actual output-setup delay/execution/native guarantees.',upstream_disposition='none'))
local=[row(p) for p in sorted(B.iterdir()) if p.is_file()]
owner=put('OWNERFINAL-stop-attempt-final-prelaunch-reserve-v2-SOURCE-PREEXEC-NOTRUN.json',dict(schema=1,status='NAMED_FINAL_PRELAUNCH_RESERVE_V2_SOURCE_CONCRETE_PREEXEC_PREPARED_NOTRUN',source=cfg['source'],tree=cfg['tree'],source_count=1440,source_clean=True,config_binding=config,implementation_bindings=implementations,root_contract=contract,exact_delta_proof=proof,original_PREEXEC_HOLD=hold,original_owner=ownerold,all_local_bindings=local,all_original_bindings=list(unique.values()),original120_rows_plus_new_historical_bindings=len(unique),phase_config_helper_unchanged=[cfg['phase_config'],cfg['phase_helper']],guard_only_authorization_unchanged=cfg['guard_only_authorization'],bounds=cfg['bounds'],outputs_ROOTrelease='ABSENT_NOT_CREATED',tests_imports_cgroup_signals_native='NOT_RUN',documentation_improvement=dict(canonical_file='docs/skills/repository-operations.md',exact_delta=doc,durable_learning='Use one final fresh launch-boundary remainder for both selectedtimeouttoken andparentfallback; refuse stages without15s reservedKILL/fallback afteroutputsetup.',evidence=[hold,proof],stale_ambiguity='Positive-only lastcheck and stale earlierTERM rejected under532HOLD; namedv2 correctsonlythatblock andaddresses.',remaining_uncertainty='No control/gate/nativeexecution; staticarithmetic isnot runtime delaymeasurement.'),upstream_disposition='none',writer_A='RELEASED_AFTER_FREEZE',captured=datetime.datetime.now(datetime.timezone.utc).isoformat()))
for r in unique.values():assert row(r['path'])==r
for r in local:assert row(r['path'])==r
print(json.dumps(owner))
