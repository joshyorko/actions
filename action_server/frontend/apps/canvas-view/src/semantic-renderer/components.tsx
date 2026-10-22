import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";

import "./semantic-renderer.css";
import type {
    CanvasAudience,
    CanvasViewer,
    CapabilityDispatcher,
    CapabilityRef,
    SemanticTextField,
    TableColumn,
} from "./types";

const SAFE_STATUS_MESSAGE_CODE_POINTS = 500;
const REQUIRED_VALUE_MESSAGE = (label: string) => `Enter a value for ${label}.`;
const INVALID_FORM_MESSAGE = "This form cannot be displayed.";
const FORM_FAILURE_MESSAGE = "Unable to complete this action. Try again.";

export interface SemanticCanvasProps {
    title: string;
    revision: string | number;
    preview: boolean;
    audience: CanvasAudience;
    viewer: CanvasViewer;
    children?: ReactNode;
}

export function SemanticCanvas({
    title,
    revision,
    preview,
    audience,
    viewer,
    children,
}: SemanticCanvasProps) {
    const titleId = useId();
    const isVisible = audience === "both" || audience === viewer;
    const audienceLabel =
        audience === "both"
            ? "Model and app audiences"
            : audience === "model"
              ? "Model audience"
              : "App audience";

    if (!isVisible) {
        return (
            <main className="semantic-canvas" aria-label="Canvas content">
                <p className="semantic-canvas__notice" role="status">
                    This view is for the {audience} audience.
                </p>
            </main>
        );
    }

    return (
        <main className="semantic-canvas" aria-labelledby={titleId}>
            <header className="semantic-canvas__header">
                <p className="semantic-canvas__eyebrow">Canvas preview</p>
                <h1 id={titleId}>{title}</h1>
                <dl className="semantic-canvas__metadata">
                    <div>
                        <dt>Revision</dt>
                        <dd>Revision {revision}</dd>
                    </div>
                    <div>
                        <dt>Audience</dt>
                        <dd>{audienceLabel}</dd>
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
    title: string;
    fields: readonly SemanticTextField[];
    capability: CapabilityRef<Id, Input, Output>;
    toInput: (values: Readonly<Record<string, string>>) => Input;
    dispatch: CapabilityDispatcher<Id, Input, Output>;
    renderResult: (result: Output) => ReactNode;
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isValidField(value: unknown): value is SemanticTextField {
    if (!isRecord(value)) return false;
    if (
        typeof value.name !== "string" ||
        value.name.trim().length === 0 ||
        typeof value.label !== "string" ||
        value.label.trim().length === 0
    ) {
        return false;
    }
    if (value.required !== undefined && typeof value.required !== "boolean") {
        return false;
    }
    if (
        value.maxLength !== undefined &&
        (!Number.isSafeInteger(value.maxLength) ||
            (value.maxLength as number) < 1)
    ) {
        return false;
    }
    if (
        value.placeholder !== undefined &&
        typeof value.placeholder !== "string"
    ) {
        return false;
    }
    return true;
}

function fieldsAreValid(
    fields: unknown,
): fields is readonly SemanticTextField[] {
    if (!Array.isArray(fields) || fields.length === 0) return false;
    const names = new Set<string>();
    for (const field of fields) {
        if (!isValidField(field) || names.has(field.name)) return false;
        names.add(field.name);
    }
    return true;
}

function requiredFieldError(
    fields: readonly SemanticTextField[],
    values: Readonly<Record<string, string>>,
): string | null {
    for (const field of fields) {
        const value = values[field.name] ?? "";
        if (field.required && !/\S/u.test(value)) {
            return REQUIRED_VALUE_MESSAGE(field.label);
        }
        if (
            field.maxLength !== undefined &&
            Array.from(value).length > field.maxLength
        ) {
            return `Use ${field.maxLength} characters or fewer for ${field.label}.`;
        }
    }
    return null;
}

export function SemanticForm<Id extends string, Input, Output>({
    title,
    fields,
    capability,
    toInput,
    dispatch,
    renderResult,
}: SemanticFormProps<Id, Input, Output>) {
    const formId = useId();
    const generationRef = useRef(0);
    const mountedRef = useRef(false);
    const [values, setValues] = useState<Record<string, string>>({});
    const [validationError, setValidationError] = useState<string | null>(null);
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
            <section className="semantic-form" aria-label={title}>
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
        if (nextValidationError) return;

        setIsSubmitting(true);
        try {
            const input = toInput(Object.freeze({ ...values }));
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
        <section className="semantic-form" aria-label={title}>
            <h2 className="semantic-form__title">{title}</h2>
            <form noValidate onSubmit={submit}>
                {fields.map((field, index) => {
                    const inputId = `${formId}-field-${index}`;
                    const errorId = `${inputId}-error`;
                    const hasError = Boolean(validationError);
                    return (
                        <div className="semantic-form__field" key={field.name}>
                            <label htmlFor={inputId}>{field.label}</label>
                            <input
                                id={inputId}
                                name={field.name}
                                type="text"
                                value={values[field.name] ?? ""}
                                placeholder={field.placeholder}
                                required={field.required}
                                maxLength={field.maxLength}
                                disabled={isSubmitting}
                                aria-invalid={hasError}
                                aria-describedby={
                                    hasError ? errorId : undefined
                                }
                                onChange={(event) => {
                                    const nextValue = event.currentTarget.value;
                                    generationRef.current += 1;
                                    setValues((current) => ({
                                        ...current,
                                        [field.name]: nextValue,
                                    }));
                                    setValidationError(null);
                                    setActionError(null);
                                    setResult(null);
                                    setIsSubmitting(false);
                                }}
                            />
                            {validationError ? (
                                <span
                                    id={errorId}
                                    className="semantic-form__field-error"
                                    role="alert"
                                >
                                    {validationError}
                                </span>
                            ) : null}
                        </div>
                    );
                })}
                <button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? "Working…" : title}
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
                    aria-label={`${title} result`}
                >
                    {renderResult(result)}
                </div>
            ) : null}
        </section>
    );
}

export interface SemanticTableProps<Row extends object> {
    caption: string;
    columns: readonly TableColumn<Row>[];
    rows: readonly Row[];
    rowKey: (row: Row, index: number) => string;
    emptyMessage?: string;
}

function validTableConfiguration<Row extends object>(
    caption: unknown,
    columns: unknown,
    rows: unknown,
    rowKey: unknown,
): columns is readonly TableColumn<Row>[] {
    if (typeof caption !== "string" || caption.trim().length === 0)
        return false;
    if (!Array.isArray(columns) || columns.length === 0) return false;
    if (!Array.isArray(rows) || typeof rowKey !== "function") return false;

    const keys = new Set<string>();
    for (const column of columns) {
        if (
            !isRecord(column) ||
            typeof column.key !== "string" ||
            column.key.length === 0 ||
            typeof column.label !== "string" ||
            column.label.trim().length === 0 ||
            keys.has(column.key)
        ) {
            return false;
        }
        keys.add(column.key);
    }

    const rowKeys = new Set<string>();
    try {
        for (const [index, row] of rows.entries()) {
            if (!isRecord(row)) return false;
            const key: unknown = rowKey(row as Row, index);
            if (
                typeof key !== "string" ||
                key.length === 0 ||
                rowKeys.has(key)
            ) {
                return false;
            }
            rowKeys.add(key);
        }
    } catch {
        return false;
    }
    return true;
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

export function SemanticTable<Row extends object>({
    caption,
    columns,
    rows,
    rowKey,
    emptyMessage = "No results to display.",
}: SemanticTableProps<Row>) {
    const isValid = validTableConfiguration<Row>(
        caption,
        columns,
        rows,
        rowKey,
    );

    if (!isValid) {
        return (
            <p role="alert" className="semantic-table__error">
                This table cannot be displayed.
            </p>
        );
    }

    if (rows.length === 0) {
        return (
            <p role="status" className="semantic-table__empty">
                {emptyMessage}
            </p>
        );
    }

    return (
        <div className="semantic-table__scroll" tabIndex={0}>
            <table className="semantic-table">
                <caption>{caption}</caption>
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
                        <tr key={rowKey(row, index)}>
                            {columns.map((column) => (
                                <td key={column.key}>
                                    {cellText(row[column.key])}
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
    state: "loading" | "success" | "empty" | "error";
    message: string;
}

export function SemanticStatus({ state, message }: SemanticStatusProps) {
    const boundedMessage = Array.from(message)
        .slice(0, SAFE_STATUS_MESSAGE_CODE_POINTS)
        .join("");
    const role = state === "error" ? "alert" : "status";

    return (
        <p className={`semantic-status semantic-status--${state}`} role={role}>
            {boundedMessage}
        </p>
    );
}
