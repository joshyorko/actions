import { createRoot } from "react-dom/client";

import "./browser-harness.css";
import {
    createCapabilityRef,
    SemanticCanvas,
    SemanticForm,
    SemanticStatus,
    SemanticTable,
} from "./index";
import type { CapabilityDispatcher } from "./index";

interface SearchInput {
    query: string;
}

interface SearchOutput {
    rows: Array<{ id: string; label: string }>;
}

const capability = createCapabilityRef<"search", SearchInput, SearchOutput>(
    "search",
);

const dispatch: CapabilityDispatcher<
    "search",
    SearchInput,
    SearchOutput
> = async (_reference, input) => ({
    rows: [
        {
            id: "synthetic-record-1",
            label: `Synthetic result for “${input.query}”`,
        },
    ],
});

function ComponentHarness() {
    return (
        <>
            <p className="semantic-harness-label">
                Component harness · synthetic data · not Runtime-hosted or
                ChatGPT E1
            </p>
            <SemanticCanvas
                title="Semantic Canvas components"
                revision="component-harness"
                preview
                audience="both"
                viewer="app"
            >
                <SemanticStatus
                    state="success"
                    message="Enter a search term to see the form and result roundtrip."
                />
                <SemanticForm
                    title="Search synthetic records"
                    fields={[
                        {
                            name: "query",
                            label: "Search term",
                            placeholder: "Try a sample phrase",
                            required: true,
                            maxLength: 80,
                        },
                    ]}
                    capability={capability}
                    toInput={(values) => ({ query: values.query })}
                    dispatch={dispatch}
                    renderResult={(result) => (
                        <SemanticTable<{
                            id: string;
                            label: string;
                        }>
                            caption="Synthetic search results"
                            columns={[{ key: "label", label: "Result" }]}
                            rows={result.rows}
                            rowKey={(row) => row.id}
                        />
                    )}
                />
            </SemanticCanvas>
        </>
    );
}

const root = document.getElementById("root");
if (!root) throw new Error("Missing browser harness mount point.");
createRoot(root).render(<ComponentHarness />);
