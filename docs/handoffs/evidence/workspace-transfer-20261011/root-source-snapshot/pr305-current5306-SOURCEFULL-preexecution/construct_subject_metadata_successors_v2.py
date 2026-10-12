from pathlib import Path
import copy,hashlib,json,stat
P=Path('/workspace/engineering/pr305-current5306-SOURCEFULL-preexecution');L=Path('/workspace/engineering/pr305-current-a54-source-LIGHT')
def bind(path):
 p=Path(path);h=hashlib.sha256()
 with p.open('rb') as f:
  for data in iter(lambda:f.read(1048576),b''):h.update(data)
 return {'path':str(p),'sha256':h.hexdigest(),'bytes':p.stat().st_size,'mode':oct(stat.S_IMODE(p.stat().st_mode))}
def check(row):
 actual=bind(row['path'])
 for key in ['sha256','bytes','mode']:assert actual[key]==row[key]
def write(path,data):
 assert not path.exists();path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n');path.chmod(0o600);return bind(path)
oldfull=P/'OWNERFINAL-current5306-managed-configured-SOURCEFULL-preexecution-proposal.json';oldlight=L/'OWNERFINAL-current5306-ordinary-a54-source-LIGHT-full-and-actual-HOLD.json'
a,b=bind(oldfull),bind(oldlight);assert a['sha256']=='fbdaba2989e187ad11547f56ff0107092a479d4592aaa48b9170cc7a2339e553';assert b['sha256']=='2c277550c5475cb6c9698dfbe092dd373a5398b553769f68a230451c96c1ca14'
full=json.loads(oldfull.read_text());light=json.loads(oldlight.read_text())
for row in full['frozen_input_bindings']:check(row)
for row in light['frozen_bindings']:check(row)
head='5306eeb26595da4ce571b99812eb50f047cfc903';tree='8418e9ffeeaaf2446771e34b5b4602bab3d357a5';target='a54c982462d1e7ad011d8152bfc299d997503fb3';parent='584a7ed0cb7112fe6691103931c007b5cc0be5f3'
assert full['source']==light['source']['commit']==head and full['tree']==light['source']['tree']==tree and light['source']['accepted_target']==target and light['source']['ordered_parents']==[parent,target]
refs=[bind('/workspace/engineering/pr305-current-e3c-source-LIGHT/OWNERFINAL-current584a-ordinary-e3-source-LIGHT-full-and-actual-HOLD.json'),bind('/workspace/engineering/pr305-current584a-SOURCEFULL-preexecution/OWNERFINAL-current584a-managed-configured-SOURCEFULL-preexecution-proposal.json'),bind('/workspace/engineering/pr305-current584a-independent-LIGHT-preexecution-review/OWNERFINAL-independent-current584a-SOURCE-LIGHT-and-managed-full-preexecution-review.json')]
assert refs[0]['sha256']=='5835c7c1b57493d784ea39cf0c037253460b04b3b3c9c4fa48fb1db1a887c387';assert refs[1]['sha256']=='2cd287244d83b2388449794bb4ea8205ca95329c8908af8ed288c91207097718';assert refs[2]['sha256'].startswith('88f103')
light2=copy.deepcopy(light);light2['status']='OWNERFINAL_CURRENT_5306_ORDINARY_A54_SOURCE_LIGHT_GO_FOR_REVIEW_FULL_AND_ACTUAL_HOLD';light2['subject_metadata_correction']={'original_unchanged_owner':b,'only_existing_field_changed':'status','old_subject_token':'ORDINARY_E3','correct_subject_token':'ORDINARY_A54','actual_unchanged_tuple':{'source':head,'tree':tree,'ordered_parents':[parent,target]},'scope':'Metadata subject clarification only; original source, gate results, proof and every frozen binding unchanged. No replay or new acceptance.'}
lightpath=L/'OWNERFINAL-current5306-ordinary-a54-source-LIGHT-subject-metadata-v2.json';lightbinding=write(lightpath,light2)
full2=copy.deepcopy(full);full2['status']='OWNERFINAL_CURRENT5306_SOURCEFULL_PREEXECUTION_READY_FOR_INDEPENDENT_REVIEW_NOT_RUN';full2['historical_preexecution']='PR305584a LIGHT5835, managed full-preexecution2cd287 and independent88f103 remain exact historical identities. Original3ec/92498 V5 actual is a separate unchanged historical tuple, not current5306 full proof.'
full2['subject_metadata_correction']={'original_unchanged_owner':a,'only_existing_fields_changed':['status','historical_preexecution'],'old_subject_tokens':['CURRENT1299','PR282 c35/d5b1/55a621'],'correct_current_tuple':{'source':head,'tree':tree,'target':target},'current_LIGHT_subject_clarification':lightbinding,'exact_historical_PR305584_bindings':refs,'execution_contract_unchanged':{'original_launcher_proposal_binding':a,'launcher_root_release_proposal_sha256':a['sha256'],'launcher_reads_original_proposal_path':str(oldfull),'source_config_scripts_argv_bounds_pre_post_guards_all_frozen_input_bindings':'UNCHANGED','root_adoption':'This named metadata successor clarifies the original executable packet; distinct root adoption/release must bind the correction and retain the launcher original-proposal hash. It does not authorize execution.'},'scope':'No source/Git/config/script/gate/test/native/install changes. Current full remains NOT_RUN.'}
fullpath=P/'OWNERFINAL-current5306-managed-configured-SOURCEFULL-preexecution-subject-metadata-v2.json';fullbinding=write(fullpath,full2)
x=copy.deepcopy(light2);x.pop('subject_metadata_correction');x['status']=light['status'];assert x==light
x=copy.deepcopy(full2);x.pop('subject_metadata_correction');x['status']=full['status'];x['historical_preexecution']=full['historical_preexecution'];assert x==full
assert bind(oldfull)==a and bind(oldlight)==b
for row in full['frozen_input_bindings']:check(row)
for row in light['frozen_bindings']:check(row)
receipt={'schema':1,'status':'OWNERFINAL_METADATA_ONLY_SUBJECT_CORRECTION_COMPLETE_NO_EXECUTION','unchanged_original_full':a,'unchanged_original_LIGHT':b,'named_correct_current_full':fullbinding,'named_correct_current_LIGHT':lightbinding,'exact_historical_PR305584_bindings':refs,'authoring_constructor':bind(__file__),'total_new_successor_JSON_bytes':lightbinding['bytes']+fullbinding['bytes'],'unchanged_all14_full_input_bindings':len(full['frozen_input_bindings']),'unchanged_all38_LIGHT_bindings':len(light['frozen_bindings']),'source_gate_execution':'NOT_RUN','documentation_improvement':{'canonical_files_reused':['docs/skills/repository-operations.md','docs/skills/provenance-observability.md'],'exact_accepted_parent_delta':bind(L/'exact-imported-a54-canonical-guide-delta.patch'),'both_parent_block_evidence':bind(L/'verified-both-parent-canonical-guide-block-preservation.json'),'durable_learning':'Bind current source/control and receipt identities separately; retain original hash-bound metadata and use named successors for corrected subjects without relabeling execution history.','stale_ambiguity_removed':'Copied CURRENT1299 and PR282c35 historical labels replaced by exact PR3055306/a54 and original584/2cd287/88f103 identities only in named successors.','remaining_uncertainty':'SourceFULL is still NOT_RUN, requires independent review, distinct root adoption/release, serialized slot and fresh capacity. No current native/browser/private/release authority.'},'upstream_disposition':'none'}
p=P/'OWNERFINAL-current5306-metadata-only-subject-correction-disposition-v2.json';r=write(p,receipt);assert r['bytes']+receipt['total_new_successor_JSON_bytes']+Path(__file__).stat().st_size<50000
print(json.dumps({'full':fullbinding,'LIGHT':lightbinding,'disposition':r,'new_written_bytes':r['bytes']+receipt['total_new_successor_JSON_bytes']+Path(__file__).stat().st_size}))
