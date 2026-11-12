import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { render } from "./utils/test-utils";
import { WorkItemsPage } from "../src/core/pages/WorkItems";

const requests: URL[] = [];
let createdQueue: string;
let populated: boolean;
const item = (queue: string) => ({
    id: "custom-item-123",
    queue_name: queue,
    state: "PENDING",
    payload: { value: 7 },
    parent_id: null,
    error_code: null,
    error_message: null,
    files: [],
    created_at: "2026-10-25T00:00:00Z",
    updated_at: "2026-10-25T00:00:00Z",
});

beforeEach(() => {
    requests.length = 0;
    createdQueue = "returned-queue";
    populated = false;
    vi.stubGlobal(
        "fetch",
        vi.fn(async (input: string, init?: RequestInit) => {
            const url = new URL(input, "http://localhost");
            requests.push(url);
            const queue = url.searchParams.get("queue_name") ?? "default";
            const body =
                init?.method === "POST"
                    ? item(createdQueue)
                    : url.pathname.endsWith("/stats")
                      ? {
                            queue_name: queue,
                            total: 0,
                            pending: 0,
                            in_progress: 0,
                            done: 0,
                            failed: 0,
                        }
                      : {
                            items:
                                populated && !url.searchParams.has("state")
                                    ? [item(queue)]
                                    : [],
                            total: populated ? 1 : 0,
                        };
            return { ok: true, json: async () => body };
        }),
    );
});

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

async function openQueue(queue: string) {
    fireEvent.change(
        await screen.findByRole("textbox", { name: "Queue to open" }),
        { target: { value: queue } },
    );
    fireEvent.click(screen.getByRole("button", { name: "Open queue" }));
    await waitFor(() =>
        expect(
            requests.some(
                (url) =>
                    url.pathname === "/api/work-items" &&
                    url.searchParams.get("queue_name") === queue,
            ),
        ).toBe(true),
    );
}

describe("Legacy Work Items queue navigation", () => {
    it("keeps explicit queue navigation reachable from an empty default queue", async () => {
        render(<WorkItemsPage />);
        await openQueue("custom-empty");
        expect(
            await screen.findByRole("combobox", { name: "Queue" }),
        ).toHaveValue("custom-empty");
        expect(screen.queryByText("All Queues")).not.toBeInTheDocument();
    });

    it("keeps omitted queue requests as Runtime default and can return to them", async () => {
        render(<WorkItemsPage />);
        await openQueue("custom-empty");
        fireEvent.change(
            await screen.findByRole("combobox", { name: "Queue" }),
            { target: { value: "" } },
        );
        await waitFor(() =>
            expect(screen.getByRole("combobox", { name: "Queue" })).toHaveValue(
                "",
            ),
        );
        expect(
            requests.some(
                (url) =>
                    url.pathname === "/api/work-items" &&
                    !url.searchParams.has("queue_name"),
            ),
        ).toBe(true);
    });

    it("requests a literal queue named all rather than silently selecting default", async () => {
        render(<WorkItemsPage />);
        await openQueue("all");
        await waitFor(() =>
            expect(
                requests.some(
                    (url) =>
                        url.pathname.endsWith("/stats") &&
                        url.searchParams.get("queue_name") === "all",
                ),
            ).toBe(true),
        );
    });

    it("follows the returned queue after creating an item from the empty page", async () => {
        render(<WorkItemsPage />);
        fireEvent.click(
            await screen.findByRole("button", { name: "Create First Item" }),
        );
        fireEvent.change(screen.getByRole("textbox", { name: "Queue Name" }), {
            target: { value: "requested-queue" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Create" }));
        await waitFor(() =>
            expect(
                requests.some(
                    (url) =>
                        url.searchParams.get("queue_name") === createdQueue,
                ),
            ).toBe(true),
        );
        expect(
            await screen.findByRole("combobox", { name: "Queue" }),
        ).toHaveValue(createdQueue);
    });

    it("keeps state navigation available when a filter has no results", async () => {
        populated = true;
        render(<WorkItemsPage />);
        fireEvent.change(
            await screen.findByRole("combobox", { name: "State" }),
            { target: { value: "FAILED" } },
        );
        expect(
            await screen.findByRole("heading", { name: "No work items yet" }),
        ).toBeInTheDocument();
        fireEvent.change(screen.getByRole("combobox", { name: "State" }), {
            target: { value: "all" },
        });
        expect(await screen.findByText("custom-item-...")).toBeInTheDocument();
    });

    it("prefills creation with the newly selected explicit queue", async () => {
        render(<WorkItemsPage />);
        await openQueue("selected-queue");
        fireEvent.click(
            await screen.findByRole("button", { name: "Create First Item" }),
        );
        expect(screen.getByRole("textbox", { name: "Queue Name" })).toHaveValue(
            "selected-queue",
        );
    });

    it("clears stale state and search filters when opening a different queue", async () => {
        populated = true;
        render(<WorkItemsPage />);
        fireEvent.change(
            await screen.findByPlaceholderText("Search by ID or payload..."),
            { target: { value: "not-present" } },
        );
        fireEvent.change(screen.getByRole("combobox", { name: "State" }), {
            target: { value: "FAILED" },
        });
        await openQueue("another-queue");
        expect(
            await screen.findByRole("combobox", { name: "State" }),
        ).toHaveValue("all");
        expect(
            screen.getByPlaceholderText("Search by ID or payload..."),
        ).toHaveValue("");
        expect(await screen.findByText("custom-item-...")).toBeInTheDocument();
    });
});
