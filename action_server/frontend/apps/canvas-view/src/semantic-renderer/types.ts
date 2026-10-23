/**
 * A typed reference to a logical binding in validated CanvasSpec data.
 *
 * The symbol only makes the reference invariant in TypeScript; it is not a
 * runtime capability or authorization token. Hosts must resolve binding IDs
 * through their server-owned binding table before dispatching any action.
 */
declare const capabilityTypes: unique symbol;

export type CapabilityRef<Id extends string, Input, Output> = Readonly<{
    bindingId: Id;
    readonly [capabilityTypes]: {
        readonly input: (value: Input) => Input;
        readonly output: (value: Output) => Output;
    };
}>;

export type CapabilityDispatcher<Id extends string, Input, Output> = (
    capability: CapabilityRef<Id, Input, Output>,
    input: Input,
) => Promise<Output>;

/** Create a source-owned reference after validating and resolving a logical ID. */
export function createCapabilityRef<Id extends string, Input, Output>(
    bindingId: Id,
): CapabilityRef<Id, Input, Output> {
    return Object.freeze({ bindingId }) as unknown as CapabilityRef<
        Id,
        Input,
        Output
    >;
}

export type CanvasViewer = "app" | "model";
export type CanvasVisibility = readonly CanvasViewer[];
export type SemanticFieldType = "text" | "integer" | "boolean";

export interface SemanticFormField {
    name: string;
    label: string;
    type: SemanticFieldType;
    required: boolean;
}

export type SemanticFormInput = Readonly<
    Record<string, string | number | boolean>
>;

export interface SemanticTextNode {
    type: "text";
    id: string;
    text: string;
}

export interface SemanticStackNode {
    type: "stack";
    id: string;
    children: CanvasNode[];
}

export interface SemanticFormNode {
    type: "form";
    id: string;
    bindingId: string;
    submitLabel: string;
    fields: SemanticFormField[];
}

export interface SemanticTableNode {
    type: "table";
    id: string;
    bindingId: string;
    rowsKey: string;
    columns: Array<{ key: string; label: string }>;
}

export interface SemanticStatusNode {
    type: "status";
    id: string;
    bindingId: string;
}

export interface SemanticArtifactNode {
    type: "artifact";
    id: string;
    bindingId: string;
    label: string;
}

export type CanvasNode =
    | SemanticStackNode
    | SemanticTextNode
    | SemanticFormNode
    | SemanticTableNode
    | SemanticStatusNode
    | SemanticArtifactNode;

/** TypeScript projection of the canonical actions.canvas-spec/v1 JSON shape. */
export interface CanvasSpecDocument {
    schemaVersion: "actions.canvas-spec/v1";
    title: string;
    visibility: CanvasVisibility;
    bindingIds: string[];
    root: CanvasNode;
}

export interface SemanticBindingStatus {
    state: "loading" | "success" | "empty" | "error";
    message: string;
}

export interface SemanticArtifactResult {
    state: "ready" | "unavailable";
    message: string;
}

export interface SemanticRendererAdapters {
    resolveFormBinding: (
        bindingId: string,
    ) => CapabilityRef<string, SemanticFormInput, unknown> | undefined;
    dispatch: CapabilityDispatcher<string, SemanticFormInput, unknown>;
    resolveStatusBinding: (
        bindingId: string,
    ) => CapabilityRef<string, never, SemanticBindingStatus> | undefined;
    getStatus: (
        capability: CapabilityRef<string, never, SemanticBindingStatus>,
    ) => SemanticBindingStatus | undefined;
    resolveArtifactBinding: (
        bindingId: string,
    ) => CapabilityRef<string, void, SemanticArtifactResult> | undefined;
    openArtifact: CapabilityDispatcher<string, void, SemanticArtifactResult>;
}
