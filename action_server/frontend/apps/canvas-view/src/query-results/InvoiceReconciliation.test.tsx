import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import "@testing-library/jest-dom/vitest";
import { parseInvoicePage } from "./invoice-bridge";
import { QueryResultsView, type QueryResultsAdapter } from "./QueryResultsView";

afterEach(cleanup);
const source = {
    invoice_id: "INV-1002",
    invoice_line_id: "INV-1002-L1",
    po_id: "PO-2002",
    po_line_id: "PO-2002-L1",
    ledger_id: "LED-3002",
    sku: "WIDGET-B",
    invoice_quantity: 5,
    invoice_unit_cents: 2200,
    po_quantity: 5,
    po_unit_cents: 2000,
    invoice_total_cents: 11000,
    ledger_total_cents: 11000,
};
const report = {
    version: "actions.invoice-reconciliation/v1",
    source,
    expected_total_cents: 10000,
    actual_line_total_cents: 11000,
    actual_total_cents: 11000,
    variance_cents: 1000,
    status: "discrepant",
    discrepancies: ["unit_price", "po_total"],
};
function page(reconciliation: unknown = report) {
    return {
        schemaVersion: "actions.invoice-page/v1",
        rows: [
            {
                id: "INV-1002",
                title: "Synthetic Supply",
                category: "legacy description",
                reconciliation,
            },
        ],
        artifact: { handle: "art_AAAAAAAAAAAAAAAAAAAAAA" },
        error: null,
        offset: 0,
        nextOffset: null,
    };
}
it("shows accurate reconciliation labels and separate integer-cent comparisons", () => {
    const result = parseInvoicePage(page());
    const adapter: QueryResultsAdapter = {
        async submitQuery() {
            throw new Error("no query on mount");
        },
        async getArtifactStatus() {
            return "ready";
        },
    };
    render(
        <QueryResultsView
            adapter={adapter}
            hostResult={{ revision: 1, result }}
            readOnly
        />,
    );
    expect(
        screen.getByRole("heading", { name: "Invoice reconciliation" }),
    ).toBeVisible();
    expect(screen.queryByText("Matching records")).not.toBeInTheDocument();
    const table = screen.getByRole("table", {
        name: "Invoice reconciliation comparisons",
    });
    for (const label of [
        "Invoice and sources",
        "Status",
        "Expected (PO)",
        "Actual (invoice)",
        "Variance",
        "Discrepancies",
    ])
        expect(
            within(table).getByRole("columnheader", { name: label }),
        ).toBeVisible();
    expect(
        within(table).getByText("Discrepant", { exact: true }),
    ).toBeVisible();
    expect(
        within(table).getByText("10,000 cents", { exact: true }),
    ).toBeVisible();
    expect(
        within(table).getByText("+1,000 cents", { exact: true }),
    ).toBeVisible();
    expect(within(table).getByText("PO total", { exact: true })).toBeVisible();
    expect(
        within(table).getByText("PO-2002 / LED-3002", { exact: true }),
    ).toBeVisible();
    expect(
        within(table).queryByText("legacy description"),
    ).not.toBeInTheDocument();
});
it("rejects unsafe comparison values and foreign invoice identity at the wire boundary", () => {
    expect(() =>
        parseInvoicePage(
            page({
                ...report,
                expected_total_cents: Number.MAX_SAFE_INTEGER + 1,
            }),
        ),
    ).toThrow();
    expect(() =>
        parseInvoicePage(
            page({ ...report, source: { ...source, invoice_id: "foreign" } }),
        ),
    ).toThrow();
});
