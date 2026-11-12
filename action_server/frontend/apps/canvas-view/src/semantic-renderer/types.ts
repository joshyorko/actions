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
    children: CanvasNodeV1[];
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

export type CanvasNodeV1 =
    | SemanticStackNode
    | SemanticTextNode
    | SemanticFormNode
    | SemanticTableNode
    | SemanticStatusNode
    | SemanticArtifactNode;

export interface SemanticStackNodeV2 {
    type: "stack";
    id: string;
    children: CanvasNodeV2[];
}
export interface SemanticCardNode {
    type: "card";
    id: string;
    title: string;
    children: CanvasNodeV2[];
}
export interface SemanticChartNode {
    type: "chart";
    id: string;
    title: string;
    bindingId: string;
    rowsKey: string;
    chartType: "bar" | "line";
    labelKey: string;
    valueKey: string;
}
export interface SemanticLogNode {
    type: "log";
    id: string;
    title: string;
    bindingId: string;
    rowsKey: string;
    messageKey: string;
}
export interface SemanticInspectorNode {
    type: "inspector";
    id: string;
    title: string;
    bindingId: string;
    valueKey: string;
    fields: Array<{ key: string; label: string }>;
}
export type CanvasNodeV2 =
    | Exclude<CanvasNodeV1, SemanticStackNode>
    | SemanticStackNodeV2
    | SemanticCardNode
    | SemanticChartNode
    | SemanticLogNode
    | SemanticInspectorNode;
export type CanvasNode = CanvasNodeV2;
interface CanvasSpecEnvelope {
    title: string;
    visibility: CanvasVisibility;
    bindingIds: string[];
}
export interface CanvasSpecDocumentV1 extends CanvasSpecEnvelope {
    schemaVersion: "actions.canvas-spec/v1";
    root: CanvasNodeV1;
}
export interface CanvasSpecDocumentV2 extends CanvasSpecEnvelope {
    schemaVersion: "actions.canvas-spec/v2";
    root: CanvasNodeV2;
}
/** Explicit version dispatch; v1 syntax never admits v2 nodes. */
export type CanvasSpecDocument = CanvasSpecDocumentV1 | CanvasSpecDocumentV2;

export interface SemanticBindingStatus {
    state: "loading" | "success" | "empty" | "error";
    message: string;
}

export interface SemanticArtifactResult {
    state: "ready" | "unavailable";
    message: string;
}

export interface SemanticRendererAdapters {
    /**
     * Pure local lookup; no fetch or authority is granted by this getter.
     * The host's changed callback rerenders consumers after state updates.
     * Arbitrary dispatch metadata is not an authorized projection.
     */
    getProjection?: (bindingId: string) => SemanticProjectionState;
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
    /** Changes when previously inspected artifact UI must be discarded. */
    artifactScopeKey?: (bindingId: string) => string;
    openArtifact: CapabilityDispatcher<string, void, SemanticArtifactResult>;
}

/** Portable JSON shape; runtime canonicalization validates numbers and bounds. */
export type SemanticProjectionValue =
    | null
    | boolean
    | number
    | string
    | readonly SemanticProjectionValue[]
    | { readonly [key: string]: SemanticProjectionValue };

export interface SemanticProjectionExecution {
    runId: string;
    attemptId: string;
}

/**
 * requestId is a trusted adapter generation, not caller-supplied authority.
 * Readiness belongs only to the same current request and Run/Attempt pair.
 * canonicalJson and data derive from the same authorized output under the
 * existing restricted RFC 8785 contract, bounded to 65536 UTF-8 bytes.
 * Clear retained data on resubmit, error or authorization denial; ignore stale
 * responses. These types alone neither validate nor authorize projection bytes.
 */
export type SemanticProjectionState =
    | { state: "not-run"; bindingId: string }
    | {
          state: "loading";
          bindingId: string;
          requestId: string;
          execution?: SemanticProjectionExecution;
      }
    | {
          state: "error";
          bindingId: string;
          requestId: string;
          execution?: SemanticProjectionExecution;
          message: string;
      }
    | {
          state: "empty" | "ready";
          bindingId: string;
          requestId: string;
          execution: SemanticProjectionExecution;
          canonicalJson: string;
          data: SemanticProjectionValue;
      };
