import type { App } from "@modelcontextprotocol/ext-apps/react";
import { z } from "zod";
import {
    parseInvoiceExecution,
    parseInvoiceReview,
} from "../query-results/review-contract";
import type {
    InvoiceReviewAdapter,
    InvoiceReviewProposal,
    InvoiceExecutionComplete,
} from "../query-results/review-contract";
import type { CanvasAppMetadata } from "./mcp-bridge";

const digest = z.string().regex(/^sha256:[0-9a-f]{64}$/u);
const reference = z.object({
    workspace_id: z.string().uuid(),
    revision_id: digest,
});
const scopeSchema = z
    .object({
        application: reference.extend({ app_id: z.string().uuid() }).strict(),
        deployment: reference
            .extend({ deployment_id: z.string().uuid() })
            .strict(),
    })
    .strict();
const sessionSchema = z
    .object({
        token: z.string().regex(/^[A-Za-z0-9_-]{43}$/u),
        scope: scopeSchema,
    })
    .strict();
const contextSchema = z
    .object({
        handle: z.string().regex(/^art_[A-Za-z0-9_-]{22}$/u),
        bindingId: z.string().regex(/^[A-Za-z][A-Za-z0-9_-]{0,63}$/u),
    })
    .strict();

type ResultScope = z.infer<typeof scopeSchema>;
function sameScope(left: ResultScope, right: ResultScope) {
    return (
        left.application.app_id === right.application.app_id &&
        left.application.revision_id === right.application.revision_id &&
        left.application.workspace_id === right.application.workspace_id &&
        left.deployment.deployment_id === right.deployment.deployment_id &&
        left.deployment.revision_id === right.deployment.revision_id &&
        left.deployment.workspace_id === right.deployment.workspace_id
    );
}

export function parseReviewedExecution(
    metadata: Record<string, unknown>,
    canvas: CanvasAppMetadata,
) {
    const session = sessionSchema.parse(metadata["actions.appSession"]);
    const context = contextSchema.parse(metadata["actions.reviewedExecution"]);
    if (
        !canvas.active ||
        session.scope.deployment.deployment_id !== canvas.applicationId ||
        session.scope.deployment.revision_id !== canvas.revisionId ||
        session.scope.application.app_id !== canvas.applicationId ||
        session.scope.application.workspace_id !==
            session.scope.deployment.workspace_id ||
        !canvas.bindings.some(
            (binding) => binding.bindingId === context.bindingId,
        )
    ) {
        throw new Error("View session differs from active Canvas revision.");
    }
    const recovered =
        metadata["actions.review"] === undefined
            ? null
            : parseInvoiceReview(metadata["actions.review"]);
    if (
        recovered &&
        (recovered.proposal.binding.handle !== context.handle ||
            !sameScope(recovered.proposal.binding.scope, session.scope))
    )
        throw new Error("Recovered review differs from View scope.");
    return {
        ...context,
        ...session,
        recoveredProposal: recovered?.proposal ?? null,
    };
}

export type ReviewedExecutionContext = ReturnType<
    typeof parseReviewedExecution
>;

export function createReviewedExecutionAdapter(
    app: App,
    context: ReviewedExecutionContext,
): InvoiceReviewAdapter {
    const call = async (name: string, args: Record<string, unknown>) => {
        const response = await app.callServerTool({
            name,
            arguments: { ...args, appSession: context.token },
        });
        if (response.isError)
            throw new Error("View request unavailable; reopen the app.");
        return response._meta;
    };
    const requireProposal = (proposal: InvoiceReviewProposal) => {
        if (
            proposal.binding.handle !== context.handle ||
            !sameScope(proposal.binding.scope, context.scope)
        )
            throw new Error("Exact review binding changed.");
    };
    const review = async (args: Record<string, unknown>) => {
        const meta = await call("canvas_dispatch", args);
        const state = parseInvoiceReview(meta?.["actions.review"]);
        requireProposal(state.proposal);
        return state;
    };
    const read = async (proposal: InvoiceReviewProposal) => {
        requireProposal(proposal);
        const meta = await call("canvas_execution_status", { proposal });
        const state = parseInvoiceExecution(meta?.["actions.execution"]);
        requireProposal(state.proposal);
        if (state.proposal.review_id !== proposal.review_id)
            throw new Error("Review identity changed.");
        return state;
    };
    const readArtifact = async (
        target:
            | { kind: "source"; proposal: InvoiceReviewProposal }
            | { kind: "result"; result: InvoiceExecutionComplete },
    ) => {
        const proposal =
            target.kind === "source" ? target.proposal : target.result.proposal;
        requireProposal(proposal);
        const meta = await call("canvas_artifact", {
            proposal,
            kind: target.kind,
        });
        const artifact = z
            .object({
                runId: z.string().uuid(),
                handle: z.string(),
                digest,
                content: z.string().max(128 * 1024),
                mediaType: z.enum(["application/json", "application/x-ndjson"]),
            })
            .strict()
            .parse(meta?.["actions.artifact"]);
        const bytes = new globalThis.TextEncoder().encode(artifact.content);
        const hash = await globalThis.crypto.subtle.digest("SHA-256", bytes);
        const measured =
            "sha256:" +
            Array.from(new Uint8Array(hash), (byte) =>
                byte.toString(16).padStart(2, "0"),
            ).join("");
        const expected =
            target.kind === "source"
                ? {
                      runId: proposal.binding.run_id,
                      handle: proposal.binding.handle,
                      digest: proposal.binding.result_digest,
                      mediaType: "application/x-ndjson",
                  }
                : {
                      runId: target.result.run_id,
                      handle: target.result.artifact.handle,
                      digest: target.result.artifact.digest,
                      mediaType: "application/json",
                  };
        if (
            artifact.runId !== expected.runId ||
            artifact.handle !== expected.handle ||
            artifact.digest !== expected.digest ||
            measured !== artifact.digest ||
            artifact.mediaType !== expected.mediaType ||
            (target.kind === "result" &&
                bytes.length !== target.result.artifact.size)
        )
            throw new Error("Exact artifact seal changed.");
        return artifact;
    };
    return {
        async inspect(proposal) {
            return (await readArtifact({ kind: "source", proposal })).content;
        },
        async offer(handle) {
            if (handle !== context.handle)
                throw new Error("Exact saved result required.");
            if (context.recoveredProposal) {
                const meta = await call("canvas_get_state", {
                    proposal: context.recoveredProposal,
                });
                const state = parseInvoiceReview(meta?.["actions.review"]);
                requireProposal(state.proposal);
                return state;
            }
            return review({ action: "offer", handle });
        },
        decide(proposal, decision) {
            requireProposal(proposal);
            return review({ action: "decide", proposal, decision });
        },
        async cancel(proposal) {
            requireProposal(proposal);
            const meta = await call("canvas_cancel", { proposal });
            const state = parseInvoiceReview(meta?.["actions.review"]);
            requireProposal(state.proposal);
            return state;
        },
        execution: {
            read,
            async inspect(result) {
                return (await readArtifact({ kind: "result", result })).content;
            },
            async execute(proposal) {
                requireProposal(proposal);
                await call("canvas_dispatch", {
                    action: "execute",
                    bindingId: context.bindingId,
                    proposal,
                });
                return read(proposal);
            },
            async download(result) {
                const artifact = await readArtifact({ kind: "result", result });
                const response = await app.downloadFile({
                    contents: [
                        {
                            type: "resource",
                            resource: {
                                uri: `actions-result://${artifact.runId}/${artifact.handle}`,
                                mimeType: "application/json",
                                text: artifact.content,
                            },
                        },
                    ],
                });
                if (response.isError) throw new Error("Host download denied.");
            },
        },
    };
}
