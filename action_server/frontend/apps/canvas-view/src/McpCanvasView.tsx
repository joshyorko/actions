import { GenericSemanticView } from "./semantic-renderer/generic-view";
import { parseGenericExecution } from "./semantic-renderer/generic-execution";
import type { GenericExecutionContext } from "./semantic-renderer/generic-execution";
import { useEffect, useMemo, useRef, useState } from "react";
import {
    useApp,
    useHostStyleVariables,
    type App,
    type McpUiHostContext,
} from "@modelcontextprotocol/ext-apps/react";

import {
    QueryResultsView,
    type ArtifactHandle,
    type ArtifactStatus,
    type HostToolInput,
    type HostToolResult,
    type QueryActionResult,
    type QueryResultsAdapter,
} from "./query-results/QueryResultsView";
import {
    createInvoiceAdapter,
    parseInvoicePage,
} from "./query-results/invoice-bridge";
import { readOnlyCanvasAdapters } from "./semantic-renderer/mcp-bridge";
import {
    CanvasLibraryView,
    parseCanvasContentMetadata,
    type CanvasContentMetadata,
} from "./semantic-renderer/canvas-library";
import { SemanticCanvasRenderer } from "./semantic-renderer";
import {
    createReviewedExecutionAdapter,
    parseReviewedExecution,
} from "./semantic-renderer/reviewed-execution";
import type { ReviewedExecutionContext } from "./semantic-renderer/reviewed-execution";
import { InvoiceReviewPanel } from "./query-results/InvoiceReviewPanel";

const FIXTURE_QUERY_TOOL = "canvas_fixture_search";
const FIXTURE_ARTIFACT_STATUS_TOOL = "canvas_fixture_artifact_status";
const FIXTURE_HANDLE_PATTERN = /^art_[A-Za-z0-9_-]{22}$/u;

type HostResultState = "none" | "success" | "error";
type HostInputState = "none" | "accepted" | "ignored";

interface DisplayHostContext {
    theme: string | null;
    locale: string | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseHostQuery(argumentsValue: unknown): string | null {
    if (!isRecord(argumentsValue)) {
        return null;
    }
    const query = argumentsValue.query;
    if (
        typeof query !== "string" ||
        query.length === 0 ||
        !/\S/u.test(query) ||
        Array.from(query).length > 64
    ) {
        return null;
    }
    return query;
}

function parseQueryActionResult(value: unknown): QueryActionResult {
    if (!isRecord(value) || !Array.isArray(value.rows)) {
        throw new Error("Unexpected query result shape.");
    }

    const rows = value.rows.map((row): QueryActionResult["rows"][number] => {
        if (
            !isRecord(row) ||
            typeof row.id !== "string" ||
            typeof row.title !== "string" ||
            typeof row.category !== "string"
        ) {
            throw new Error("Unexpected query result row.");
        }
        return { id: row.id, title: row.title, category: row.category };
    });

    let artifact: QueryActionResult["artifact"];
    if (value.artifact === null) {
        artifact = null;
    } else if (
        isRecord(value.artifact) &&
        typeof value.artifact.handle === "string" &&
        FIXTURE_HANDLE_PATTERN.test(value.artifact.handle)
    ) {
        artifact = { handle: value.artifact.handle as ArtifactHandle };
    } else {
        throw new Error("Unexpected query artifact shape.");
    }

    let error: QueryActionResult["error"];
    if (value.error === null) {
        error = null;
    } else if (
        isRecord(value.error) &&
        value.error.code === "no_matches" &&
        value.error.message === "No records matched that query."
    ) {
        error = {
            code: "no_matches",
            message: "No records matched that query.",
        };
    } else {
        throw new Error("Unexpected query error shape.");
    }

    return { rows, artifact, error };
}

function parseArtifactStatus(value: unknown): ArtifactStatus {
    if (!isRecord(value)) {
        throw new Error("Unexpected artifact status shape.");
    }
    if (
        value.status === "ready" ||
        value.status === "processing" ||
        value.status === "unavailable"
    ) {
        return value.status;
    }
    throw new Error("Unexpected artifact status value.");
}

function getStructuredResult(
    result: Awaited<ReturnType<App["callServerTool"]>>,
) {
    if (result.isError || result.structuredContent === undefined) {
        throw new Error("The fixture tool call failed.");
    }
    return result.structuredContent;
}

function createFixtureAdapter(app: App): QueryResultsAdapter {
    return {
        async submitQuery({ query }) {
            const result = await app.callServerTool({
                name: FIXTURE_QUERY_TOOL,
                arguments: { query },
            });
            return parseQueryActionResult(getStructuredResult(result));
        },
        async getArtifactStatus(handle) {
            const result = await app.callServerTool({
                name: FIXTURE_ARTIFACT_STATUS_TOOL,
                arguments: { handle },
            });
            return parseArtifactStatus(getStructuredResult(result));
        },
    };
}

function displayContext(
    context: McpUiHostContext | undefined,
): DisplayHostContext {
    return {
        theme: typeof context?.theme === "string" ? context.theme : null,
        locale: typeof context?.locale === "string" ? context.locale : null,
    };
}

export function McpCanvasView() {
    const [hostInput, setHostInput] = useState<HostToolInput | null>(null);
    const [hostResult, setHostResult] = useState<HostToolResult | null>(null);
    const [invoiceMode, setInvoiceMode] = useState(false);
    const [hostInputState, setHostInputState] =
        useState<HostInputState>("none");
    const [hostResultState, setHostResultState] =
        useState<HostResultState>("none");
    const [hostContext, setHostContext] = useState<DisplayHostContext | null>(
        null,
    );
    const [canvasContent, setCanvasContent] =
        useState<CanvasContentMetadata | null>(null);
    const canvasView =
        canvasContent?.kind === "app" ? canvasContent.canvas : null;
    const canvasLibrary =
        canvasContent?.kind === "library" ? canvasContent.library : null;
    const [canvasViewError, setCanvasViewError] = useState(false);
    const [genericExecution, setGenericExecution] =
        useState<GenericExecutionContext | null>(null);
    const [reviewedExecution, setReviewedExecution] =
        useState<ReviewedExecutionContext | null>(null);
    const inputRevision = useRef(0);

    const { app, isConnected, error } = useApp({
        appInfo: { name: "Actions Canvas Query Fixture", version: "0.1.0" },
        capabilities: {},
        onAppCreated: (createdApp) => {
            createdApp.addEventListener(
                "toolinput",
                ({ arguments: toolArguments }) => {
                    const query = parseHostQuery(toolArguments);
                    setInvoiceMode(
                        isRecord(toolArguments) &&
                            typeof toolArguments.handle === "string" &&
                            FIXTURE_HANDLE_PATTERN.test(toolArguments.handle),
                    );
                    inputRevision.current += 1;
                    setCanvasContent(null);
                    setReviewedExecution(null);
                    setGenericExecution(null);
                    setCanvasViewError(false);
                    setHostInput({ revision: inputRevision.current, query });
                    setHostInputState(query === null ? "ignored" : "accepted");
                    setHostResultState("none");
                    setHostResult(null);
                },
            );
            createdApp.addEventListener("toolresult", (result) => {
                setReviewedExecution(null);
                setGenericExecution(null);
                const invoicePage = result._meta?.["actions.invoicePage"];
                if (invoicePage !== undefined) {
                    setCanvasContent(null);
                    setCanvasViewError(false);
                    setInvoiceMode(true);
                    try {
                        const parsed = parseInvoicePage(invoicePage);
                        inputRevision.current += 1;
                        setHostResult({
                            revision: inputRevision.current,
                            result: parsed,
                        });
                        setHostResultState(
                            result.isError ? "error" : "success",
                        );
                    } catch {
                        setHostResult({
                            revision: ++inputRevision.current,
                            result: null,
                        });
                        setHostResultState("error");
                    }
                } else {
                    const metadata = result._meta?.["actions.canvas"];
                    if (metadata !== undefined) {
                        setInvoiceMode(false);
                        setHostResultState(
                            result.isError ? "error" : "success",
                        );
                        setHostResult({
                            revision: ++inputRevision.current,
                            result: null,
                        });
                        if (result.isError) {
                            setCanvasContent(null);
                            setCanvasViewError(true);
                        } else {
                            try {
                                const content =
                                    parseCanvasContentMetadata(metadata);
                                if (content.kind === "library") {
                                    if (
                                        [
                                            "actions.appSession",
                                            "actions.reviewedExecution",
                                            "actions.genericExecution",
                                        ].some(
                                            (key) =>
                                                result._meta?.[key] !==
                                                undefined,
                                        )
                                    )
                                        throw new Error(
                                            "Library content cannot carry execution metadata.",
                                        );
                                    setCanvasContent(content);
                                    setCanvasViewError(false);
                                    return;
                                }
                                const parsed = content.canvas;
                                setCanvasContent(content);
                                setGenericExecution(null);
                                setReviewedExecution(null);
                                if (
                                    !parsed.preview &&
                                    result._meta?.[
                                        "actions.genericExecution"
                                    ] !== undefined
                                ) {
                                    setGenericExecution(
                                        parseGenericExecution(
                                            result._meta ?? {},
                                            parsed,
                                        ),
                                    );
                                }
                                if (
                                    !parsed.preview &&
                                    result._meta?.[
                                        "actions.genericExecution"
                                    ] === undefined &&
                                    (result._meta?.["actions.appSession"] !==
                                        undefined ||
                                        result._meta?.[
                                            "actions.reviewedExecution"
                                        ] !== undefined)
                                ) {
                                    setReviewedExecution(
                                        parseReviewedExecution(
                                            result._meta ?? {},
                                            parsed,
                                        ),
                                    );
                                }
                                setCanvasViewError(false);
                            } catch {
                                setCanvasContent(null);
                                setCanvasViewError(true);
                                setHostResultState("error");
                            }
                        }
                    } else {
                        setHostResultState(
                            result.isError ? "error" : "success",
                        );
                    }
                    if (result.isError && metadata === undefined)
                        setHostResult({
                            revision: ++inputRevision.current,
                            result: null,
                        });
                }
            });
            createdApp.addEventListener("hostcontextchanged", () => {
                setHostContext(displayContext(createdApp.getHostContext()));
            });
        },
    });

    useHostStyleVariables(app, app?.getHostContext());

    useEffect(() => {
        if (isConnected && app) {
            setHostContext(displayContext(app.getHostContext()));
        } else {
            setCanvasContent(null);
            setReviewedExecution(null);
            setGenericExecution(null);
            setCanvasViewError(false);
        }
    }, [app, isConnected]);

    const adapter = useMemo(
        () =>
            app && isConnected
                ? invoiceMode
                    ? createInvoiceAdapter(app)
                    : createFixtureAdapter(app)
                : null,
        [app, isConnected, invoiceMode],
    );
    const reviewedAdapter = useMemo(
        () =>
            app && isConnected && reviewedExecution
                ? createReviewedExecutionAdapter(app, reviewedExecution)
                : null,
        [app, isConnected, reviewedExecution],
    );

    return (
        <>
            <details
                aria-label="MCP Apps connection"
                className="mcp-connection"
            >
                <summary>Host connection details</summary>
                {error ? (
                    <p role="alert">Could not connect to the MCP host.</p>
                ) : (
                    <p role="status" data-testid="mcp-connection-state">
                        {isConnected
                            ? "Connected to MCP host"
                            : "Connecting to MCP host…"}
                    </p>
                )}
                <dl className="mcp-connection__details">
                    <div>
                        <dt>Host theme</dt>
                        <dd data-testid="mcp-host-theme">
                            {hostContext?.theme ?? "unset"}
                        </dd>
                    </div>
                    <div>
                        <dt>Host locale</dt>
                        <dd data-testid="mcp-host-locale">
                            {hostContext?.locale ?? "unset"}
                        </dd>
                    </div>
                    <div>
                        <dt>Tool input</dt>
                        <dd data-testid="mcp-tool-input-state">
                            {hostInputState}
                        </dd>
                    </div>
                    <div>
                        <dt>Tool result</dt>
                        <dd data-testid="mcp-tool-result-state">
                            {hostResultState}
                        </dd>
                    </div>
                </dl>
            </details>
            {canvasLibrary ? (
                <CanvasLibraryView library={canvasLibrary} />
            ) : canvasView ? (
                <section aria-label="Semantic Canvas app">
                    {genericExecution && app && !canvasView.preview ? (
                        <GenericSemanticView
                            key={genericExecution.token}
                            app={app}
                            canvas={canvasView}
                            context={genericExecution}
                        />
                    ) : (
                        <>
                            {canvasView.spec.visibility.includes("app") ? (
                                <p role="status">
                                    {reviewedAdapter
                                        ? "Semantic form bindings are read-only. Saved-result review and execution controls are available below."
                                        : "This app is displayed read-only; interactive actions are disabled."}
                                </p>
                            ) : null}
                            <SemanticCanvasRenderer
                                spec={canvasView.spec}
                                revision={
                                    canvasView.preview
                                        ? canvasView.revision
                                        : canvasView.revisionId
                                }
                                scopeKey={canvasView.scopeKey}
                                preview={canvasView.preview}
                                viewer="app"
                                adapters={readOnlyCanvasAdapters}
                            />
                        </>
                    )}
                    {reviewedAdapter && reviewedExecution ? (
                        <InvoiceReviewPanel
                            key={reviewedExecution.token}
                            adapter={reviewedAdapter}
                            handle={reviewedExecution.handle}
                        />
                    ) : null}
                </section>
            ) : canvasViewError ? (
                <main aria-label="Canvas app unavailable">
                    <p role="alert">Canvas content could not be validated.</p>
                </main>
            ) : adapter ? (
                <QueryResultsView
                    adapter={adapter}
                    hostInput={hostInput}
                    hostResult={hostResult}
                    readOnly={invoiceMode}
                />
            ) : (
                <main aria-labelledby="canvas-view-title">
                    <h1 id="canvas-view-title">Canvas View</h1>
                    <p>The query fixture appears after the MCP handshake.</p>
                </main>
            )}
        </>
    );
}
