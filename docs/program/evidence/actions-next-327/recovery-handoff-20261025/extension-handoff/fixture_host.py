"""Disposable managed-API subset fixture; not an ordinary installed-host claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
from types import SimpleNamespace
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    source = args.source.resolve()
    tree = subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=source, text=True).strip()
    if tree != 'f094faf5d2eabbef0a159a7fabb4983a59a8e56c':
        raise SystemExit('Use the exact a37 source tree; this fixture is not qualified on other sources')
    args.state.mkdir(mode=0o700, parents=True, exist_ok=False)
    sys.path.insert(0, str(source / 'action_server/tests'))
    from action_server_tests.test_invoice_review import reviewed
    from action_server_tests.test_managed_work_items_sql_service import _SQLiteInvoiceProvider
    from actions.server import __version__
    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.foundry.sql_authorization import reference_grant_subject
    from actions.server.managed_work_items.authorization import SqlQueueAuthorization, bearer_authenticator
    from actions.server.managed_work_items.api import create_router
    from actions.server.managed_work_items.contracts import API_PREFIX, ManagedCaller, Permission, public_contract_schema
    from actions.server.managed_work_items.sql_service import SQLManagedWorkItemsService
    from fastapi import FastAPI
    if __version__ != '1.1.0a37':
        raise SystemExit('Runtime a37 required')
    database = args.state / 'invoice-source.sqlite'
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE invoices(invoice_id TEXT, customer TEXT, amount_cents INTEGER, days_overdue INTEGER)')
        db.executemany('INSERT INTO invoices VALUES (?,?,?,?)', [('synthetic-001','North',12500,42),('synthetic-002','South',400,3)])
    fixture = reviewed.__wrapped__(SimpleNamespace(param='sqlite'), args.state, _SQLiteInvoiceProvider(database))
    values = next(fixture)
    try:
        db, _, _, reviews, actor, scope, handle, _ = values
        proposal = reviews.offer(actor, scope, handle)
        with db.transaction():
            for kind, subject in [('workspace',scope.application.workspace_id),('reference',reference_grant_subject(scope.deployment))]:
                db.insert(FoundryAccessGrant(str(uuid4()),scope.application.workspace_id,actor.principal_id,kind,subject,json.dumps([p.value for p in Permission])))
        identity = ManagedCaller(actor=actor,worker_id=str(uuid4()))
        service = SQLManagedWorkItemsService(reviews,SqlQueueAuthorization(db))
        token = secrets.token_urlsafe(32)
        token_path = args.state / 'local-bearer'
        fd = os.open(token_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f: f.write(token)
        app = FastAPI()
        app.include_router(create_router(service,bearer_authenticator(token,identity)))
        queue = {'workspace_id':scope.application.workspace_id,'deployment':scope.deployment.model_dump(mode='json'),'queue_id':reviews.queue(scope).queue_name}
        schema = public_contract_schema()
        info = {'base_url':f'http://127.0.0.1:{args.port}','workspace_id':scope.application.workspace_id,'queue':queue,'review':proposal.model_dump(mode='json'),'run_id':proposal.binding.run_id,'artifact_handle':handle,'local_auth_file':str(token_path),'schema_canonical_sha256':hashlib.sha256(json.dumps(schema,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),'limitations':['synthetic definition/authorization setup with real SQL query Run/Attempt/output/review','no RCC worker: retry and complete not advertised','no ordinary Runtime startup, generic producer/consumer or installed acceptance claim']}
        (args.state/'fixture.json').write_text(json.dumps(info,indent=2)+'\n')
        if args.self_test:
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                headers={'authorization':'Bearer '+token}
                assert client.get(API_PREFIX+'/schema').status_code == 401
                assert client.get(API_PREFIX+'/schema',headers=headers).json()==schema
                r=client.get(API_PREFIX+'/capabilities',params={'workspace_id':scope.application.workspace_id},headers=headers)
                assert r.status_code==200,r.text
                for operation,fields in [('reviews.list',{}),('runs.get',{'run_id':proposal.binding.run_id}),('artifacts.read',{'artifact_handle':handle})]:
                    r=client.post(API_PREFIX+'/operations',headers=headers,json={'operation':operation,'queue':queue,**fields})
                    assert r.status_code==200,(operation,r.text)
            print(json.dumps({'status':'PASS','schema_canonical_sha256':info['schema_canonical_sha256'],'checks':['unauthenticated refusal','schema','capabilities','review','Run','artifact']}))
        else:
            print(json.dumps({'fixture_file':str(args.state/'fixture.json'),'base_url':info['base_url'],'workspace_id':info['workspace_id']}),flush=True)
            import uvicorn
            uvicorn.run(app,host='127.0.0.1',port=args.port,access_log=False)
    finally:
        fixture.close()


if __name__ == '__main__':
    main()
