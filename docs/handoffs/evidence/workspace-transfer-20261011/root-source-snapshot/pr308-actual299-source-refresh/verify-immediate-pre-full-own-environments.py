import hashlib,json,subprocess,sys
from pathlib import Path
import toolkit
root=toolkit.REPOSITORY_ROOT;out=Path('/workspace/engineering/pr308-actual299-source-refresh');old='493ecbd2c9163786675cc0cc9b3853e6e75ca196'
previous=json.loads(Path('/workspace/engineering/pr302-actual310-source-refresh/own-bootstrap-reuse-complete-gateway-proof.json').read_text())
full=json.loads(Path('/workspace/engineering/pr310-current-refresh/bootstrap-reuse.json').read_text())
inputs=sorted(set(previous['all19inputs_exact'])|set(full['inputs_sha256']));records={}
for name in inputs:
 before=subprocess.check_output(['git','show',old+':'+name],cwd=root);now=(root/name).read_bytes();assert before==now,name;records[name]=hashlib.sha256(now).hexdigest()
log=Path('/workspace/engineering/pr308-refresh-owned/bootstrap.log');assert hashlib.sha256(log.read_bytes()).hexdigest()=='8812f8f47f040dee39b872299c8cc91d5380fcca9831b646647c7654c525b756';assert 'actual main robot run" was SUCCESS' in log.read_text()
origins=[];envs={}
for package,module in [('actions','actions'),('actions-http-helper','actions_http'),('devutils','devutils.invoke_utils'),('work-items','actions.work_items'),('action_server','actions.server._rcc_runtime_adapter')]:
 prefix=root/package/'.venv';cfg=prefix/'pyvenv.cfg';assert cfg.is_file();envs[package]={'config_sha256':hashlib.sha256(cfg.read_bytes()).hexdigest(),'python_resolved':str((prefix/'bin/python').resolve())};dest=out/('immediate-pre-full-origin-'+package+'.json')
 code='import importlib,json,sys; from pathlib import Path; m=importlib.import_module('+repr(module)+'); prefix=Path('+repr(str(prefix))+'); source=Path(m.__file__).resolve(); assert Path(sys.prefix).resolve()==prefix.resolve(); assert source.is_relative_to(Path('+repr(str(root/package/'src'))+').resolve()); Path('+repr(str(dest))+').write_text(json.dumps({"module":'+repr(module)+',"origin":str(source),"prefix":sys.prefix,"python":sys.executable}))'
 toolkit.poetry(package,'run','python','-c',code);origins.append(json.loads(dest.read_text()))
r={'status':'OWN_PREPARED_BOOTSTRAP_REUSE_VERIFIED_NO_INSTALL','prepared_source':old,'original_bootstrap_log':str(log),'original_bootstrap_log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'measured_inputs':len(inputs),'inputs_exact_prepared_git_bytes_sha256':records,'own5venvs_current_config_and_python':envs,'own5actual_prefix_and_source_origin_assertions':origins,'new_Bootstrap_executed':False,'original_scope':'original own successful Bootstrap, complete declared24 gateway/build plus19 manifest/lock union30 comparisons; no claim missing historical config hashes'}
(out/'immediate-pre-full-own-Bootstrap-reuse-inputs-and-origins.json').write_text(json.dumps(r,indent=2)+'\n');print('All',len(inputs),'prepared inputs equal; five own module origins and prefixes pass; no installs',flush=True)
