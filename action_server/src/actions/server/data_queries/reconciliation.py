"""Typed synthetic invoice reconciliation result, with integer-cent source data."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ._invoice_task import reconcile_invoice

OPERATION = "invoices.reconcile/v1"


class ReconciliationSource(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    invoice_id: str = Field(min_length=1, max_length=128)
    invoice_line_id: str = Field(min_length=1, max_length=128)
    po_id: str = Field(min_length=1, max_length=128)
    po_line_id: str = Field(min_length=1, max_length=128)
    ledger_id: str = Field(min_length=1, max_length=128)
    sku: str = Field(min_length=1, max_length=128)
    invoice_quantity: int = Field(ge=1, le=100000000)
    invoice_unit_cents: int = Field(ge=0, le=100000000)
    po_quantity: int = Field(ge=1, le=100000000)
    po_unit_cents: int = Field(ge=0, le=100000000)
    invoice_total_cents: int = Field(ge=0, le=100000000)
    ledger_total_cents: int = Field(ge=0, le=100000000)


class InvoiceReconciliation(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )
    version: Literal[
        "actions.invoice-reconciliation/v1"
    ] = "actions.invoice-reconciliation/v1"
    source: ReconciliationSource
    expected_total_cents: int
    actual_line_total_cents: int
    actual_total_cents: int
    variance_cents: int
    status: Literal["matched", "discrepant"]
    discrepancies: list[
        Literal["quantity", "unit_price", "line_total", "po_total", "ledger_total"]
    ]

    @model_validator(mode="after")
    def exact_source_comparison(self):
        if self.model_dump(mode="json") != reconcile_invoice(
            self.source.model_dump(mode="json")
        ):
            raise ValueError("reconciliation differs from its exact source records")
        return self


def description(report: dict) -> str:
    value = InvoiceReconciliation.model_validate(report)
    source = value.source
    return (
        f"{value.status.upper()} | {source.invoice_id} / {source.po_id} / {source.ledger_id}\n"
        f"{source.sku} | lines {source.invoice_line_id} / {source.po_line_id}\n"
        f"Quantity expected {source.po_quantity}, actual {source.invoice_quantity}; "
        f"unit price expected {source.po_unit_cents}c, actual {source.invoice_unit_cents}c\n"
        f"Total expected {value.expected_total_cents}c, actual {value.actual_total_cents}c, "
        f"ledger {source.ledger_total_cents}c; variance {value.variance_cents:+d}c\n"
        f"Discrepancies: {', '.join(value.discrepancies) or 'none'}"
    )
