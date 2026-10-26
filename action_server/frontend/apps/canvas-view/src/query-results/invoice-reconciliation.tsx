import { z } from "zod";

const integer = z.number().int().refine(Number.isSafeInteger);
const cents = integer.refine((value) => value >= 0);
const id = z.string().min(1).max(128);
export const reconciliationSchema = z
    .object({
        version: z.literal("actions.invoice-reconciliation/v1"),
        source: z
            .object({
                invoice_id: id,
                invoice_line_id: id,
                po_id: id,
                po_line_id: id,
                ledger_id: id,
                sku: id,
                invoice_quantity: integer,
                invoice_unit_cents: cents,
                po_quantity: integer,
                po_unit_cents: cents,
                invoice_total_cents: cents,
                ledger_total_cents: cents,
            })
            .strict(),
        expected_total_cents: cents,
        actual_line_total_cents: cents,
        actual_total_cents: cents,
        variance_cents: integer,
        status: z.enum(["matched", "discrepant"]),
        discrepancies: z.array(
            z.enum([
                "quantity",
                "unit_price",
                "line_total",
                "po_total",
                "ledger_total",
            ]),
        ),
    })
    .strict();
export type InvoiceReconciliation = z.infer<typeof reconciliationSchema>;
const labels = {
    quantity: "Quantity",
    unit_price: "Unit price",
    line_total: "Invoice line total",
    po_total: "PO total",
    ledger_total: "Ledger total",
} satisfies Record<InvoiceReconciliation["discrepancies"][number], string>;
const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const money = (value: number) => `${number.format(value)} cents`;

export function ReconciliationCells({
    title,
    value,
}: {
    title: string;
    value: InvoiceReconciliation;
}) {
    const source = value.source;
    return (
        <>
            <th scope="row">
                <strong>{source.invoice_id}</strong>
                <span className="query-view__source">{title}</span>
                <span className="query-view__source">
                    {source.po_id} / {source.ledger_id}
                </span>
                <span className="query-view__source">{source.sku}</span>
                <details>
                    <summary>Line IDs</summary>
                    {source.invoice_line_id}
                    <br />
                    {source.po_line_id}
                </details>
            </th>
            <td>
                <span
                    className={`query-view__badge query-view__badge--${value.status}`}
                >
                    {value.status === "matched" ? "Matched" : "Discrepant"}
                </span>
            </td>
            <td>
                <dl className="query-view__comparison">
                    <dt>Quantity</dt>
                    <dd>{number.format(source.po_quantity)}</dd>
                    <dt>Unit price</dt>
                    <dd>{money(source.po_unit_cents)}</dd>
                    <dt>Total</dt>
                    <dd>{money(value.expected_total_cents)}</dd>
                </dl>
            </td>
            <td>
                <dl className="query-view__comparison">
                    <dt>Quantity</dt>
                    <dd>{number.format(source.invoice_quantity)}</dd>
                    <dt>Unit price</dt>
                    <dd>{money(source.invoice_unit_cents)}</dd>
                    <dt>Total</dt>
                    <dd>{money(value.actual_total_cents)}</dd>
                    <dt>Ledger</dt>
                    <dd>{money(source.ledger_total_cents)}</dd>
                    {value.discrepancies.includes("line_total") && (
                        <>
                            <dt>Line total</dt>
                            <dd>{money(value.actual_line_total_cents)}</dd>
                        </>
                    )}
                </dl>
            </td>
            <td className="query-view__variance">
                {value.variance_cents > 0 ? "+" : ""}
                {money(value.variance_cents)}
            </td>
            <td>
                {value.discrepancies.length ? (
                    <ul className="query-view__discrepancies">
                        {value.discrepancies.map((item) => (
                            <li key={item}>{labels[item]}</li>
                        ))}
                    </ul>
                ) : (
                    "None"
                )}
            </td>
        </>
    );
}
