import importlib, json, sys
from pathlib import Path
import toolkit
R=Path("/workspace/engineering/pr300")
O=Path("/workspace/engineering/pr300-issue86-assembled-transport-source-successor")
for package, module in (("actions","actions"),("actions-http-helper","actions_http"),("devutils","devutils.invoke_utils"),("work-items","actions.work_items"),("action_server","actions.server.run_outputs.transport")):
 code=f"import importlib,json,sys; from pathlib import Path; m=importlib.import_module({module!r}); r=Path({str(R/package)!r}); origin=Path(m.__file__).resolve(); assert Path(sys.prefix).resolve()==(r/'.venv').resolve(); assert origin.is_relative_to(r/'src'); Path({str(O)!r}, 'origin-'+{package!r}+'.json').write_text(json.dumps(dict(module={module!r},prefix=sys.prefix,origin=str(origin),python=sys.executable)))"
 toolkit.poetry(package,"run","python","-c",code)
