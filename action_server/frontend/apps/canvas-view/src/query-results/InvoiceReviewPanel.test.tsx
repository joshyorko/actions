import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";

import { InvoiceReviewPanel } from "./InvoiceReviewPanel";
import { parseInvoiceExecution } from "./review-contract";

afterEach(cleanup);

it("reads saved bytes only on an explicit inspect action before approval", async () => {
    const adapter = {
        offer: vi.fn().mockResolvedValue({
            proposal,
            receipt: {
                review_id: proposal.review_id,
                state: "pending",
                work_item_id: null,
            },
        }),
        inspect: vi
            .fn()
            .mockResolvedValue(
                '{"invoice_id":"synthetic-1","amount_cents":100}\n',
            ),
        decide: vi.fn(),
        cancel: vi.fn(),
    };
    render(
        <InvoiceReviewPanel
            adapter={adapter}
            handle={proposal.binding.handle}
        />,
    );
    expect(adapter.inspect).not.toHaveBeenCalled();
    await userEvent.click(
        screen.getByRole("button", { name: "Review these results" }),
    );
    expect(adapter.inspect).not.toHaveBeenCalled();
    await userEvent.click(
        await screen.findByRole("button", {
            name: "Inspect complete saved result",
        }),
    );
    expect(adapter.inspect).toHaveBeenCalledExactlyOnceWith(proposal);
    expect(await screen.findByText(/"invoice_id":"synthetic-1"/)).toBeVisible();
    expect(adapter.decide).not.toHaveBeenCalled();
});

const proposal = {
    review_id: "10000000-0000-4000-8000-000000000001",
    binding: {
        handle: "art_AAAAAAAAAAAAAAAAAAAAAA",
        run_id: "20000000-0000-4000-8000-000000000002",
        result_digest: `sha256:${"a".repeat(64)}`,
        input_digest: `sha256:${"b".repeat(64)}`,
        source_version: `sha256:${"c".repeat(64)}`,
        request_fingerprint: "d".repeat(64),
        scope: {
            deployment: {
                workspace_id: "30000000-0000-4000-8000-000000000003",
                deployment_id: "40000000-0000-4000-8000-000000000004",
                revision_id: `sha256:${"e".repeat(64)}`,
            },
            application: {
                workspace_id: "30000000-0000-4000-8000-000000000003",
                app_id: "50000000-0000-4000-8000-000000000005",
                revision_id: `sha256:${"f".repeat(64)}`,
            },
        },
    },
};

it("requires an explicit offer followed by an explicit approval", async () => {
    const user = userEvent.setup();
    const pending = {
        proposal,
        receipt: {
            review_id: proposal.review_id,
            state: "pending" as const,
            work_item_id: null,
        },
    };
    const adapter = {
        offer: vi.fn().mockResolvedValue(pending),
        decide: vi.fn().mockResolvedValue({
            ...pending,
            receipt: {
                ...pending.receipt,
                state: "approved",
                work_item_id: "60000000-0000-4000-8000-000000000006",
            },
        }),
        cancel: vi.fn(),
        execution: {
            read: vi.fn().mockResolvedValue({ phase: "queued", proposal }),
            download: vi.fn(),
        },
    };
    render(
        <InvoiceReviewPanel
            adapter={adapter}
            handle={proposal.binding.handle}
        />,
    );
    expect(adapter.offer).not.toHaveBeenCalled();
    expect(adapter.decide).not.toHaveBeenCalled();
    await user.click(
        screen.getByRole("button", { name: "Review these results" }),
    );
    expect(
        await screen.findByText(/including rows beyond this page/),
    ).toBeVisible();
    expect(adapter.decide).not.toHaveBeenCalled();
    await user.click(
        screen.getByRole("button", { name: "Approve these results" }),
    );
    expect(adapter.decide).toHaveBeenCalledWith(proposal, "approve");
    expect(
        await screen.findByText("Approved. Work item created."),
    ).toBeVisible();
    expect(adapter.execution.read).not.toHaveBeenCalled();
    await user.click(
        screen.getByRole("button", { name: "Check execution result" }),
    );
    expect(await screen.findByText("Work is queued.")).toBeVisible();
    expect(adapter.execution.read).toHaveBeenCalledWith(proposal);
    expect(adapter.execution.download).not.toHaveBeenCalled();
    const completed = {
        phase: "completed",
        proposal,
        work_item_id: "60000000-0000-4000-8000-000000000006",
        run_id: "70000000-0000-4000-8000-000000000007",
        attempt_id: "80000000-0000-4000-8000-000000000008",
        artifact: {
            handle: "art_BBBBBBBBBBBBBBBBBBBBBB",
            digest: `sha256:${"a".repeat(64)}`,
            size: 100,
            media_type: "application/json",
        },
    };
    adapter.execution.read.mockResolvedValue(completed);
    await user.click(
        screen.getByRole("button", { name: "Check execution result" }),
    );
    expect(await screen.findByText("Execution result is ready.")).toBeVisible();
    expect(adapter.execution.download).not.toHaveBeenCalled();
    await user.click(
        screen.getByRole("button", { name: "Download execution result" }),
    );
    expect(adapter.execution.download).toHaveBeenCalledWith(completed);
    expect(
        screen.queryByRole("button", { name: "Cancel work item" }),
    ).not.toBeInTheDocument();
});

it("never treats a denied review as approval", async () => {
    const adapter = {
        offer: vi.fn().mockRejectedValue(new Error("denied")),
        decide: vi.fn(),
        cancel: vi.fn(),
    };
    render(
        <InvoiceReviewPanel
            adapter={adapter}
            handle="art_AAAAAAAAAAAAAAAAAAAAAA"
        />,
    );
    await userEvent.click(
        screen.getByRole("button", { name: "Review these results" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
        "Unable to record this review.",
    );
    expect(adapter.decide).not.toHaveBeenCalled();
    expect(
        screen.queryByText("Approved. Work item created."),
    ).not.toBeInTheDocument();
});

it("dispatches only after a separate approval and explicit execute click", async () => {
    const approved = {
        proposal,
        receipt: {
            review_id: proposal.review_id,
            state: "approved" as const,
            work_item_id: "60000000-0000-4000-8000-000000000006",
        },
    };
    const adapter = {
        offer: vi.fn().mockResolvedValue(approved),
        decide: vi.fn(),
        cancel: vi.fn(),
        execution: {
            execute: vi.fn().mockResolvedValue({ proposal, phase: "running" }),
            read: vi.fn(),
            download: vi.fn(),
        },
    };
    render(
        <InvoiceReviewPanel
            adapter={adapter}
            handle={proposal.binding.handle}
        />,
    );
    expect(adapter.execution.execute).not.toHaveBeenCalled();
    await userEvent.click(
        screen.getByRole("button", { name: "Review these results" }),
    );
    expect(adapter.execution.execute).not.toHaveBeenCalled();
    await userEvent.click(
        await screen.findByRole("button", { name: "Execute approved result" }),
    );
    expect(adapter.execution.execute).toHaveBeenCalledExactlyOnceWith(proposal);
    expect(await screen.findByText("Work is running.")).toBeVisible();
});

it("shows blocked outcomes and explicit terminal failure download without retrying", async () => {
    const blocked = parseInvoiceExecution({ proposal, phase: "blocked" });
    const dead = parseInvoiceExecution({
        proposal,
        phase: "dead_letter",
        work_item_id: "60000000-0000-4000-8000-000000000006",
        run_id: "70000000-0000-4000-8000-000000000007",
        attempt_id: "80000000-0000-4000-8000-000000000008",
        artifact: {
            handle: "art_BBBBBBBBBBBBBBBBBBBBBB",
            digest: `sha256:${"a".repeat(64)}`,
            size: 100,
            media_type: "application/json",
        },
    });
    const adapter = {
        offer: vi.fn().mockResolvedValue({
            proposal,
            receipt: {
                review_id: proposal.review_id,
                state: "approved",
                work_item_id: "60000000-0000-4000-8000-000000000006",
            },
        }),
        decide: vi.fn(),
        cancel: vi.fn(),
        execution: {
            read: vi.fn().mockResolvedValue(blocked),
            download: vi.fn(),
        },
    };
    render(
        <InvoiceReviewPanel
            adapter={adapter}
            handle={proposal.binding.handle}
        />,
    );
    const user = userEvent.setup();
    await user.click(
        screen.getByRole("button", { name: "Review these results" }),
    );
    await user.click(
        screen.getByRole("button", { name: "Check execution result" }),
    );
    expect(
        await screen.findByText(
            "Work is blocked. An operator must review the outcome.",
        ),
    ).toBeVisible();
    expect(adapter.execution.download).not.toHaveBeenCalled();
    adapter.execution.read.mockResolvedValue(dead);
    await user.click(
        screen.getByRole("button", { name: "Check execution result" }),
    );
    expect(
        await screen.findByText(
            "Retry limit reached. Review the failure evidence.",
        ),
    ).toBeVisible();
    expect(adapter.execution.download).not.toHaveBeenCalled();
    await user.click(
        screen.getByRole("button", { name: "Download failure evidence" }),
    );
    expect(adapter.execution.download).toHaveBeenCalledWith(dead);
    expect(adapter.decide).not.toHaveBeenCalled();
    expect(adapter.cancel).not.toHaveBeenCalled();
    expect(
        screen.queryByRole("button", { name: "Cancel work item" }),
    ).not.toBeInTheDocument();
    expect(() =>
        parseInvoiceExecution({ ...dead, phase: "blocked" }),
    ).toThrow();
});
