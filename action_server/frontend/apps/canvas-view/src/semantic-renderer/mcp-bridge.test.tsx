import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";

const host = vi.hoisted(() => ({
    listeners: new Map<string, (event: unknown) => void>(),
    callServerTool: vi.fn(),
}));

vi.mock("@modelcontextprotocol/ext-apps/react", () => {
    const app = {
        addEventListener: (name: string, listener: (event: unknown) => void) =>
            host.listeners.set(name, listener),
        getHostContext: () => ({ theme: "dark", locale: "en-US" }),
        callServerTool: host.callServerTool,
    };

    return {
        useApp: (options: { onAppCreated: (app: unknown) => void }) => {
            options.onAppCreated(app);
            return { app, isConnected: true, error: null };
        },
    };
});

import { McpCanvasView } from "../McpCanvasView";
import { parseCanvasViewMetadata } from "./mcp-bridge";

afterEach(() => {
    cleanup();
    host.listeners.clear();
    host.callServerTool.mockClear();
});

const spec = {
    schemaVersion: "actions.canvas-spec/v1",
    title: "Foundry app",
    visibility: ["app"],
    bindingIds: ["search"],
    root: {
        type: "stack",
        id: "main",
        children: [
            { type: "text", id: "intro", text: "Read-only app content." },
            {
                type: "form",
                id: "search-form",
                bindingId: "search",
                submitLabel: "Search",
                fields: [
                    {
                        name: "query",
                        label: "Search records",
                        type: "text",
                        required: true,
                    },
                ],
            },
            { type: "status", id: "search-status", bindingId: "search" },
        ],
    },
};

const activeCanvas = {
    applicationId: "50000000-0000-4000-8000-000000000005",
    revisionId: `sha256:${"a".repeat(64)}`,
    active: true,
    spec,
    bindings: [
        {
            bindingId: "search",
            capabilityId: "60000000-0000-4000-8000-000000000006",
            packageRevision: {
                workspace_id: "30000000-0000-4000-8000-000000000003",
                package_id: "40000000-0000-4000-8000-000000000004",
                revision_id: `sha256:${"b".repeat(64)}`,
            },
        },
    ],
};

function emitToolResult(metadata: unknown) {
    emitHostResult({
        isError: false,
        structuredContent: {
            applicationId: "model-visible summary only",
        },
        _meta: { "actions.canvas": metadata },
    });
}

function emitHostResult(result: unknown) {
    const listener = host.listeners.get("toolresult");
    if (!listener)
        throw new Error("MCP toolresult listener was not installed.");
    act(() => listener(result));
}

function emitToolInput(argumentsValue: unknown) {
    const listener = host.listeners.get("toolinput");
    if (!listener) throw new Error("MCP toolinput listener was not installed.");
    act(() => listener({ arguments: argumentsValue }));
}

describe("official MCP Canvas bridge", () => {
    it("renders semantic state from tool-result metadata and stays read-only", () => {
        render(<McpCanvasView />);

        emitToolResult(activeCanvas);

        expect(
            screen.getByRole("heading", { name: "Foundry app" }),
        ).toBeVisible();
        expect(screen.getByText("Read-only app content.")).toBeVisible();
        expect(
            screen.getByText("Revision sha256:" + "a".repeat(64)),
        ).toBeVisible();
        expect(screen.getByText("This action is unavailable.")).toBeVisible();
        expect(screen.queryByRole("button", { name: "Search" })).toBeNull();
        expect(screen.getByTestId("mcp-host-theme")).toHaveTextContent("dark");
        expect(host.callServerTool).not.toHaveBeenCalled();
    });

    it("renders a preview reply without enabling its form", () => {
        render(<McpCanvasView />);

        emitToolResult({ spec, preview: true });

        expect(
            screen.getByRole("heading", { name: "Foundry app" }),
        ).toBeVisible();
        expect(screen.getByText("Preview", { exact: true })).toBeVisible();
        expect(screen.getByRole("button", { name: "Search" })).toBeDisabled();
        expect(
            screen.getByText("Status is available in the active view."),
        ).toBeVisible();
        expect(host.callServerTool).not.toHaveBeenCalled();
    });

    it("remounts view state when the immutable app revision changes", () => {
        render(<McpCanvasView />);

        emitToolResult(activeCanvas);
        expect(screen.getByText("Read-only app content.")).toBeVisible();

        emitToolResult({
            ...activeCanvas,
            revisionId: `sha256:${"c".repeat(64)}`,
            spec: {
                ...spec,
                title: "Revised app",
                root: {
                    type: "text",
                    id: "revised-content",
                    text: "Content from the new revision.",
                },
            },
            bindings: [
                {
                    ...activeCanvas.bindings[0],
                },
            ],
        });

        expect(
            screen.getByRole("heading", { name: "Revised app" }),
        ).toBeVisible();
        expect(
            screen.getByText("Content from the new revision."),
        ).toBeVisible();
        expect(screen.queryByText("Read-only app content.")).toBeNull();
    });

    it("respects the app audience projection without exposing hidden details", () => {
        render(<McpCanvasView />);

        emitToolResult({
            ...activeCanvas,
            spec: { ...spec, visibility: ["model"] },
        });

        expect(screen.getByText("This view is unavailable.")).toBeVisible();
        expect(
            screen.queryByRole("heading", { name: "Foundry app" }),
        ).toBeNull();
        expect(
            screen.queryByText(
                "This app is displayed read-only; interactive actions are disabled.",
            ),
        ).toBeNull();
    });

    it("preserves the query fixture adapter and explicit query submission", async () => {
        const user = userEvent.setup();
        host.callServerTool.mockResolvedValue({
            isError: false,
            structuredContent: { rows: [], artifact: null, error: null },
        });
        render(<McpCanvasView />);

        emitToolInput({ query: "alpha" });
        expect(
            screen.getByRole("textbox", { name: "Search records" }),
        ).toHaveValue("alpha");
        await user.click(screen.getByRole("button", { name: "Search" }));

        expect(host.callServerTool).toHaveBeenCalledWith({
            name: "canvas_fixture_search",
            arguments: { query: "alpha" },
        });
    });

    it("preserves invoice metadata rendering without querying on open", () => {
        render(<McpCanvasView />);

        emitHostResult({
            isError: false,
            _meta: {
                "actions.invoicePage": {
                    schemaVersion: "actions.invoice-page/v1",
                    rows: [],
                    artifact: { handle: "art_AAAAAAAAAAAAAAAAAAAAAA" },
                    error: null,
                    offset: 0,
                    nextOffset: null,
                },
            },
        });

        expect(
            screen.getByRole("heading", { name: "Invoice results" }),
        ).toBeVisible();
        expect(screen.queryByRole("textbox")).toBeNull();
        expect(host.callServerTool).not.toHaveBeenCalled();
    });

    it("rejects malformed schema and binding scope before rendering", () => {
        expect(() =>
            parseCanvasViewMetadata({
                ...activeCanvas,
                bindings: [],
            }),
        ).toThrow(/binding scope/i);

        const injectedNode = JSON.parse(
            '{"type":"text","id":"safe","text":"Visible","__proto__":{"polluted":true}}',
        ) as unknown;
        expect(() =>
            parseCanvasViewMetadata({
                ...activeCanvas,
                spec: { ...spec, bindingIds: [], root: injectedNode },
                bindings: [],
            }),
        ).toThrow();
        expect(Object.prototype).not.toHaveProperty("polluted");
    });
});
