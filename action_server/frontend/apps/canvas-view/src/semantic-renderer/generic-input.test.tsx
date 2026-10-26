import { expect, it, vi } from "vitest";
import type { App } from "@modelcontextprotocol/ext-apps/react";
import {
    createGenericExecutionAdapter,
    type GenericExecutionContext,
} from "./generic-execution";
const id = "11111111-1111-4111-8111-111111111111";
const revision = `sha256:${"1".repeat(64)}`;
const queue = {
    workspace_id: id,
    deployment: { workspace_id: id, deployment_id: id, revision_id: revision },
    queue_id: "selected",
};
const context = {
    token: "a".repeat(43),
    version: "actions.generic-app/v1",
    bindingIds: ["run"],
    inputBindings: [{ bindingId: "run", queue, inputMode: "claim" }],
    executions: [],
    outputBindings: [],
    scope: {
        application: { app_id: id, workspace_id: id, revision_id: revision },
        deployment: queue.deployment,
    },
} as GenericExecutionContext;
it("lists then claims exact selected input without autoexecution or payload replacement", async () => {
    const call = vi.fn(
        async (request: {
            name: string;
            arguments: Record<string, unknown>;
        }) => {
            expect(request.arguments.queue).toEqual(queue);
            expect(request.arguments.inputs).toBeUndefined();
            expect(request.arguments.owner_id).toBeUndefined();
            if (request.name === "canvas_get_state")
                return {
                    _meta: {
                        "actions.execution": {
                            bindingId: "run",
                            queue,
                            items: [
                                {
                                    itemId: id,
                                    state: "PENDING",
                                    inputDigest: revision,
                                    preview: '{"value":"input"}',
                                    selectable: true,
                                },
                            ],
                            nextCursor: null,
                        },
                    },
                };
            return {
                _meta: {
                    "actions.execution": {
                        bindingId: "run",
                        runId: id,
                        attemptId: id,
                        state: "ready",
                        cancelRequested: false,
                        workItemId: id,
                        workItemEpoch: 1,
                    },
                },
            };
        },
    );
    const controller = createGenericExecutionAdapter(
        { callServerTool: call } as unknown as App,
        context,
        vi.fn(),
        vi.fn(),
    );
    expect(call).not.toHaveBeenCalled();
    expect(controller.adapters.resolveFormBinding("run")).toBeUndefined();
    await controller.loadInputs("run");
    await controller.submitInput("run", id);
    expect(call.mock.calls.map(([r]) => r.arguments.action)).toEqual([
        "inputs",
        "submit_input",
    ]);
    expect(controller.states.get("run")?.state).toBe("ready");
});

it("retains uncertain selection identity and rejects changed item or response", async () => {
    const other = "22222222-2222-4222-8222-222222222222";
    const requests: Record<string, unknown>[] = [];
    const call = vi.fn(
        async (request: {
            name: string;
            arguments: Record<string, unknown>;
        }) => {
            requests.push(request.arguments);
            if (request.name === "canvas_get_state")
                return {
                    _meta: {
                        "actions.execution": {
                            bindingId: "run",
                            queue,
                            items: [id, other].map((itemId) => ({
                                itemId,
                                state: "PENDING",
                                inputDigest: revision,
                                preview: "{}",
                                selectable: true,
                            })),
                            nextCursor: null,
                        },
                    },
                };
            throw new Error("lost receipt");
        },
    );
    const controller = createGenericExecutionAdapter(
        { callServerTool: call } as unknown as App,
        context,
        vi.fn(),
        vi.fn(),
    );
    await controller.loadInputs("run");
    await expect(controller.submitInput("run", id)).rejects.toThrow("lost");
    await expect(controller.submitInput("run", other)).rejects.toThrow(
        "uncertain",
    );
    await expect(controller.submitInput("run", id)).rejects.toThrow("lost");
    expect(requests[1].idempotencyKey).toBe(requests[2].idempotencyKey);
    expect(controller.states.size).toBe(0);
});

it("rejects a selected-item response before accepting its Run", async () => {
    const call = vi.fn(async (request: { name: string }) =>
        request.name === "canvas_get_state"
            ? {
                  _meta: {
                      "actions.execution": {
                          bindingId: "run",
                          queue,
                          items: [
                              {
                                  itemId: id,
                                  state: "PENDING",
                                  inputDigest: revision,
                                  preview: "{}",
                                  selectable: true,
                              },
                          ],
                          nextCursor: null,
                      },
                  },
              }
            : {
                  _meta: {
                      "actions.execution": {
                          bindingId: "run",
                          runId: id,
                          attemptId: id,
                          state: "ready",
                          cancelRequested: false,
                          workItemId: "22222222-2222-4222-8222-222222222222",
                          workItemEpoch: 1,
                      },
                  },
              },
    );
    const controller = createGenericExecutionAdapter(
        { callServerTool: call } as unknown as App,
        context,
        vi.fn(),
        vi.fn(),
    );
    await controller.loadInputs("run");
    await expect(controller.submitInput("run", id)).rejects.toThrow("identity");
    expect(controller.states.size).toBe(0);
});

it("renders explicit queue selection and claim controls with no launch", async () => {
    const { render, screen, fireEvent, waitFor } =
        await import("@testing-library/react");
    const { GenericInputForm } = await import("./generic-input-form");
    const call = vi.fn(async (request: { name: string }) =>
        request.name === "canvas_get_state"
            ? {
                  _meta: {
                      "actions.execution": {
                          bindingId: "run",
                          queue,
                          items: [
                              {
                                  itemId: id,
                                  state: "PENDING",
                                  inputDigest: revision,
                                  preview: '{"value":"saved"}',
                                  selectable: true,
                              },
                          ],
                          nextCursor: null,
                      },
                  },
              }
            : {
                  _meta: {
                      "actions.execution": {
                          bindingId: "run",
                          runId: id,
                          attemptId: id,
                          state: "ready",
                          cancelRequested: false,
                          workItemId: id,
                          workItemEpoch: 1,
                      },
                  },
              },
    );
    const controller = createGenericExecutionAdapter(
        { callServerTool: call } as unknown as App,
        context,
        vi.fn(),
        vi.fn(),
    );
    const view = render(
        <GenericInputForm
            binding={context.inputBindings[0]}
            controller={controller}
        />,
    );
    expect(call).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Load inputs" }));
    await waitFor(() =>
        expect(controller.inputPages.get("run")?.items).toHaveLength(1),
    );
    view.rerender(
        <GenericInputForm
            binding={context.inputBindings[0]}
            controller={controller}
        />,
    );
    fireEvent.change(screen.getByLabelText("Input item for run"), {
        target: { value: id },
    });
    fireEvent.click(
        screen.getByRole("button", { name: "Claim selected input" }),
    );
    await waitFor(() =>
        expect(controller.states.get("run")?.state).toBe("ready"),
    );
    await waitFor(() => {
        expect(controller.inputPages.has("run")).toBe(false);
        expect(
            (
                screen.getByLabelText("Input item for run") as unknown as {
                    value: string;
                }
            ).value,
        ).toBe("");
        expect(
            (
                screen.getByRole("button", {
                    name: "Claim selected input",
                }) as HTMLButtonElement
            ).disabled,
        ).toBe(true);
    });
    expect(screen.queryByText(`${id} — PENDING`)).toBeNull();
    expect(call).toHaveBeenCalledTimes(2);
    expect(screen.getByText(/Choose Continue execution/u)).toBeTruthy();
});

it.each(["execute", "refresh"] as const)(
    "allows a second explicit selected item after terminal %s",
    async (method) => {
        const second = "22222222-2222-4222-8222-222222222222";
        let selected = id;
        const call = vi.fn(
            async (request: {
                name: string;
                arguments: Record<string, unknown>;
            }) => {
                if (request.name === "canvas_get_state")
                    return {
                        _meta: {
                            "actions.execution": {
                                bindingId: "run",
                                queue,
                                items: [id, second].map((itemId) => ({
                                    itemId,
                                    state: "PENDING",
                                    inputDigest: revision,
                                    preview: "😀".repeat(511),
                                    previewTruncated: true,
                                    selectable: true,
                                })),
                                nextCursor: null,
                            },
                        },
                    };
                const claiming = request.arguments.action === "submit_input";
                if (claiming) selected = String(request.arguments.itemId);
                return {
                    _meta: {
                        "actions.execution": {
                            bindingId: "run",
                            runId: selected,
                            attemptId: selected,
                            state: claiming ? "ready" : "completed",
                            cancelRequested: false,
                            workItemId: selected,
                            workItemEpoch: 1,
                        },
                    },
                };
            },
        );
        const controller = createGenericExecutionAdapter(
            { callServerTool: call } as unknown as App,
            context,
            vi.fn(),
            vi.fn(),
        );
        await controller.loadInputs("run");
        expect(
            controller.inputPages.get("run")?.items[0].previewTruncated,
        ).toBe(true);
        await controller.submitInput("run", id);
        expect(controller.inputPages.has("run")).toBe(false);
        await controller[method]("run");
        await controller.loadInputs("run");
        await controller.submitInput("run", second);
        expect(controller.states.get("run")?.workItemId).toBe(second);
    },
);
