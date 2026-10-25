import type { App } from "@modelcontextprotocol/ext-apps/react";
import { z } from "zod";
import type { CanvasAppMetadata } from "./mcp-bridge";
import { createCapabilityRef } from "./types";
import type { SemanticRendererAdapters, SemanticFormInput } from "./types";

const binding = z.string().regex(/^[A-Za-z][A-Za-z0-9_-]{0,63}$/u);
const ref = z.object({
    workspace_id: z.string().uuid(),
    revision_id: z.string().regex(/^sha256:[0-9a-f]{64}$/u),
});
const session = z
    .object({
        token: z.string().regex(/^[A-Za-z0-9_-]{43}$/u),
        scope: z
            .object({
                application: ref.extend({ app_id: z.string().uuid() }).strict(),
                deployment: ref
                    .extend({ deployment_id: z.string().uuid() })
                    .strict(),
            })
            .strict(),
    })
    .strict();
const execution = z
    .object({
        bindingId: binding,
        runId: z.string().uuid(),
        attemptId: z.string().uuid(),
        state: z.enum([
            "ready",
            "completed",
            "failed",
            "cancel_requested",
            "reconciliation_required",
            "running",
            "expired",
        ]),
        cancelRequested: z.boolean(),
        workItemId: z.string().uuid().optional(),
        workItemEpoch: z.number().int().positive().optional(),
        outputs: z
            .array(
                z
                    .object({
                        handle: z.string().regex(/^art_[A-Za-z0-9_-]{22}$/u),
                    })
                    .strict(),
            )
            .max(64)
            .optional(),
    })
    .strict();
const inputQueue = z
    .object({
        workspace_id: z.string().uuid(),
        deployment: ref.extend({ deployment_id: z.string().uuid() }).strict(),
        queue_id: z.string().min(1).max(256),
    })
    .strict();
const sameDeployment = (
    a: z.infer<typeof inputQueue>["deployment"],
    b: z.infer<typeof inputQueue>["deployment"],
) =>
    a.workspace_id === b.workspace_id &&
    a.deployment_id === b.deployment_id &&
    a.revision_id === b.revision_id;
const sameQueue = (
    a: z.infer<typeof inputQueue>,
    b: z.infer<typeof inputQueue>,
) =>
    a.workspace_id === b.workspace_id &&
    a.queue_id === b.queue_id &&
    sameDeployment(a.deployment, b.deployment);
const inputBinding = z
    .object({
        bindingId: binding,
        queue: inputQueue,
        inputMode: z.enum(["required", "claim"]),
    })
    .strict();
const inputPage = z
    .object({
        bindingId: binding,
        queue: inputQueue,
        items: z
            .array(
                z
                    .object({
                        itemId: z.string().uuid(),
                        state: z.string(),
                        inputDigest: z.string().regex(/^sha256:[0-9a-f]{64}$/u),
                        preview: z.string().max(2048),
                        previewTruncated: z.boolean().default(false),
                        selectable: z.boolean(),
                    })
                    .strict(),
            )
            .max(20),
        nextCursor: z.string().uuid().nullable(),
    })
    .strict();
const outputBinding = z
    .object({ bindingId: binding, queue: inputQueue })
    .strict();
const outputPage = z
    .object({
        bindingId: binding,
        runId: z.string().uuid(),
        attemptId: z.string().uuid(),
        queue: inputQueue,
        items: z
            .array(
                z
                    .object({
                        itemId: z.string().uuid(),
                        parentId: z.string().uuid().nullable(),
                        queueState: z.enum([
                            "PENDING",
                            "IN_PROGRESS",
                            "COMPLETED",
                            "FAILED",
                        ]),
                        cancelRequested: z.boolean(),
                        preview: z.string().max(2048),
                        previewTruncated: z.boolean(),
                    })
                    .strict(),
            )
            .max(20),
        nextCursor: z.string().uuid().nullable(),
    })
    .strict();
const contextSchema = z
    .object({
        version: z.literal("actions.generic-app/v1"),
        bindingIds: z.array(binding).min(1).max(32),
        executions: z.array(execution).max(32).default([]),
        inputBindings: z.array(inputBinding).max(32).default([]),
        outputBindings: z.array(outputBinding).max(32).default([]),
    })
    .strict();
export type GenericExecutionState = z.infer<typeof execution>;
export function parseGenericExecution(
    meta: Record<string, unknown>,
    canvas: CanvasAppMetadata,
) {
    const scope = session.parse(meta["actions.appSession"]);
    const value = contextSchema.parse(meta["actions.genericExecution"]);
    if (
        !canvas.active ||
        new Set(value.outputBindings.map((item) => item.bindingId)).size !==
            value.outputBindings.length ||
        value.outputBindings.some(
            (item) =>
                !value.bindingIds.includes(item.bindingId) ||
                item.queue.workspace_id !==
                    scope.scope.deployment.workspace_id ||
                !sameDeployment(item.queue.deployment, scope.scope.deployment),
        ) ||
        new Set(value.inputBindings.map((item) => item.bindingId)).size !==
            value.inputBindings.length ||
        value.inputBindings.some(
            (item) =>
                !value.bindingIds.includes(item.bindingId) ||
                item.queue.workspace_id !==
                    scope.scope.deployment.workspace_id ||
                !sameDeployment(item.queue.deployment, scope.scope.deployment),
        ) ||
        scope.scope.deployment.deployment_id !== canvas.applicationId ||
        scope.scope.deployment.revision_id !== canvas.revisionId ||
        scope.scope.application.app_id !== canvas.applicationId ||
        scope.scope.application.workspace_id !==
            scope.scope.deployment.workspace_id ||
        new Set(value.bindingIds).size !== value.bindingIds.length ||
        new Set(value.executions.map((item) => item.bindingId)).size !==
            value.executions.length ||
        value.executions.some(
            (item) => !value.bindingIds.includes(item.bindingId),
        ) ||
        value.bindingIds.some(
            (id) =>
                !canvas.bindings.some(
                    (b) =>
                        b.bindingId === id &&
                        b.packageRevision.workspace_id ===
                            scope.scope.deployment.workspace_id,
                ),
        )
    )
        throw new Error("Generic View differs from active app scope.");
    return { ...scope, ...value };
}
export type GenericExecutionContext = ReturnType<typeof parseGenericExecution>;
export function createGenericExecutionAdapter(
    app: App,
    context: GenericExecutionContext,
    changed: () => void,
    inspect: (text: string, bindingId: string) => void,
) {
    const states = new Map<string, GenericExecutionState>(
        (context.executions ?? []).map((item) => [item.bindingId, item]),
    );
    const outputPages = new Map<string, z.infer<typeof outputPage>>();
    const inputPages = new Map<string, z.infer<typeof inputPage>>();
    const selectedInput = (id: string) =>
        (context.inputBindings ?? []).find((entry) => entry.bindingId === id);
    const pending = new Map<string, { key: string; input: string }>();
    const allowed = (id: string) => context.bindingIds.includes(id);
    const call = async (name: string, args: Record<string, unknown>) => {
        const reply = await app.callServerTool({
            name,
            arguments: { ...args, mode: "generic", appSession: context.token },
        });
        if (reply.isError)
            throw new Error(
                "App request denied or unavailable; inspect state before retrying.",
            );
        return reply._meta ?? {};
    };
    const accept = (
        id: string,
        meta: Record<string, unknown>,
        expectedRun?: string,
        expectedItem?: string,
    ) => {
        const result = execution.parse(meta["actions.execution"]);
        if (
            result.bindingId !== id ||
            (expectedItem !== undefined &&
                result.workItemId !== expectedItem) ||
            (expectedRun !== undefined && result.runId !== expectedRun)
        )
            throw new Error("App execution identity changed.");
        if (states.get(id)?.runId !== result.runId) outputPages.delete(id);
        states.set(id, result);
        if (result.state === "completed" || result.state === "failed")
            pending.delete(id);
        changed();
        return result;
    };
    const read = async (
        id: string,
        name: "canvas_execution_status" | "canvas_cancel",
    ) => {
        const current = states.get(id);
        if (!allowed(id) || !current)
            throw new Error("No retained execution selected.");
        return accept(
            id,
            await call(name, { bindingId: id, runId: current.runId }),
            current.runId,
        );
    };
    const adapters: SemanticRendererAdapters = {
        resolveFormBinding: (id) =>
            allowed(id) && !selectedInput(id)
                ? createCapabilityRef<string, SemanticFormInput, unknown>(id)
                : undefined,
        dispatch: async (capability, input) => {
            const id = capability.bindingId;
            if (!allowed(id)) throw new Error("Binding is unavailable.");
            const encoded = JSON.stringify(input);
            const prior = pending.get(id);
            if (prior && prior.input !== encoded)
                throw new Error(
                    "An uncertain submission exists; inspect it before changing input.",
                );
            const request = prior ?? {
                key: globalThis.crypto.randomUUID(),
                input: encoded,
            };
            pending.set(id, request);
            const admitted = accept(
                id,
                await call("canvas_dispatch", {
                    action: "submit",
                    bindingId: id,
                    inputs: input,
                    idempotencyKey: request.key,
                }),
            );
            const result =
                admitted.state === "ready"
                    ? accept(
                          id,
                          await call("canvas_dispatch", {
                              action: "execute",
                              bindingId: id,
                              runId: admitted.runId,
                          }),
                          admitted.runId,
                      )
                    : admitted;
            if (result.state === "completed" || result.state === "failed")
                pending.delete(id);
            return result;
        },
        resolveStatusBinding: (id) =>
            allowed(id) ? createCapabilityRef(id) : undefined,
        getStatus: (capability) => {
            const state = states.get(capability.bindingId);
            return {
                state:
                    state?.state === "completed"
                        ? "success"
                        : state?.state === "failed"
                          ? "error"
                          : state
                            ? "loading"
                            : "empty",
                message: state
                    ? `Execution ${state.state.replaceAll("_", " ")}.`
                    : "No execution submitted.",
            };
        },
        resolveArtifactBinding: (id) =>
            allowed(id) ? createCapabilityRef(id) : undefined,
        openArtifact: async (capability) => {
            const state = states.get(capability.bindingId);
            const handle = state?.outputs?.[0]?.handle;
            if (!state || !handle)
                return {
                    state: "unavailable",
                    message: "No authorized result artifact is available.",
                };
            const meta = await call("canvas_artifact", {
                bindingId: capability.bindingId,
                runId: state.runId,
                handle,
            });
            const artifact = z
                .object({
                    bindingId: binding,
                    runId: z.string().uuid(),
                    handle: z.string(),
                    text: z.string().max(65536),
                })
                .strict()
                .parse(meta["actions.artifact"]);
            if (
                artifact.bindingId !== capability.bindingId ||
                artifact.runId !== state.runId ||
                artifact.handle !== handle
            )
                throw new Error("Artifact identity differs.");
            inspect(artifact.text, capability.bindingId);
            return {
                state: "ready",
                message: "Authorized result inspected below.",
            };
        },
    };
    return {
        adapters,
        states,
        inputPages,
        outputPages,
        loadOutputs: async (id: string, cursor: string | null = null) => {
            const selected = (context.outputBindings ?? []).find(
                (entry) => entry.bindingId === id,
            );
            const current = states.get(id);
            if (!selected || current?.state !== "completed")
                throw new Error("No successful producing Run selected.");
            outputPages.delete(id);
            changed();
            const page = outputPage.parse(
                (
                    await call("canvas_get_state", {
                        action: "outputs",
                        bindingId: id,
                        runId: current.runId,
                        cursor,
                    })
                )["actions.execution"],
            );
            if (
                page.bindingId !== id ||
                page.runId !== current.runId ||
                page.attemptId !== current.attemptId ||
                !sameQueue(page.queue, selected.queue) ||
                states.get(id)?.runId !== current.runId ||
                states.get(id)?.attemptId !== current.attemptId
            )
                throw new Error("Producing Run identity changed.");
            outputPages.set(id, page);
            changed();
            return page;
        },
        loadInputs: async (id: string, cursor: string | null = null) => {
            const selected = selectedInput(id);
            if (!selected) throw new Error("No explicit input queue binding.");
            const page = inputPage.parse(
                (
                    await call("canvas_get_state", {
                        action: "inputs",
                        bindingId: id,
                        queue: selected.queue,
                        cursor,
                    })
                )["actions.execution"],
            );
            if (page.bindingId !== id || !sameQueue(page.queue, selected.queue))
                throw new Error("Input queue identity changed.");
            inputPages.set(id, page);
            changed();
            return page;
        },
        submitInput: async (id: string, itemId: string) => {
            const selected = selectedInput(id);
            if (
                !selected ||
                !inputPages
                    .get(id)
                    ?.items.some(
                        (item) => item.itemId === itemId && item.selectable,
                    )
            )
                throw new Error("Select an available exact input item.");
            const encoded = JSON.stringify({ queue: selected.queue, itemId });
            const prior = pending.get(id);
            if (prior && prior.input !== encoded)
                throw new Error(
                    "An uncertain input selection exists; inspect it before changing selection.",
                );
            const request = prior ?? {
                key: globalThis.crypto.randomUUID(),
                input: encoded,
            };
            pending.set(id, request);
            const result = accept(
                id,
                await call("canvas_dispatch", {
                    action: "submit_input",
                    bindingId: id,
                    queue: selected.queue,
                    itemId,
                    idempotencyKey: request.key,
                }),
                undefined,
                itemId,
            );
            if (result.workItemId !== itemId)
                throw new Error("Selected input identity changed.");
            inputPages.delete(id);
            if (result.state === "completed" || result.state === "failed")
                pending.delete(id);
            return result;
        },
        execute: async (id: string) => {
            const state = states.get(id);
            if (!allowed(id) || state?.state !== "ready")
                throw new Error("No unlaunched execution selected.");
            return accept(
                id,
                await call("canvas_dispatch", {
                    action: "execute",
                    bindingId: id,
                    runId: state.runId,
                }),
                state.runId,
            );
        },
        refresh: (id: string) => read(id, "canvas_execution_status"),
        cancel: (id: string) => read(id, "canvas_cancel"),
    };
}
