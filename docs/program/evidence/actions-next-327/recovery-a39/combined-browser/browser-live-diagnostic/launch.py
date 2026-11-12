import functools,json,re,sys
from pathlib import Path
from actions.server.foundry.package_registry import FoundryPackageRegistry
OUT=Path('/workspace/actions-327-a39/browser-live-diagnostic/phases.jsonl')
def record(phase,kind,message=''):
    # Never record arguments, body, environment, traceback locals or credentials.
    message=re.sub(r'(?i)(bearer\s+|token[=: ]+|password[=: ]+)[^\s,]+',r'\1[redacted]',message)
    with OUT.open('a') as stream:stream.write(json.dumps({'phase':phase,'kind':kind,'message':message[:400]})+'\n')
for name in ('compile_trusted_source','admit_compiled'):
    original=getattr(FoundryPackageRegistry,name)
    def wrap(fn,phase):
        @functools.wraps(fn)
        def invoke(*args,**kwargs):
            record(phase,'entered')
            try:
                value=fn(*args,**kwargs)
                evidence=getattr(value,'evidence',None)
                record(phase,'returned',str(getattr(evidence,'failure_code','')))
                return value
            except Exception as exc:
                record(phase,type(exc).__name__,str(exc));raise
        return invoke
    setattr(FoundryPackageRegistry,name,wrap(original,name))
from actions.server.cli import main
sys.exit(main())
