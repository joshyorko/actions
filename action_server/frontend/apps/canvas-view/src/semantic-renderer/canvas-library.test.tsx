import { act, cleanup, render, screen, within } from "@testing-library/react";
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
        useHostStyleVariables: vi.fn(),
        useApp: (options: { onAppCreated: (app: unknown) => void }) => {
            options.onAppCreated(app);
            return { app, isConnected: true, error: null };
        },
    };
});

import { McpCanvasView } from "../McpCanvasView";

afterEach(() => {
    cleanup();
    host.listeners.clear();
    host.callServerTool.mockClear();
});

const spec = (title: string, children: unknown[] = []) => ({
    schemaVersion: "actions.canvas-spec/v1",
    title,
    visibility: ["model", "app"],
    bindingIds: [],
    root: { type: "stack", id: "main", children },
});

const appId = "50000000-0000-4000-8000-000000000005";
const title = "Dakota pinned post2 generated word count";
const revisionId = `sha256:${"a".repeat(64)}`;
const activeCanvas = {
    applicationId: appId,
    revisionId,
    active: true,
    spec: spec(title, [
        {
            type: "text",
            id: "welcome",
            text: "Dakota pinned post2 generated word count is ready to compose.",
        },
        {
            type: "text",
            id: "guidance",
            text: "Describe the interface you want. Add a backend only when it needs one.",
        },
    ]),
    bindings: [],
};

// Actual canvas_open tool-result shape observed in the parent-owned host trace.
const authoringLibrary = {
    applications: [
        { activeRevisionId: revisionId, applicationId: appId, title },
    ],
};

// Separate read-only projection returned by CanvasLibraryDiscovery in source.
const emptyProjection = {
    apps: [],
    currentApp: null,
    empty: true,
    emptyMessage:
        "No apps are available to you yet. Create one with canvas_create.",
};

const firstProjectedApp = {
    appId: "app-1",
    title: "Invoice review",
    revisionId: "revision-1",
    summary: "Review the latest invoice results.",
    spec: spec("Invoice review"),
};
const secondProjectedApp = {
    appId: "app-2",
    title: "Open work",
    revisionId: "revision-2",
    summary: "Inspect available work items.",
    spec: spec("Open work"),
};
const populatedProjection = {
    apps: [firstProjectedApp, secondProjectedApp],
    currentApp: firstProjectedApp,
    empty: false,
    emptyMessage: null,
};

function emitToolResult(
    canvasMetadata: unknown,
    additionalMetadata: Record<string, unknown> = {},
) {
    const listener = host.listeners.get("toolresult");
    if (!listener)
        throw new Error("MCP toolresult listener was not installed.");
    act(() =>
        listener({
            isError: false,
            content: [
                {
                    type: "text",
                    text: "Your Action Canvas library is ready.",
                },
            ],
            _meta: { ...additionalMetadata, "actions.canvas": canvasMetadata },
        }),
    );
}

describe("read-only Canvas library tool-result view", () => {
    it.each([0, 200])(
        "renders a bounded authoring list of %i draft apps",
        (count) => {
            render(<McpCanvasView />);
            emitToolResult({
                applications: Array.from({ length: count }, (_, index) => ({
                    applicationId: `50000000-0000-4000-8000-${index.toString(16).padStart(12, "0")}`,
                    title: `App ${index}`,
                    activeRevisionId: null,
                })),
            });
            expect(
                screen.getByRole("heading", { name: "Action Canvas library" }),
            ).toBeVisible();
            expect(screen.queryAllByRole("listitem")).toHaveLength(count);
            expect(screen.queryByRole("alert")).toBeNull();
            expect(host.callServerTool).not.toHaveBeenCalled();
        },
    );

    it("rejects an authoring list above the producer's 200-app limit", () => {
        render(<McpCanvasView />);
        emitToolResult({
            applications: Array.from({ length: 201 }, (_, index) => ({
                applicationId: `50000000-0000-4000-8000-${index.toString(16).padStart(12, "0")}`,
                title: `App ${index}`,
                activeRevisionId: null,
            })),
        });
        expect(screen.getByRole("alert")).toBeVisible();
        expect(host.callServerTool).not.toHaveBeenCalled();
    });

    it("renders canvas_get before the following canvas_open application list", () => {
        render(<McpCanvasView />);

        emitToolResult(activeCanvas);
        expect(screen.getByRole("heading", { name: title })).toBeVisible();
        expect(
            screen.getByText(
                "Dakota pinned post2 generated word count is ready to compose.",
            ),
        ).toBeVisible();
        expect(screen.queryByRole("alert")).toBeNull();

        emitToolResult(authoringLibrary);

        expect(
            screen.getByRole("heading", { name: "Action Canvas library" }),
        ).toBeVisible();
        expect(screen.getByText(title, { exact: true })).toBeVisible();
        expect(screen.queryByRole("alert")).toBeNull();
        expect(screen.queryByRole("heading", { name: title })).toBeNull();
        expect(screen.queryByRole("button")).toBeNull();
        expect(screen.queryByRole("link")).toBeNull();
        expect(host.callServerTool).not.toHaveBeenCalled();
    });

    it("renders the source empty-library projection without controls", () => {
        render(<McpCanvasView />);

        emitToolResult(emptyProjection);

        expect(
            screen.getByRole("heading", { name: "Action Canvas library" }),
        ).toBeVisible();
        expect(
            screen.getByText(emptyProjection.emptyMessage, { exact: true }),
        ).toBeVisible();
        expect(screen.queryByRole("alert")).toBeNull();
        expect(screen.queryByRole("button")).toBeNull();
        expect(screen.queryByRole("link")).toBeNull();
        expect(host.callServerTool).not.toHaveBeenCalled();
    });

    it("lists projected apps and marks current selection without actions", () => {
        render(<McpCanvasView />);

        emitToolResult(populatedProjection);

        expect(
            screen.getByRole("heading", { name: "Action Canvas library" }),
        ).toBeVisible();
        expect(
            screen.getByText("Invoice review", { exact: true }),
        ).toBeVisible();
        expect(
            screen.getByText("Review the latest invoice results.", {
                exact: true,
            }),
        ).toBeVisible();
        expect(screen.getByText("Open work", { exact: true })).toBeVisible();
        expect(
            screen.getByText("Inspect available work items.", {
                exact: true,
            }),
        ).toBeVisible();
        expect(
            within(screen.getByRole("list")).getByText("Current", {
                exact: true,
            }),
        ).toBeVisible();
        expect(screen.queryByRole("button")).toBeNull();
        expect(screen.queryByRole("link")).toBeNull();
        expect(host.callServerTool).not.toHaveBeenCalled();
    });

    it("accepts a later listed app as the current selection", () => {
        render(<McpCanvasView />);

        emitToolResult({
            ...populatedProjection,
            currentApp: secondProjectedApp,
        });

        expect(
            screen.getByRole("heading", { name: "Action Canvas library" }),
        ).toBeVisible();
        expect(
            within(screen.getByRole("list")).getByText("Current", {
                exact: true,
            }),
        ).toBeVisible();
        expect(host.callServerTool).not.toHaveBeenCalled();
    });

    it.each([
        ["unknown authoring-list field", { ...authoringLibrary, extra: true }],
        [
            "duplicate authoring-list identity",
            {
                applications: [
                    ...authoringLibrary.applications,
                    authoringLibrary.applications[0],
                ],
            },
        ],
        ["unknown projection field", { ...emptyProjection, extra: true }],
        [
            "malformed projected CanvasSpec",
            {
                ...populatedProjection,
                apps: [
                    {
                        ...firstProjectedApp,
                        spec: {
                            ...spec("Invoice review"),
                            schemaVersion: "actions.canvas-spec/v99",
                        },
                    },
                ],
                currentApp: {
                    ...firstProjectedApp,
                    spec: {
                        ...spec("Invoice review"),
                        schemaVersion: "actions.canvas-spec/v99",
                    },
                },
            },
        ],
        [
            "current projection outside the list",
            {
                ...populatedProjection,
                currentApp: { ...secondProjectedApp, appId: "outside-list" },
            },
        ],
        [
            "duplicate projected app identity",
            {
                ...populatedProjection,
                apps: [
                    firstProjectedApp,
                    { ...secondProjectedApp, appId: firstProjectedApp.appId },
                ],
            },
        ],
        [
            "empty flag inconsistent with entries",
            { ...populatedProjection, apps: [], currentApp: null },
        ],
        [
            "empty message inconsistent with entries",
            { ...emptyProjection, emptyMessage: null },
        ],
    ])("rejects %s", (_case, metadata) => {
        render(<McpCanvasView />);

        emitToolResult(metadata);

        expect(screen.getByRole("alert")).toBeVisible();
        expect(
            screen.queryByRole("heading", { name: "Action Canvas library" }),
        ).toBeNull();
        expect(host.callServerTool).not.toHaveBeenCalled();
    });

    it.each([
        "actions.genericExecution",
        "actions.appSession",
        "actions.reviewedExecution",
    ])("rejects a library carrying app execution metadata %s", (key) => {
        render(<McpCanvasView />);

        emitToolResult(authoringLibrary, { [key]: {} });

        expect(screen.getByRole("alert")).toBeVisible();
        expect(host.callServerTool).not.toHaveBeenCalled();
    });

    it("preserves strict app parsing and clears app state across list transitions", () => {
        render(<McpCanvasView />);

        emitToolResult(activeCanvas);
        expect(screen.getByRole("heading", { name: title })).toBeVisible();

        emitToolResult(authoringLibrary);
        expect(
            screen.getByRole("heading", { name: "Action Canvas library" }),
        ).toBeVisible();
        expect(screen.queryByRole("heading", { name: title })).toBeNull();

        emitToolResult({ ...activeCanvas, extra: true });
        expect(screen.getByRole("alert")).toBeVisible();
        expect(
            screen.queryByRole("heading", { name: "Action Canvas library" }),
        ).toBeNull();
        expect(host.callServerTool).not.toHaveBeenCalled();
    });
});
