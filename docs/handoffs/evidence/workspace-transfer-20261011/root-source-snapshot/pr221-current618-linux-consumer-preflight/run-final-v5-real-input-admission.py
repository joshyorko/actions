from pathlib import Path
import importlib.util,json,hashlib
B=Path('/workspace/engineering/pr221-current618-linux-consumer-preflight');p=B/'installed-consumer-runner-v5.py';s=importlib.util.spec_from_file_location('frozen_v5_readonly_input_admission',p);r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
floor=r.load('floor');mixed=Path('/workspace/engineering/pr221-current618-wheel-integrity-owned')
try:floor.select_runtime_wheel(mixed)
except ValueError as error:assert str(error).endswith('found 2');mixed_result='REJECTED_2_MATCHING_CP312_WHEELS'
else:raise AssertionError('Original mixed-directory admission unexpectedly passed')
selected=floor.select_runtime_wheel(r.WHEEL.parent);assert selected==r.WHEEL;result=r.admit_current_inputs();assert not r.ATTEMPT.exists()
result.update({'status':'READONLY_INPUT_ADMISSION_ONLY_NOT_CONSUMER','real_source_selector':str(r.SOURCES['floor'][0]),'selector_source_sha256':r.SOURCES['floor'][1],'original_mixed_directory':str(mixed),'original_mixed_result':mixed_result,'selected_exact_path':str(selected),'selected_original_sha256':r.digest(selected),'dedicated_input_directory':str(r.WHEEL.parent),'directory_mode':oct(r.WHEEL.parent.stat().st_mode&0o777),'two_original_pair_copies':[{'filename':p.name,'bytes':p.stat().st_size,'sha256':r.digest(p),'mode':oct(p.stat().st_mode&0o777)} for p in sorted(r.WHEEL.parent.iterdir())],'attempt_absent':True,'worker_install_pip_CLI_cleanup_executed':False})
p=B/'v5-final-real-directory-selector-and-current-input-admission.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');p.chmod(0o600);print(json.dumps({'read_only_final_admission':'PASS','mixed':'REJECT2','isolated':'EXACT_CP312','python':202,'tracked':215,'RECORD':221,'RECORD_verified':220,'no_consumer':True,'receipt_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
