import type {
    SemanticProjectionExecution,
    SemanticProjectionState,
    SemanticProjectionValue,
} from "./types";

const LIMIT = 65536;

/** Restricted RFC 8785 output validation, not a new JSON input grammar. */
function canonical(value: unknown): string {
    if (value === null || typeof value === "boolean")
        return JSON.stringify(value);
    if (typeof value === "number") {
        if (
            !Number.isFinite(value) ||
            (Number.isInteger(value) && !Number.isSafeInteger(value))
        )
            throw new Error("Nonportable number");
        return JSON.stringify(value);
    }
    if (typeof value === "string") {
        // Unicode scalar values only; paired surrogate code units are valid.
        for (const scalar of value) {
            const point = scalar.codePointAt(0)!;
            if (point >= 0xd800 && point <= 0xdfff)
                throw new Error("Invalid Unicode scalar");
        }
        if (value.normalize("NFC") !== value)
            throw new Error("Noncanonical Unicode");
        return JSON.stringify(value);
    }
    if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
    if (
        typeof value === "object" &&
        Object.getPrototypeOf(value) === Object.prototype
    ) {
        const object = value as Record<string, unknown>;
        // Default JS string sort is RFC 8785 UTF-16 code-unit ordering.
        return `{${Object.keys(object)
            .sort()
            .map((key) => `${canonical(key)}:${canonical(object[key])}`)
            .join(",")}}`;
    }
    throw new Error("Non-JSON projection");
}

function freeze(value: SemanticProjectionValue): SemanticProjectionValue {
    if (value !== null && typeof value === "object") {
        Object.values(value).forEach(freeze);
        Object.freeze(value);
    }
    return value;
}

function decode(
    wire: unknown,
    bindingId: string,
    execution: SemanticProjectionExecution,
) {
    if (!wire || typeof wire !== "object")
        throw new Error("Missing projection");
    const record = wire as Record<string, unknown>;
    if (
        Object.keys(record).sort().join(",") !==
            "attemptId,bindingId,canonicalJson,data,runId" ||
        record.bindingId !== bindingId ||
        record.runId !== execution.runId ||
        record.attemptId !== execution.attemptId ||
        typeof record.canonicalJson !== "string"
    )
        throw new Error("Projection identity differs");
    const text = record.canonicalJson;
    if (new globalThis.TextEncoder().encode(text).length > LIMIT)
        throw new Error("Projection exceeds limit");
    const data: SemanticProjectionValue = JSON.parse(text);
    // Exact re-encoding also rejects duplicate keys, alternate number spellings,
    // underflow, normalization changes, whitespace and noncanonical escapes.
    if (canonical(data) !== text || canonical(record.data) !== text)
        throw new Error("Projection canonical bytes differ");
    return { canonicalJson: text, data: freeze(data) };
}

/** Pure local state; load is explicitly invoked only after trusted execution success. */
export function createGeneratedProjectionController(changed: () => void) {
    const states = new Map<string, SemanticProjectionState>();
    let generation = 0;
    const getProjection = (bindingId: string): SemanticProjectionState =>
        states.get(bindingId) ?? Object.freeze({ state: "not-run", bindingId });
    const set = (bindingId: string, state: SemanticProjectionState) => {
        states.set(bindingId, Object.freeze(state));
        changed();
    };
    const begin = (bindingId: string): string => {
        const requestId = String(++generation);
        set(bindingId, { state: "loading", bindingId, requestId });
        return requestId;
    };
    const fail = (bindingId: string, requestId: string) => {
        const current = states.get(bindingId);
        if (
            !current ||
            !("requestId" in current) ||
            current.requestId !== requestId
        )
            return;
        set(bindingId, {
            state: "error",
            bindingId,
            requestId,
            message: "Generated result unavailable.",
        });
    };
    const load = async (
        bindingId: string,
        requestId: string,
        execution: SemanticProjectionExecution,
        readAuthorizedProjection: () => Promise<unknown>,
    ): Promise<void> => {
        const before = states.get(bindingId);
        if (
            before?.state !== "loading" ||
            before.requestId !== requestId ||
            before.execution
        )
            return;
        const exactExecution = Object.freeze({ ...execution });
        const pending: SemanticProjectionState = Object.freeze({
            state: "loading",
            bindingId,
            requestId,
            execution: exactExecution,
        });
        states.set(bindingId, pending);
        changed();
        try {
            const wire = await readAuthorizedProjection();
            if (states.get(bindingId) !== pending) return;
            const result = decode(wire, bindingId, exactExecution);
            set(bindingId, {
                state:
                    result.data === null ||
                    (Array.isArray(result.data) && result.data.length === 0)
                        ? "empty"
                        : "ready",
                bindingId,
                requestId,
                execution: exactExecution,
                ...result,
            });
        } catch {
            if (states.get(bindingId) === pending) fail(bindingId, requestId);
        }
    };
    return Object.freeze({ getProjection, begin, fail, load });
}
