import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { render } from "./utils/test-utils";

const queryState = vi.hoisted(() => ({
    workItems: {} as Record<string, unknown>,
    stats: {} as Record<string, unknown>,
}));

vi.mock("../src/queries/workItems", () => ({
    useWorkItems: () => queryState.workItems,
    useWorkItemStats: () => queryState.stats,
    useCreateWorkItem: () => ({ mutate: vi.fn(), isPending: false }),
    useDeleteWorkItem: () => ({ mutate: vi.fn(), isPending: false }),
    downloadWorkItemFile: vi.fn(),
}));

import { WorkItemsPage } from "../src/core/pages/WorkItems";

const sampleItem = {
    id: "native-item-208",
    queue_name: "default",
    state: "PENDING" as const,
    payload: { probe: "runtime" },
    parent_id: null,
    error_code: null,
    error_message: null,
    files: [],
    created_at: "2026-10-08T12:00:00+00:00",
    updated_at: "2026-10-08T12:00:00+00:00",
};

const emptyStats = {
    queue_name: "default",
    pending: 0,
    in_progress: 0,
    done: 0,
    failed: 0,
    total: 0,
};

function apiError(message: string, status: number, code?: string): Error {
    return Object.assign(new Error(message), { status, code });
}

beforeEach(() => {
    queryState.workItems = {
        data: undefined,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
    };
    queryState.stats = { data: undefined };
});

describe("Work Items page states", () => {
    it("shows an explicit loading state", () => {
        queryState.workItems.isLoading = true;

        render(<WorkItemsPage />);

        expect(
            screen.getByRole("status", { name: "Loading work items..." }),
        ).toBeInTheDocument();
    });

    it("shows an empty queue only after a successful empty response", () => {
        queryState.workItems.data = { items: [], total: 0 };
        queryState.stats.data = emptyStats;

        render(<WorkItemsPage />);

        expect(
            screen.getByRole("heading", { name: "No work items yet" }),
        ).toBeInTheDocument();
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("shows persisted items when the Runtime queue is populated", () => {
        queryState.workItems.data = { items: [sampleItem], total: 1 };
        queryState.stats.data = { ...emptyStats, pending: 1, total: 1 };

        render(<WorkItemsPage />);

        expect(
            screen.getByRole("heading", { name: "Work Items" }),
        ).toBeInTheDocument();
        expect(screen.getAllByText("PENDING").length).toBeGreaterThan(0);
        expect(screen.getByText(/native-item-/)).toBeInTheDocument();
    });

    it("renders the Runtime's COMPLETED wire state with the success treatment", () => {
        queryState.workItems.data = {
            items: [{ ...sampleItem, state: "COMPLETED" }],
            total: 1,
        };
        queryState.stats.data = { ...emptyStats, done: 1, total: 1 };

        render(<WorkItemsPage />);

        const badge = screen.getByText("COMPLETED").closest("span");
        expect(badge).toHaveClass("bg-success/10");
        expect(badge?.querySelector("svg")).not.toBeNull();
    });

    it("gives Runtime-specific recovery when bundled support is unavailable", () => {
        queryState.workItems.error = apiError(
            "Work Items support is unavailable in this Runtime.",
            503,
            "work_items_runtime_unavailable",
        );

        render(<WorkItemsPage />);

        expect(
            screen.getByRole("heading", {
                name: "Work Items support unavailable",
            }),
        ).toBeInTheDocument();
        expect(
            screen.getByText(/update or reinstall the Runtime/i),
        ).toBeInTheDocument();
        expect(screen.queryByText(/package\.yaml/i)).not.toBeInTheDocument();
        expect(
            screen.getByRole("button", { name: "Retry" }),
        ).toBeInTheDocument();
    });

    it("separates a found-but-unloadable Runtime package from missing support", () => {
        queryState.workItems.error = apiError(
            "The Runtime found Work Items support but could not load it.",
            503,
            "work_items_load_failed",
        );

        render(<WorkItemsPage />);

        expect(
            screen.getByRole("heading", { name: "Work Items failed to load" }),
        ).toBeInTheDocument();
        expect(screen.getByText(/could not load it/i)).toBeInTheDocument();
        expect(
            screen.getByRole("button", { name: "Retry" }),
        ).toBeInTheDocument();
    });

    it("reports authorization denial separately from Runtime availability", () => {
        queryState.workItems.error = apiError("Forbidden", 403);

        render(<WorkItemsPage />);

        expect(
            screen.getByRole("heading", { name: "Access denied" }),
        ).toBeInTheDocument();
        expect(
            screen.getByText(/check your Runtime access/i),
        ).toBeInTheDocument();
        expect(screen.queryByText(/package\.yaml/i)).not.toBeInTheDocument();
    });

    it("shows a bounded recovery message for Runtime storage failures", () => {
        queryState.workItems.error = apiError(
            "The Runtime could not read its local Work Items storage.",
            503,
            "work_items_storage_unavailable",
        );

        render(<WorkItemsPage />);

        expect(
            screen.getByRole("heading", {
                name: "Work Items storage unavailable",
            }),
        ).toBeInTheDocument();
        expect(screen.getByText(/local Runtime storage/i)).toBeInTheDocument();
        expect(
            screen.getByRole("button", { name: "Retry" }),
        ).toBeInTheDocument();
    });

    it("does not turn a failed load with no data into a successful empty queue", () => {
        queryState.workItems.data = undefined;
        queryState.workItems.error = apiError("Internal Server Error", 500);

        render(<WorkItemsPage />);

        expect(
            screen.getByRole("heading", { name: "Work Items server error" }),
        ).toBeInTheDocument();
        expect(
            screen.queryByRole("heading", { name: "No work items yet" }),
        ).not.toBeInTheDocument();
        expect(
            screen.getByRole("button", { name: "Retry" }),
        ).toBeInTheDocument();
    });
    it("labels creation fields and announces invalid JSON with a recovery path", () => {
        queryState.workItems.data = { items: [], total: 0 };
        queryState.stats.data = emptyStats;
        render(<WorkItemsPage />);
        fireEvent.click(screen.getByRole("button", { name: "Create First Item" }));
        const queue = screen.getByRole("textbox", { name: "Queue Name" });
        const payload = screen.getByRole("textbox", { name: "Payload (JSON)" });
        fireEvent.change(queue, { target: { value: "accessibility-probe" } });
        fireEvent.change(payload, { target: { value: "{" } });
        fireEvent.click(screen.getByRole("button", { name: "Create" }));
        expect(screen.getByRole("alert")).toHaveTextContent("Invalid JSON");
        expect(payload).toHaveAttribute("aria-invalid", "true");
        fireEvent.change(payload, { target: { value: '{"probe":true}' } });
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
        expect(payload).toHaveAttribute("aria-invalid", "false");
    });

});
