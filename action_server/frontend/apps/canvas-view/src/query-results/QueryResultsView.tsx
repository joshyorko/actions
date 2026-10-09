import { useRef, useState } from "react";
import type { FormEvent } from "react";
import type * as React from "react";

import "./query-results.css";

export type ArtifactHandle = string & {
    readonly __artifactHandle: unique symbol;
};

export interface QueryInput {
    query: string;
}

export interface QueryRow {
    id: string;
    title: string;
    category: string;
}

export interface QueryActionResult {
    rows: QueryRow[];
    artifact: { handle: ArtifactHandle } | null;
    error: {
        code: "no_matches";
        message: "No records matched that query.";
    } | null;
}

export type ArtifactStatus = "ready" | "processing" | "unavailable";

/**
 * Trusted host adapter injected by the application owner.
 *
 * These fixed methods do not accept client-selected tool names, binding IDs,
 * app IDs, revisions, URLs, or paths. The adapter must bind them to
 * server-owned authorization and dispatch policy.
 */
export interface QueryResultsAdapter {
    submitQuery(input: QueryInput): Promise<QueryActionResult>;
    getArtifactStatus(handle: ArtifactHandle): Promise<ArtifactStatus>;
}

interface QueryResultsViewProps {
    adapter: QueryResultsAdapter;
}

const MAX_QUERY_CODE_POINTS = 64;
const NO_MATCHES_MESSAGE = "No records matched that query.";
const SEARCH_FAILURE_MESSAGE = "Unable to search right now. Try again.";
const ARTIFACT_FAILURE_MESSAGE = "Unable to check the result artifact.";

function queryValidationMessage(query: string): string | null {
    if (query.length === 0 || !/\S/u.test(query)) {
        return "Enter a search query containing at least one visible character.";
    }
    if (Array.from(query).length > MAX_QUERY_CODE_POINTS) {
        return `Use ${MAX_QUERY_CODE_POINTS} characters or fewer.`;
    }
    return null;
}

export function QueryResultsView({ adapter }: QueryResultsViewProps) {
    const [query, setQuery] = useState("");
    const [validationError, setValidationError] = useState<string | null>(null);
    const [actionError, setActionError] = useState<string | null>(null);
    const [result, setResult] = useState<QueryActionResult | null>(null);
    const [artifactStatus, setArtifactStatus] = useState<string | null>(null);
    const [isSearching, setIsSearching] = useState(false);
    const [isCheckingArtifact, setIsCheckingArtifact] = useState(false);
    const inputRef = useRef<React.ComponentRef<"input">>(null);

    const submit = async (event: FormEvent) => {
        event.preventDefault();
        const error = queryValidationMessage(query);
        setValidationError(error);
        setActionError(null);
        setArtifactStatus(null);
        setResult(null);
        if (error) {
            inputRef.current?.focus();
            return;
        }

        setIsSearching(true);
        try {
            const nextResult = await adapter.submitQuery({ query });
            setResult(nextResult);
        } catch {
            // Adapter errors may include provider or transport details; keep those out
            // of the rendered view and provide a bounded recovery message.
            setActionError(SEARCH_FAILURE_MESSAGE);
        } finally {
            setIsSearching(false);
        }
    };

    const checkArtifact = async () => {
        const handle = result?.artifact?.handle;
        if (!handle) {
            return;
        }
        setActionError(null);
        setIsCheckingArtifact(true);
        try {
            const status = await adapter.getArtifactStatus(handle);
            setArtifactStatus(
                status === "ready"
                    ? "Result artifact is ready."
                    : status === "processing"
                      ? "Result artifact is still processing."
                      : "Result artifact is unavailable.",
            );
        } catch {
            setActionError(ARTIFACT_FAILURE_MESSAGE);
        } finally {
            setIsCheckingArtifact(false);
        }
    };

    const describedBy = validationError
        ? "query-help query-error"
        : "query-help";

    return (
        <main className="query-view" aria-labelledby="query-view-title">
            <header className="query-view__header">
                <p className="query-view__eyebrow">Canvas fixture</p>
                <h1 id="query-view-title">Search records</h1>
                <p className="query-view__intro">
                    Search the sample catalog and review its matching records.
                </p>
            </header>

            <section
                className="query-view__panel"
                aria-labelledby="query-form-title"
            >
                <h2 id="query-form-title">Find records</h2>
                <form
                    className="query-view__form"
                    noValidate
                    aria-busy={isSearching}
                    onSubmit={submit}
                >
                    <label htmlFor="query-input">Search records</label>
                    <input
                        ref={inputRef}
                        id="query-input"
                        name="query"
                        type="text"
                        autoComplete="off"
                        required
                        maxLength={MAX_QUERY_CODE_POINTS * 2}
                        aria-invalid={validationError ? true : undefined}
                        aria-describedby={describedBy}
                        value={query}
                        disabled={isSearching}
                        onChange={(event) => {
                            setQuery(event.currentTarget.value);
                            setValidationError(null);
                            setActionError(null);
                            setResult(null);
                            setArtifactStatus(null);
                        }}
                    />
                    <p id="query-help" className="query-view__hint">
                        Enter up to 64 characters. Search terms stay within this
                        local fixture.
                    </p>
                    {validationError && (
                        <p
                            id="query-error"
                            className="query-view__error"
                            role="alert"
                        >
                            {validationError}
                        </p>
                    )}
                    <button
                        className="query-view__button query-view__button--primary"
                        type="submit"
                        disabled={isSearching}
                    >
                        {isSearching ? "Searching…" : "Search"}
                    </button>
                </form>
            </section>

            <section
                className="query-view__panel query-view__results"
                aria-labelledby="results-title"
                aria-busy={isSearching || isCheckingArtifact}
            >
                <div className="query-view__section-heading">
                    <div>
                        <p className="query-view__eyebrow">Results</p>
                        <h2 id="results-title">Matching records</h2>
                    </div>
                    {result?.rows.length ? (
                        <span className="query-view__count">
                            {result.rows.length} records
                        </span>
                    ) : null}
                </div>

                {isSearching && (
                    <p
                        className="query-view__status"
                        role="status"
                        aria-live="polite"
                    >
                        Searching records…
                    </p>
                )}
                {actionError && (
                    <p className="query-view__error" role="alert">
                        {actionError}
                    </p>
                )}
                {result?.error && (
                    <p className="query-view__error" role="alert">
                        {NO_MATCHES_MESSAGE}
                    </p>
                )}
                {result && !result.error && result.rows.length === 0 && (
                    <p className="query-view__empty" role="status">
                        No records to show yet. Try a search above.
                    </p>
                )}
                {result && !result.error && result.rows.length > 0 && (
                    <div className="query-view__table-wrap" tabIndex={0}>
                        <table>
                            <caption className="query-view__sr-only">
                                Search results
                            </caption>
                            <thead>
                                <tr>
                                    <th scope="col">Title</th>
                                    <th scope="col">Category</th>
                                </tr>
                            </thead>
                            <tbody>
                                {result.rows.map((row) => (
                                    <tr key={row.id}>
                                        <th scope="row">{row.title}</th>
                                        <td>{row.category}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {!result && !actionError && !isSearching && (
                    <p className="query-view__empty" role="status">
                        Search records to see matching results.
                    </p>
                )}

                {result?.artifact && !result.error && (
                    <div className="query-view__artifact" aria-live="polite">
                        <div>
                            <h3>Result artifact</h3>
                            <p className="query-view__hint">
                                An opaque result handle is available. The handle
                                alone does not grant access.
                            </p>
                        </div>
                        <button
                            className="query-view__button"
                            type="button"
                            onClick={checkArtifact}
                            disabled={isCheckingArtifact}
                        >
                            {isCheckingArtifact
                                ? "Checking…"
                                : "Check artifact status"}
                        </button>
                    </div>
                )}
                {artifactStatus && (
                    <p className="query-view__status" role="status">
                        {artifactStatus}
                    </p>
                )}
            </section>
        </main>
    );
}
