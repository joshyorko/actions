"""Review decisions and the single authoritative SDK Work Item SQL row."""

from pydantic.dataclasses import dataclass

from actions.server._models import _db_rules


@dataclass
class FencedWorkItem:
    id: str
    workspace_id: str
    queue_name: str
    parent_id: str
    state: str
    payload: str
    created_ms: str
    claim_owner: str
    claim_epoch: int
    claim_deadline_ms: str
    cancel_requested: int
    error_message: str
    format: str
    _db_rules.foreign_keys.add("FencedWorkItem.workspace_id")
    _db_rules.indexes.add("FencedWorkItem.queue_name")


@dataclass
class InvoiceReview:
    id: str
    workspace_id: str
    run_id: str
    binding_id: str
    binding_json: str
    state: str
    work_item_id: str
    decision_json: str
    cancellation_json: str
    _db_rules.foreign_keys.update(
        {"InvoiceReview.workspace_id", "InvoiceReview.run_id"}
    )
    _db_rules.unique_indexes.add("InvoiceReview.binding_id")


MODEL_CLASSES = [FencedWorkItem, InvoiceReview]
