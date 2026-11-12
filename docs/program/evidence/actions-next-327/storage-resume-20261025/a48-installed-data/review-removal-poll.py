"""AST-extracted controller class with inert Docker and virtual clock only."""
import ast
import json
import re
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

BASE=Path(__file__).parent
source=BASE/'run-owned-postgres.py'
tree=ast.parse(source.read_text())
selected=ast.Module(body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ('exception_diagnostic','OwnedFixtureContainer')],type_ignores=[])
results=[]
for case in ('delayed-removal','never-removed','unknown-error','inspection-timeout'):
    clock=SimpleNamespace(now=0.0)
    clock.monotonic=lambda:clock.now
    def sleep(seconds):clock.now+=seconds
    clock.sleep=sleep
    ns=dict(Path=Path,re=re,json=json,subprocess=subprocess,uuid4=uuid4,time=clock)
    exec(compile(selected,str(source),'exec'),ns)
    with tempfile.TemporaryDirectory(dir=BASE,prefix='poll-mock-') as tmp:
        calls=[];cid='a'*64;removed=False
        def run(command,**kwargs):
            global removed
            calls.append((command,kwargs['timeout']))
            if command[1]=='inspect':
                if removed and case=='inspection-timeout':
                    assert kwargs['timeout']<=3
                    raise subprocess.TimeoutExpired(command,kwargs['timeout'])
                absent=removed and case!='never-removed' and clock.now>=0.5
                return SimpleNamespace(returncode=int(absent),stdout='[]' if absent else json.dumps([{'Id':cid,'Name':'/'+owner.name}]),stderr='')
            if command[1:3]==['container','ls']:
                assert 'id='+cid in command
                return SimpleNamespace(returncode=0,stdout='',stderr='')
            assert command[-1]==cid
            if command[1]=='rm':
                removed=True
                return SimpleNamespace(returncode=1,stdout='',stderr='unknown' if case=='unknown-error' else 'removal of container '+cid+' is already in progress')
            assert command[1]=='stop'
            return SimpleNamespace(returncode=0,stdout='',stderr='')
        owner=ns['OwnedFixtureContainer'](Path(tmp),run);owner.attempted=True;owner.container_id=cid
        failure=None
        try:result=owner.cleanup()
        except BaseException as exc:failure=type(exc).__name__
        assert sum(c[0][1]=='stop' for c in calls)==1
        assert sum(c[0][1]=='rm' for c in calls)==1
        assert clock.now<=15
        if case=='delayed-removal':
            assert failure is None and result['status']=='REMOVED' and result['warnings']
            assert owner.cleanup_steps[-1]['polls']==3
        else:assert failure is not None
        if case=='never-removed':assert clock.now==15
        if case=='unknown-error':assert owner.cleanup_steps[-1]['classification']=='confirmed-absent'
        results.append({'case':case,'status':'PASS','virtual_seconds':clock.now,'expected_failure':failure})
(BASE/'review-removal-poll.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results))
