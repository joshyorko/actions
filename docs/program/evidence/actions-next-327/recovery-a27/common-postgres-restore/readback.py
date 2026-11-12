import hashlib
import json
import os
import sys
from pathlib import Path

from actions.server._database import Database
from actions.server._models import Run, get_all_model_classes
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import CapabilityWorkItemPolicy
from actions.server.foundry.generic_work_item_execution import GenericWorkItemExecution
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.managed_work_items.contracts import ManagedCaller
from actions.server.managed_work_items.authorization import SqlQueueAuthorization
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.models import RunAttempt
from actions.server.run_outputs.service import RunOutputService
from actions.server.run_outputs.types import ExecutionSnapshot, OutputRef

context = json.loads(Path(sys.argv[1]).read_text())
snapshot = ExecutionSnapshot.model_validate_json(json.dumps(context['snapshot']))
caller = ManagedCaller.model_validate_json(json.dumps(context['caller']))
policy = CapabilityWorkItemPolicy.model_validate_json(json.dumps(context['policy']))
db = Database(context['database'])
fd = os.open(context['objects'], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
try:
    with db.connect(), FilesystemOutputProvider(fd) as provider:
        db.initialize(get_all_model_classes())
        auth = SqlFoundryAuthorization(db)
        registry = FoundryPackageRegistry(db, provider, auth, executor=object())
        deployments = FoundryDeploymentService(FoundryRepository(db), registry, auth, registry)
        outputs = RunOutputService(db, {snapshot.provider_key: provider}, capabilities=registry)
        service = GenericWorkItemExecution(deployments, outputs, snapshot, policy, SqlQueueAuthorization(db))
        run, attempt, ticket = service.read_execution(caller, context['item'])
        assert run.id == context['run'] and attempt.state == 'succeeded'
        refs = [OutputRef.model_validate_json(json.dumps(x)) for x in json.loads(run.result)['outputs']]
        assert len(refs) == 4
        hashes = []
        for ref in refs:
            with outputs.resolve(caller.actor, snapshot.workspace_id, ref.handle) as value:
                data = value.read(value.size + 1)
                expected_size, expected_digest = value.size, value.digest
            digest = 'sha256:' + hashlib.sha256(data).hexdigest()
            assert digest == expected_digest and len(data) == expected_size
            hashes.append({'handle': ref.handle, 'sha256': digest, 'size': len(data)})
        assert registry.get_capability(snapshot.capability) is not None
        result = {'status': 'PASS', 'run': run.id, 'attempt': attempt.id,
                  'runs': len(db.all(Run)), 'attempts': len(db.all(RunAttempt)),
                  'snapshot': snapshot.model_dump(mode='json'), 'outputs': hashes}
finally:
    os.close(fd)
print(json.dumps(result, sort_keys=True))
