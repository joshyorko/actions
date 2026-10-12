"""Nine real SQLite/reload/pool controls, PREPARED ONLY until ROOT test release.

Environment collection and worker handles are explicit controlled seams. No
native/provider/action subprocess runs. Real import transaction, routes and
pool generation algorithms remain under test; native fixture evidence is a
separate future gate. Each opt-in mutant alters one current function privately.
"""
import ast
import inspect
import os
import textwrap
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest


class ControlledFailure(RuntimeError):
    pass


class OldHandle:
    can_reuse = True


def _install_one_private_mutant(monkeypatch, name):
    """Deliberately broken current algorithms: baseline controls must reject them."""
    if os.environ.get('RCC_RELOAD_PRIVATE_MUTANT') != name:
        return
    from actions.server import _actions_import, _server
    from actions.server._actions_process_pool import ActionsProcessPool
    if name in ('prepare_under_writer', 'publish_before_commit', 'omit_candidate_cleanup', 'omit_repaired_publish'):
        owner, key = _actions_import, 'import_action_packages'
    elif name in ('publish_staged_routes', 'omit_restore_token'):
        owner, key = _server, '_reload_action_generation'
    else:
        owner, key = ActionsProcessPool, 'on_reload'
    original = getattr(owner, key)
    tree = ast.parse(textwrap.dedent(inspect.getsource(original)))
    function = tree.body[0]
    hits = 0
    if name == 'prepare_under_writer':
        parent = next(n for n in function.body if isinstance(n, ast.Try))
        loop = next(n for n in parent.body if isinstance(n, ast.For))
        i = parent.body.index(loop)
        parent.body[i] = ast.With(items=[ast.withitem(context_expr=ast.Call(func=ast.Attribute(value=ast.Call(func=ast.Name(id='get_db', ctx=ast.Load()), args=[], keywords=[]), attr='transaction', ctx=ast.Load()), args=[], keywords=[]))], body=[loop])
        hits = 1
    elif name == 'publish_before_commit':
        for node in ast.walk(function):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and any(isinstance(n,ast.Name) and n.id == 'after_import' for n in ast.walk(node.test)):
                node.body.extend(ast.parse('publish_generation()\npublish_generation = None').body)
                hits += 1
    elif name == 'publish_staged_routes':
        for parent in ast.walk(function):
            if hasattr(parent, 'body') and isinstance(parent.body,list):
                for i,node in enumerate(parent.body):
                    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prepared' for t in node.targets):
                        parent.body.insert(i+1,ast.parse('action_routes.publish_prepared_actions(prepared)').body[0]);hits+=1;break
    elif name == 'early_generation':
        increment = next(n for n in ast.walk(function) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='_generation' for t in n.targets))
        for parent in ast.walk(function):
            if hasattr(parent,'body') and isinstance(parent.body,list) and increment in parent.body:parent.body.remove(increment)
        warmup_try=next(n for n in ast.walk(function) if isinstance(n,ast.Try) and any(isinstance(x,ast.Attribute) and x.attr=='_warmup_processes_unlocked' for x in ast.walk(n)))
        warmup_try.body.insert(0,increment);hits=1
    else:
        class BreakOne(ast.NodeTransformer):
            def visit_Assign(self,node):
                nonlocal hits
                if name == 'omit_idle_restore' and any(isinstance(t,ast.Attribute) and t.attr=='_idle_processes' for t in node.targets) and isinstance(node.value,ast.Name) and node.value.id=='old_idle_processes':hits+=1;return ast.Pass()
                if name == 'keep_old_reusable' and any(isinstance(t,ast.Attribute) and t.attr=='can_reuse' for t in node.targets):hits+=1;return ast.Pass()
                return self.generic_visit(node)
            def visit_Expr(self,node):
                nonlocal hits
                if name == 'omit_restore_token' and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='restore_generation':hits+=1;return ast.Pass()
                if name == 'omit_repaired_publish' and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='publish_generation':hits+=1;return ast.Pass()
                return self.generic_visit(node)
            def visit_For(self,node):
                nonlocal hits
                if name=='omit_candidate_cleanup' and isinstance(node.iter,ast.Call) and isinstance(node.iter.func,ast.Name) and node.iter.func.id=='reversed':hits+=1;return ast.Pass()
                return self.generic_visit(node)
        tree=BreakOne().visit(tree)
    assert hits == 1, 'PRIVATE_MUTANT_MUST_CHANGE_EXACTLY_ONE_CURRENT_SEAM'
    ast.fix_missing_locations(tree)
    namespace=dict(original.__globals__)
    exec(compile(tree,'private-current-reload-single-seam-mutant','exec'),namespace)
    monkeypatch.setattr(owner,key,namespace[key])


@pytest.fixture
def catalog_case(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from actions.server import _actions_import, _app, _models, _server
    from actions.server._actions_process_pool import ActionsProcessPool
    from actions.server._api_action_routes import _ActionRoutes
    from actions.server._database import Database
    from actions.server._models import Action, ActionPackage, McpCatalogName, McpResourceRouting, get_model_db_rules
    from actions.server._settings import Settings
    db=Database(tmp_path/'catalog.sqlite')
    db.initialize([ActionPackage,Action,McpCatalogName,McpResourceRouting])
    monkeypatch.setattr(_models,'get_db',lambda:db)
    app=FastAPI();monkeypatch.setattr(_app,'get_app',lambda:app)
    old_dir=tmp_path/'G0';new_dir=tmp_path/'G1';old_dir.mkdir();new_dir.mkdir()
    (old_dir/'my_actions.py').write_text('G0 exact original source')
    (new_dir/'my_actions.py').write_text('G1 controlled candidate source')
    package=ActionPackage('package-id','package',str(old_dir),'G0','{}')
    action=Action('action-id',package.id,'do_it','G0 docs','my_actions.py',1,'{"type":"object","properties":{}}','{"type":"string"}')
    candidate=ActionPackage('candidate-id','package',str(new_dir),'G1','{}')
    candidate_action=Action('candidate-action-id',candidate.id,'do_it','G1 docs','my_actions.py',1,'{"type":"object","properties":{}}','{"type":"string"}')
    events=[];retired=[];state=dict(reject=None,warmup=None,after=None)
    pool=ActionsProcessPool(Settings(datadir=tmp_path,artifacts_dir=tmp_path/'artifacts',min_processes=0,max_processes=2),{package.id:package},[action])
    monkeypatch.setattr(pool,'_retire_detached',lambda handle,**kwargs:retired.append(handle))
    def warmup(**kwargs):
        assert kwargs == dict(include_running=False)
        events.append('warmup')
        if state['warmup'] is not None:state['warmup']()
    monkeypatch.setattr(pool,'_warmup_processes_unlocked',warmup)
    def collect(**kwargs):
        events.append('collect-outside-writer' if not db.in_transaction() else 'collect-under-writer')
        assert not db.in_transaction(), 'CANDIDATE_PREPARATION_MUST_PRECEDE_WRITER_TRANSACTION'
        def cleanup():
            events.append('candidate-cleanup')
            (new_dir/'my_actions.py').unlink()
            new_dir.rmdir()
        kwargs['_candidate_cleanup'].append(cleanup)
        if state['reject'] is not None:raise state['reject']
        kwargs['_prepared'].append((candidate,[candidate_action]))
    monkeypatch.setattr(_actions_import,'import_action_package',collect)
    routes=_ActionRoutes('',[])
    with db.connect():
        db.create_tables(get_model_db_rules())
        with db.transaction():db.insert(package);db.insert(action)
        routes.register_actions()
        original=dict(generation=pool.generation,routes=list(app.router.routes),catalog=routes.mcp_server_setup_helper._catalog,source=(old_dir/'my_actions.py').read_bytes())
        original['catalog_identity_snapshot'] = _catalog_identity_snapshot(original['catalog'])
        def after():
            events.append('after-import-before-commit')
            assert db.in_transaction()
            if state['after'] is not None:state['after']()
            closures=_server._reload_action_generation(routes,pool,db.all(Action),{p.id:p for p in db.all(ActionPackage)},defer_publication=True)
            assert app.router.routes == original['routes'], 'STAGED_ROUTES_MUST_NOT_PUBLISH'
            assert routes.mcp_server_setup_helper._catalog is original['catalog']
            publish,rollback=closures
            def committed_publish():
                assert not db.in_transaction(), 'PUBLICATION_MUST_FOLLOW_DURABLE_SQLITE_COMMIT'
                events.append('publish-after-commit');publish()
            return committed_publish,rollback
        def admit():
            return _actions_import.import_action_packages(datadir=tmp_path,action_package_dirs=['owned-candidate'],disable_not_imported=True,skip_lint=True,whitelist='',after_import=after)
        c=SimpleNamespace(db=db,pool=pool,routes=routes,app=app,package=package,action=action,candidate=candidate,candidate_action=candidate_action,old_dir=old_dir,new_dir=new_dir,original=original,events=events,retired=retired,state=state,admit=admit,Action=Action,ActionPackage=ActionPackage)
        yield c


def _catalog_identity_snapshot(catalog):
    """Freeze field structure, object identity and values without mutable aliases.

    A rollback may copy the outer catalog. Its original field containers and
    nested objects must remain exact, including their immutable value payloads.
    """
    seen = set()

    def freeze(value):
        if isinstance(value, (type(None), bool, int, float, str, bytes)):
            return ("value", type(value), id(value), value)
        identity = id(value)
        if identity in seen:
            return ("reference", type(value), identity)
        seen.add(identity)
        if isinstance(value, dict):
            contents = tuple((freeze(key), freeze(item)) for key, item in value.items())
            return ("dict", type(value), identity, contents)
        if isinstance(value, (list, tuple)):
            return ("sequence", type(value), identity, tuple(freeze(item) for item in value))
        if callable(value):
            return ("callable", type(value), identity)
        try:
            fields = vars(value)
        except TypeError as error:
            raise AssertionError("UNSUPPORTED_CATALOG_SNAPSHOT_LEAF") from error
        contents = tuple((name, freeze(item)) for name, item in fields.items())
        return ("object", type(value), identity, contents)

    return (type(catalog), tuple((name, freeze(value)) for name, value in vars(catalog).items()))


def assert_last_good(c):
    assert c.db.all(c.ActionPackage)[0].directory == str(c.old_dir)
    assert c.db.all(c.Action)[0].docs == 'G0 docs'
    assert c.pool.generation == c.original['generation']
    assert c.pool.actions[0].docs == 'G0 docs'
    assert c.app.router.routes == c.original['routes']
    assert _catalog_identity_snapshot(c.routes.mcp_server_setup_helper._catalog) == c.original['catalog_identity_snapshot']
    assert (c.old_dir/'my_actions.py').read_bytes() == c.original['source']


def test_candidate_preparation_precedes_real_sqlite_writer(catalog_case,monkeypatch):
    _install_one_private_mutant(monkeypatch,'prepare_under_writer')
    c=catalog_case;c.admit()
    assert c.events.index('collect-outside-writer') < c.events.index('after-import-before-commit')


def test_publication_follows_actual_sqlite_commit(catalog_case,monkeypatch):
    _install_one_private_mutant(monkeypatch,'publish_before_commit')
    c=catalog_case;c.admit()
    assert c.events[-1] == 'publish-after-commit'
    assert not c.db.in_transaction()
    assert c.db.all(c.Action)[0].docs == 'G1 docs'


def test_staged_pool_keeps_original_routes_until_commit(catalog_case,monkeypatch):
    _install_one_private_mutant(monkeypatch,'publish_staged_routes')
    c=catalog_case;c.admit()
    assert c.routes.mcp_server_setup_helper._catalog is not c.original['catalog']
    assert c.pool.generation == c.original['generation']+1


def test_failed_warmup_restores_original_idle_and_catalog(catalog_case,monkeypatch):
    _install_one_private_mutant(monkeypatch,'omit_idle_restore')
    c=catalog_case;idle=OldHandle();c.pool._idle_processes={'old':[idle]};original_idle=c.pool._idle_processes
    failure=ControlledFailure('owned warmup sentinel')
    def fail():
        c.pool._idle_processes={'candidate':[OldHandle()]}
        raise failure
    c.state['warmup']=fail
    with pytest.raises(ControlledFailure) as caught:c.admit()
    assert caught.value is failure
    assert c.pool._idle_processes is original_idle
    assert idle not in c.retired
    assert_last_good(c)


def test_actual_commit_failure_restores_original_generation_token(catalog_case,monkeypatch):
    _install_one_private_mutant(monkeypatch,'omit_restore_token')
    c=catalog_case;failure=ControlledFailure('owned nondurable commit sentinel');connection=c.db._tlocal.conn
    class CommitFail:
        def __getattr__(self,name):return getattr(connection,name)
        def commit(self):raise failure
        def rollback(self):connection.rollback()
    c.db._tlocal.conn=CommitFail()
    try:
        with pytest.raises(ControlledFailure) as caught:c.admit()
        assert caught.value is failure
        assert_last_good(c)
    finally:c.db._tlocal.conn=connection;connection.rollback()


def test_running_old_handle_drains_only_after_new_publication(catalog_case,monkeypatch):
    _install_one_private_mutant(monkeypatch,'keep_old_reusable')
    c=catalog_case;old=OldHandle();c.pool._running_processes={'old':[old]};started=threading.Event();release=threading.Event();result=[]
    def controlled_inflight():
        started.set()
        if release.wait(2):result.append(('G0',c.original['source']))
    thread=threading.Thread(target=controlled_inflight,name='owned-synthetic-drain-witness');thread.start()
    try:
        assert started.wait(2);c.admit()
        assert not old.can_reuse and old not in c.retired
        assert thread.is_alive() and not result
        assert c.db.all(c.Action)[0].docs == 'G1 docs'
        assert c.events[-1]=='publish-after-commit'
        release.set();thread.join(2)
        assert not thread.is_alive() and result==[('G0',c.original['source'])]
    finally:release.set();thread.join(2)


def test_candidate_warmup_precedes_generation_switch(catalog_case,monkeypatch):
    _install_one_private_mutant(monkeypatch,'early_generation')
    c=catalog_case;old=OldHandle();c.pool._running_processes={'old':[old]}
    def check():
        assert c.pool._lock.locked(), 'WARMUP_CALLBACK_REQUIRES_EXISTING_POOL_LOCK'
        assert c.pool._generation == c.original['generation']
        assert old.can_reuse
        assert c.pool.actions[0].docs == 'G1 docs'
    c.state['warmup']=check;c.admit()
    assert c.pool.generation==c.original['generation']+1


def test_rejected_candidate_cleanup_preserves_last_good(catalog_case,monkeypatch):
    _install_one_private_mutant(monkeypatch,'omit_candidate_cleanup')
    c=catalog_case;failure=SyntaxError('owned candidate rejection sentinel');c.state['reject']=failure
    with pytest.raises(SyntaxError) as caught:c.admit()
    assert caught.value is failure
    assert_last_good(c)
    assert 'after-import-before-commit' not in c.events and 'publish-after-commit' not in c.events
    assert not c.new_dir.exists()


def test_repaired_candidate_publishes_without_admitting_failed_generation(catalog_case,monkeypatch):
    _install_one_private_mutant(monkeypatch,'omit_repaired_publish')
    c=catalog_case;c.state['reject']=SyntaxError('owned G2 rejection')
    with pytest.raises(SyntaxError):c.admit()
    assert_last_good(c);assert not c.new_dir.exists()
    c.new_dir.mkdir();(c.new_dir/'my_actions.py').write_text('G3 repaired controlled source')
    c.candidate_action.docs='G3 docs';c.state['reject']=None;c.admit()
    assert c.db.all(c.Action)[0].docs=='G3 docs'
    assert c.routes.mcp_server_setup_helper._catalog.tools[0].description=='G3 docs'
    assert c.pool.generation==c.original['generation']+1
    assert c.events.count('publish-after-commit')==1
