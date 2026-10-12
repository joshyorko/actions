import toolkit
for package,module in [('actions','actions'),('action_server','actions.server'),('actions-http-helper','actions_http'),('devutils','devutils.invoke_utils'),('work-items','actions.work_items')]:
    code = 'import importlib,sys,json; from pathlib import Path; r=Path.cwd(); m=importlib.import_module('+repr(module)+'); assert Path(sys.prefix).resolve()==(r/".venv").resolve(); assert Path(m.__file__).resolve().is_relative_to(r/"src"); print(json.dumps({"package":'+repr(package)+',"own_prefix":True,"own_source":True,"prefix":sys.prefix,"source":m.__file__}))'
    toolkit.poetry(package,'run','python','-c',code)
