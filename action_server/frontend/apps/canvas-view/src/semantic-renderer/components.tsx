import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";

import "./semantic-renderer.css";
import { createCapabilityRef } from "./types";
import type {
    CanvasNode,
    CanvasSpecDocument,
    CanvasViewer,
    CanvasVisibility,
    CapabilityDispatcher,
    CapabilityRef,
    SemanticArtifactResult,
    SemanticBindingStatus,
    SemanticFormField,
    SemanticFormInput,
    SemanticRendererAdapters,
} from "./types";

const SAFE_STATUS_MESSAGE_CODE_POINTS = 500;
const REQUIRED_VALUE_MESSAGE = (label: string) => `Enter a value for ${label}.`;
const INVALID_FORM_MESSAGE = "This form cannot be displayed.";
const INVALID_SPEC_MESSAGE = "This Canvas view cannot be displayed.";
const FORM_FAILURE_MESSAGE = "Unable to complete this action. Try again.";

function hasOwn(value: object, key: PropertyKey): boolean {
    return Object.prototype.hasOwnProperty.call(value, key);
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function emptyRecord<T>(): Record<string, T> {
    return Object.create(null) as Record<string, T>;
}

function recordWith<T>(
    record: Readonly<Record<string, T>>,
    key: string,
    value: T,
): Record<string, T> {
    const next = emptyRecord<T>();
    for (const currentKey of Object.keys(record)) {
        next[currentKey] = record[currentKey];
    }
    next[key] = value;
    return next;
}

function ownValue<T>(
    record: Readonly<Record<string, T>>,
    key: string,
): T | undefined {
    return hasOwn(record, key) ? record[key] : undefined;
}

function labelForVisibility(visibility: CanvasVisibility): string {
    if (visibility.includes("app") && visibility.includes("model")) {
        return "Model and app audiences";
    }
    return visibility[0] === "model" ? "Model audience" : "App audience";
}

export interface SemanticCanvasProps {
    title: string;
    revision: string | number;
    preview: boolean;
    visibility: CanvasVisibility;
    viewer: CanvasViewer;
    children?: ReactNode;
}

export function SemanticCanvas({
    title,
    revision,
    preview,
    visibility,
    viewer,
    children,
}: SemanticCanvasProps) {
    const titleId = useId();
    const isVisible = visibility.includes(viewer);

    if (!isVisible) {
        return (
            <main className="semantic-canvas" aria-label="Canvas content">
                <p className="semantic-canvas__notice" role="status">
                    This view is unavailable.
                </p>
            </main>
        );
    }

    return (
        <main className="semantic-canvas" aria-labelledby={titleId}>
            <header className="semantic-canvas__header">
                <p className="semantic-canvas__eyebrow">Canvas view</p>
                <h1 id={titleId}>{title}</h1>
                <dl className="semantic-canvas__metadata">
                    <div>
                        <dt>Revision</dt>
                        <dd>Revision {revision}</dd>
                    </div>
                    <div>
                        <dt>Audience</dt>
                        <dd>{labelForVisibility(visibility)}</dd>
                    </div>
                </dl>
                {preview ? (
                    <span className="semantic-canvas__preview">Preview</span>
                ) : null}
            </header>
            <div className="semantic-canvas__content">{children}</div>
        </main>
    );
}

export interface SemanticFormProps<Id extends string, Input, Output> {
    scopeKey: string;
    submitLabel: string;
    fields: readonly SemanticFormField[];
    capability: CapabilityRef<Id, Input, Output>;
    toInput: (values: SemanticFormInput) => Input;
    dispatch: CapabilityDispatcher<Id, Input, Output>;
    renderResult: (result: Output) => ReactNode;
    disabled?: boolean;
}

type FormState = Record<string, string | boolean>;

function initialValues(fields: readonly SemanticFormField[]): FormState {
    const values = emptyRecord<string | boolean>();
    for (const field of fields) {
        values[field.name] = field.type === "boolean" ? false : "";
    }
    return values;
}

function isValidField(value: unknown): value is SemanticFormField {
    if (!isRecord(value)) return false;
    return (
        typeof value.name === "string" &&
        value.name.trim().length > 0 &&
        typeof value.label === "string" &&
        value.label.trim().length > 0 &&
        (value.type === "text" ||
            value.type === "integer" ||
            value.type === "boolean") &&
        typeof value.required === "boolean"
    );
}

function fieldsAreValid(
    fields: unknown,
): fields is readonly SemanticFormField[] {
    if (!Array.isArray(fields) || fields.length === 0) return false;
    const names = new Set<string>();
    for (const field of fields) {
        if (!isValidField(field) || names.has(field.name)) return false;
        names.add(field.name);
    }
    return true;
}

interface FormValidationError {
    fieldName: string;
    message: string;
}

function requiredFieldError(
    fields: readonly SemanticFormField[],
    values: Readonly<FormState>,
): FormValidationError | null {
    for (const field of fields) {
        const value = ownValue(values, field.name);
        if (field.type === "boolean") {
            if (field.required && value !== true) {
                return {
                    fieldName: field.name,
                    message: REQUIRED_VALUE_MESSAGE(field.label),
                };
            }
            continue;
        }

        const textValue = typeof value === "string" ? value : "";
        if (field.required && !/\S/u.test(textValue)) {
            return {
                fieldName: field.name,
                message: REQUIRED_VALUE_MESSAGE(field.label),
            };
        }
        if (
            field.type === "integer" &&
            textValue !== "" &&
            (!/^-?\d+$/u.test(textValue) ||
                !Number.isSafeInteger(Number(textValue)))
        ) {
            return {
                fieldName: field.name,
                message: `Enter a whole number for ${field.label}.`,
            };
        }
    }
    return null;
}

function makeInput(
    fields: readonly SemanticFormField[],
    values: Readonly<FormState>,
): SemanticFormInput {
    const input = emptyRecord<string | number | boolean>();
    for (const field of fields) {
        const value = ownValue(values, field.name);
        if (field.type === "boolean") {
            input[field.name] = value === true;
        } else if (field.type === "integer") {
            if (typeof value === "string" && value !== "") {
                input[field.name] = Number(value);
            }
        } else {
            input[field.name] = typeof value === "string" ? value : "";
        }
    }
    return Object.freeze(input);
}

export function SemanticForm<Id extends string, Input, Output>(
    props: SemanticFormProps<Id, Input, Output>,
) {
    const { scopeKey, ...formProps } = props;
    const key = JSON.stringify([
        scopeKey,
        props.capability.bindingId,
        props.fields,
    ]);
    return <SemanticFormInstance key={key} {...formProps} />;
}

function SemanticFormInstance<Id extends string, Input, Output>({
    submitLabel,
    fields,
    capability,
    toInput,
    dispatch,
    renderResult,
    disabled = false,
}: Omit<SemanticFormProps<Id, Input, Output>, "scopeKey">) {
    const formId = useId();
    const generationRef = useRef(0);
    const mountedRef = useRef(false);
    const [values, setValues] = useState<FormState>(() =>
        initialValues(fields),
    );
    const [validationError, setValidationError] =
        useState<FormValidationError | null>(null);
    const [actionError, setActionError] = useState<string | null>(null);
    const [result, setResult] = useState<Output | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const fieldsValid = fieldsAreValid(fields);

    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
            generationRef.current += 1;
        };
    }, []);

    if (!fieldsValid) {
        return (
            <section className="semantic-form" aria-label={submitLabel}>
                <p role="alert">{INVALID_FORM_MESSAGE}</p>
            </section>
        );
    }

    const submit = async (event: FormEvent) => {
        event.preventDefault();
        const generation = ++generationRef.current;
        const nextValidationError = requiredFieldError(fields, values);
        setValidationError(nextValidationError);
        setActionError(null);
        setResult(null);
        if (nextValidationError || disabled) return;

        setIsSubmitting(true);
        try {
            const input = toInput(makeInput(fields, values));
            const nextResult = await dispatch(capability, input);
            if (!mountedRef.current || generationRef.current !== generation) {
                return;
            }
            setResult(nextResult);
        } catch {
            if (!mountedRef.current || generationRef.current !== generation) {
                return;
            }
            setActionError(FORM_FAILURE_MESSAGE);
        } finally {
            if (mountedRef.current && generationRef.current === generation) {
                setIsSubmitting(false);
            }
        }
    };

    return (
        <section className="semantic-form" aria-label={submitLabel}>
            <h2 className="semantic-form__title">{submitLabel}</h2>
            <form noValidate onSubmit={submit}>
                {fields.map((field, index) => {
                    const inputId = `${formId}-field-${index}`;
                    const errorId = `${inputId}-error`;
                    const fieldError =
                        validationError?.fieldName === field.name
                            ? validationError.message
                            : null;
                    const hasError = Boolean(fieldError);
                    const value = ownValue(values, field.name);
                    const isBoolean = field.type === "boolean";
                    return (
                        <div className="semantic-form__field" key={field.name}>
                            <label htmlFor={inputId}>{field.label}</label>
                            <input
                                id={inputId}
                                name={field.name}
                                type={
                                    isBoolean
                                        ? "checkbox"
                                        : field.type === "integer"
                                          ? "number"
                                          : "text"
                                }
                                step={field.type === "integer" ? 1 : undefined}
                                value={
                                    isBoolean ? undefined : (value as string)
                                }
                                checked={isBoolean ? value === true : undefined}
                                required={field.required}
                                disabled={isSubmitting || disabled}
                                aria-invalid={hasError}
                                aria-describedby={
                                    hasError ? errorId : undefined
                                }
                                onChange={(event) => {
                                    const nextValue = isBoolean
                                        ? event.currentTarget.checked
                                        : event.currentTarget.value;
                                    generationRef.current += 1;
                                    setValues((current) =>
                                        recordWith(
                                            current,
                                            field.name,
                                            nextValue,
                                        ),
                                    );
                                    setValidationError(null);
                                    setActionError(null);
                                    setResult(null);
                                    setIsSubmitting(false);
                                }}
                            />
                            {fieldError ? (
                                <span
                                    id={errorId}
                                    className="semantic-form__field-error"
                                    role="alert"
                                >
                                    {fieldError}
                                </span>
                            ) : null}
                        </div>
                    );
                })}
                <button type="submit" disabled={isSubmitting || disabled}>
                    {isSubmitting ? "Working…" : submitLabel}
                </button>
            </form>
            {actionError ? (
                <p role="alert" className="semantic-form__error">
                    {actionError}
                </p>
            ) : null}
            {result !== null ? (
                <div
                    className="semantic-form__result"
                    aria-label={`${submitLabel} result`}
                >
                    {renderResult(result)}
                </div>
            ) : null}
        </section>
    );
}

export interface SemanticTableProps {
    caption?: string;
    columns: readonly { key: string; label: string }[];
    rows: readonly Record<string, unknown>[];
    emptyMessage?: string;
}

function cellText(value: unknown): string {
    if (value === null || value === undefined) return "—";
    if (typeof value === "string" || typeof value === "boolean") {
        return String(value);
    }
    if (typeof value === "number") {
        return Number.isFinite(value) ? String(value) : "—";
    }
    return "Complex value";
}

export function SemanticTable({
    caption,
    columns,
    rows,
    emptyMessage = "No results to display.",
}: SemanticTableProps) {
    if (
        !Array.isArray(columns) ||
        columns.length === 0 ||
        !Array.isArray(rows) ||
        columns.some(
            (column) =>
                !isRecord(column) ||
                typeof column.key !== "string" ||
                !column.key ||
                typeof column.label !== "string" ||
                !column.label,
        ) ||
        rows.some((row) => !isRecord(row))
    ) {
        return (
            <p role="alert" className="semantic-table__error">
                This table cannot be displayed.
            </p>
        );
    }

    if (rows.length === 0) {
        return (
            <p
                role="status"
                aria-label={caption || "Results"}
                className="semantic-table__empty"
            >
                {emptyMessage}
            </p>
        );
    }

    return (
        <div
            className="semantic-table__scroll"
            role="region"
            aria-label={caption || "Results"}
            tabIndex={0}
        >
            <table className="semantic-table">
                {caption ? <caption>{caption}</caption> : null}
                <thead>
                    <tr>
                        {columns.map((column) => (
                            <th key={column.key} scope="col">
                                {column.label}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row, index) => (
                        <tr key={`row-${index}`}>
                            {columns.map((column) => (
                                <td key={column.key}>
                                    {cellText(
                                        hasOwn(row, column.key)
                                            ? row[column.key]
                                            : undefined,
                                    )}
                                </td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

export interface SemanticStatusProps {
    state: SemanticBindingStatus["state"];
    message: string;
}

export function SemanticStatus({ state, message }: SemanticStatusProps) {
    const safeMessage = typeof message === "string" ? message : "";
    const boundedMessage = Array.from(safeMessage)
        .slice(0, SAFE_STATUS_MESSAGE_CODE_POINTS)
        .join("");
    const role = state === "error" ? "alert" : "status";

    return (
        <p className={`semantic-status semantic-status--${state}`} role={role}>
            {boundedMessage}
        </p>
    );
}

interface SemanticArtifactProps {
    label: string;
    capability: CapabilityRef<string, void, SemanticArtifactResult> | undefined;
    openArtifact: CapabilityDispatcher<string, void, SemanticArtifactResult>;
    disabled: boolean;
}

function SemanticArtifact({
    label,
    capability,
    openArtifact,
    disabled,
}: SemanticArtifactProps) {
    const [artifactResult, setArtifactResult] =
        useState<SemanticArtifactResult | null>(null);
    const [isOpening, setIsOpening] = useState(false);

    const open = async () => {
        if (!capability || disabled || isOpening) return;
        setIsOpening(true);
        setArtifactResult(null);
        try {
            const result = await openArtifact(capability, undefined);
            setArtifactResult(result);
        } catch {
            setArtifactResult({
                state: "unavailable",
                message: FORM_FAILURE_MESSAGE,
            });
        } finally {
            setIsOpening(false);
        }
    };

    return (
        <div className="semantic-artifact">
            <button
                type="button"
                disabled={!capability || disabled || isOpening}
                onClick={() => void open()}
            >
                {isOpening ? "Opening…" : label}
            </button>
            {artifactResult ? (
                <SemanticStatus
                    state={
                        artifactResult.state === "ready" ? "success" : "error"
                    }
                    message={artifactResult.message}
                />
            ) : null}
        </div>
    );
}

function isSupportedNode(node: unknown): node is CanvasNode {
    if (!isRecord(node) || typeof node.id !== "string") return false;
    switch (node.type) {
        case "stack":
            return (
                Array.isArray(node.children) &&
                node.children.every(isSupportedNode)
            );
        case "text":
            return typeof node.text === "string";
        case "form":
            return (
                typeof node.bindingId === "string" &&
                typeof node.submitLabel === "string" &&
                Array.isArray(node.fields) &&
                node.fields.every(isValidField)
            );
        case "table":
            return (
                typeof node.bindingId === "string" &&
                typeof node.rowsKey === "string" &&
                Array.isArray(node.columns) &&
                node.columns.length > 0 &&
                node.columns.every(
                    (column) =>
                        isRecord(column) &&
                        typeof column.key === "string" &&
                        column.key.length > 0 &&
                        typeof column.label === "string" &&
                        column.label.length > 0,
                )
            );
        case "status":
            return typeof node.bindingId === "string";
        case "artifact":
            return (
                typeof node.bindingId === "string" &&
                typeof node.label === "string"
            );
        default:
            return false;
    }
}

function isRenderableSpec(spec: unknown): spec is CanvasSpecDocument {
    return (
        isRecord(spec) &&
        spec.schemaVersion === "actions.canvas-spec/v1" &&
        typeof spec.title === "string" &&
        Array.isArray(spec.visibility) &&
        spec.visibility.every(
            (audience) => audience === "app" || audience === "model",
        ) &&
        Array.isArray(spec.bindingIds) &&
        spec.bindingIds.every((bindingId) => typeof bindingId === "string") &&
        isSupportedNode(spec.root)
    );
}

export interface SemanticCanvasRendererProps {
    spec: CanvasSpecDocument;
    revision: string | number;
    /** Must include authorized app/binding scope, immutable revision, and node identity. */
    scopeKey: string;
    preview: boolean;
    viewer: CanvasViewer;
    adapters: SemanticRendererAdapters;
    /** Trusted host-only slots; never populated from serialized CanvasSpec. */
    appFormOverrides?: ReadonlyMap<string, ReactNode>;
    appPanels?: ReadonlyMap<string, ReactNode>;
}

export function SemanticCanvasRenderer(props: SemanticCanvasRendererProps) {
    const key = JSON.stringify([props.scopeKey, props.revision, props.spec]);
    return <SemanticCanvasRendererInstance key={key} {...props} />;
}

function SemanticCanvasRendererInstance({
    spec,
    revision,
    scopeKey,
    preview,
    viewer,
    adapters,
    appFormOverrides,
    appPanels,
}: SemanticCanvasRendererProps) {
    const [results, setResults] =
        useState<Record<string, unknown>>(emptyRecord);

    if (!isRenderableSpec(spec)) {
        return (
            <main className="semantic-canvas" aria-label="Canvas content">
                <p role="alert">{INVALID_SPEC_MESSAGE}</p>
            </main>
        );
    }

    const bindings = new Set(spec.bindingIds);
    if (!spec.visibility.includes(viewer)) {
        return (
            <SemanticCanvas
                title={spec.title}
                revision={revision}
                preview={preview}
                visibility={spec.visibility}
                viewer={viewer}
            />
        );
    }

    const privateSlotsVisible = viewer === "app" && !preview;

    const resolveResult = (bindingId: string): unknown =>
        ownValue(results, bindingId);

    const renderNode = (node: CanvasNode): ReactNode => {
        switch (node.type) {
            case "stack":
                return (
                    <div className="semantic-stack" key={node.id}>
                        {node.children.map((child) => renderNode(child))}
                    </div>
                );
            case "text":
                return <p key={node.id}>{node.text}</p>;
            case "form": {
                if (
                    privateSlotsVisible &&
                    bindings.has(node.bindingId) &&
                    appFormOverrides?.has(node.bindingId)
                ) {
                    return (
                        <div key={node.id} data-semantic-node-id={node.id}>
                            {appFormOverrides.get(node.bindingId)}
                        </div>
                    );
                }
                const capability = preview
                    ? createCapabilityRef<string, SemanticFormInput, unknown>(
                          node.bindingId,
                      )
                    : bindings.has(node.bindingId)
                      ? adapters.resolveFormBinding(node.bindingId)
                      : undefined;
                if (!capability) {
                    return (
                        <p key={node.id} role="alert">
                            This action is unavailable.
                        </p>
                    );
                }
                const dispatch = async (
                    reference: CapabilityRef<
                        string,
                        SemanticFormInput,
                        unknown
                    >,
                    input: SemanticFormInput,
                ) => {
                    const result = await adapters.dispatch(reference, input);
                    setResults((current) =>
                        recordWith(current, reference.bindingId, result),
                    );
                    return result;
                };
                return (
                    <SemanticForm
                        key={node.id}
                        scopeKey={`${scopeKey}:${revision}:${node.id}`}
                        submitLabel={node.submitLabel}
                        fields={node.fields}
                        capability={capability}
                        toInput={(input) => input}
                        dispatch={dispatch}
                        disabled={preview}
                        renderResult={() => null}
                    />
                );
            }
            case "table": {
                const result = bindings.has(node.bindingId)
                    ? resolveResult(node.bindingId)
                    : undefined;
                const candidateRows =
                    isRecord(result) && hasOwn(result, node.rowsKey)
                        ? result[node.rowsKey]
                        : undefined;
                const rows = Array.isArray(candidateRows)
                    ? candidateRows.filter(isRecord)
                    : [];
                return (
                    <SemanticTable
                        key={node.id}
                        caption={node.columns
                            .map((column) => column.label)
                            .join(", ")}
                        columns={node.columns}
                        rows={rows}
                    />
                );
            }
            case "status": {
                const capability =
                    !preview && bindings.has(node.bindingId)
                        ? adapters.resolveStatusBinding(node.bindingId)
                        : undefined;
                const status =
                    capability && !preview
                        ? adapters.getStatus(capability)
                        : undefined;
                return status ? (
                    <SemanticStatus
                        key={node.id}
                        state={status.state}
                        message={status.message}
                    />
                ) : (
                    <SemanticStatus
                        key={node.id}
                        state="empty"
                        message={
                            preview
                                ? "Status is available in the active view."
                                : "No status is available."
                        }
                    />
                );
            }
            case "artifact": {
                const capability =
                    !preview && bindings.has(node.bindingId)
                        ? adapters.resolveArtifactBinding(node.bindingId)
                        : undefined;
                return (
                    <SemanticArtifact
                        key={node.id}
                        label={node.label}
                        capability={capability}
                        openArtifact={adapters.openArtifact}
                        disabled={preview}
                    />
                );
            }
        }
    };

    return (
        <SemanticCanvas
            title={spec.title}
            revision={revision}
            preview={preview}
            visibility={spec.visibility}
            viewer={viewer}
        >
            {renderNode(spec.root)}
            {privateSlotsVisible && appPanels
                ? [...appPanels]
                      .filter(([bindingId]) => bindings.has(bindingId))
                      .map(([bindingId, panel]) => (
                          <div
                              className="semantic-stack"
                              key={`app-panel:${bindingId}`}
                          >
                              {panel}
                          </div>
                      ))
                : null}
        </SemanticCanvas>
    );
}
