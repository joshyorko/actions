import * as axeCore from "axe-core";
import {
    act,
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";

import fixture from "../../../../../../docs/contracts/canvas/fixtures/query-results-v0.1.fixture.json";
import {
    QueryResultsView,
    type QueryActionResult,
    type QueryResultsAdapter,
} from "./QueryResultsView";

const success = fixture.success as QueryActionResult;

afterEach(cleanup);

function adapter(
    overrides: Partial<QueryResultsAdapter> = {},
): QueryResultsAdapter {
    return {
        submitQuery: vi.fn().mockResolvedValue(success),
        getArtifactStatus: vi.fn().mockResolvedValue("ready"),
        ...overrides,
    };
}

function deferred<T>() {
    let resolve!: (value: T | PromiseLike<T>) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((resolvePromise, rejectPromise) => {
        resolve = resolvePromise;
        reject = rejectPromise;
    });
    return { promise, resolve, reject };
}

describe("QueryResultsView fixture renderer", () => {
    it("renders a labelled idle form without accessibility violations", async () => {
        render(<QueryResultsView adapter={adapter()} />);

        expect(
            screen.getByRole("heading", { name: "Search records" }),
        ).toBeVisible();
        expect(
            screen.getByRole("textbox", { name: "Search records" }),
        ).toBeVisible();
        const a11y = await axeCore.run(document.body, {
            rules: { "color-contrast": { enabled: false } },
        });
        expect(a11y.violations).toEqual([]);
    });

    it("rejects blank input locally and submits only the fixed query shape", async () => {
        const user = userEvent.setup();
        const app = adapter();
        render(<QueryResultsView adapter={app} />);

        await user.type(
            screen.getByRole("textbox", { name: "Search records" }),
            "   ",
        );
        await user.click(screen.getByRole("button", { name: "Search" }));

        expect(screen.getByRole("alert")).toHaveTextContent(
            "at least one visible character",
        );
        expect(app.submitQuery).not.toHaveBeenCalled();

        await user.clear(
            screen.getByRole("textbox", { name: "Search records" }),
        );
        await user.type(
            screen.getByRole("textbox", { name: "Search records" }),
            fixture.input.query,
        );
        await user.click(screen.getByRole("button", { name: "Search" }));

        await waitFor(() =>
            expect(app.submitQuery).toHaveBeenCalledWith({
                query: fixture.input.query,
            }),
        );
        expect(
            screen.getByRole("table", { name: "Search results" }),
        ).toBeVisible();
        expect(
            screen.getByRole("row", { name: "Alpha guide Guide" }),
        ).toBeVisible();
        expect(
            screen.getByRole("row", { name: "Alpha checklist Checklist" }),
        ).toBeVisible();
    });

    it("uses the injected status method with the opaque handle", async () => {
        const user = userEvent.setup();
        const app = adapter();
        render(<QueryResultsView adapter={app} />);

        await user.type(
            screen.getByRole("textbox", { name: "Search records" }),
            "alpha",
        );
        await user.click(screen.getByRole("button", { name: "Search" }));
        await user.click(
            await screen.findByRole("button", {
                name: "Check artifact status",
            }),
        );

        expect(app.getArtifactStatus).toHaveBeenCalledWith(
            success.artifact!.handle,
        );
        expect(
            await screen.findByText("Result artifact is ready."),
        ).toBeVisible();
        expect(
            screen.getByText(/handle alone does not grant access/),
        ).toBeVisible();
    });

    it("ignores a stale status success and finalizer after the query changes", async () => {
        const user = userEvent.setup();
        const oldStatus = deferred<"ready" | "processing" | "unavailable">();
        const currentStatus = deferred<
            "ready" | "processing" | "unavailable"
        >();
        const nextResult: QueryActionResult = {
            ...success,
            artifact: { handle: "art_Bbbbbbbbbbbbbbbbbbbbbb" as never },
        };
        const app = adapter({
            submitQuery: vi
                .fn<QueryResultsAdapter["submitQuery"]>()
                .mockResolvedValueOnce(success)
                .mockResolvedValueOnce(nextResult),
            getArtifactStatus: vi
                .fn<QueryResultsAdapter["getArtifactStatus"]>()
                .mockReturnValueOnce(oldStatus.promise)
                .mockReturnValueOnce(currentStatus.promise),
        });
        render(<QueryResultsView adapter={app} />);

        await user.type(
            screen.getByRole("textbox", { name: "Search records" }),
            "alpha",
        );
        await user.click(screen.getByRole("button", { name: "Search" }));
        await user.click(
            await screen.findByRole("button", {
                name: "Check artifact status",
            }),
        );

        const input = screen.getByRole("textbox", { name: "Search records" });
        await user.clear(input);
        await user.type(input, "beta");
        await user.click(screen.getByRole("button", { name: "Search" }));
        await user.click(
            await screen.findByRole("button", {
                name: "Check artifact status",
            }),
        );
        expect(
            screen.getByRole("button", { name: "Checking…" }),
        ).toBeDisabled();

        await act(async () => {
            oldStatus.resolve("unavailable");
            await oldStatus.promise;
        });

        expect(
            screen.queryByText("Result artifact is unavailable."),
        ).toBeNull();
        expect(
            screen.getByRole("button", { name: "Checking…" }),
        ).toBeDisabled();

        await act(async () => {
            currentStatus.resolve("ready");
            await currentStatus.promise;
        });
        expect(
            await screen.findByText("Result artifact is ready."),
        ).toBeVisible();
    });

    it("ignores a stale status rejection while the new result is checking", async () => {
        const user = userEvent.setup();
        const oldStatus = deferred<"ready" | "processing" | "unavailable">();
        const currentStatus = deferred<
            "ready" | "processing" | "unavailable"
        >();
        const app = adapter({
            getArtifactStatus: vi
                .fn<QueryResultsAdapter["getArtifactStatus"]>()
                .mockReturnValueOnce(oldStatus.promise)
                .mockReturnValueOnce(currentStatus.promise),
        });
        render(<QueryResultsView adapter={app} />);

        await user.type(
            screen.getByRole("textbox", { name: "Search records" }),
            "alpha",
        );
        await user.click(screen.getByRole("button", { name: "Search" }));
        await user.click(
            await screen.findByRole("button", {
                name: "Check artifact status",
            }),
        );

        const input = screen.getByRole("textbox", { name: "Search records" });
        await user.clear(input);
        await user.type(input, "beta");
        await user.click(screen.getByRole("button", { name: "Search" }));
        await user.click(
            await screen.findByRole("button", {
                name: "Check artifact status",
            }),
        );

        await act(async () => {
            oldStatus.reject(new Error("stale provider details"));
            await oldStatus.promise.catch(() => undefined);
        });

        expect(screen.queryByRole("alert")).toBeNull();
        expect(
            screen.getByRole("button", { name: "Checking…" }),
        ).toBeDisabled();
        await act(async () => {
            currentStatus.resolve("ready");
            await currentStatus.promise;
        });
        expect(
            await screen.findByText("Result artifact is ready."),
        ).toBeVisible();
    });

    it("ignores a stale status rejection after the view is reopened", async () => {
        const user = userEvent.setup();
        const oldStatus = deferred<"ready" | "processing" | "unavailable">();
        const app = adapter({
            getArtifactStatus: vi
                .fn<QueryResultsAdapter["getArtifactStatus"]>()
                .mockReturnValue(oldStatus.promise),
        });
        const view = render(<QueryResultsView adapter={app} />);

        await user.type(
            screen.getByRole("textbox", { name: "Search records" }),
            "alpha",
        );
        await user.click(screen.getByRole("button", { name: "Search" }));
        await user.click(
            await screen.findByRole("button", {
                name: "Check artifact status",
            }),
        );
        view.unmount();

        render(<QueryResultsView adapter={adapter()} />);
        await act(async () => {
            oldStatus.reject(new Error("stale provider details"));
            await oldStatus.promise.catch(() => undefined);
        });

        expect(screen.queryByRole("alert")).toBeNull();
        expect(
            screen.getByText("Search records to see matching results."),
        ).toBeVisible();
    });

    it("announces loading and then the empty state", async () => {
        const user = userEvent.setup();
        let finishSearch: ((result: QueryActionResult) => void) | undefined;
        const app = adapter({
            submitQuery: vi.fn<QueryResultsAdapter["submitQuery"]>(
                () =>
                    new Promise((resolve) => {
                        finishSearch = resolve;
                    }),
            ),
        });
        render(<QueryResultsView adapter={app} />);

        await user.type(
            screen.getByRole("textbox", { name: "Search records" }),
            "alpha",
        );
        await user.click(screen.getByRole("button", { name: "Search" }));
        expect(screen.getByRole("status")).toHaveTextContent(
            "Searching records",
        );

        finishSearch?.({ rows: [], artifact: null, error: null });
        expect(
            await screen.findByText(
                "No records to show yet. Try a search above.",
            ),
        ).toBeVisible();
    });

    it("renders the fixed domain error message without accepting its free text", async () => {
        const user = userEvent.setup();
        const app = adapter({
            submitQuery: vi.fn().mockResolvedValue({
                ...fixture.domainError,
                error: {
                    ...fixture.domainError.error,
                    message: "untrusted provider detail",
                },
            }),
        });
        render(<QueryResultsView adapter={app} />);

        await user.type(
            screen.getByRole("textbox", { name: "Search records" }),
            "missing",
        );
        await user.click(screen.getByRole("button", { name: "Search" }));

        expect(await screen.findByRole("alert")).toHaveTextContent(
            "No records matched that query.",
        );
        expect(
            screen.queryByText("untrusted provider detail"),
        ).not.toBeInTheDocument();
    });

    it("hides adapter exception details and exposes a bounded failure", async () => {
        const app = adapter({
            submitQuery: vi
                .fn()
                .mockRejectedValue(new Error("secret=do-not-render")),
        });
        render(<QueryResultsView adapter={app} />);

        fireEvent.change(
            screen.getByRole("textbox", { name: "Search records" }),
            {
                target: { value: "alpha" },
            },
        );
        fireEvent.click(screen.getByRole("button", { name: "Search" }));

        expect(await screen.findByRole("alert")).toHaveTextContent(
            "Unable to search right now.",
        );
        expect(screen.queryByText(/do-not-render/)).not.toBeInTheDocument();
    });
});
