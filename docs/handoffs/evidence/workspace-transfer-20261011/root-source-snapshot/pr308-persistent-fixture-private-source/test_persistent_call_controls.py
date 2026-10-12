import ast
import copy
import importlib.util
import os
from pathlib import Path

import pytest


def load_validator():
    path=Path(os.environ['PERSISTENT_CANDIDATE_FILE'])
    namespace={'Path':Path,'math':__import__('math')}
    nodes=[n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='_validate_persistent_call_series']
    assert len(nodes)==1
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path), 'exec'),namespace)
    return namespace['_validate_persistent_call_series']


@pytest.fixture
def series(tmp_path):
    root=tmp_path/'managed';source=tmp_path/'sources';root.mkdir();source.mkdir()
    expected={'compatibility_id':'c'*64,'version':'v18.19.5','binary_sha256':'b'*64,'source_commit':'d'*40}
    kwargs={'expected_compatibility':expected,'artifact_digest':'sha256:'+'a'*64,'receipt_path':str(tmp_path/'real-lease.json'),'source_hash':'e'*64,'managed_root':root,'source_root':source}
    rows=[{'ordinal':i,'counter':i,'worker_pid':123,'worker_created':1234.125,'wrapper_pid':100,'wrapper_created':1230.5,'artifact_digest':kwargs['artifact_digest'],'compatibility':copy.deepcopy(expected),'receipt_path':kwargs['receipt_path'],'action_source_sha256':kwargs['source_hash'],'action_source_path':str(source/'snapshot/action.py'),'python_executable':str(root/'python'),'core_origin':str(root/'actions/__init__.py'),'core_version':'1.0.2'} for i in range(1,7)]
    return rows,kwargs


def test_valid_synthetic_series_only(series):
    rows,kwargs=series
    assert load_validator()(rows,**kwargs)==rows


@pytest.mark.parametrize('poison',['pid','created','wrapper','wrapper_created','artifact','compatibility','lease','counter','missing','bool','overflow','core','python','source','source_hash','nan','few','extra'])
def test_poisoned_synthetic_series_is_refused(series,poison):
    rows,kwargs=series
    if poison=='pid': rows[3]['worker_pid']=124
    elif poison=='created': rows[3]['worker_created']=1234.126
    elif poison=='wrapper': rows[3]['wrapper_pid']=101
    elif poison=='wrapper_created': rows[3]['wrapper_created']=1230.6
    elif poison=='artifact':rows[3]['artifact_digest']='sha256:'+'f'*64
    elif poison=='compatibility':rows[3]['compatibility']['binary_sha256']='f'*64
    elif poison=='lease':rows[3]['receipt_path']+='-other'
    elif poison=='counter':rows[3]['counter']=3
    elif poison=='missing':del rows[3]['worker_created']
    elif poison=='bool':rows[3]['worker_pid']=True
    elif poison=='overflow':rows[3]['worker_pid']=2**65
    elif poison=='core':rows[3]['core_origin']='/unowned/private/core.py'
    elif poison=='python':rows[3]['python_executable']='/unowned/python'
    elif poison=='source':rows[3]['action_source_path']='/unowned/action.py'
    elif poison=='source_hash':rows[3]['action_source_sha256']='f'*64
    elif poison=='nan':rows[3]['worker_created']=float('nan')
    elif poison=='few':rows.pop()
    elif poison=='extra':rows[3]['unmeasured_field']='synthetic'
    with pytest.raises(AssertionError):load_validator()(rows,**kwargs)


def _synthetic_loop_fixture(series,monkeypatch,require_reuse):
    import contextlib
    import dataclasses
    import json
    import types
    import psutil
    from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor,approved_rcc_test_policy

    rows,kwargs=series
    expected=dataclasses.asdict(approved_rcc_test_policy('released-18.19.5-linux-amd64'))
    descriptor=RccRuntimeDescriptor(artifact_digest=kwargs['artifact_digest'],rcc_version='v18.19.5',rcc_compatibility=approved_rcc_test_policy('released-18.19.5-linux-amd64'))
    package=types.SimpleNamespace(env_json=descriptor.to_json())
    class FakeProcess:
        def __init__(self,pid):self.pid=pid
        def create_time(self):return 1230.5 if self.pid==100 else 1234.125
        def parents(self):return [FakeProcess(100)]
    monkeypatch.setattr(psutil,'Process',FakeProcess)
    calls=[]
    class FakeHandle:
        pid=100
        _rcc_wrapper=types.SimpleNamespace(receipt_file=Path(kwargs['receipt_path']))
        def run_action(self,*args):
            if require_reuse:assert args[-1] is True,'persistent real delegation omitted reuse flag'
            calls.append(args)
            payload={k:rows[0][k] for k in ('action_source_sha256','action_source_path','python_executable','core_origin','core_version')}
            payload.update(counter=str(len(calls)),worker_pid='123')
            args[6].write_text(json.dumps({'result':payload}))
            return 0
    class FakePool:
        @contextlib.contextmanager
        def obtain_process_for_action(self,action):yield FakeHandle()
    namespace={'Path':Path,'json':json}
    path=Path(os.environ['PERSISTENT_CANDIDATE_FILE'])
    nodes=[n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ('_validate_persistent_call_series','_run_persistent_staged_calls')]
    assert len(nodes)==2
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)
    run_type=dataclasses.make_dataclass('SyntheticRun',[('id',str),('numbered_id',int)])
    run_dir=kwargs['managed_root'].parent/'runs';run_dir.mkdir()
    result=namespace['_run_persistent_staged_calls'](FakePool(),package,object(),run_type('synthetic-owned-run',1),run_dir,{'action.py':kwargs['source_hash']},kwargs['managed_root'],kwargs['source_root'],expected)
    assert len(calls)==6 and len(result[2])==6
    return calls


def test_synthetic_delegate_uses_actual_reuse_flag(series,monkeypatch):
    assert all(call[-1] is True for call in _synthetic_loop_fixture(series,monkeypatch,True))


def test_synthetic_delegate_uses_existing_descriptor_dataclass_API(series,monkeypatch):
    assert len(_synthetic_loop_fixture(series,monkeypatch,False))==6
