import { render, screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { SemanticCanvasRenderer } from "./components";
import { parseCanvasSpec } from "./mcp-bridge";
import fixture from "../../../../../../docs/contracts/canvas/fixtures/semantic-v2.fixture.json";

const adapters = {
    resolveFormBinding: vi.fn(),
    dispatch: vi.fn(),
    resolveStatusBinding: vi.fn(),
    getStatus: vi.fn(),
    resolveArtifactBinding: vi.fn(),
    openArtifact: vi.fn(),
};

it("composes a v2 card with existing nodes without invoking adapters", () => {
    const spec = parseCanvasSpec({
        schemaVersion: "actions.canvas-spec/v2",
        title: "Operations overview",
        visibility: ["app"],
        bindingIds: [],
        root: {
            type: "card",
            id: "overview",
            title: "Queue summary",
            children: [
                {
                    type: "text",
                    id: "description",
                    text: "No automatic work is performed.",
                },
                {
                    type: "stack",
                    id: "details",
                    children: [
                        {
                            type: "card",
                            id: "nested",
                            title: "Details",
                            children: [],
                        },
                    ],
                },
            ],
        },
    });
    render(
        <SemanticCanvasRenderer
            spec={spec}
            revision="test"
            scopeKey="owned:v2"
            viewer="app"
            preview={false}
            adapters={adapters}
        />,
    );
    const card = screen.getByRole("region", { name: "Queue summary" });
    expect(
        within(card).getByRole("heading", { name: "Queue summary" }),
    ).toBeTruthy();
    expect(
        within(card).getByText("No automatic work is performed."),
    ).toBeTruthy();
    expect(within(card).getByRole("region", { name: "Details" })).toBeTruthy();
    for (const adapter of Object.values(adapters))
        expect(adapter).not.toHaveBeenCalled();
});

it("keeps admitted data nodes visible with an explicit unavailable state before the host projection join", () => {
    const spec = parseCanvasSpec(fixture);
    render(
        <SemanticCanvasRenderer
            spec={spec}
            revision="test"
            scopeKey="owned:v2"
            viewer="app"
            preview={false}
            adapters={adapters}
        />,
    );
    expect(
        screen.getAllByRole("alert").map((element) => element.textContent),
    ).toEqual([
        "Result data is unavailable.",
        "Result data is unavailable.",
        "Result data is unavailable.",
    ]);
    for (const adapter of Object.values(adapters))
        expect(adapter).not.toHaveBeenCalled();
});
