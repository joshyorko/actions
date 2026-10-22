import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";

import { InvoiceReviewPanel } from "./InvoiceReviewPanel";

afterEach(cleanup);

it("requires an explicit offer followed by an explicit approval", async () => {
    const user = userEvent.setup();
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
