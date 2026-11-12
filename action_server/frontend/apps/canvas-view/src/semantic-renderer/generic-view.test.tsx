import {
    render,
    screen,
    fireEvent,
    waitFor,
    within,
} from "@testing-library/react";
import { expect, it, vi } from "vitest";
import type { App } from "@modelcontextprotocol/ext-apps/react";
import { GenericSemanticView } from "./generic-view";
import type { CanvasAppMetadata } from "./mcp-bridge";
import type { GenericExecutionContext } from "./generic-execution";
const id = "11111111-1111-4111-8111-111111111111";
const context = {
    token: "a".repeat(43),
    version: "actions.generic-app/v1",
    bindingIds: ["run"],
    scope: {
        application: {
            app_id: id,
            workspace_id: id,
            revision_id: `sha256:${"1".repeat(64)}`,
        },
        deployment: {
            deployment_id: id,
            workspace_id: id,
            revision_id: `sha256:${"2".repeat(64)}`,
        },
    },
} as GenericExecutionContext;
const canvas = {
    applicationId: id,
    revisionId: `sha256:${"2".repeat(64)}`,
    active: true,
    preview: false,
    scopeKey: "owned",
    bindings: [],
    spec: {
        schemaVersion: "actions.canvas-spec/v1",
        title: "Generic job",
        visibility: ["app", "model"],
        bindingIds: ["run"],
        root: {
            type: "form",
            id: "input",
            bindingId: "run",
            submitLabel: "Run job",
            fields: [
                { name: "value", label: "Value", type: "text", required: true },
            ],
        },
    },
} as CanvasAppMetadata;
it("semantic form explicitly submits and shows persistent Run status without mount execution", async () => {
    const call = vi.fn(async (req: { arguments: { action: string } }) => ({
        _meta: {
            "actions.execution": {
                bindingId: "run",
                runId: id,
                attemptId: id,
                state:
                    req.arguments.action === "submit" ? "ready" : "completed",
                cancelRequested: false,
            },
        },
    }));
    render(
        <GenericSemanticView
            app={{ callServerTool: call } as unknown as App}
            canvas={canvas}
            context={context}
        />,
    );
    expect(call).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Value"), {
        target: { value: "hello" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run job" }));
    await waitFor(() => expect(call).toHaveBeenCalledTimes(2));
    expect(
        (
            await screen.findByRole("button", { name: "Refresh status" })
        ).hasAttribute("disabled"),
    ).toBe(false);
    expect(
        screen.queryByRole("button", { name: "Request cancellation" }),
    ).toBeNull();
});

it.each(["failed", "running", "cancel_requested"])(
    "announces a response without claiming results for a %s Run",
    async (executionState) => {
        const call = vi.fn(async (req: { arguments: { action: string } }) => ({
            _meta: {
                "actions.execution": {
                    bindingId: "run",
                    runId: id,
                    attemptId: id,
                    state:
                        req.arguments.action === "submit"
                            ? "ready"
                            : executionState,
                    cancelRequested: executionState === "cancel_requested",
                },
            },
        }));
        render(
            <GenericSemanticView
                app={{ callServerTool: call } as unknown as App}
                canvas={canvas}
                context={context}
            />,
        );
        expect(call).not.toHaveBeenCalled();
        fireEvent.change(screen.getByLabelText("Value"), {
            target: { value: "hello" },
        });
        fireEvent.click(screen.getByRole("button", { name: "Run job" }));
        const form = screen.getByRole("region", {
            name: "Run job",
        });
        await waitFor(() =>
            expect(within(form).getByRole("status").textContent).toBe(
                "Run job: response received.",
            ),
        );
        expect(call).toHaveBeenCalledTimes(2);
        expect(screen.queryByText(/results ready/i)).toBeNull();
        const execution = screen.getByRole("region", { name: "Execution run" });
        expect(
            within(execution).getByRole(
                executionState === "failed" ? "alert" : "status",
            ).textContent,
        ).toBe(executionState.replaceAll("_", " "));
    },
);
