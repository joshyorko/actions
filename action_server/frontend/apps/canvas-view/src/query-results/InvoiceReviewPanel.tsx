import { useEffect, useRef, useState } from "react";

import type {
    InvoiceExecutionComplete,
    InvoiceExecutionState,
    InvoiceReviewAdapter,
    InvoiceReviewState,
} from "./review-contract";

export function InvoiceReviewPanel({
    adapter,
    handle,
}: {
    adapter: InvoiceReviewAdapter;
    handle: string;
}) {
    const [review, setReview] = useState<InvoiceReviewState | null>(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState(false);
    const [execution, setExecution] = useState<InvoiceExecutionState | null>(
        null,
    );
    const [executionError, setExecutionError] = useState(false);
    const executionAdapter = adapter.execution;
    const mounted = useRef(false);
    useEffect(() => {
        mounted.current = true;
        return () => {
            mounted.current = false;
        };
    }, []);

    const perform = async (operation: () => Promise<InvoiceReviewState>) => {
        setBusy(true);
        setError(false);
        try {
            const next = await operation();
            if (next.proposal.binding.handle !== handle)
                throw new Error("Review result changed.");
            if (mounted.current) setReview(next);
        } catch {
            if (mounted.current) setError(true);
        } finally {
            if (mounted.current) setBusy(false);
        }
    };
    const checkExecution = async () => {
        if (!review || !executionAdapter) return;
        setBusy(true);
        setExecutionError(false);
        try {
            const next = await executionAdapter.read(review.proposal);
            if (
                next.proposal.review_id !== review.proposal.review_id ||
                next.proposal.binding.handle !== handle
            )
                throw new Error("Execution identity changed.");
            if (mounted.current) setExecution(next);
        } catch {
            if (mounted.current) setExecutionError(true);
        } finally {
            if (mounted.current) setBusy(false);
        }
    };
    const downloadExecution = async (result: InvoiceExecutionComplete) => {
        if (!executionAdapter) return;
        setBusy(true);
        setExecutionError(false);
        try {
            await executionAdapter.download(result);
        } catch {
            if (mounted.current) setExecutionError(true);
        } finally {
            if (mounted.current) setBusy(false);
        }
    };
    const phases = {
        pending: "Review is pending.",
        rejected: "Review was rejected.",
        cancelled: "Work was cancelled.",
        queued: "Work is queued.",
        running: "Work is running.",
        failed: "Work failed.",
        completed: "Execution result is ready.",
    };
    return (
        <section
            className="query-view__panel invoice-review"
            aria-label="Review saved invoice result"
            aria-busy={busy}
        >
            {!review && (
                <button
                    type="button"
                    disabled={busy}
                    onClick={() => void perform(() => adapter.offer(handle))}
                >
                    Review these results
                </button>
            )}
            {error && <p role="alert">Unable to record this review.</p>}
            {review?.receipt.state === "pending" && (
                <>
                    <p>
                        Approve the complete saved result, including rows beyond
                        this page. Export it to inspect every row.
                    </p>
                    <details>
                        <summary>Result identity</summary>
                        <p>
                            Result:{" "}
                            <code>{review.proposal.binding.result_digest}</code>
                        </p>
                        <p>
                            Inputs:{" "}
                            <code>{review.proposal.binding.input_digest}</code>
                        </p>
                        <p>
                            Source:{" "}
                            <code>
                                {review.proposal.binding.source_version}
                            </code>
                        </p>
                        <p>
                            Application revision:{" "}
                            <code>
                                {
                                    review.proposal.binding.scope.application
                                        .revision_id
                                }
                            </code>
                        </p>
                        <p>
                            Deployment revision:{" "}
                            <code>
                                {
                                    review.proposal.binding.scope.deployment
                                        .revision_id
                                }
                            </code>
                        </p>
                    </details>
                    <button
                        type="button"
                        disabled={busy}
                        onClick={() =>
                            void perform(() =>
                                adapter.decide(review.proposal, "approve"),
                            )
                        }
                    >
                        Approve these results
                    </button>
                    <button
                        type="button"
                        disabled={busy}
                        onClick={() =>
                            void perform(() =>
                                adapter.decide(review.proposal, "reject"),
                            )
                        }
                    >
                        Reject these results
                    </button>
                </>
            )}
            {review?.receipt.state === "approved" && (
                <p role="status">Approved. Work item created.</p>
            )}
            {review?.receipt.state === "approved" && executionAdapter && (
                <>
                    <button
                        type="button"
                        disabled={busy}
                        onClick={() => void checkExecution()}
                    >
                        Check execution result
                    </button>
                    {execution && (
                        <p role="status">{phases[execution.phase]}</p>
                    )}
                    {execution?.phase === "completed" && (
                        <button
                            type="button"
                            disabled={busy}
                            onClick={() => void downloadExecution(execution)}
                        >
                            Download execution result
                        </button>
                    )}
                    {executionError && (
                        <p role="alert">Unable to access execution result.</p>
                    )}
                </>
            )}
            {review?.receipt.state === "rejected" && (
                <p role="status">Rejected. No work item created.</p>
            )}
            {review?.receipt.state === "cancelled" && (
                <p role="status">Cancelled.</p>
            )}
            {review &&
                !["completed", "failed", "cancelled"].includes(
                    execution?.phase ?? "",
                ) &&
                ["pending", "approved"].includes(review.receipt.state) && (
                    <button
                        type="button"
                        disabled={busy}
                        onClick={() =>
                            void perform(() => adapter.cancel(review.proposal))
                        }
                    >
                        {review.receipt.work_item_id
                            ? "Cancel work item"
                            : "Cancel review"}
                    </button>
                )}
        </section>
    );
}
