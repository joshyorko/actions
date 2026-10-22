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

export type CanvasAudience = "app" | "model" | "both";
export type CanvasViewer = "app" | "model";

export interface SemanticTextField {
    name: string;
    label: string;
    required?: boolean;
    maxLength?: number;
    placeholder?: string;
}

export interface TableColumn<Row extends object> {
    key: Extract<keyof Row, string>;
    label: string;
}
