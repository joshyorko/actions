import type {
    CanvasNode,
    CanvasNodeV1,
    CanvasSpecDocument,
    SemanticFieldType,
    SemanticRendererAdapters,
} from "./types";

const CANVAS_SPEC_VERSION = "actions.canvas-spec/v1";
const CANVAS_SPEC_VERSION_V2 = "actions.canvas-spec/v2";
const MAX_SPEC_BYTES = 64 * 1024;
const IDENTIFIER_PATTERN = /^[A-Za-z][A-Za-z0-9_-]{0,63}$/u;
const UUID_PATTERN =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/u;
const DIGEST_PATTERN = /^sha256:[0-9a-f]{64}$/u;

export interface CanvasBindingScope {
    bindingId: string;
    capabilityId: string;
    packageRevision: {
        workspace_id: string;
        package_id: string;
        revision_id: string;
    };
}

export interface CanvasAppMetadata {
    applicationId: string;
    revisionId: string;
    active: boolean;
    spec: CanvasSpecDocument;
    bindings: readonly CanvasBindingScope[];
    preview: false;
    scopeKey: string;
}

export interface CanvasPreviewMetadata {
    spec: CanvasSpecDocument;
    preview: true;
    revision: "preview";
    scopeKey: string;
}

export type CanvasViewMetadata = CanvasAppMetadata | CanvasPreviewMetadata;

function isPlainRecord(value: unknown): value is Record<string, unknown> {
    if (typeof value !== "object" || value === null || Array.isArray(value)) {
        return false;
    }
    const prototype = Object.getPrototypeOf(value);
    return (
        (prototype === Object.prototype || prototype === null) &&
        Reflect.ownKeys(value).every((key) => {
            const descriptor = Object.getOwnPropertyDescriptor(value, key);
            return (
                typeof key === "string" &&
                descriptor !== undefined &&
                "value" in descriptor &&
                descriptor.enumerable
            );
        })
    );
}

function isPlainArray(value: unknown): value is unknown[] {
    if (
        !Array.isArray(value) ||
        Object.getPrototypeOf(value) !== Array.prototype
    )
        return false;
    const keys = Reflect.ownKeys(value);
    return (
        keys.length === value.length + 1 &&
        keys.every((key) => {
            if (key === "length") return true;
            if (
                typeof key !== "string" ||
                !/^(0|[1-9][0-9]*)$/u.test(key) ||
                Number(key) >= value.length
            )
                return false;
            const descriptor = Object.getOwnPropertyDescriptor(value, key);
            return (
                descriptor !== undefined &&
                "value" in descriptor &&
                descriptor.enumerable
            );
        })
    );
}

function hasOwn(value: object, key: PropertyKey): boolean {
    return Object.prototype.hasOwnProperty.call(value, key);
}

function hasExactKeys(value: Record<string, unknown>, keys: readonly string[]) {
    const actualKeys = Reflect.ownKeys(value);
    return (
        actualKeys.length === keys.length &&
        actualKeys.every(
            (key) => typeof key === "string" && keys.includes(key),
        ) &&
        keys.every((key) => hasOwn(value, key))
    );
}

function codePointLength(value: string): number {
    return Array.from(value).length;
}

function isBoundedText(
    value: unknown,
    minimum: number,
    maximum: number,
): value is string {
    if (typeof value !== "string") return false;
    const length = codePointLength(value);
    return (
        length >= minimum &&
        length <= maximum &&
        Array.from(value).every((character) => {
            const point = character.codePointAt(0)!;
            return point < 0xd800 || point > 0xdfff;
        })
    );
}

function isIdentifier(value: unknown): value is string {
    return typeof value === "string" && IDENTIFIER_PATTERN.test(value);
}

function isPackageLocalIdentifier(value: unknown): value is string {
    return (
        isBoundedText(value, 1, MAX_SPEC_BYTES) &&
        value === value.normalize("NFC") &&
        Array.from(value).every((character) => {
            const point = character.codePointAt(0);
            return point !== undefined && (point < 0xd800 || point > 0xdfff);
        })
    );
}

function parseField(value: unknown) {
    if (
        !isPlainRecord(value) ||
        !hasExactKeys(value, ["name", "label", "type", "required"]) ||
        !isIdentifier(value.name) ||
        !isBoundedText(value.label, 1, 256) ||
        (value.type !== "text" &&
            value.type !== "integer" &&
            value.type !== "boolean") ||
        typeof value.required !== "boolean"
    ) {
        throw new Error("Invalid Canvas form field.");
    }
    return {
        name: value.name,
        label: value.label,
        type: value.type as SemanticFieldType,
        required: value.required,
    };
}

interface NodeValidationState {
    nodeIds: Set<string>;
    bindingIds: Set<string>;
    totalNodes: number;
    version: "actions.canvas-spec/v1" | "actions.canvas-spec/v2";
    referencedBindings: Set<string>;
}

function parseNode(
    value: unknown,
    depth: number,
    state: NodeValidationState,
): CanvasNode {
    if (
        !isPlainRecord(value) ||
        typeof value.type !== "string" ||
        !isIdentifier(value.id) ||
        state.nodeIds.has(value.id) ||
        depth > 8 ||
        state.totalNodes >= 128
    ) {
        throw new Error("Invalid Canvas node.");
    }
    state.nodeIds.add(value.id);
    state.totalNodes += 1;

    if ("bindingId" in value && typeof value.bindingId === "string") {
        state.referencedBindings.add(value.bindingId);
    }
    switch (value.type) {
        case "stack": {
            if (
                !hasExactKeys(value, ["type", "id", "children"]) ||
                !isPlainArray(value.children) ||
                value.children.length > 128
            ) {
                throw new Error("Invalid Canvas stack.");
            }
            return {
                type: "stack",
                id: value.id,
                children: value.children.map((child) =>
                    parseNode(child, depth + 1, state),
                ),
            };
        }
        case "card": {
            if (
                state.version !== CANVAS_SPEC_VERSION_V2 ||
                !hasExactKeys(value, ["type", "id", "title", "children"]) ||
                !isBoundedText(value.title, 1, 256) ||
                !isPlainArray(value.children) ||
                value.children.length > 128
            ) {
                throw new Error("Invalid Canvas card.");
            }
            return {
                type: "card",
                id: value.id,
                title: value.title,
                children: value.children.map((child) =>
                    parseNode(child, depth + 1, state),
                ),
            };
        }
        case "chart": {
            if (
                state.version !== CANVAS_SPEC_VERSION_V2 ||
                !hasExactKeys(value, [
                    "type",
                    "id",
                    "title",
                    "bindingId",
                    "rowsKey",
                    "chartType",
                    "labelKey",
                    "valueKey",
                ]) ||
                !isBoundedText(value.title, 1, 256) ||
                !isIdentifier(value.bindingId) ||
                !state.bindingIds.has(value.bindingId) ||
                !isIdentifier(value.rowsKey) ||
                !isIdentifier(value.labelKey) ||
                !isIdentifier(value.valueKey) ||
                (value.chartType !== "bar" && value.chartType !== "line")
            ) {
                throw new Error("Invalid Canvas chart.");
            }
            return {
                type: "chart",
                id: value.id,
                title: value.title,
                bindingId: value.bindingId,
                rowsKey: value.rowsKey,
                chartType: value.chartType,
                labelKey: value.labelKey,
                valueKey: value.valueKey,
            };
        }
        case "log": {
            if (
                state.version !== CANVAS_SPEC_VERSION_V2 ||
                !hasExactKeys(value, [
                    "type",
                    "id",
                    "title",
                    "bindingId",
                    "rowsKey",
                    "messageKey",
                ]) ||
                !isBoundedText(value.title, 1, 256) ||
                !isIdentifier(value.bindingId) ||
                !state.bindingIds.has(value.bindingId) ||
                !isIdentifier(value.rowsKey) ||
                !isIdentifier(value.messageKey)
            ) {
                throw new Error("Invalid Canvas log.");
            }
            return {
                type: "log",
                id: value.id,
                title: value.title,
                bindingId: value.bindingId,
                rowsKey: value.rowsKey,
                messageKey: value.messageKey,
            };
        }
        case "inspector": {
            if (
                state.version !== CANVAS_SPEC_VERSION_V2 ||
                !hasExactKeys(value, [
                    "type",
                    "id",
                    "title",
                    "bindingId",
                    "valueKey",
                    "fields",
                ]) ||
                !isBoundedText(value.title, 1, 256) ||
                !isIdentifier(value.bindingId) ||
                !state.bindingIds.has(value.bindingId) ||
                !isIdentifier(value.valueKey) ||
                !isPlainArray(value.fields) ||
                value.fields.length < 1 ||
                value.fields.length > 16
            ) {
                throw new Error("Invalid Canvas inspector.");
            }
            const fields = value.fields.map((field) => {
                if (
                    !isPlainRecord(field) ||
                    !hasExactKeys(field, ["key", "label"]) ||
                    !isIdentifier(field.key) ||
                    !isBoundedText(field.label, 1, 256)
                ) {
                    throw new Error("Invalid Canvas inspector field.");
                }
                return { key: field.key, label: field.label };
            });
            if (
                new Set(fields.map((field) => field.key)).size !== fields.length
            )
                throw new Error("Duplicate inspector fields.");
            return {
                type: "inspector",
                id: value.id,
                title: value.title,
                bindingId: value.bindingId,
                valueKey: value.valueKey,
                fields,
            };
        }
        case "text":
            if (
                !hasExactKeys(value, ["type", "id", "text"]) ||
                !isBoundedText(value.text, 1, 4096)
            ) {
                throw new Error("Invalid Canvas text node.");
            }
            return { type: "text", id: value.id, text: value.text };
        case "form": {
            if (
                !hasExactKeys(value, [
                    "type",
                    "id",
                    "bindingId",
                    "submitLabel",
                    "fields",
                ]) ||
                !isIdentifier(value.bindingId) ||
                !isBoundedText(value.submitLabel, 1, 128) ||
                !isPlainArray(value.fields) ||
                value.fields.length === 0 ||
                value.fields.length > 32
            ) {
                throw new Error("Invalid Canvas form.");
            }
            if (!state.bindingIds.has(value.bindingId)) {
                throw new Error(
                    "Canvas form references an undeclared binding.",
                );
            }
            const fields = value.fields.map(parseField);
            if (
                new Set(fields.map((field) => field.name)).size !==
                fields.length
            ) {
                throw new Error("Canvas form field names must be unique.");
            }
            return {
                type: "form",
                id: value.id,
                bindingId: value.bindingId,
                submitLabel: value.submitLabel,
                fields,
            };
        }
        case "table": {
            if (
                !hasExactKeys(value, [
                    "type",
                    "id",
                    "bindingId",
                    "rowsKey",
                    "columns",
                ]) ||
                !isIdentifier(value.bindingId) ||
                !isIdentifier(value.rowsKey) ||
                !isPlainArray(value.columns) ||
                value.columns.length === 0 ||
                value.columns.length > 16
            ) {
                throw new Error("Invalid Canvas table.");
            }
            if (!state.bindingIds.has(value.bindingId)) {
                throw new Error(
                    "Canvas table references an undeclared binding.",
                );
            }
            const columns = value.columns.map((column) => {
                if (
                    !isPlainRecord(column) ||
                    !hasExactKeys(column, ["key", "label"]) ||
                    !isIdentifier(column.key) ||
                    !isBoundedText(column.label, 1, 256)
                ) {
                    throw new Error("Invalid Canvas table column.");
                }
                return { key: column.key, label: column.label };
            });
            if (
                new Set(columns.map((column) => column.key)).size !==
                columns.length
            ) {
                throw new Error("Canvas table column keys must be unique.");
            }
            return {
                type: "table",
                id: value.id,
                bindingId: value.bindingId,
                rowsKey: value.rowsKey,
                columns,
            };
        }
        case "status":
            if (
                !hasExactKeys(value, ["type", "id", "bindingId"]) ||
                !isIdentifier(value.bindingId) ||
                !state.bindingIds.has(value.bindingId)
            ) {
                throw new Error("Invalid Canvas status node.");
            }
            return {
                type: "status",
                id: value.id,
                bindingId: value.bindingId,
            };
        case "artifact":
            if (
                !hasExactKeys(value, ["type", "id", "bindingId", "label"]) ||
                !isIdentifier(value.bindingId) ||
                !state.bindingIds.has(value.bindingId) ||
                !isBoundedText(value.label, 1, 256)
            ) {
                throw new Error("Invalid Canvas artifact node.");
            }
            return {
                type: "artifact",
                id: value.id,
                bindingId: value.bindingId,
                label: value.label,
            };
        default:
            throw new Error("Unsupported Canvas node type.");
    }
}

export function parseCanvasSpec(value: unknown): CanvasSpecDocument {
    if (
        !isPlainRecord(value) ||
        !hasExactKeys(value, [
            "schemaVersion",
            "title",
            "visibility",
            "bindingIds",
            "root",
        ]) ||
        (value.schemaVersion !== CANVAS_SPEC_VERSION &&
            value.schemaVersion !== CANVAS_SPEC_VERSION_V2) ||
        !isBoundedText(value.title, 1, 128) ||
        !isPlainArray(value.visibility) ||
        value.visibility.length > 2 ||
        value.visibility.some(
            (audience) => audience !== "app" && audience !== "model",
        ) ||
        new Set(value.visibility).size !== value.visibility.length ||
        !isPlainArray(value.bindingIds) ||
        value.bindingIds.length > 32 ||
        value.bindingIds.some((bindingId) => !isIdentifier(bindingId)) ||
        new Set(value.bindingIds).size !== value.bindingIds.length
    ) {
        throw new Error("Invalid versioned CanvasSpec document.");
    }

    const bindingIds = [...value.bindingIds] as string[];
    const nodeIds = new Set<string>();
    const referencedBindings = new Set<string>();
    const root = parseNode(value.root, 1, {
        nodeIds,
        bindingIds: new Set(bindingIds),
        totalNodes: 0,
        version: value.schemaVersion,
        referencedBindings,
    });
    if (
        value.schemaVersion === CANVAS_SPEC_VERSION_V2 &&
        bindingIds.some((id) => !referencedBindings.has(id))
    )
        throw new Error("Unused Canvas binding.");
    const envelope = {
        title: value.title,
        visibility: [...value.visibility] as Array<"app" | "model">,
        bindingIds,
    };
    const spec: CanvasSpecDocument =
        value.schemaVersion === CANVAS_SPEC_VERSION
            ? {
                  schemaVersion: CANVAS_SPEC_VERSION,
                  ...envelope,
                  root: root as CanvasNodeV1,
              }
            : { schemaVersion: CANVAS_SPEC_VERSION_V2, ...envelope, root };
    if (
        new globalThis.TextEncoder().encode(JSON.stringify(spec)).byteLength >
        MAX_SPEC_BYTES
    ) {
        throw new Error("CanvasSpec exceeds the size limit.");
    }
    return spec;
}

function parseBinding(value: unknown): CanvasBindingScope {
    if (
        !isPlainRecord(value) ||
        !hasExactKeys(value, [
            "bindingId",
            "capabilityId",
            "packageRevision",
        ]) ||
        !isIdentifier(value.bindingId) ||
        !isPackageLocalIdentifier(value.capabilityId) ||
        !isPlainRecord(value.packageRevision) ||
        !hasExactKeys(value.packageRevision, [
            "workspace_id",
            "package_id",
            "revision_id",
        ]) ||
        typeof value.packageRevision.workspace_id !== "string" ||
        !UUID_PATTERN.test(value.packageRevision.workspace_id) ||
        typeof value.packageRevision.package_id !== "string" ||
        !UUID_PATTERN.test(value.packageRevision.package_id) ||
        typeof value.packageRevision.revision_id !== "string" ||
        !DIGEST_PATTERN.test(value.packageRevision.revision_id)
    ) {
        throw new Error("Invalid Canvas binding scope.");
    }
    return {
        bindingId: value.bindingId,
        capabilityId: value.capabilityId,
        packageRevision: {
            workspace_id: value.packageRevision.workspace_id,
            package_id: value.packageRevision.package_id,
            revision_id: value.packageRevision.revision_id,
        },
    };
}

function parseActiveCanvas(value: Record<string, unknown>): CanvasAppMetadata {
    if (
        !hasExactKeys(value, [
            "applicationId",
            "revisionId",
            "active",
            "spec",
            "bindings",
        ]) ||
        typeof value.applicationId !== "string" ||
        !UUID_PATTERN.test(value.applicationId) ||
        typeof value.revisionId !== "string" ||
        !DIGEST_PATTERN.test(value.revisionId) ||
        typeof value.active !== "boolean" ||
        !Array.isArray(value.bindings)
    ) {
        throw new Error("Invalid Canvas app metadata.");
    }

    const spec = parseCanvasSpec(value.spec);
    const bindings = value.bindings.map(parseBinding);
    if (bindings.length !== spec.bindingIds.length) {
        throw new Error("Canvas binding scope does not match the spec.");
    }
    const bindingsById = new Map<string, CanvasBindingScope>();
    let workspaceId: string | undefined;
    for (const binding of bindings) {
        if (
            bindingsById.has(binding.bindingId) ||
            !spec.bindingIds.includes(binding.bindingId) ||
            (workspaceId !== undefined &&
                workspaceId !== binding.packageRevision.workspace_id)
        ) {
            throw new Error("Canvas binding scope is inconsistent.");
        }
        workspaceId = binding.packageRevision.workspace_id;
        bindingsById.set(binding.bindingId, binding);
    }

    const sortedBindings = [...bindingsById.values()].sort((left, right) =>
        left.bindingId.localeCompare(right.bindingId),
    );
    const scopeKey = JSON.stringify([
        value.applicationId,
        value.revisionId,
        sortedBindings.map((binding) => [
            binding.bindingId,
            binding.capabilityId,
            binding.packageRevision.workspace_id,
            binding.packageRevision.package_id,
            binding.packageRevision.revision_id,
        ]),
    ]);

    return {
        applicationId: value.applicationId,
        revisionId: value.revisionId,
        active: value.active,
        spec,
        bindings: sortedBindings,
        preview: false,
        scopeKey,
    };
}

/** Parse only the closed, authoring-owned Canvas view shapes from MCP _meta. */
export function parseCanvasViewMetadata(value: unknown): CanvasViewMetadata {
    if (!isPlainRecord(value)) {
        throw new Error("Canvas view metadata must be an object.");
    }
    if (hasOwn(value, "preview")) {
        if (
            !hasExactKeys(value, ["spec", "preview"]) ||
            value.preview !== true
        ) {
            throw new Error("Invalid Canvas preview metadata.");
        }
        const spec = parseCanvasSpec(value.spec);
        return {
            spec,
            preview: true,
            revision: "preview",
            scopeKey: JSON.stringify(["preview", spec]),
        };
    }
    return parseActiveCanvas(value);
}

/** No app execution/status/artifact operations are configured for this view. */
const readOnlyAdapters: SemanticRendererAdapters = {
    resolveFormBinding: () => undefined,
    dispatch: async (): Promise<unknown> => {
        throw new Error("Canvas app operations are not configured.");
    },
    resolveStatusBinding: () => undefined,
    getStatus: () => undefined,
    resolveArtifactBinding: () => undefined,
    openArtifact: async () => ({
        state: "unavailable",
        message: "Canvas app operations are not configured.",
    }),
};

export const readOnlyCanvasAdapters = Object.freeze(readOnlyAdapters);
