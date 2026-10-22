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
