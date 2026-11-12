import { createRoot } from "react-dom/client";
import { useRef, useState } from "react";

import "./browser-harness.css";
import {
    createCapabilityRef,
    SemanticCanvas,
    SemanticForm,
    SemanticStatus,
    SemanticTable,
} from "./index";
import type { CapabilityDispatcher } from "./index";
import type { CanvasNode } from "./types";
import { parseCanvasSpec, readOnlyCanvasAdapters } from "./mcp-bridge";
import {
    SemanticCard,
    SemanticChart,
    SemanticLog,
    SemanticInspector,
    SemanticCanvasRenderer,
} from "./components";

interface SearchInput {
    query: string;
}

interface SearchOutput {
    rows: Array<{ id: string; label: string }>;
}

const capability = createCapabilityRef<"search", SearchInput, SearchOutput>(
    "search",
);

const scenario = new window.URLSearchParams(window.location.search).get(
    "scenario",
);
function ComponentHarness() {
    const completePending = useRef<(() => void) | undefined>(undefined);
    const [dispatchCount, setDispatchCount] = useState(0);
    if (scenario === "v2-nesting") {
        let root: CanvasNode = {
            type: "text",
            id: "leaf",
            text: "Deepest content remains readable.",
        };
        for (let level = 7; level >= 1; level -= 1) {
            root = {
                type: "card",
                id: `card${level}`,
                title: `Level ${level} ${"X".repeat(128)}`,
                children: [root],
            };
        }
        const spec = parseCanvasSpec({
            schemaVersion: "actions.canvas-spec/v2",
            title: "Nested cards",
            visibility: ["app"],
            bindingIds: [],
            root,
        });
        return (
            <SemanticCanvasRenderer
                spec={spec}
                revision="nesting-harness"
                scopeKey="synthetic:nesting"
                viewer="app"
                preview
                adapters={readOnlyCanvasAdapters}
            />
        );
    }
    if (scenario === "v2-presentation") {
        return (
            <>
                <p className="semantic-harness-label">
                    Component harness · admitted synthetic values · not
                    Runtime-hosted or ChatGPT E1
                </p>
                <SemanticCanvas
                    title="Operations overview"
                    revision="v2-presentation-harness"
                    visibility={["app"]}
                    viewer="app"
                    preview={false}
                >
                    <SemanticCard title="Daily activity">
                        <SemanticChart
                            title="Processed items"
                            chartType="bar"
                            points={[
                                { label: "Monday", value: 12 },
                                { label: "Tuesday", value: 24 },
                                { label: "Wednesday", value: 18 },
                            ]}
                        />
                        <SemanticChart
                            title="Queue changes"
                            chartType="line"
                            points={[
                                { label: "Monday", value: 4 },
                                { label: "Tuesday", value: -2 },
                                { label: "Wednesday", value: 0 },
                            ]}
                        />
                        <SemanticLog
                            title="Run messages"
                            messages={Array.from(
                                { length: 40 },
                                (_, index) =>
                                    `Message ${index + 1}: synthetic retained event`,
                            )}
                        />
                        <SemanticInspector
                            title="Selected record"
                            fields={[
                                {
                                    key: "id",
                                    label: "Identifier",
                                    value: "record-" + "a".repeat(120),
                                },
                                {
                                    key: "enabled",
                                    label: "Enabled",
                                    value: false,
                                },
                                { key: "count", label: "Count", value: 0 },
                            ]}
                        />
                    </SemanticCard>
                </SemanticCanvas>
            </>
        );
    }
    const dispatch: CapabilityDispatcher<
        "search",
        SearchInput,
        SearchOutput
    > = async (_reference, input) => {
        setDispatchCount((count) => count + 1);
        if (scenario === "error") throw new Error("Synthetic backend failure");
        if (scenario === "empty") return { rows: [] };
        const result = {
            rows: [
                {
                    id: "synthetic-record-1",
                    label: `Synthetic result for “${input.query}”`,
                },
            ],
        };
        if (scenario === "loading") {
            return new Promise((resolve) => {
                completePending.current = () => resolve(result);
            });
        }
        return result;
    };
    return (
        <>
            <p className="semantic-harness-label">
                Component harness · synthetic data · not Runtime-hosted or
                ChatGPT E1
            </p>
            {scenario === "loading" ? (
                <button
                    type="button"
                    onClick={() => completePending.current?.()}
                >
                    Complete synthetic request
                </button>
            ) : null}
            {scenario ? (
                <p>
                    Synthetic dispatches:{" "}
                    <span data-testid="synthetic-dispatch-count">
                        {dispatchCount}
                    </span>
                </p>
            ) : null}
            <SemanticCanvas
                title="Semantic Canvas components"
                revision="component-harness"
                preview={false}
                visibility={["app", "model"]}
                viewer="app"
            >
                <SemanticStatus
                    state="success"
                    message="Enter a search term to see the form and result roundtrip."
                />
                <SemanticForm<"search", SearchInput, SearchOutput>
                    scopeKey="component-harness:search"
                    submitLabel="Search synthetic records"
                    fields={[
                        {
                            name: "query",
                            label: "Search term",
                            type: "text",
                            required: true,
                        },
                    ]}
                    capability={capability}
                    toInput={(values) => ({
                        query: String(values.query ?? ""),
                    })}
                    dispatch={dispatch}
                    renderResult={(result) => (
                        <SemanticTable
                            caption="Synthetic search results"
                            columns={[{ key: "label", label: "Result" }]}
                            rows={result.rows}
                        />
                    )}
                />
                <SemanticTable
                    caption="Synthetic operations records"
                    columns={Array.from({ length: 16 }, (_, index) => ({
                        key: `field${index}`,
                        label: `Field ${index + 1}`,
                    }))}
                    rows={[
                        Object.fromEntries(
                            Array.from({ length: 16 }, (_, index) => [
                                `field${index}`,
                                `Record ${index + 1}`,
                            ]),
                        ),
                    ]}
                />
            </SemanticCanvas>
        </>
    );
}

const root = document.getElementById("root");
if (!root) throw new Error("Missing browser harness mount point.");
createRoot(root).render(<ComponentHarness />);
