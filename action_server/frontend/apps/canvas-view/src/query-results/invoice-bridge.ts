import type { App } from "@modelcontextprotocol/ext-apps/react";
import { z } from "zod";
import { reconciliationSchema } from "./invoice-reconciliation";
import { parseInvoiceExecution, parseInvoiceReview } from "./review-contract";
import type { InvoiceReviewAdapter } from "./review-contract";

import type {
    ArtifactHandle,
    QueryActionResult,
    QueryResultsAdapter,
} from "./QueryResultsView";

const handleSchema = z.string().regex(/^art_[A-Za-z0-9_-]{22}$/u);
const pageSchema = z.object({
    reviewAvailable: z.boolean().optional(),
    schemaVersion: z.literal("actions.invoice-page/v1"),
    rows: z
        .array(
            z.object({
                id: z.string().max(256),
                title: z.string().max(256),
                category: z.string().max(2048),
                reconciliation: reconciliationSchema.optional(),
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
        page.rows.some(
            (row) =>
                row.reconciliation &&
                row.reconciliation.source.invoice_id !== row.id,
        )
    )
        throw new Error("Invoice comparison identity changed.");
    if (
        page.nextOffset !== null &&
        page.nextOffset !== page.offset + page.rows.length
    )
        throw new Error("Invalid next page.");
    return {
        reviewAvailable: page.reviewAvailable ?? false,
        rows: page.rows,
        // Branded only after validating the canonical opaque handle.
        artifact: { handle: page.artifact.handle as ArtifactHandle },
        error: null,
        pagination: { offset: page.offset, nextOffset: page.nextOffset },
    };
}

export function createInvoiceAdapter(app: App): QueryResultsAdapter {
    const reviewCall = async (
        name: string,
        argumentsValue: Record<string, unknown>,
        handle: string,
    ) => {
        const result = await app.callServerTool({
            name,
            arguments: argumentsValue,
        });
        if (result.isError) throw new Error("Review denied.");
        const state = parseInvoiceReview(
            result._meta?.["actions.invoiceReview"],
        );
        if (state.proposal.binding.handle !== handle)
            throw new Error("Review identity changed.");
        return state;
    };
    const review: InvoiceReviewAdapter = {
        execution: {
            async read(proposal) {
                const result = await app.callServerTool({
                    name: "invoice_review_execution",
                    arguments: { proposal },
                });
                if (result.isError) throw new Error("Execution result denied.");
                const state = parseInvoiceExecution(
                    result._meta?.["actions.invoiceExecution"],
                );
                if (JSON.stringify(state.proposal) !== JSON.stringify(proposal))
                    throw new Error("Execution proposal changed.");
                return state;
            },
            async download(result) {
                if (!result.artifact.uri)
                    throw new Error("Download transport is not configured.");
                const uri = new globalThis.URL(result.artifact.uri);
                const workspace =
                    result.proposal.binding.scope.application.workspace_id;
                if (
                    !["https:", "http:"].includes(uri.protocol) ||
                    uri.username ||
                    uri.password ||
                    uri.search ||
                    uri.hash ||
                    (uri.protocol === "http:" &&
                        !["127.0.0.1", "localhost", "[::1]"].includes(
                            uri.hostname,
                        )) ||
                    uri.pathname !==
                        `/api/workspaces/${workspace}/outputs/${result.artifact.handle}`
                )
                    throw new Error("Invalid execution download route.");
                const downloaded = await app.downloadFile({
                    contents: [
                        {
                            type: "resource_link",
                            uri: uri.href,
                            name: "invoice-execution.json",
                            mimeType: result.artifact.media_type,
                        },
                    ],
                });
                if (downloaded.isError)
                    throw new Error("Host download denied.");
            },
        },
        offer(handle) {
            return reviewCall("invoice_review_offer", { handle }, handle);
        },
        async decide(proposal, decision) {
            const state = await reviewCall(
                "invoice_review_decide",
                { proposal, decision },
                proposal.binding.handle,
            );
            if (JSON.stringify(state.proposal) !== JSON.stringify(proposal))
                throw new Error("Review proposal changed.");
            return state;
        },
        async cancel(proposal) {
            const state = await reviewCall(
                "invoice_review_cancel",
                { proposal },
                proposal.binding.handle,
            );
            if (JSON.stringify(state.proposal) !== JSON.stringify(proposal))
                throw new Error("Review proposal changed.");
            return state;
        },
    };
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
        review,
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
