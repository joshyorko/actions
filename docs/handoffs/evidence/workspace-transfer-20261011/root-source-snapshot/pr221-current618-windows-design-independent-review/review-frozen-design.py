import ast
import datetime
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile
import yaml

B=Path('/workspace/engineering/pr221-current618-static-frontend-trace-owned')
O=Path('/workspace/engineering/pr221-current618-windows-design-independent-review')
R=Path('/workspace/engineering/pr282')
SOURCE='6181b044c75de35386f1ae30e71725398b6a7feb'
TREE='99ac5309add45af65049546dd3a99f357884cf3b'
BUILD='e7666eacf2687f65050b97a88e791f8d0ce4cd20'
def sha(data):return hashlib.sha256(data).hexdigest()
def bind(row):
 p=Path(row['path']);v=p.read_bytes();assert len(v)==row['bytes'] and sha(v)==row['sha256'];return row
def load(p):return json.loads(Path(p).read_bytes())
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*a])
def blob(path):return git('show',SOURCE+':'+path)
owner=bind({'path':str(B/'OWNERFINAL-windows-static-and-complete-checkout-diagnosis-v2.json'),'bytes':23744,'sha256':'0839a2ba6ee40b9b2e244f399496158e4775e5bbe1bd3fcc3d6056bbbf51c683'})
proposal=bind({'path':str(B/'bounded-complete-runtime-checkout-and-filter-proposal-v2.json'),'bytes':78439,'sha256':'8575d7293cbcc2dcb025dcf8403896b4a6242c7229467a723018225bf5601bf1'})
d=load(owner['path']);p=load(proposal['path'])
assert d['actual_service_free_control_execution']=='NOT_RUN_REQUIRES_OWNER_AUTHORIZATION'
assert p['actual_control_test_execution_now']=='NOT_RUN'
assert d['source']==SOURCE and d['tree']==TREE and d['producer_checkout']==BUILD
assert git('rev-parse',SOURCE+'^{tree}').decode().strip()==TREE
assert git('rev-parse',BUILD+'^{tree}').decode().strip()==TREE
assert git('show','-s','--format=%P',BUILD).decode().split()==d['producer_ordered_parents']==['a70993fafc99a9f94041485542d5a720797ca394',SOURCE]
assert len(d['evidence'])==24
for row in d['evidence']:bind(row)
bind(d['original_owner_qualification']);original=load(d['original_owner_qualification']['path']);assert len(original['evidence'])==24
for row in original['evidence']:bind(row)
assert len(d['source_bindings'])==10
for row in d['source_bindings']:
 bind(row['private_source_snapshot']);data=blob(row['public_git_path'])
 assert data==Path(row['private_source_snapshot']['path']).read_bytes() and len(data)==row['bytes'] and sha(data)==row['sha256']
 meta=git('ls-tree',SOURCE,'--',row['public_git_path']).split(b'\t',1)[0].decode().split()
 assert meta==[row['git_mode'],'blob',row['git_blob']]
bind(p['generator_snapshot']);assert Path(p['generator_snapshot']['path']).read_bytes()==blob('.github/workflows/_gen_workflows.py')
bind(p['candidate_source_delta']['narrow_attributes_patch'])
rules=p['candidate_source_delta']['rules'];assert len(rules)==7 and len(set(rules))==7
assert rules[0]=='action_server/src/**/*.py text eol=lf'
assert rules[1]=='action_server/frontend/apps/runtime/index.html text eol=lf'
nonpython=[r.rsplit(' text eol=lf',1)[0] for r in rules[2:]]
assert nonpython==p['separate_qualification_failures']['tracked_checkout_bytes']['nonPython_public_source_paths']
patch=Path(p['candidate_source_delta']['narrow_attributes_patch']['path']).read_text()
assert [l[1:] for l in patch.splitlines() if l.startswith('+action_server/')]==rules
py=p['candidate_source_delta']['Runtime_source_Python_inventory'];assert len(py)==201
tracked={n.decode():m.decode().split() for row in git('ls-tree','-r','-z',SOURCE).split(b'\0') if row for m,n in [row.split(b'\t',1)]}
assert {row['public_source_path'] for row in py}=={path for path in tracked if path.startswith('action_server/src/') and path.endswith('.py')}
for row in py:
 data=blob(row['public_source_path']);assert len(data)==row['bytes'] and sha(data)==row['sha256']
 assert tracked[row['public_source_path']]==[row['mode'],'blob',row['git_blob']]
 assert data.count(b'\r')==row['CR']==0 and data.count(b'\n')==row['LF']
for path in nonpython:assert b'\r' not in blob(path)
input_html=blob('action_server/frontend/apps/runtime/index.html');assert len(input_html)==372 and input_html.count(b'\n')==13 and b'\r' not in input_html

asset={};module={}
for platform,row in d['confirmed']['retained_assets'].items():
 bind(row['wheel'])
 with zipfile.ZipFile(row['wheel']['path']) as z:body=z.read('actions/server/_static_contents.py')
 tree=ast.parse(body);assert len(tree.body)==1 and isinstance(tree.body[0],ast.Assign)
 assert len(tree.body[0].targets)==1 and tree.body[0].targets[0].id=='FILE_CONTENTS'
 values=ast.literal_eval(tree.body[0].value);assert set(values)=={'index.html'} and isinstance(values['index.html'],bytes)
 data=values['index.html'];asset[platform]=data;module[platform]=body
 assert len(body)==row['module_bytes'] and sha(body)==row['module_sha256'] and body.count(b'\r')==row['module_CR_count']==0
 assert len(data)==row['decoded_asset_bytes'] and sha(data)==row['decoded_asset_sha256']
 assert data.count(b'\r')==row['decoded_asset_CR'] and data.count(b'\r\n')==row['decoded_asset_CRLF'] and data.count(b'\n')==row['decoded_asset_LF']
linux,windows=asset['Linux'],asset['Windows']
assert windows.replace(b'\r',b'')==linux and windows.replace(b'\r\n',b'\n')!=linux
assert windows.count(b'\r')==13 and windows.count(b'\r\n')==12 and b'\r\r\n' in windows
scaffold={}
for number,line in enumerate(input_html.splitlines(keepends=True),1):
 body=line.rstrip(b'\n');positions=[m.start() for m in re.finditer(re.escape(body),linux)]
 if len(positions)==1:scaffold[positions[0]+len(body)]=number
mapping=[{'ordinal':n+1,'normalized_asset_offset':m.start()-n,'input_scaffold_line_end':scaffold.get(m.start()-n),'CRLF':windows[m.start()+1:m.start()+2]==b'\n'} for n,m in enumerate(re.finditer(b'\r',windows))]
assert mapping==d['confirmed']['Windows_CR_scaffold_mapping']
assert [m['input_scaffold_line_end'] for m in mapping]==[1,2,3,4,5,6,7,8,9,10,10,12,13]
observations=load('/workspace/engineering/pr221-current618-wheel-integrity-owned/safe-source-body-and-builder-observations.json')
rows=next(c for c in observations['classifications'] if c['platform']=='Windows' and c['python_abi']=='cp312')['tracked_package_comparisons']
windows_wheel=d['confirmed']['retained_assets']['Windows']['wheel']['path'];changed=[];py_count=0;text_count=0;noncr=[]
with zipfile.ZipFile(windows_wheel) as z:
 for row in rows:
  name=row['public_member_path'];data=z.read(name);source=blob('action_server/src/'+name)
  assert sha(data)==row['wheel_sha256'] and sha(source)==row['source_sha256']
  if source!=data:
   if data.replace(b'\r\n',b'\n')==source:
    changed.append(name);py_count+=name.endswith('.py');text_count+=not name.endswith('.py')
   else:noncr.append(name)
assert len(changed)==178 and py_count==173 and text_count==5 and noncr==['actions/server/_static_contents.py']
assert sorted('action_server/src/'+name for name in changed if not name.endswith('.py'))==sorted(nonpython)
tasks=ast.parse(blob('action_server/tasks.py'));f=next(n for n in tasks.body if isinstance(n,ast.FunctionDef) and n.name=='build_frontend')
assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='read_bytes' and n.lineno==153 for n in ast.walk(f))
assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='repr' and n.lineno==166 for n in ast.walk(f))
writer=next(n for n in ast.walk(f) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='open' and n.lineno==155)
assert {kw.arg:ast.literal_eval(kw.value) for kw in writer.keywords}=={'encoding':'utf-8','newline':'\n'}
assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='replace' for n in ast.walk(f))
assert b'_static_contents' not in blob('action_server/build.py')

filters=[]
for flow in p['affected_generated_build_and_test_filters']:
 bind(flow['source_snapshot']);raw=blob(flow['public_workflow_path']);assert raw==Path(flow['source_snapshot']['path']).read_bytes()
 data=yaml.safe_load(raw);event=data['on'] if 'on' in data else data[True];pr=event['pull_request']
 assert pr['branches']==flow['current_PR_branches'] and pr['paths']==flow['current_PR_paths']
 assert not any(fnmatch.fnmatchcase('.gitattributes',pattern) for pattern in pr['paths'])
 assert flow['proposed_PR_paths_delta']==['.gitattributes']
 assert any(fnmatch.fnmatchcase('community',b) for b in pr['branches'])
 assert any(fnmatch.fnmatchcase('integration/community-release-20261008',b) for b in pr['branches'])
 assert not any(fnmatch.fnmatchcase('unrelated/branch',b) for b in pr['branches'])
 count=0
 for job in data['jobs'].values():
  matrix=job.get('strategy',{}).get('matrix',{});mult=1
  for k,v in matrix.items():
   if k not in ['include','exclude']:mult*=len(v)
  count+=mult
 assert count==flow['expanded_job_count']
 filters.append({'generator_class':flow['generator_class'],'workflow':flow['public_workflow_path'],'declared_expanded_jobs':count,'current_attributes_only_excluded':True,'proposed_single_PR_path_addition':'.gitattributes','events_matrix_needs_permissions_tags_registry_timeouts_assertions_must_remain_exact':True})
assert len(filters)==2
logs=[]
for row in d['original_builder_step_bindings']:
 bind(row['original_decoded_log']);text=Path(row['original_decoded_log']['path']).read_text();lines=text.splitlines()
 assert BUILD in text and row['effective_core_autocrlf_observation']=='UNAVAILABLE' and row['original_checked_out_runtime_HTML_input']=='UNAVAILABLE' and row['original_pre_encoder_dist_index_digest']=='UNAVAILABLE'
 assert not any('autocrlf' in line.lower() for line in lines)
 begin,end=row['frontend_step_lines'];assert 'inv build-frontend' in lines[begin-1] and 'build-oauth2-config' in lines[end]
 for number in row['npm_artifacts_command_lines']:assert 'npm run build:artifacts' in lines[number-1]
 for number in row['runtime_inline_script_invocation_lines']:assert 'inline-runtime-assets.mjs' in lines[number-1]
 logs.append(row['job_id'])
canonical=d['Documentation_improvement']['exact_delta'];bind(canonical)
assert canonical['sha256']=='1306a314811448c8090b4aa2e77340e676bbba397ceb6c7ee0477b908cb9b2bf'
lesson='\n'.join(line[1:] for line in Path(canonical['path']).read_text().splitlines() if line.startswith('+') and not line.startswith('+++'))
assert 'module\'s newline to LF does not normalize the embedded asset' in lesson
assert 'semantic equivalence separate' in lesson and 'checkout-versus-compiler causation unknown' in lesson
assert 'tracked non-Python package text' in lesson and 'workflow path filters' in lesson
proof={'schema':'current618-windows-checkout-source-design-independent-review/v1','status':'GO_DESIGN_ONLY_SOURCE_AND_CONTROLS_NOT_EXECUTED','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'owner_final':owner,'frozen_proposal':proposal,'verified':{'owner_refs':24,'original_artifact_refs':24,'source_snapshot_Git_bindings':10,'current_source':SOURCE,'synthetic_builder':BUILD,'equal_tree':TREE,'producer_not_relabeled_actual':True,'sourcePython_inventory':201,'narrow_attributes':rules,'new_attributes_rewrite_source_blobs':False,'two_filter_scope':filters,'CRLF_only_tracked_differences':178,'Python':173,'other_package_text':5,'generated_static_module_additional_non_CRLF_only_difference':True,'decoded_Windows_CR':13,'CRLF':12,'lone_CR':1,'all_CR_removed_Linux_equal_diagnostic_only':True,'outer_both_generated_modules_CR':0,'original_builder_logs_bound':logs,'original_checkout_config_input_compiler_intermediate':'UNAVAILABLE/UNKNOWN'},'required_meaningful_future_controls':{'real_temporary_Git_index_checkout_not_fnmatch_for_attributes':True,'complete_selected_body_SHA_byte_equality':{'Python':201,'nonPython':5,'HTML':1},'autocrlf_TRUE_RED_and_narrow7rules_TRUE_FALSE_GREEN':'NOT_RUN','seven_removed_rule_poison_states':'NOT_RUN','binaryZIP_bat_intentional_CRLF_testfixtures_otherpackages_preserved':'REQUIRED_NOT_RUN','exact_gitattributes_only_two_workflows_community_integration_select_wrongbranch_reject':'REQUIRED_NOT_RUN','six_unrelated_generated_outputs_and_other_generator_AST_exact':'REQUIRED_AFTER_SOURCE_AUTHORIZATION','source_following_hosted_Windows_distribution_bytes_requalification':'REQUIRED_NOT_RUN'},'actual_temporary_Git_execution':'NOT_RUN confirmed by owner; existing private-index check-attr merely observed current text=auto/eol unset; no measured checkout GREEN exists','diagnosis_scope':'13CR localization strongly supports an HTML scaffold input representation hypothesis. Source contract proposal is testable, but missing original checkout input/config/compiler intermediate prevents proving historical cause or compiler/semantic equivalence. No normalization of actual installed/wheel/frontend bytes, RECORD or private metadata is proposed.','documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md','Exact_delta':canonical,'Durable_learning':d['Documentation_improvement']['durable_learning'],'Evidence':'Independent AST read_bytes/repr/LF module writer; original Windows/Linux module and decodedasset hashes/counts/scaffold mapping; current173Python+5nonPython CRLF-only mismatches plus generated-static raw difference; exact two workflow current path filters exclude attributes-only changes.','Stale_or_ambiguous_guidance_removed':d['Documentation_improvement']['stale_or_ambiguous_guidance_removed'],'Remaining_uncertainty':d['Documentation_improvement']['remaining_uncertainty'],'Disposition':'Accept exact16-line1306 proposal for root integration; no cosmetic independent guide delta.'},'authority':'Independent design GO only; no source implementation/control run/actual consumer or Windows source gate authorized by this review. Root owns separate source authorization and frozen implementation review.','remaining_HOLDs':d['remaining_holds'],'not_performed':['Source/index/branch writes','Tests/tempGit checkout/poison/gateway/installer executions','Downloads or live CI polling','Consumer/native/browser/provider run','Release/merge/push/issue closure'],'upstream_disposition':'none'}
dest=O/'independent-frozen-Windows-checkout-design-review.json';assert not dest.exists();dest.write_text(json.dumps(proof,indent=2)+'\n');dest.chmod(0o444)
print(json.dumps({'path':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest.read_bytes()),'status':proof['status']}))
