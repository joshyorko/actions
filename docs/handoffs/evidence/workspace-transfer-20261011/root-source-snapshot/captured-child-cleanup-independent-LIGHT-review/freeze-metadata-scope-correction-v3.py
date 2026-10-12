import hashlib,json,stat,subprocess
from pathlib import Path
O=Path(__file__).resolve().parent;D=Path('/workspace/engineering/captured-child-cleanup-light-owned');R=Path('/workspace/engineering/captured-child-cleanup')
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(n,a):
 p=O/n;assert not p.exists();p.write_text(json.dumps(a,indent=2,sort_keys=True)+'\n');p.chmod(0o600);return bind(p)
oldp=O/'OWNERFINAL-independent-captured-child-cleanup-frozen-LIGHT-review-v2.json';assert bind(oldp)['sha256']=='f50b893f28531422244e62156c5fa54d22c64e11e4f30d4678013324a66d660c'
a=json.loads(oldp.read_bytes());fixture=json.loads((D/'own-ignored-pinned-RCC-fixture-preparation.json').read_bytes());actual={}
for key in ('source','primary','own_ignored_destination'):
 p=Path(fixture[key]);row=bind(p);assert row['bytes']==fixture['bytes'] and row['sha256']==fixture['sha256'];actual[key]={**row,'mode':oct(stat.S_IMODE(p.stat().st_mode))}
assert actual['source']['mode']==actual['own_ignored_destination']['mode']=='0o711' and actual['primary']['mode']=='0o700'
diagnosis=save('original-review-failure-mode-scope-diagnosis-v2.json',{'status':'CORRECTED_REVIEWER_MODE_SCOPE_METADATA_ONLY','original_draft_preserved':bind(O/'original-review-failure-mode-scope-diagnosis.json'),'original_draft_error':'First draft reason guessed primary mode0755; its measured observed row was correctly0o700. Initial inspector mistakenly asserted allthree0711. No source/gate failure.','measured_scope':actual,'correct_requirement':'Same original binary SHA/size acrossthree; copied/source fixture0711 and managedprimary0700 measured separately. Owner does not require allthree same mode.','source_or_gate_mutation_or_reexecution':False})
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()==a['head'] and not subprocess.check_output(['git','status','--porcelain'],cwd=R)
a['retained_original_independent_inspector_failure']=diagnosis
a['metadata_only_successor_disposition']={'draft_v2_preserved':bind(oldp),'change':'Only bind named corrected mode-scope diagnosis and actual three-mode metadata; all v2 source/env/JUnit/reference verification preserved exactly, no rerun/tests/source changes.','prior_incorrect_diagnosis_preserved':bind(O/'original-review-failure-mode-scope-diagnosis.json')}
a['three_RCC_binary_identities_and_measured_modes']=actual
a['immutable_verification_constructor_preserved']=a['immutable_constructor'];a['immutable_constructor']=bind(__file__)
print(json.dumps(save('OWNERFINAL-independent-captured-child-cleanup-frozen-LIGHT-review-v3.json',a)))
