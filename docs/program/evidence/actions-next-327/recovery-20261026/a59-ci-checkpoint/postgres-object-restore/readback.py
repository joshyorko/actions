import hashlib
import json
import os
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

from actions.server._database import Database
from actions.server._models import Run, get_all_model_classes
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import CapabilityWorkItemPolicy
from actions.server.foundry.generic_work_item_execution import GenericWorkItemExecution
from actions.server.foundry.models import FoundryAudit, FoundryRequest
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.managed_work_items.contracts import ManagedCaller
from actions.server.managed_work_items.authorization import SqlQueueAuthorization
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.models import RunAttempt, RunExecutionIntent, RunOutput, RunPin
from actions.server.run_outputs.service import RunOutputService
from actions.server.run_outputs.types import ExecutionSnapshot, OutputRef

context = json.loads(Path(sys.argv[1]).read_text())
prepared_path = Path(context['prepared_receipt'])
prepared = json.loads(prepared_path.read_text())
assert prepared['schemaVersion'] == 'actions.prepared-rcc-cache/v1'
assert prepared['rccVersion'] == 'v18.19.3'
assert prepared['artifactDigest'] == 'sha256:ab46f17f4b1ec8d620a3111ad103eff36f78515df5b4db88d1739f5b1e0a6a24'
assert prepared['specificationDigest'] == 'sha256:c73d38836f2c9e4655fba9221dbe9d208a57a25f40728a0e3e377f0a6f33a60d'
assert Path(prepared['robocorpHome']).resolve(strict=True) == Path(context['expected_robocorp_home']).resolve(strict=True)
assert Path(prepared['robocorpHome']).resolve() != Path(context['forbidden_robocorp_home']).resolve()
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
        def digest_rows(rows):
            values = [asdict(row) if is_dataclass(row) else row.model_dump(mode='json') for row in rows]
            encoded = json.dumps(values, sort_keys=True, separators=(',', ':'), default=str).encode()
            return {'count': len(values), 'sha256': hashlib.sha256(encoded).hexdigest()}

        def inventory():
            models = (Run, RunAttempt, RunExecutionIntent, RunPin, RunOutput, FoundryAudit, FoundryRequest)
            return {model.__name__: digest_rows(db.all(model)) for model in models}

        inventories_before = inventory()
        run, attempt, ticket = service.read_execution(caller, context['item'])
        assert run.id == context['run'] and attempt.state == 'succeeded'
        # Repeat the ordinary authorized terminal read in this fresh process.
        # It must resolve the retained Run and Attempt without an RCC adapter.
        replay_run, replay_attempt, replay_ticket = service.read_execution(caller, context['item'])
        assert (replay_run.id, replay_attempt.id, replay_ticket.fence) == (run.id, attempt.id, ticket.fence)
        inventories_after = inventory()
        assert inventories_after == inventories_before
        record = json.loads(run.result)
        assert record['version'] == 1 and run.status == 2
        result_record = record['result']
        assert result_record['rccSpecificationDigest'] == prepared['specificationDigest']
        assert result_record['rccArtifactDigest'] == prepared['artifactDigest']
        assert result_record['launch']['rccArtifactDigest'] == result_record['rccArtifactDigest']
        assert result_record['launch']['sourceArtifactDigest'] == result_record['sourceArtifactDigest']
        assert result_record['lineage']['runId'] == run.id
        refs = [OutputRef.model_validate_json(json.dumps(x['ref'])) for x in result_record['outputs']]
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
        requests = db.all(FoundryRequest, where='operation=?', values=['generic-work-items.enqueue'])
        linked_requests = [row for row in requests if json.loads(row.result_json).get('item_id') == context['item']]
        assert len(linked_requests) == 1
        audit = db.all(FoundryAudit, where='foundry_request_id=?', values=[linked_requests[0].id])
        intents = db.all(RunExecutionIntent, where='id=?', values=[run.id])
        pins = db.all(RunPin, where='run_id=?', values=[run.id])
        attempts_for_run = db.all(RunAttempt, where='run_id=?', values=[run.id])
        outputs_for_run = db.all(RunOutput, where='run_id=?', values=[run.id])
        assert len(audit) == 1 and len(pins) == 1
        # This direct generated-work-item path persists its launch in Run.result.
        # RunExecutionIntent belongs to the detached dispatcher, not this path.
        assert intents == []
        launch = result_record['launch']
        assert isinstance(launch, dict) and launch['lineage']['runId'] == run.id
        launch_digest = hashlib.sha256(json.dumps(launch, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert len(attempts_for_run) == 1 and len(outputs_for_run) == 4
        result = {'status': 'PASS', 'run': run.id, 'attempt': attempt.id,
                  'runs': len(db.all(Run)), 'attempts': len(db.all(RunAttempt)),
                  'snapshot': snapshot.model_dump(mode='json'), 'outputs': hashes,
                  'journal': {'storage':'Run.result.result.launch','sha256':launch_digest}, 'detached_intents':digest_rows(intents), 'audit': digest_rows(audit),
                  'requests': digest_rows(linked_requests), 'run_pin': digest_rows(pins),
                  'run_attempt': digest_rows(attempts_for_run), 'run_outputs': digest_rows(outputs_for_run),
                  'source_artifact_digest': result_record['sourceArtifactDigest'],
                  'rcc_specification_digest': result_record['rccSpecificationDigest'],
                  'rcc_artifact_digest': result_record['rccArtifactDigest'],
                  'prepared_receipt_sha256': hashlib.sha256(prepared_path.read_bytes()).hexdigest(),
                  'prepared_robocorp_home': str(Path(prepared['robocorpHome']).resolve()),
                  'inventories_before': inventories_before, 'inventories_after': inventories_after}
finally:
    os.close(fd)
print(json.dumps(result, sort_keys=True))
