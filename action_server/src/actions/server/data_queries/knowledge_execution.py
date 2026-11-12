"""Host-bound Knowledge operations on canonical Run/Attempt/output authority.

No admission, worker, grants or provider DDL are created here. A provider version
is staging until an exact successful Run publication and sealed corpus authorize
its consumption. The host reconstructs immutable bindings on restart.
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Literal, Mapping, Protocol
from weakref import WeakValueDictionary

from pydantic import BaseModel, ConfigDict, Field

from actions.server._models import Run, RunStatus
from actions.server.data_queries.knowledge_normalization import (
    MAX_CORPUS_BYTES,
    NormalizedKnowledge,
    normalize_knowledge,
    validate_corpus,
)
from actions.server.data_queries.knowledge_values import KnowledgeRevisionRef
from actions.server.data_queries.sealed_sources import (
    ReadBudget,
    SealedReadRejected,
    json_bytes,
)
from actions.server.deployments.ids import ProviderProfileRevisionRef
from actions.server.deployments.provider_registry import SourceManifest
from actions.server.foundry.knowledge_authority import KnowledgeRevisionAuthority
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.foundry.provider_execution import SQLRecordPin
from actions.server.foundry.provider_models import FoundryProviderAvailability
from actions.server.foundry.provider_registry import _ref_id
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.models import RunAttempt, RunOutput, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    RunOutputService,
    _lock_workspace,
    _now,
    _one,
    _transaction,
)
from actions.server.run_outputs.types import (
    Actor,
    AttemptFence,
    ExecutionSnapshot,
    OutputRef,
    SealReceipt,
    output_id_from_handle,
)


class VersionStore(Protocol):
    def put(
        self, corpus: NormalizedKnowledge, *, operation_id: str, budget: ReadBudget
    ) -> KnowledgeRevisionRef:
        ...

    def read(
        self, ref: KnowledgeRevisionRef, *, budget: ReadBudget
    ) -> NormalizedKnowledge:
        ...


class KnowledgeSearch(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    ingestion_handle: str = Field(pattern=r"^art_[A-Za-z0-9_-]{22}$")
    query: str = Field(min_length=1, max_length=512)
    offset: int = Field(default=0, ge=0, le=100000)
    limit: int = Field(default=20, ge=1, le=100)


def snapshot_key(snapshot: ExecutionSnapshot) -> str:
    checked = ExecutionSnapshot.model_validate_json(snapshot.model_dump_json())
    return (
        "sha256:"
        + hashlib.sha256(json_bytes(checked.model_dump(mode="json"))).hexdigest()
    )


@dataclass(frozen=True)
class KnowledgeExecutionBinding:
    """Exact host configuration, never accepted from a caller request."""

    snapshot: ExecutionSnapshot
    revision: KnowledgeRevisionRef
    source_provider: ProviderProfileRevisionRef
    source: SourceManifest
    blobs: FilesystemOutputProvider
    seals: Mapping[str, SealReceipt]
    versions: VersionStore
    operation: Literal["ingest", "search"]


@dataclass(frozen=True, eq=False)
class PreparedKnowledgeIngestion:
    """Issued nonterminal staging; only canonical publication confers readiness.

    Receipt bytes are immutable; the receipt property returns a fresh dict.
    Keep this value alive until publication/rejection. No durable job is created.
    """

    actor: Actor
    binding: KnowledgeExecutionBinding
    fence: AttemptFence
    output: OutputRef
    corpus_digest: str
    corpus_size: int
    operation_id: str
    output_name: str
    input_mapping_applied: bool
    budget: ReadBudget
    receipt_json: bytes
    provider_pin: SQLRecordPin
    output_pin: SQLRecordPin

    @property
    def receipt(self) -> dict:
        return json.loads(self.receipt_json)


class KnowledgeExecution:
    def __init__(
        self,
        outputs: RunOutputService,
        authority: KnowledgeRevisionAuthority,
        bindings: tuple[KnowledgeExecutionBinding, ...],
    ):
        if outputs.db is not authority.db:
            raise TypeError("Knowledge and Run authority must share common SQL")
        self.outputs, self.authority, self.db = outputs, authority, outputs.db
        self._prepared: WeakValueDictionary[
            int, PreparedKnowledgeIngestion
        ] = WeakValueDictionary()
        self.bindings: dict[str, KnowledgeExecutionBinding] = {}
        for binding in bindings:
            key = snapshot_key(binding.snapshot)
            if (
                key in self.bindings
                or binding.operation not in ("ingest", "search")
                or binding.snapshot.workspace_id
                != str(binding.revision.workspace_id.root)
                or binding.source_provider.workspace_id != binding.revision.workspace_id
                or binding.source.kind != "knowledge"
            ):
                raise ValueError("invalid or duplicate exact Knowledge binding")
            self.bindings[key] = binding

    def _selected(self, snapshot: ExecutionSnapshot) -> KnowledgeExecutionBinding:
        binding = self.bindings.get(snapshot_key(snapshot))
        if binding is None:
            raise AccessDenied("exact Knowledge execution binding unavailable")
        return binding

    def _authorize(
        self, actor: Actor, binding: KnowledgeExecutionBinding, *, manage: bool
    ):
        spec = self.authority.require_revision(
            actor, binding.revision, "knowledge.read"
        )
        if manage:
            self.authority.require_revision(actor, binding.revision, "knowledge.manage")
        auth = self.authority.authorization
        auth.require_reference(actor, binding.source_provider, "knowledge.read")
        descriptor = self.authority.providers.describe(actor, binding.source_provider)
        if (
            descriptor.kind != "knowledge"
            or descriptor.source_revision != spec.source_revision
            or binding.source.revision_id != spec.source_revision
        ):
            raise AccessDenied("Knowledge source selection differs")
        return spec

    def execute(
        self, actor: Actor, fence: AttemptFence, cancelled: threading.Event
    ) -> str:
        """Worker hook: existing admitted inputs/fence select the operation.

        On failure leave the canonical Run nonterminal. Provider write success is
        not completion; an explicit retry under the same live fence is idempotent.
        Expired/uncertain Attempts still require the existing recovery policy.
        """
        snapshot, inputs = self.outputs.execution_context(actor, fence)
        binding = self._selected(snapshot)
        if binding.operation == "search":
            spec = self._authorize(actor, binding, manage=False)
            publication_budget = ReadBudget(spec.timeout_ms, cancelled)
            request = KnowledgeSearch.model_validate(inputs)
            result = self.search_for_execution(actor, fence, request, cancelled)
            publication_budget.check()
            raw = json_bytes(result)
            output = self.outputs.stage(
                fence,
                [raw],
                name="knowledge-search.json",
                media_type="application/json",
                retention_seconds=86400,
            )
            with _transaction(self.db):
                _lock_workspace(self.db, snapshot.workspace_id)
                self._authorize(actor, binding, manage=False)
                publication_budget.check()
                self.outputs.publish(actor, fence, [output], result)
            return output.handle
        prepared = self.prepare_ingestion(actor, fence, cancelled)
        with _transaction(self.db):
            self.recheck_prepared_ingestion(actor, fence, prepared)
            self.outputs.publish(actor, fence, [prepared.output], prepared.receipt)
        return prepared.output.handle

    def prepare_ingestion(
        self,
        actor: Actor,
        fence: AttemptFence,
        cancelled: threading.Event,
        *,
        operation_id: str | None = None,
        output_name: str = "knowledge-corpus.json",
        mapped_inputs: dict | None = None,
        timeout_ms: int | None = None,
    ) -> PreparedKnowledgeIngestion:
        """Stage provider/output bytes under an existing admission, never complete it.

        Generated hosts must choose stable distinct operation IDs/output names
        for each declared ingestion. Defaults preserve standalone v1 behavior.
        mapped_inputs={} is a trusted host seam only after artifact-verified
        projection; it does not replace the actual admitted snapshot or fence.
        """
        actor, fence = Actor.model_validate(actor), AttemptFence.model_validate(fence)
        operation_id = fence.run_id if operation_id is None else operation_id
        if (
            type(operation_id) is not str  # noqa: E721 -- reject behavior-overriding subclasses
            or not 1 <= len(operation_id) <= 128
            or not operation_id.isascii()
            or not all(c.isalnum() or c in "_-" for c in operation_id)
        ):
            raise SealedReadRejected("invalid Knowledge operation identity")
        if (
            type(output_name) is not str  # noqa: E721 -- reject behavior-overriding subclasses
            or not 1 <= len(output_name.encode("utf-8")) <= 255
            or any(c in output_name for c in ("/", "\\", "\x00"))
            or output_name in {".", ".."}
        ):
            raise SealedReadRejected("portable output display name required")
        snapshot, inputs = self.outputs.execution_context(actor, fence)
        binding = self._selected(snapshot)
        if binding.operation != "ingest":
            raise AccessDenied("Knowledge ingestion binding required")
        if mapped_inputs is not None:
            if type(mapped_inputs) is not dict or mapped_inputs:  # noqa: E721 -- exact trusted empty projection only
                raise SealedReadRejected("exact empty mapped ingestion inputs required")
        elif inputs != {}:
            raise SealedReadRejected(
                "Knowledge ingestion accepts no caller source inputs"
            )
        spec = self._authorize(actor, binding, manage=True)
        with _transaction(self.db):
            state = _one(
                self.db, FoundryProviderAvailability, _ref_id(binding.source_provider)
            )
            if not state.enabled:
                raise AccessDenied("Knowledge provider disabled")
            provider_pin = SQLRecordPin.capture(
                self.db,
                FoundryProviderAvailability,
                "id=?",
                (_ref_id(binding.source_provider),),
            )
        if timeout_ms is not None and (
            not isinstance(timeout_ms, int)
            or isinstance(timeout_ms, bool)
            or not 1 <= timeout_ms <= 30000
        ):
            raise SealedReadRejected("bounded Knowledge preparation timeout required")
        budget = ReadBudget(
            min(spec.timeout_ms, timeout_ms)
            if timeout_ms is not None
            else spec.timeout_ms,
            cancelled,
        )
        corpus = normalize_knowledge(
            spec, binding.source, binding.blobs, binding.seals, budget
        )
        if (
            binding.versions.put(corpus, operation_id=operation_id, budget=budget)
            != binding.revision
        ):
            raise SealedReadRejected("Knowledge provider returned a different revision")
        budget.check()
        output = self.outputs.stage(
            fence,
            [corpus.raw],
            name=output_name,
            media_type="application/json",
            retention_seconds=86400,
        )
        budget.check()
        with _transaction(self.db):
            output_pin = SQLRecordPin.capture(
                self.db, RunOutput, "id=?", (output.output_id,)
            )
        prepared = PreparedKnowledgeIngestion(
            actor,
            binding,
            fence,
            output,
            corpus.digest,
            len(corpus.raw),
            operation_id,
            output_name,
            mapped_inputs is not None,
            budget,
            json_bytes(self._receipt(binding, fence, output.handle, corpus.digest)),
            provider_pin,
            output_pin,
        )
        self._prepared[id(prepared)] = prepared
        return prepared

    def recheck_prepared_ingestion(
        self,
        actor: Actor,
        fence: AttemptFence,
        prepared: PreparedKnowledgeIngestion,
        *,
        preparation_complete: bool = False,
    ) -> None:
        """SQL-only final check; caller owns the encompassing publication transaction.

        Never call providers.describe/_read here: they verify retained blob bytes.
        Current grants, immutable definition SQL and issued availability/output
        pins replace provider/file I/O at the final canonical publication boundary.
        """
        if (
            type(prepared) is not PreparedKnowledgeIngestion
            or self._prepared.get(id(prepared)) is not prepared
            or actor != prepared.actor
            or fence != prepared.fence
        ):
            raise SealedReadRejected("unissued or mismatched Knowledge preparation")

        def check_budget():
            if not isinstance(preparation_complete, bool):
                raise ValueError("explicit preparation phase required")
            if preparation_complete:
                if prepared.budget.cancelled.is_set():
                    raise SealedReadRejected("Knowledge publication cancelled")
            else:
                prepared.budget.check()

        check_budget()
        with _transaction(self.db):
            _lock_workspace(self.db, prepared.binding.snapshot.workspace_id)
            if self.db.backend_name == "postgresql":
                self.db.select(
                    FoundryAccessGrant,
                    "SELECT * FROM foundry_access_grant WHERE workspace_id=? AND principal_id=? ORDER BY id LIMIT 129 FOR SHARE",
                    [prepared.binding.snapshot.workspace_id, actor.principal_id],
                )
            snapshot, inputs = self.outputs.execution_context(actor, fence)
            if self._selected(snapshot) is not prepared.binding or (
                not prepared.input_mapping_applied and inputs != {}
            ):
                raise AccessDenied("Knowledge prepared admission changed")
            self.authority.require_revision(
                actor, prepared.binding.revision, "knowledge.read"
            )
            self.authority.require_revision(
                actor, prepared.binding.revision, "knowledge.manage"
            )
            for permission in ("knowledge.read", "provider.inspect"):
                self.authority.authorization.require_reference(
                    actor, prepared.binding.source_provider, permission
                )
            prepared.provider_pin.recheck(self.db)
            prepared.output_pin.recheck(self.db)
            output = _one(self.db, RunOutput, prepared.output.output_id)
            if (
                output.run_id != fence.run_id
                or output.run_attempt_id != fence.attempt_id
                or output.epoch != fence.epoch
                or output.state != "provisional"
                or output.workspace_id != snapshot.workspace_id
                or output.provider_key != snapshot.provider_key
                or output.digest != prepared.corpus_digest
                or output.size != prepared.corpus_size
                or not 1 <= output.size <= MAX_CORPUS_BYTES
                or output.name != prepared.output_name
                or output.media_type != "application/json"
                or int(output.expires_ms) <= _now(self.db)
            ):
                raise SealedReadRejected("prepared Knowledge output differs")
            check_budget()

    @staticmethod
    def _receipt(binding, fence, handle, digest):
        return {
            "version": "actions.knowledge-ingestion/v1",
            "revision": binding.revision.model_dump(mode="json"),
            "sourceProvider": binding.source_provider.model_dump(mode="json"),
            "snapshotDigest": snapshot_key(binding.snapshot),
            "fence": fence.model_dump(mode="json"),
            "corpusHandle": handle,
            "corpusDigest": digest,
        }

    def _published(
        self,
        actor: Actor,
        binding: KnowledgeExecutionBinding,
        handle: str,
        budget: ReadBudget,
    ) -> NormalizedKnowledge:
        """Read and validate the existing canonical terminal publication, not a cache flag."""
        with _transaction(self.db):
            output = _one(self.db, RunOutput, output_id_from_handle(handle))
            pin = _one(self.db, RunPin, output.run_id)
            source_binding = self._selected(self.outputs._pinned(pin))
            if (
                source_binding.operation != "ingest"
                or source_binding.revision != binding.revision
                or source_binding.source_provider != binding.source_provider
            ):
                raise AccessDenied("Knowledge ingestion publication selection differs")
            run = _one(self.db, Run, output.run_id)
            attempt = _one(self.db, RunAttempt, pin.current_attempt_id)
            fence = AttemptFence(
                run_id=run.id,
                attempt_id=attempt.id,
                owner_id=attempt.owner_id,
                epoch=pin.epoch,
            )
            snapshot_workspace = source_binding.snapshot.workspace_id
            expected = self._receipt(source_binding, fence, handle, output.digest)
            try:
                envelope = json.loads(run.result or "null")
                if (
                    run.status != RunStatus.PASSED
                    or attempt.state != "succeeded"
                    or attempt.run_id != run.id
                    or attempt.workspace_id != snapshot_workspace
                    or attempt.epoch != pin.epoch
                    or pin.workspace_id != snapshot_workspace
                    or output.run_attempt_id != attempt.id
                    or output.epoch != pin.epoch
                    or envelope["result"] != expected
                ):
                    raise ValueError()
            except (ValueError, KeyError, TypeError):
                raise AccessDenied(
                    "Knowledge ingestion publication unavailable"
                ) from None
        with self.outputs.resolve(
            actor, str(binding.revision.workspace_id.root), handle
        ) as result:
            if (
                result.name != "knowledge-corpus.json"
                or result.media_type != "application/json"
                or result.size > MAX_CORPUS_BYTES
            ):
                raise SealedReadRejected("Knowledge corpus output differs")
            parts, size = [], 0
            while True:
                budget.check()
                chunk = result.read(65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_CORPUS_BYTES:
                    raise SealedReadRejected("Knowledge corpus output exceeds bound")
                parts.append(chunk)
            corpus = NormalizedKnowledge(b"".join(parts), result.digest)
        spec, _ = validate_corpus(corpus)
        if (
            spec.reference != binding.revision
            or binding.versions.read(binding.revision, budget=budget) != corpus
        ):
            raise SealedReadRejected("Knowledge provider and published corpus differ")
        return corpus

    def search_for_execution(
        self,
        actor: Actor,
        fence: AttemptFence,
        request: KnowledgeSearch,
        cancelled: threading.Event,
    ) -> dict:
        """Logical-consumer hook under the actual admitted Run's live fence.

        A host may map declared inputs to this closed request. This does not publish
        the consumer Run or start a Task; the existing runner retains that duty.
        """
        request = KnowledgeSearch.model_validate_json(request.model_dump_json())
        snapshot, _ = self.outputs.execution_context(actor, fence)
        binding = self._selected(snapshot)
        if binding.operation != "search":
            raise AccessDenied("Knowledge search binding required")
        spec = self._authorize(actor, binding, manage=False)
        if (
            len(request.query) > spec.max_query_characters
            or request.offset > spec.max_offset
            or request.limit > spec.max_results
            or not request.query.strip()
            or "\x00" in request.query
        ):
            raise SealedReadRejected("Knowledge query exceeds declared limits")
        budget = ReadBudget(spec.timeout_ms, cancelled)
        corpus = self._published(actor, binding, request.ingestion_handle, budget)
        _, documents = validate_corpus(corpus)
        needle = request.query.casefold()
        hits, total = [], 0
        for document in documents:
            budget.check()
            if needle in document["text"].casefold():
                if request.offset <= total < request.offset + request.limit:
                    hits.append(document)
                total += 1
        result = {
            "version": "actions.knowledge-search/v1",
            "revision": binding.revision.model_dump(mode="json"),
            "ingestionHandle": request.ingestion_handle,
            "corpusDigest": corpus.digest,
            "query": request.query,
            "offset": request.offset,
            "limit": request.limit,
            "total": total,
            "hits": hits,
        }
        if len(json_bytes(result)) > spec.max_result_bytes:
            raise SealedReadRejected(
                "Knowledge search result exceeds declared byte limit"
            )
        with _transaction(self.db):
            _lock_workspace(self.db, snapshot.workspace_id)
            self._authorize(actor, binding, manage=False)
            self.outputs.execution_context(actor, fence)
            budget.check()
        return result
