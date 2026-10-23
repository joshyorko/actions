import { createElement } from "react";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFile } from "node:fs/promises";
import { resolve as resolvePath } from "node:path";
import { cwd } from "node:process";
import { describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";

import * as renderer from "./index";
import type {
    CanvasSpecDocument,
    CapabilityDispatcher,
    CapabilityRef,
    SemanticFormInput,
    SemanticRendererAdapters,
} from "./index";

interface SearchInput {
    query: string;
}

interface SearchOutput {
    items: Array<{ name: string; status: string }>;
}

type SearchDispatcher = CapabilityDispatcher<string, SearchInput, SearchOutput>;

const SearchForm = renderer.SemanticForm<string, SearchInput, SearchOutput>;
const TypedForm = renderer.SemanticForm<string, SemanticFormInput, unknown>;

function assertTypedBindingDispatch(
    reference: CapabilityRef<"search", SearchInput, SearchOutput>,
    dispatch: CapabilityDispatcher<"search", SearchInput, SearchOutput>,
) {
    dispatch(reference, { query: "valid" });

    // @ts-expect-error A binding accepts only its declared input shape.
    dispatch(reference, { toolName: "client-selected" });
}

void assertTypedBindingDispatch;

async function readCanonicalFixture(): Promise<CanvasSpecDocument> {
    const contents = await readFile(
        resolvePath(
            cwd(),
            "apps/canvas-view/src/semantic-renderer/fixtures/canvas-spec-v1.fixture.json",
        ),
        "utf8",
    );
    return JSON.parse(contents) as CanvasSpecDocument;
}

function createAdapters(
    dispatchImplementation: SearchDispatcher = vi
        .fn<SearchDispatcher>()
        .mockResolvedValue({ items: [] }),
    options: {
        status?: {
            state: "loading" | "success" | "empty" | "error";
            message: string;
        };
        artifact?: { state: "ready" | "unavailable"; message: string };
    } = {},
): SemanticRendererAdapters {
    const formCapability = renderer.createCapabilityRef<
        string,
        SemanticFormInput,
        unknown
    >("search");
    const statusCapability = renderer.createCapabilityRef<
        string,
        never,
        { state: "loading" | "success" | "empty" | "error"; message: string }
    >("search");
    const artifactCapability = renderer.createCapabilityRef<
        string,
        void,
        { state: "ready" | "unavailable"; message: string }
    >("search");
    const dispatch: SemanticRendererAdapters["dispatch"] = async (
        capability,
        input,
    ) =>
        dispatchImplementation(
            capability as unknown as CapabilityRef<
                string,
                SearchInput,
                SearchOutput
            >,
            input as unknown as SearchInput,
        );

    return {
        resolveFormBinding: (bindingId) =>
            bindingId === "search" ? formCapability : undefined,
        dispatch,
        resolveStatusBinding: (bindingId) =>
            bindingId === "search" ? statusCapability : undefined,
        getStatus: () => options.status,
        resolveArtifactBinding: (bindingId) =>
            bindingId === "search" ? artifactCapability : undefined,
        openArtifact: async () =>
            options.artifact ?? {
                state: "ready",
                message: "Artifact is ready.",
            },
    };
}

const baseRevisionProps = {
    revision: "rev-7",
    scopeKey: "app-a:rev-7",
    preview: false,
    viewer: "app" as const,
};

describe("semantic Canvas components", () => {
    it("exports semantic components and the renderer", () => {
        expect(renderer.SemanticCanvas).toBeTypeOf("function");
        expect(renderer.SemanticCanvasRenderer).toBeTypeOf("function");
        expect(renderer.SemanticForm).toBeTypeOf("function");
        expect(renderer.SemanticTable).toBeTypeOf("function");
        expect(renderer.SemanticStatus).toBeTypeOf("function");
        expect(renderer.createCapabilityRef).toBeTypeOf("function");
    });

    it("renders the canonical PR330 fixture through injected adapters", async () => {
        const spec = await readCanonicalFixture();
        const adapters = createAdapters();
        render(
            createElement(renderer.SemanticCanvasRenderer, {
                spec,
                ...baseRevisionProps,
                adapters,
            }),
        );

        expect(
            screen.getByRole("heading", { name: "Search records" }),
        ).toBeVisible();
        expect(screen.getByText("Search the existing records.")).toBeVisible();
        expect(
            screen.getByRole("spinbutton", { name: "Maximum results" }),
        ).toBeVisible();
        expect(screen.getByText("No results to display.")).toBeVisible();
        expect(screen.getByText("No status is available.")).toBeVisible();
        expect(
            screen.getByRole("button", { name: "Download CSV" }),
        ).toBeEnabled();
    });

    it("renders the title and revision as text, not markup", () => {
        render(
            createElement(
                renderer.SemanticCanvas,
                {
                    title: 'Records <img src="x" onerror="alert(1)" />',
                    revision: "rev-7",
                    preview: true,
                    visibility: ["app"],
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

    it("hides every detail, including title and revision, for empty visibility", () => {
        render(
            createElement(
                renderer.SemanticCanvas,
                {
                    title: "Private details",
                    revision: "rev-secret",
                    preview: true,
                    visibility: [],
                    viewer: "model",
                },
                createElement("p", null, "Private result"),
            ),
        );

        expect(screen.queryByText("Private details")).toBeNull();
        expect(screen.queryByText("Revision rev-secret")).toBeNull();
        expect(screen.queryByText("Private result")).toBeNull();
        expect(screen.getByText("This view is unavailable.")).toBeVisible();
    });

    it("does not expose app-only content to the model viewer", () => {
        render(
            createElement(
                renderer.SemanticCanvas,
                {
                    title: "Private details",
                    revision: "rev-1",
                    preview: true,
                    visibility: ["app"],
                    viewer: "model",
                },
                createElement("p", null, "App-only result"),
            ),
        );

        expect(screen.queryByText("App-only result")).toBeNull();
        expect(screen.queryByText("Private details")).toBeNull();
        expect(screen.queryByText("Revision rev-1")).toBeNull();
        expect(screen.getByText("This view is unavailable.")).toBeVisible();
    });

    it.each(["constructor", "toString"])(
        "treats an untouched required %s field as empty and never dispatches",
        async (fieldName) => {
            const user = userEvent.setup();
            const dispatch = vi.fn().mockResolvedValue({ items: [] });
            const capability = renderer.createCapabilityRef<
                string,
                SearchInput,
                SearchOutput
            >("search");
            render(
                createElement(SearchForm, {
                    scopeKey: "app-a:rev-1:form-a",
                    submitLabel: "Search",
                    fields: [
                        {
                            name: fieldName,
                            label: "Special property",
                            type: "text",
                            required: true,
                        },
                    ],
                    capability,
                    toInput: (values) => ({
                        query: String(values[fieldName] ?? ""),
                    }),
                    dispatch,
                    renderResult: () => null,
                }),
            );

            await user.click(screen.getByRole("button", { name: "Search" }));
            expect(await screen.findByRole("alert")).toHaveTextContent(
                "Enter a value for Special property.",
            );
            expect(dispatch).not.toHaveBeenCalled();

            await user.type(
                screen.getByRole("textbox", { name: "Special property" }),
                "user value",
            );
            await user.click(screen.getByRole("button", { name: "Search" }));
            await waitFor(() =>
                expect(dispatch).toHaveBeenCalledWith(capability, {
                    query: "user value",
                }),
            );
        },
    );

    it("dispatches fixture integer and boolean fields as number and boolean", async () => {
        const spec = await readCanonicalFixture();
        const root = spec.root;
        if (root.type !== "stack") throw new Error("Expected a stack fixture.");
        const form = root.children.find((node) => node.type === "form");
        if (form?.type !== "form") throw new Error("Expected a fixture form.");
        form.fields.push({
            name: "includeArchived",
            label: "Include archived",
            type: "boolean",
            required: false,
        });

        const dispatch = vi.fn(async () => ({
            items: [{ name: "Found record", status: "active" }],
        }));
        const user = userEvent.setup();
        render(
            createElement(renderer.SemanticCanvasRenderer, {
                spec,
                ...baseRevisionProps,
                adapters: createAdapters(dispatch),
            }),
        );

        await user.type(
            screen.getByRole("textbox", { name: "Search records" }),
            "records",
        );
        await user.type(
            screen.getByRole("spinbutton", { name: "Maximum results" }),
            "7",
        );
        await user.click(
            screen.getByRole("checkbox", { name: "Include archived" }),
        );
        await user.click(screen.getByRole("button", { name: "Search" }));

        await waitFor(() =>
            expect(dispatch).toHaveBeenCalledWith(expect.anything(), {
                query: "records",
                limit: 7,
                includeArchived: true,
            }),
        );
        expect(
            await screen.findByRole("row", {
                name: "Found record active",
            }),
        ).toBeVisible();
    });

    it("validates required booleans and rejects non-integer input", async () => {
        const user = userEvent.setup();
        const dispatch = vi.fn().mockResolvedValue({ items: [] });
        const capability = renderer.createCapabilityRef<
            string,
            SemanticFormInput,
            unknown
        >("search");
        render(
            createElement(TypedForm, {
                scopeKey: "app-a:rev-1:typed-form",
                submitLabel: "Run",
                fields: [
                    {
                        name: "accepted",
                        label: "Accept terms",
                        type: "boolean",
                        required: true,
                    },
                    {
                        name: "count",
                        label: "Count",
                        type: "integer",
                        required: true,
                    },
                ],
                capability,
                toInput: (values) => values,
                dispatch,
                renderResult: () => null,
            }),
        );

        await user.click(screen.getByRole("button", { name: "Run" }));
        expect(await screen.findByRole("alert")).toHaveTextContent(
            "Enter a value for Accept terms.",
        );
        expect(dispatch).not.toHaveBeenCalled();

        await user.click(
            screen.getByRole("checkbox", { name: "Accept terms" }),
        );
        await user.type(
            screen.getByRole("spinbutton", { name: "Count" }),
            "1.5",
        );
        await user.click(screen.getByRole("button", { name: "Run" }));
        expect(await screen.findByRole("alert")).toHaveTextContent(
            "Enter a whole number for Count.",
        );
        expect(dispatch).not.toHaveBeenCalled();
    });

    it("resets inputs and ignores a deferred response when capability scope changes", async () => {
        let resolveFirst: (value: SearchOutput) => void = () => {
            throw new Error("First scope dispatch was not started.");
        };
        const firstResult = new Promise<SearchOutput>((resolve) => {
            resolveFirst = resolve;
        });
        let firstScopeCalls = 0;
        const dispatch: SearchDispatcher = vi.fn((capability) => {
            if (capability.bindingId === "search-a") {
                firstScopeCalls += 1;
                return firstScopeCalls === 1
                    ? Promise.resolve({
                          items: [{ name: "Old scope result", status: "old" }],
                      })
                    : firstResult;
            }
            return Promise.resolve({
                items: [{ name: "New scope", status: "current" }],
            });
        });
        const firstCapability = renderer.createCapabilityRef<
            string,
            SearchInput,
            SearchOutput
        >("search-a");
        const secondCapability = renderer.createCapabilityRef<
            string,
            SearchInput,
            SearchOutput
        >("search-b");
        const form = (
            scopeKey: string,
            capability: CapabilityRef<string, SearchInput, SearchOutput>,
        ) =>
            createElement(SearchForm, {
                scopeKey,
                submitLabel: "Search",
                fields: [
                    {
                        name: "query",
                        label: "Search term",
                        type: "text",
                        required: true,
                    },
                ],
                capability,
                toInput: (values) => ({ query: String(values.query ?? "") }),
                dispatch,
                renderResult: (result) =>
                    createElement("output", null, result.items[0]?.name),
            });

        const user = userEvent.setup();
        const view = render(
            form("app-a:revision-1:query-form", firstCapability),
        );
        await user.type(
            screen.getByRole("textbox", { name: "Search term" }),
            "first scope",
        );
        await user.click(screen.getByRole("button", { name: "Search" }));
        expect(dispatch).toHaveBeenCalledWith(firstCapability, {
            query: "first scope",
        });
        expect(await screen.findByText("Old scope result")).toBeVisible();

        await user.click(screen.getByRole("button", { name: "Search" }));
        expect(dispatch).toHaveBeenCalledTimes(2);

        view.rerender(form("app-b:revision-2:query-form", secondCapability));
        expect(
            screen.getByRole("textbox", { name: "Search term" }),
        ).toHaveValue("");
        expect(screen.queryByText("Old scope result")).toBeNull();
        await act(async () => {
            resolveFirst({
                items: [{ name: "Old scope", status: "stale" }],
            });
            await firstResult;
        });
        expect(screen.queryByText("Old scope")).toBeNull();

        await user.type(
            screen.getByRole("textbox", { name: "Search term" }),
            "second scope",
        );
        await user.click(screen.getByRole("button", { name: "Search" }));
        expect(await screen.findByText("New scope")).toBeVisible();
        expect(dispatch).toHaveBeenLastCalledWith(secondCapability, {
            query: "second scope",
        });
    });

    it("rejects malformed specs and duplicate form fields before rendering controls", async () => {
        const spec = await readCanonicalFixture();
        const malformed = JSON.parse(
            JSON.stringify(spec),
        ) as CanvasSpecDocument;
        Reflect.set(malformed, "schemaVersion", "actions.canvas-spec/v999");
        const view = render(
            createElement(renderer.SemanticCanvasRenderer, {
                spec: malformed as unknown as CanvasSpecDocument,
                ...baseRevisionProps,
                adapters: createAdapters(),
            }),
        );
        expect(screen.getByRole("alert")).toHaveTextContent(
            "This Canvas view cannot be displayed.",
        );
        expect(screen.queryByRole("textbox")).toBeNull();

        view.unmount();
        const capability = renderer.createCapabilityRef<
            string,
            SearchInput,
            SearchOutput
        >("search");
        render(
            createElement(SearchForm, {
                scopeKey: "app-a:rev-1:duplicate-form",
                submitLabel: "Search",
                fields: [
                    {
                        name: "query",
                        label: "First field",
                        type: "text",
                        required: false,
                    },
                    {
                        name: "query",
                        label: "Duplicate field",
                        type: "text",
                        required: false,
                    },
                ],
                capability,
                toInput: () => ({ query: "" }),
                dispatch: vi.fn(),
                renderResult: () => null,
            }),
        );
        expect(screen.getByRole("alert")).toHaveTextContent(
            "This form cannot be displayed.",
        );
        expect(screen.queryByRole("textbox")).toBeNull();
    });

    it("does not resolve any binding when the spec hides all audiences", async () => {
        const spec = await readCanonicalFixture();
        spec.visibility = [];
        const adapters = createAdapters();
        const resolveForm = vi.spyOn(adapters, "resolveFormBinding");
        const resolveStatus = vi.spyOn(adapters, "resolveStatusBinding");
        const resolveArtifact = vi.spyOn(adapters, "resolveArtifactBinding");
        const getStatus = vi.spyOn(adapters, "getStatus");

        render(
            createElement(renderer.SemanticCanvasRenderer, {
                spec,
                ...baseRevisionProps,
                adapters,
            }),
        );

        expect(screen.getByText("This view is unavailable.")).toBeVisible();
        expect(
            screen.queryByRole("heading", { name: "Search records" }),
        ).toBeNull();
        expect(resolveForm).not.toHaveBeenCalled();
        expect(resolveStatus).not.toHaveBeenCalled();
        expect(resolveArtifact).not.toHaveBeenCalled();
        expect(getStatus).not.toHaveBeenCalled();
    });

    it("projects status, opens artifacts through the typed adapter, and keeps preview inert", async () => {
        const spec = await readCanonicalFixture();
        const openArtifact = vi.fn(async () => ({
            state: "ready" as const,
            message: "CSV is ready.",
        }));
        const adapters = {
            ...createAdapters(undefined, {
                status: { state: "success", message: "Search completed." },
            }),
            openArtifact,
        };
        const user = userEvent.setup();
        render(
            createElement(renderer.SemanticCanvasRenderer, {
                spec,
                ...baseRevisionProps,
                adapters,
            }),
        );

        expect(screen.getByText("Search completed.")).toBeVisible();
        await user.click(screen.getByRole("button", { name: "Download CSV" }));
        expect(openArtifact).toHaveBeenCalledTimes(1);
        expect(await screen.findByText("CSV is ready.")).toBeVisible();

        const previewSpec = JSON.parse(
            JSON.stringify(spec),
        ) as CanvasSpecDocument;
        const previewAdapters = {
            ...createAdapters(),
            openArtifact: vi.fn(async () => ({
                state: "ready" as const,
                message: "Should not run.",
            })),
            getStatus: vi.fn(() => ({
                state: "success" as const,
                message: "Should not be read.",
            })),
        };
        const resolveForm = vi.spyOn(previewAdapters, "resolveFormBinding");
        const resolveStatus = vi.spyOn(previewAdapters, "resolveStatusBinding");
        const resolveArtifact = vi.spyOn(
            previewAdapters,
            "resolveArtifactBinding",
        );
        const previewView = render(
            createElement(renderer.SemanticCanvasRenderer, {
                spec: previewSpec,
                ...baseRevisionProps,
                preview: true,
                adapters: previewAdapters,
            }),
        );
        expect(
            within(previewView.container).getByRole("button", {
                name: "Download CSV",
            }),
        ).toBeDisabled();
        expect(previewAdapters.openArtifact).not.toHaveBeenCalled();
        expect(previewAdapters.getStatus).not.toHaveBeenCalled();
        expect(resolveForm).not.toHaveBeenCalled();
        expect(resolveStatus).not.toHaveBeenCalled();
        expect(resolveArtifact).not.toHaveBeenCalled();
        previewView.unmount();
    });

    it("treats table row and column data as own-property text", () => {
        const row = Object.create({ name: "inherited value" }) as Record<
            string,
            unknown
        >;
        row.status = '<script>alert("x")</script>';
        render(
            createElement(renderer.SemanticTable, {
                caption: "Records",
                columns: [
                    { key: "name", label: "Name" },
                    { key: "status", label: "Status" },
                ],
                rows: [row],
            }),
        );

        expect(screen.getByRole("cell", { name: "—" })).toBeVisible();
        expect(
            screen.getByRole("cell", {
                name: '<script>alert("x")</script>',
            }),
        ).toBeVisible();
        expect(document.querySelector("script")).toBeNull();
    });
});
