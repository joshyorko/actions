from pathlib import Path
import hashlib,json,subprocess,time
B=Path('/workspace/engineering/pr221-current618-linux-consumer-preflight');R=Path('/workspace/engineering/pr282')
def bind(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
p=B/'OWNERFINAL-current618-isolated-Linux-consumer-preexecution-proposal-v5.json';assert bind(p)['sha256']=='5650f8ee5f90f209ccc547d67593f1d5f2e773340b92f4b81dae83a1d1ff5db4';d=json.loads(p.read_text());refs={}
for row in d['all_private_preexecution_files_and_preserved_originals']:assert bind(row['path'])==row;refs[row['path']]=row
assert bind(d['runner']['path'])==d['runner'] and bind(d['input_manifest']['path'])==d['input_manifest'] and bind(d['input_gate']['path'])==d['input_gate']
assert not Path(d['planned_ONE_actual_gateway']['attempt_root']).exists();assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain'])
before=json.loads((B/'v5-original-ref-and-harness-before-preparation-proof.json').read_text());assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD']).decode().strip()==before['harness_head']
for row in before['all1433_harness_typed_bodies_execbits']:
 q=R/row['path'];b=q.read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'];assert bool(q.stat().st_mode&0o111)==(row['mode']=='100755')
d['previous_v4_bounded_design_scope_historical']=d['bounded_design_scope'];d['bounded_design_scope']='V5 only: preserve unchanged v4 provenance and all existing nine runner functions/93 controls; isolate exact original Linux pair copies privately and rebind only WHEEL, ATTEMPT suffix3 and SOURCES input_manifest path/SHA. Admit actualdirectory with real unchanged selector before immutablefreeze; retain failed mixed-directory gateway without retry. Current100 servicefree controls and input guard are preparation only, not actualconsumer. No helper/platform-filter/installedguard/cleanup/budget/sourcebranch changes.'
d['previous_immutable_v5_owner_before_scope_wording_correction']=bind(p);d['previous_immutable_v5_constructor']=d['immutable_constructor'];d['immutable_constructor']=bind(Path(__file__));d['metadata_only_successor_disposition']='Inherited v4 bounded_design_scope is now explicitly historical; current v5 scope corrected. No runner/manifest/gate/copies/control counts or mechanism changed; no rerun or sourcebranch mutation.'
for q in [p,Path(__file__)]:refs[str(q)]=bind(q)
d['all_private_preexecution_files_and_preserved_originals']=sorted(refs.values(),key=lambda x:x['path']);d['evidence_refs_fingerprint_sha256']=hashlib.sha256(json.dumps(d['all_private_preexecution_files_and_preserved_originals'],sort_keys=True,separators=(',',':')).encode()).hexdigest();d['frozen_at_utc_epoch']=time.time()
out=B/'OWNERFINAL-current618-isolated-Linux-consumer-preexecution-proposal-v5-successor-v2.json';assert not out.exists();out.write_text(json.dumps(d,indent=2)+'\n');out.chmod(0o600)
print(json.dumps({'OWNERFINAL_v5_final_successor':bind(out),'immutable_constructor':bind(Path(__file__)),'runner':d['runner'],'manifest':d['input_manifest'],'original_v5_preserved':bind(p),'refs':len(refs),'harness1433_exact':True,'metadata_only_no_rerun':True,'no_actual_authorization':True}))
