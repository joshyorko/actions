import { z } from "zod";

const digest = z.string().regex(/^sha256:[a-f0-9]{64}$/u);
const workspace = z.string().uuid();
const proposalSchema = z
    .object({
        review_id: z.string().uuid(),
        binding: z
            .object({
                handle: z.string().regex(/^art_[A-Za-z0-9_-]{22}$/u),
                run_id: z.string().uuid(),
                result_digest: digest,
                input_digest: digest,
                source_version: digest,
                request_fingerprint: z.string().regex(/^[a-f0-9]{64}$/u),
                scope: z
                    .object({
                        deployment: z
                            .object({
                                workspace_id: workspace,
                                deployment_id: z.string().uuid(),
                                revision_id: digest,
                            })
                            .strict(),
                        application: z
                            .object({
                                workspace_id: workspace,
                                app_id: z.string().uuid(),
                                revision_id: digest,
                            })
                            .strict(),
                    })
                    .strict(),
            })
            .strict(),
    })
    .strict();

const stateSchema = z
    .object({
        proposal: proposalSchema,
        receipt: z
            .object({
                review_id: z.string().uuid(),
                state: z.enum(["pending", "approved", "rejected", "cancelled"]),
                work_item_id: z.string().uuid().nullable(),
            })
            .strict(),
    })
    .strict();

export type InvoiceReviewProposal = z.infer<typeof proposalSchema>;
export type InvoiceReviewState = z.infer<typeof stateSchema>;
export interface InvoiceReviewAdapter {
    execution?: InvoiceExecutionAdapter;
    offer(handle: string): Promise<InvoiceReviewState>;
    decide(
        proposal: InvoiceReviewProposal,
        decision: "approve" | "reject",
    ): Promise<InvoiceReviewState>;
    cancel(proposal: InvoiceReviewProposal): Promise<InvoiceReviewState>;
}

export function parseInvoiceReview(value: unknown): InvoiceReviewState {
    const result = stateSchema.parse(value);
    if (
        result.receipt.review_id !== result.proposal.review_id ||
        result.proposal.binding.scope.application.workspace_id !==
            result.proposal.binding.scope.deployment.workspace_id ||
        (result.receipt.state === "approved" &&
            result.receipt.work_item_id === null) ||
        (["pending", "rejected"].includes(result.receipt.state) &&
            result.receipt.work_item_id !== null)
    ) {
        throw new Error("Review identity changed.");
    }
    return result;
}

const executionSchema = z.discriminatedUnion("phase", [
    z
        .object({
            proposal: proposalSchema,
            phase: z.enum([
                "pending",
                "rejected",
                "cancelled",
                "queued",
                "running",
                "failed",
                "blocked",
            ]),
        })
        .strict(),
    z
        .object({
            proposal: proposalSchema,
            phase: z.enum(["completed", "dead_letter"]),
            work_item_id: z.string().uuid(),
            run_id: z.string().uuid(),
            attempt_id: z.string().uuid(),
            artifact: z
                .object({
                    handle: z.string().regex(/^art_[A-Za-z0-9_-]{22}$/u),
                    digest,
                    size: z.number().int().nonnegative(),
                    media_type: z.literal("application/json"),
                    uri: z.string().url().optional(),
                })
                .strict(),
        })
        .strict(),
]);

export type InvoiceExecutionState = z.infer<typeof executionSchema>;
export type InvoiceExecutionComplete = Extract<
    InvoiceExecutionState,
    { phase: "completed" | "dead_letter" }
>;
export interface InvoiceExecutionAdapter {
    read(proposal: InvoiceReviewProposal): Promise<InvoiceExecutionState>;
    download(result: InvoiceExecutionComplete): Promise<void>;
}

export function parseInvoiceExecution(value: unknown): InvoiceExecutionState {
    const result = executionSchema.parse(value);
    if (
        result.proposal.binding.scope.application.workspace_id !==
        result.proposal.binding.scope.deployment.workspace_id
    )
        throw new Error("Execution scope changed.");
    return result;
}
