import { expect, it, vi } from "vitest";
import type { App } from "@modelcontextprotocol/ext-apps/react";
import {
    createGenericExecutionAdapter,
    type GenericExecutionContext,
} from "./generic-execution";
const first = "11111111-1111-4111-8111-111111111111";
const second = "22222222-2222-4222-8222-222222222222";
const handle = `art_${"A".repeat(22)}`;
const state = (runId = first, status = "completed") => ({
    bindingId: "run",
    runId,
    attemptId: runId,
    state: status,
    cancelRequested: false,
    outputs: [{ handle }],
});
const context = {
    token: "a".repeat(43),
    bindingIds: ["run"],
    executions: [state()],
} as GenericExecutionContext;
const artifact = {
    _meta: {
        "actions.artifact": {
            bindingId: "run",
            runId: first,
            handle,
            text: '{"count":3,"text":"gamma delta epsilon"}',
        },
    },
};
for (const projection of [false, true]) {
    it(`clears inspected success immediately on new failed submission (projection=${projection})`, async () => {
        let complete!: (value: unknown) => void;
        const pending = new Promise((resolve) => {
            complete = resolve;
        });
        const call = vi.fn(async ({ name }: { name: string }) =>
            name === "canvas_artifact" ? artifact : pending,
        );
        const c = createGenericExecutionAdapter(
            { callServerTool: call } as unknown as App,
            context,
            vi.fn(),
            vi.fn(),
            projection,
        );
        await c.adapters.openArtifact!(
            c.adapters.resolveArtifactBinding!("run")!,
        );
        expect(c.inspectedArtifacts.get("run")).toContain('"count":3');
        const submitted = c.adapters.dispatch(
            c.adapters.resolveFormBinding("run")!,
            {},
        );
        expect(c.inspectedArtifacts.has("run")).toBe(false);
        expect(
            await c.adapters.openArtifact!(
                c.adapters.resolveArtifactBinding!("run")!,
            ),
        ).toMatchObject({ state: "unavailable" });
        complete({ _meta: { "actions.execution": state(second, "failed") } });
        await submitted;
        expect(c.inspectedArtifacts.has("run")).toBe(false);
    });
    it(`rejects late old artifact after failed newer execution (projection=${projection})`, async () => {
        let complete!: (value: unknown) => void;
        const delayed = new Promise((resolve) => {
            complete = resolve;
        });
        const inspect = vi.fn();
        const call = vi.fn(async ({ name }: { name: string }) =>
            name === "canvas_artifact"
                ? delayed
                : { _meta: { "actions.execution": state(second, "failed") } },
        );
        const c = createGenericExecutionAdapter(
            { callServerTool: call } as unknown as App,
            context,
            vi.fn(),
            inspect,
            projection,
        );
        const old = c.adapters.openArtifact!(
            c.adapters.resolveArtifactBinding!("run")!,
        );
        const rejected = expect(old).rejects.toThrow();
        await c.adapters.dispatch(c.adapters.resolveFormBinding("run")!, {});
        complete(artifact);
        await rejected;
        expect(inspect).not.toHaveBeenCalled();
        expect(c.inspectedArtifacts.has("run")).toBe(false);
    });
}
it("invalidates only the binding whose execution changed", async () => {
    const call = vi.fn(
        async ({
            name,
            arguments: args,
        }: {
            name: string;
            arguments: Record<string, unknown>;
        }) =>
            name === "canvas_artifact"
                ? {
                      _meta: {
                          "actions.artifact": {
                              ...artifact._meta["actions.artifact"],
                              bindingId: args.bindingId,
                          },
                      },
                  }
                : { _meta: { "actions.execution": state(second, "failed") } },
    );
    const c = createGenericExecutionAdapter(
        { callServerTool: call } as unknown as App,
        {
            ...context,
            bindingIds: ["run", "other"],
            executions: [state(), { ...state(), bindingId: "other" }],
        } as GenericExecutionContext,
        vi.fn(),
        vi.fn(),
    );
    for (const id of ["run", "other"])
        await c.adapters.openArtifact(c.adapters.resolveArtifactBinding(id)!);
    const otherKey = c.adapters.artifactScopeKey!("other");
    await c.adapters.dispatch(c.adapters.resolveFormBinding("run")!, {});
    expect(c.inspectedArtifacts.has("run")).toBe(false);
    expect(c.inspectedArtifacts.get("other")).toContain('"count":3');
    expect(c.adapters.artifactScopeKey!("other")).toBe(otherKey);
});
it("preserves authorized diagnostic artifact inspection on the current failed Run", async () => {
    const inspect = vi.fn();
    const c = createGenericExecutionAdapter(
        { callServerTool: vi.fn(async () => artifact) } as unknown as App,
        {
            ...context,
            executions: [state(first, "failed")],
        } as GenericExecutionContext,
        vi.fn(),
        inspect,
    );
    expect(
        await c.adapters.openArtifact(
            c.adapters.resolveArtifactBinding("run")!,
        ),
    ).toMatchObject({ state: "ready" });
    expect(inspect).toHaveBeenCalledWith(
        artifact._meta["actions.artifact"].text,
        "run",
    );
});
