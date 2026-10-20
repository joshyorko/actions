import type { App } from "@modelcontextprotocol/ext-apps/react";
import { z } from "zod";

import type {
    ArtifactHandle,
    QueryActionResult,
    QueryResultsAdapter,
} from "./QueryResultsView";

const handleSchema = z.string().regex(/^art_[A-Za-z0-9_-]{22}$/u);
const pageSchema = z.object({
    schemaVersion: z.literal("actions.invoice-page/v1"),
    rows: z
        .array(
            z.object({
                id: z.string().max(256),
                title: z.string().max(256),
                category: z.string().max(256),
            }),
        )
        .max(99),
    artifact: z.object({ handle: handleSchema }),
    error: z.null(),
    offset: z.number().int().min(0).max(100000),
    nextOffset: z.number().int().min(0).max(100000).nullable(),
});

export function parseInvoicePage(value: unknown): QueryActionResult {
    const page = pageSchema.parse(value);
    if (
        page.nextOffset !== null &&
        page.nextOffset !== page.offset + page.rows.length
    )
        throw new Error("Invalid next page.");
    return {
        rows: page.rows,
        // Branded only after validating the canonical opaque handle.
        artifact: { handle: page.artifact.handle as ArtifactHandle },
        error: null,
        pagination: { offset: page.offset, nextOffset: page.nextOffset },
    };
}

export function createInvoiceAdapter(app: App): QueryResultsAdapter {
    const exportDescriptor = async (handle: ArtifactHandle) => {
        const result = await app.callServerTool({
            name: "invoice_result_export",
            arguments: { handle },
        });
        if (result.isError) throw new Error("Export denied.");
        const descriptor = z
            .object({
                handle: handleSchema,
                digest: z.string().regex(/^sha256:[a-f0-9]{64}$/u),
                size: z.number().int().nonnegative(),
                mediaType: z.literal("application/x-ndjson"),
                uri: z.string().url().optional(),
            })
            .parse(result._meta?.["actions.invoiceExport"]);
        if (descriptor.handle !== handle)
            throw new Error("Export identity changed.");
        return descriptor;
    };
    return {
        async submitQuery() {
            throw new Error("Published results cannot execute queries.");
        },
        async getArtifactStatus(handle) {
            await exportDescriptor(handle);
            return "ready";
        },
        async pageResult(handle, offset) {
            const result = await app.callServerTool({
                name: "invoice_result_page",
                arguments: { handle, offset, limit: 20 },
            });
            if (result.isError) throw new Error("Page denied.");
            const page = parseInvoicePage(
                result._meta?.["actions.invoicePage"],
            );
            if (
                page.artifact?.handle !== handle ||
                page.pagination?.offset !== offset
            )
                throw new Error("Page identity changed.");
            return page;
        },
        async exportResult(handle) {
            const descriptor = await exportDescriptor(handle);
            if (!descriptor.uri)
                throw new Error("Download transport is not configured.");
            const uri = new globalThis.URL(descriptor.uri);
            if (
                !["https:", "http:"].includes(uri.protocol) ||
                uri.username ||
                uri.password ||
                uri.search ||
                uri.hash ||
                !uri.pathname.endsWith(`/outputs/${handle}`)
            )
                throw new Error("Invalid download route.");
            const result = await app.downloadFile({
                contents: [
                    {
                        type: "resource_link",
                        uri: uri.href,
                        name: "invoices.ndjson",
                        mimeType: descriptor.mediaType,
                    },
                ],
            });
            if (result.isError) throw new Error("Host download denied.");
        },
    };
}
