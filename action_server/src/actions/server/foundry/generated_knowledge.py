"""Knowledge preparation for the existing generated Run/RCC publication path.

Corpus provider writes are staging. Only a validated successful generated Run
and its exact sealed corpus inventory authorize a later consumer.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from actions.server._models import Run, RunStatus
from actions.server.data_queries.knowledge_execution import (
    KnowledgeExecution,
    KnowledgeExecutionBinding,
    KnowledgeSearch,
    PreparedKnowledgeIngestion,
)
from actions.server.data_queries.knowledge_normalization import (
    MAX_CORPUS_BYTES,
    NormalizedKnowledge,
    validate_corpus,
)
from actions.server.data_queries.sealed_sources import ReadBudget, json_bytes
from actions.server.foundry.logical_receipts import KnowledgeOperationEvidence
from actions.server.foundry.provider_execution import SQLRecordPin
from actions.server.run_outputs.models import RunAttempt, RunOutput, RunPin
from actions.server.run_outputs.service import AccessDenied, _now, _one, _transaction
from actions.server.run_outputs.types import (
    AttemptFence,
    ExecutionSnapshot,
    output_id_from_handle,
)


def operation_key(run_id, requirement_id, operation):
    return hashlib.sha256(
        json_bytes(
            [
                "actions.generated-knowledge-operation/v1",
                run_id,
                requirement_id,
                operation,
            ]
        )
    ).hexdigest()


@dataclass(frozen=True)
class KnowledgePreparation:
    service: KnowledgeExecution
    ingestion: PreparedKnowledgeIngestion | None
    parameters: bytes
    result: bytes
    evidence: KnowledgeOperationEvidence
    budget: ReadBudget
    source_snapshot: ExecutionSnapshot | None = None
    source_pins: tuple[SQLRecordPin, ...] = ()

    def recheck(self, actor, fence):
        if self.budget.cancelled.is_set():
            raise AccessDenied("Knowledge publication cancelled or deadline exceeded")
        if self.ingestion is not None:
            self.service.recheck_prepared_ingestion(
                actor, fence, self.ingestion, preparation_complete=True
            )
        else:
            if self.source_snapshot is None:
                raise AccessDenied("Knowledge source snapshot required")
            for pin in self.source_pins:
                pin.recheck(self.service.db)
            self.service.outputs._authorize(actor, self.source_snapshot, "read")
            output = _one(
                self.service.db,
                RunOutput,
                output_id_from_handle(self.evidence.corpus_handle),
            )
            if output.state != "final" or int(output.expires_ms) <= _now(
                self.service.db
            ):
                raise AccessDenied("Knowledge ingestion output no longer available")
        if self.budget.cancelled.is_set():
            raise AccessDenied("Knowledge publication cancelled or deadline exceeded")


def _ingestion_source(outputs, actor, handle, revision, provider):
    """Validate the complete generated source, then retain SQL-only final pins."""
    from actions.server.deployments.foundry_repository import FoundryRepository
    from actions.server.foundry.logical_receipts import _parse, validate_bound_record

    with _transaction(outputs.db):
        output = _one(outputs.db, RunOutput, output_id_from_handle(handle))
        pin = _one(outputs.db, RunPin, output.run_id)
        snapshot = outputs._pinned(pin)
        outputs._authorize(actor, snapshot, "read")
        run = _one(outputs.db, Run, output.run_id)
        attempt = _one(outputs.db, RunAttempt, pin.current_attempt_id)
        fence = AttemptFence(
            run_id=run.id,
            attempt_id=attempt.id,
            owner_id=attempt.owner_id,
            epoch=pin.epoch,
        )
        if (
            run.status != RunStatus.PASSED
            or attempt.state != "succeeded"
            or attempt.epoch != pin.epoch
            or attempt.run_id != run.id
            or attempt.workspace_id != snapshot.workspace_id
            or snapshot.workspace_id != str(revision.workspace_id.root)
            or output.run_attempt_id != attempt.id
            or output.epoch != pin.epoch
        ):
            raise AccessDenied("successful Knowledge source Attempt required")
        carrier = json.loads(run.result)
        record = carrier["result"]
        validate_bound_record(
            outputs.db,
            outputs.capabilities,
            snapshot,
            run,
            fence,
            record,
            claim=record.get("claim"),
            terminal=True,
            outputs=carrier["outputs"],
            _allow_expired_terminal=True,
        )
        summary = _parse(record["logicalReads"])
        matches = [
            op
            for op in summary.operations
            if getattr(op, "knowledge", None) is not None
            and op.operation.endswith(".ingest/v1")
            and op.knowledge.corpus_handle == handle
        ]
        if len(matches) != 1:
            raise AccessDenied("exact generated Knowledge ingestion required")
        selected = matches[0]
        evidence = selected.knowledge
        stored = FoundryRepository(outputs.db).get_revision(snapshot.deployment)
        bindings = [
            b
            for b in stored.revision.specification.bindings
            if b.requirement.requirement_id.root == selected.requirement_id
        ]
        if (
            len(bindings) != 1
            or bindings[0].provider != provider
            or evidence.revision != revision
        ):
            raise AccessDenied("Knowledge source binding differs")
        pins = tuple(
            SQLRecordPin.capture(outputs.db, model, "id=?", (identity,))
            for model, identity in [
                (Run, run.id),
                (RunPin, pin.id),
                (RunAttempt, attempt.id),
                (RunOutput, output.id),
            ]
        )
        return evidence, snapshot, pins


def prepare_knowledge(
    execution,
    actor,
    fence,
    snapshot,
    binding,
    requirement,
    operation,
    parameters,
    event,
):
    from actions.server.data_queries.knowledge_operations import (
        encode_result,
        knowledge_contract,
    )
    from actions.server.foundry.logical_receipts import KnowledgeOperationEvidence

    kind = knowledge_contract(operation)
    budget = ReadBudget(operation.timeout_ms, event)
    with execution.configured.open_knowledge(
        actor, binding.provider, manage=kind == "ingest"
    ) as selected:
        service = KnowledgeExecution(
            execution.outputs,
            selected.authority,
            (
                KnowledgeExecutionBinding(
                    snapshot,
                    selected.revision,
                    selected.source_provider,
                    selected.source,
                    selected.blobs,
                    selected.seals,
                    selected.versions,
                    kind,
                ),
            ),
        )
        spec = selected.authority.require_revision(
            actor, selected.revision, "knowledge.read"
        )
        pending, source_snapshot, source_pins = None, None, ()
        if kind == "ingest":
            key = operation_key(fence.run_id, requirement.id, operation.name)
            pending = service.prepare_ingestion(
                actor,
                fence,
                event,
                operation_id=key,
                output_name="knowledge-" + key + ".json",
                mapped_inputs=parameters,
                timeout_ms=operation.timeout_ms,
            )
            evidence = KnowledgeOperationEvidence(
                revision=selected.revision,
                corpusHandle=pending.output.handle,
                corpusDigest=pending.corpus_digest,
                corpusOutput=pending.output_name,
                sourceFence=fence,
            )
            result = {
                "version": "actions.knowledge-ingestion-staged/v1",
                "revision": selected.revision.model_dump(mode="json"),
                "corpusHandle": pending.output.handle,
                "corpusDigest": pending.corpus_digest,
                "status": "staged",
            }
        else:
            request = KnowledgeSearch.model_validate(parameters)
            if (
                len(request.query) > spec.max_query_characters
                or request.offset > spec.max_offset
                or request.limit > min(spec.max_results, operation.max_rows)
                or not request.query.strip()
                or "\x00" in request.query
            ):
                raise AccessDenied("Knowledge query exceeds declared bounds")
            evidence, source_snapshot, source_pins = _ingestion_source(
                execution.outputs,
                actor,
                request.ingestion_handle,
                selected.revision,
                selected.source_provider,
            )
            with execution.outputs.resolve(
                actor, snapshot.workspace_id, request.ingestion_handle
            ) as stream:
                if (
                    stream.name != evidence.corpus_output
                    or stream.media_type != "application/json"
                    or stream.size > MAX_CORPUS_BYTES
                    or stream.digest != evidence.corpus_digest
                ):
                    raise AccessDenied("Knowledge corpus output differs")
                parts, size = [], 0
                while True:
                    budget.check()
                    chunk = stream.read(65536)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_CORPUS_BYTES:
                        raise AccessDenied("Knowledge corpus exceeds bound")
                    parts.append(chunk)
                corpus = NormalizedKnowledge(b"".join(parts), stream.digest)
            definition, documents = validate_corpus(corpus)
            if (
                definition.reference != selected.revision
                or selected.versions.read(selected.revision, budget=budget) != corpus
            ):
                raise AccessDenied("Knowledge provider and published corpus differ")
            hits, total = [], 0
            for document in documents:
                budget.check()
                if request.query.casefold() in document["text"].casefold():
                    if request.offset <= total < request.offset + request.limit:
                        hits.append(document)
                    total += 1
            result = {
                "version": "actions.knowledge-search/v1",
                "revision": selected.revision.model_dump(mode="json"),
                "ingestionHandle": request.ingestion_handle,
                "corpusDigest": corpus.digest,
                "query": request.query,
                "offset": request.offset,
                "limit": request.limit,
                "total": total,
                "hits": hits,
            }
            if len(json_bytes(result)) > spec.max_result_bytes:
                raise AccessDenied("Knowledge result exceeds definition bound")
        budget.check()
        if pending is not None:
            pending.budget.check()
        wrapped = encode_result(operation, result)
        prepared = KnowledgePreparation(
            service,
            pending,
            json_bytes(parameters),
            json_bytes(wrapped),
            evidence,
            budget,
            source_snapshot,
            source_pins,
        )
        prepared.recheck(actor, fence)
        return prepared
