import { createElement } from "react";
import type { ComponentType, ReactNode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import type { CapabilityDispatcher, CapabilityRef } from "./index";

interface SearchInput {
    query: string;
}

interface SearchOutput {
    rows: Array<{ id: string; label: string }>;
}

const searchColumns = [{ key: "label", label: "Record" }] as const;

type SearchDispatcher = CapabilityDispatcher<
    "search",
    SearchInput,
    SearchOutput
>;

interface SemanticCanvasProps {
    title: string;
    revision: string;
    preview: boolean;
    audience: "app" | "model" | "both";
    viewer: "app" | "model";
    children?: ReactNode;
}

interface SemanticFormProps {
    title: string;
    fields: Array<{ name: string; label: string; required?: boolean }>;
    capability: CapabilityRef<"search", SearchInput, SearchOutput>;
    toInput: (values: Record<string, string>) => SearchInput;
    dispatch: CapabilityDispatcher<"search", SearchInput, SearchOutput>;
    renderResult: (result: SearchOutput) => ReactNode;
}

interface SemanticTableProps {
    caption: string;
    columns: typeof searchColumns;
    rows: SearchOutput["rows"];
    rowKey: (row: SearchOutput["rows"][number]) => string;
    emptyMessage?: string;
}

interface SemanticStatusProps {
    state: "loading" | "success" | "empty" | "error";
    message: string;
}

interface SemanticRendererApi {
    createCapabilityRef: <Id extends string, Input, Output>(
        bindingId: Id,
    ) => CapabilityRef<Id, Input, Output>;
    SemanticCanvas: ComponentType<SemanticCanvasProps>;
    SemanticForm: ComponentType<SemanticFormProps>;
    SemanticTable: ComponentType<SemanticTableProps>;
    SemanticStatus: ComponentType<SemanticStatusProps>;
}

function assertTypedBindingDispatch(
    reference: CapabilityRef<"search", SearchInput, SearchOutput>,
    dispatch: CapabilityDispatcher<"search", SearchInput, SearchOutput>,
) {
    dispatch(reference, { query: "valid" });

    // @ts-expect-error A binding accepts only its declared input shape.
    dispatch(reference, { toolName: "client-selected" });
}

void assertTypedBindingDispatch;

const rendererModules = import.meta.glob<SemanticRendererApi>("./index.ts", {
    eager: true,
});

function loadRenderer() {
    return rendererModules["./index.ts"] ?? null;
}

describe("semantic Canvas components", () => {
    it("exports semantic rendering components", async () => {
        const renderer = loadRenderer();
        expect(renderer).not.toBeNull();
        if (!renderer) return;
        expect(renderer.SemanticCanvas).toBeTypeOf("function");
        expect(renderer.SemanticForm).toBeTypeOf("function");
        expect(renderer.SemanticTable).toBeTypeOf("function");
        expect(renderer.SemanticStatus).toBeTypeOf("function");
        expect(renderer.createCapabilityRef).toBeTypeOf("function");
    });

    it("shows preview revision and audience as safe text", async () => {
        const renderer = loadRenderer();
        expect(renderer).not.toBeNull();
        if (!renderer) return;

        render(
            createElement(
                renderer.SemanticCanvas,
                {
                    title: 'Records <img src="x" onerror="alert(1)" />',
                    revision: "rev-7",
                    preview: true,
                    audience: "app",
                    viewer: "app",
                },
                createElement("p", null, "Preview content"),
            ),
        );

        expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
            'Records <img src="x" onerror="alert(1)" />',
        );
        expect(screen.getByText("Preview")).toBeVisible();
        expect(screen.getByText("Revision rev-7")).toBeVisible();
        expect(screen.getByText("App audience")).toBeVisible();
        expect(document.querySelector("img")).toBeNull();
    });

    it("keeps app-only content out of the model audience", async () => {
        const renderer = loadRenderer();
        expect(renderer).not.toBeNull();
        if (!renderer) return;

        render(
            createElement(
                renderer.SemanticCanvas,
                {
                    title: "Private details",
                    revision: "rev-1",
                    preview: true,
                    audience: "app",
                    viewer: "model",
                },
                createElement("p", null, "App-only result"),
            ),
        );

        expect(screen.queryByText("App-only result")).toBeNull();
        expect(
            screen.queryByRole("heading", { name: "Private details" }),
        ).toBeNull();
        expect(screen.queryByText("Revision rev-1")).toBeNull();
        expect(
            screen.getByText("This view is for the app audience."),
        ).toBeVisible();
    });

    it("renders action errors as bounded text without interpreting markup", () => {
        const renderer = loadRenderer();
        expect(renderer).not.toBeNull();
        if (!renderer) return;

        render(
            createElement(renderer.SemanticStatus, {
                state: "error",
                message: '<script>alert("secret")</script>',
            }),
        );

        expect(screen.getByRole("alert")).toHaveTextContent(
            '<script>alert("secret")</script>',
        );
        expect(document.querySelector("script")).toBeNull();
    });

    it("dispatches typed form input and renders the returned table", async () => {
        const renderer = loadRenderer();
        expect(renderer).not.toBeNull();
        if (!renderer) return;

        const user = userEvent.setup();
        const dispatch: SearchDispatcher = vi.fn().mockResolvedValue({
            rows: [{ id: "record-1", label: "Reference guide" }],
        });
        const capability = renderer.createCapabilityRef<
            "search",
            SearchInput,
            SearchOutput
        >("search");

        render(
            createElement(renderer.SemanticForm, {
                title: "Search records",
                fields: [
                    { name: "query", label: "Search term", required: true },
                ],
                capability,
                toInput: (values: Record<string, string>) => ({
                    query: values.query,
                }),
                dispatch,
                renderResult: (result: SearchOutput) =>
                    createElement(renderer.SemanticTable, {
                        caption: "Search results",
                        columns: searchColumns,
                        rows: result.rows,
                        rowKey: (row: SearchOutput["rows"][number]) => row.id,
                    }),
            }),
        );

        await user.type(
            screen.getByRole("textbox", { name: "Search term" }),
            "guide",
        );
        await user.click(
            screen.getByRole("button", { name: "Search records" }),
        );

        await waitFor(() =>
            expect(dispatch).toHaveBeenCalledWith(capability, {
                query: "guide",
            }),
        );
        expect(
            await screen.findByRole("table", { name: "Search results" }),
        ).toBeVisible();
        expect(
            screen.getByRole("row", { name: "Reference guide" }),
        ).toBeVisible();
    });

    it("does not dispatch a required field with only whitespace", async () => {
        const renderer = loadRenderer();
        expect(renderer).not.toBeNull();
        if (!renderer) return;

        const user = userEvent.setup();
        const dispatch: SearchDispatcher = vi
            .fn()
            .mockResolvedValue({ rows: [] });
        const capability = renderer.createCapabilityRef<
            "search",
            SearchInput,
            SearchOutput
        >("search");

        render(
            createElement(renderer.SemanticForm, {
                title: "Search records",
                fields: [
                    { name: "query", label: "Search term", required: true },
                ],
                capability,
                toInput: (values: Record<string, string>) => ({
                    query: values.query,
                }),
                dispatch,
                renderResult: () => null,
            }),
        );

        await user.type(
            screen.getByRole("textbox", { name: "Search term" }),
            "   ",
        );
        await user.click(
            screen.getByRole("button", { name: "Search records" }),
        );

        expect(await screen.findByRole("alert")).toHaveTextContent(
            "Enter a value for Search term.",
        );
        expect(dispatch).not.toHaveBeenCalled();
    });

    it("rejects malformed field definitions before rendering controls", async () => {
        const renderer = loadRenderer();
        expect(renderer).not.toBeNull();
        if (!renderer) return;

        const dispatch: SearchDispatcher = vi
            .fn()
            .mockResolvedValue({ rows: [] });
        const capability = renderer.createCapabilityRef<
            "search",
            SearchInput,
            SearchOutput
        >("search");

        render(
            createElement(renderer.SemanticForm, {
                title: "Search records",
                fields: [
                    { name: "query", label: "First field" },
                    { name: "query", label: "Duplicate field" },
                ],
                capability,
                toInput: (values: Record<string, string>) => ({
                    query: values.query,
                }),
                dispatch,
                renderResult: () => null,
            }),
        );

        expect(screen.getByRole("alert")).toHaveTextContent(
            "This form cannot be displayed.",
        );
        expect(screen.queryByRole("textbox")).toBeNull();
        expect(dispatch).not.toHaveBeenCalled();
    });

    it("renders returned table cells as text and shows an empty result", async () => {
        const renderer = await loadRenderer();
        expect(renderer).not.toBeNull();
        if (!renderer) return;

        const columns = [{ key: "label", label: "Record" }] as const;
        const maliciousLabel = '<svg onload="alert(1)">';
        const view = render(
            createElement(renderer.SemanticTable, {
                caption: "Records",
                columns,
                rows: [{ id: "record-1", label: maliciousLabel }],
                rowKey: (row: { id: string; label: string }) => row.id,
            }),
        );

        expect(
            screen.getByRole("cell", { name: maliciousLabel }),
        ).toBeVisible();
        expect(document.querySelector("svg")).toBeNull();

        view.rerender(
            createElement(renderer.SemanticTable, {
                caption: "Records",
                columns,
                rows: [] as Array<{ id: string; label: string }>,
                rowKey: (row: { id: string; label: string }) => row.id,
                emptyMessage: "No records found.",
            }),
        );
        expect(screen.getByRole("status")).toHaveTextContent(
            "No records found.",
        );
    });
});
