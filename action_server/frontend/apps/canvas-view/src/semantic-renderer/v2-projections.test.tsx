import { render, screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { SemanticCanvasRenderer } from "./components";
import { parseCanvasSpec } from "./mcp-bridge";
import type {
    CanvasSpecDocument,
    SemanticProjectionState,
    SemanticProjectionValue,
    SemanticRendererAdapters,
} from "./types";
import fixture from "../../../../../../docs/contracts/canvas/fixtures/semantic-v2.fixture.json";

// Consumer tests inject trusted current snapshots. They do not qualify Runtime
// authorization, output issuance, canonicalization or stale-response rejection.
const id = "11111111-1111-4111-8111-111111111111";
const canonical =
    '{"details":{"name":"Current record"},"logs":[{"message":"Started"}],"rows":[{"label":"Current row","value":12.5}]}';

function successful(
    canonicalJson = canonical,
    state: "ready" | "empty" = "ready",
): SemanticProjectionState {
    let data: SemanticProjectionValue;
    try {
        data = JSON.parse(canonicalJson);
    } catch {
        data = null;
    }
    return {
        state,
        requestId: "request-current",
        bindingId: "data",
        execution: { runId: id, attemptId: id },
        canonicalJson,
        data,
    };
}

function adaptersFor(
    getProjection: (bindingId: string) => SemanticProjectionState,
) {
    return {
        resolveFormBinding: vi.fn(),
        dispatch: vi.fn(),
        resolveStatusBinding: vi.fn(),
        getStatus: vi.fn(),
        resolveArtifactBinding: vi.fn(),
        openArtifact: vi.fn(),
        getProjection: vi.fn(getProjection),
    } satisfies SemanticRendererAdapters;
}

function only(kind: "chart" | "log" | "inspector") {
    return parseCanvasSpec({
        ...fixture,
        root: {
            ...fixture.root,
            children: fixture.root.children.filter(
                (node) => node.type === kind,
            ),
        },
    });
}

function view(
    adapters: SemanticRendererAdapters,
    spec: CanvasSpecDocument = parseCanvasSpec(fixture),
    preview = false,
    viewer: "app" | "model" = "app",
) {
    return (
        <SemanticCanvasRenderer
            spec={spec}
            revision="current"
            scopeKey="owned:current"
            viewer={viewer}
            preview={preview}
            adapters={adapters}
        />
    );
}

it("renders all data nodes from a current projection without dispatch or artifact effects", () => {
    const adapters = adaptersFor(() => successful());
    render(view(adapters));
    expect(screen.getByRole("table", { name: "Values data" })).toBeTruthy();
    expect(screen.getByRole("cell", { name: "Current row" })).toBeTruthy();
    expect(screen.getByRole("listitem").textContent).toBe("Started");
    expect(
        within(screen.getByRole("region", { name: "Details" })).getByRole(
            "definition",
        ).textContent,
    ).toBe("Current record");
    expect(adapters.getProjection).toHaveBeenCalledWith("data");
    for (const adapter of [
        adapters.dispatch,
        adapters.openArtifact,
        adapters.resolveFormBinding,
        adapters.resolveArtifactBinding,
        adapters.resolveStatusBinding,
        adapters.getStatus,
    ]) {
        expect(adapter).not.toHaveBeenCalled();
    }
});

it.each([
    [
        { state: "not-run", bindingId: "data" } as const,
        "Run this action to load results.",
    ],
    [
        {
            state: "loading",
            bindingId: "data",
            requestId: "request-current",
        } as const,
        "Loading results…",
    ],
    [
        {
            state: "error",
            bindingId: "data",
            message: "Unavailable",
            requestId: "request-current",
        } as const,
        "Results are unavailable. Refresh execution status before retrying.",
    ],
] as const)(
    "distinguishes the %s snapshot from successful output",
    (projection, message) => {
        render(view(adaptersFor(() => projection)));
        expect(screen.getAllByText(message)).toHaveLength(3);
        expect(screen.queryByRole("table")).toBeNull();
        expect(screen.queryByText("No results.")).toBeNull();
    },
);

it("shows admitted empty output distinctly from missing or loading output", () => {
    render(view(adaptersFor(() => successful("{}", "empty"))));
    expect(screen.getAllByText("No results.")).toHaveLength(3);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();
});

it.each(["preview", "model"] as const)(
    "does not inspect private projections in the %s view",
    (mode) => {
        const adapters = adaptersFor(() => successful());
        const spec = parseCanvasSpec({
            ...fixture,
            visibility: ["app", "model"],
        });
        render(
            view(
                adapters,
                spec,
                mode === "preview",
                mode === "model" ? "model" : "app",
            ),
        );
        expect(adapters.getProjection).not.toHaveBeenCalled();
        expect(adapters.dispatch).not.toHaveBeenCalled();
        expect(screen.queryByText("Current record")).toBeNull();
        expect(screen.queryByRole("table")).toBeNull();
    },
);

it("drops prior rendered data when the host replaces its current request snapshot", () => {
    let current: SemanticProjectionState = successful();
    const adapters = adaptersFor(() => current);
    const rendered = render(view(adapters));
    expect(screen.getByRole("cell", { name: "Current row" })).toBeTruthy();
    current = {
        state: "loading",
        bindingId: "data",
        requestId: "request-next",
    };
    rendered.rerender(view(adapters));
    expect(screen.queryByText("Current row")).toBeNull();
    expect(screen.queryByText("Current record")).toBeNull();
    expect(screen.queryByRole("listitem")).toBeNull();
    current = {
        state: "error",
        bindingId: "data",
        message: "Unavailable",
        requestId: "request-next",
    };
    rendered.rerender(view(adapters));
    expect(screen.getAllByRole("alert")).toHaveLength(3);
    expect(screen.queryByRole("table")).toBeNull();
});

it("fails closed when the local projection getter refuses access", () => {
    const adapters = adaptersFor(() => {
        throw new Error("private authorization details");
    });
    render(view(adapters));
    expect(screen.getAllByText("Result data is unavailable.")).toHaveLength(3);
    expect(screen.queryByText("private authorization details")).toBeNull();
});

it("shows unavailable results when the host has no projection getter", () => {
    const adapters: SemanticRendererAdapters = {
        ...adaptersFor(() => successful()),
        getProjection: undefined,
    };
    render(view(adapters));
    expect(screen.getAllByText("Result data is unavailable.")).toHaveLength(3);
    expect(adapters.dispatch).not.toHaveBeenCalled();
});

it("reads bounded canonical output rather than a divergent parsed-data property", () => {
    const projection = {
        ...successful(),
        data: { details: { name: "Unverified replacement" } },
    };
    render(view(adaptersFor(() => projection)));
    expect(
        within(screen.getByRole("region", { name: "Details" })).getByRole(
            "definition",
        ).textContent,
    ).toBe("Current record");
    expect(screen.queryByText("Unverified replacement")).toBeNull();
});

it.each([
    '{"rows":[{"label":"value","value":9007199254740992}]}',
    '{"rows":[{"label":"value","value":1e309}]}',
    '{"rows":[{"label":"value","value":-0}]}',
    '{"rows":[{"label":"e\\u0301","value":1}]}',
    '{"rows":[{"label":"\\ud800","value":1}]}',
    '{"rows":[{"value":1}]}',
    '{"rows":[{"label":"value","value":null}]}',
    '{"rows":{}}',
    "{invalid-json",
])(
    "refuses malformed or unsupported chart values without a partial chart: %s",
    (raw) => {
        render(
            view(
                adaptersFor(() => successful(raw)),
                only("chart"),
            ),
        );
        expect(screen.getByRole("alert").textContent).toBe(
            "This result cannot be displayed.",
        );
        expect(screen.queryByRole("img")).toBeNull();
        expect(screen.queryByRole("table")).toBeNull();
    },
);

it.each([200, 201])(
    "enforces the %i-row chart boundary without truncation",
    (length) => {
        const rows = Array.from({ length }, (_, index) => ({
            label: String(index),
            value: index,
        }));
        render(
            view(
                adaptersFor(() => successful(JSON.stringify({ rows }))),
                only("chart"),
            ),
        );
        if (length === 200) {
            expect(
                within(screen.getByRole("table")).getAllByRole("row"),
            ).toHaveLength(201);
        } else {
            expect(screen.getByRole("alert")).toBeTruthy();
            expect(screen.queryByRole("table")).toBeNull();
        }
    },
);

it.each([256, 257])(
    "bounds chart labels by Unicode code points at %i",
    (length) => {
        const label = "😀".repeat(length);
        render(
            view(
                adaptersFor(() =>
                    successful(JSON.stringify({ rows: [{ label, value: 1 }] })),
                ),
                only("chart"),
            ),
        );
        if (length === 256)
            expect(screen.getByRole("cell", { name: label })).toBeTruthy();
        else expect(screen.getByRole("alert")).toBeTruthy();
    },
);

it.each([500, 501])("enforces the %i-entry log boundary", (length) => {
    render(
        view(
            adaptersFor(() =>
                successful(
                    JSON.stringify({
                        logs: Array.from({ length }, () => ({
                            message: "entry",
                        })),
                    }),
                ),
            ),
            only("log"),
        ),
    );
    if (length === 500)
        expect(screen.getAllByRole("listitem")).toHaveLength(500);
    else {
        expect(screen.getByRole("alert")).toBeTruthy();
        expect(screen.queryByRole("listitem")).toBeNull();
    }
});

it.each([1024, 1025])(
    "enforces the %i-code-point log message boundary",
    (length) => {
        render(
            view(
                adaptersFor(() =>
                    successful(
                        JSON.stringify({
                            logs: [{ message: "é".repeat(length) }],
                        }),
                    ),
                ),
                only("log"),
            ),
        );
        if (length === 1024) expect(screen.getByRole("listitem")).toBeTruthy();
        else expect(screen.getByRole("alert")).toBeTruthy();
    },
);

it.each([4096, 4097])(
    "bounds inspector scalar text at %i code points",
    (length) => {
        render(
            view(
                adaptersFor(() =>
                    successful(
                        JSON.stringify({
                            details: {
                                name: "😀".repeat(length),
                                secret: "undeclared",
                            },
                        }),
                    ),
                ),
                only("inspector"),
            ),
        );
        if (length === 4096)
            expect(
                within(
                    screen.getByRole("region", { name: "Details" }),
                ).getByRole("definition"),
            ).toBeTruthy();
        else expect(screen.getByRole("alert")).toBeTruthy();
        expect(screen.queryByText("undeclared")).toBeNull();
    },
);

it.each(['{"details":{}}', '{"details":{"name":{"nested":"unsupported"}}}'])(
    "refuses absent or nonscalar declared inspector fields: %s",
    (raw) => {
        render(
            view(
                adaptersFor(() => successful(raw)),
                only("inspector"),
            ),
        );
        expect(screen.getByRole("alert")).toBeTruthy();
        expect(
            within(screen.getByRole("region", { name: "Details" })).queryByRole(
                "definition",
            ),
        ).toBeNull();
    },
);

it.each([65536, 65537])(
    "measures the exact canonical UTF-8 byte budget at %i bytes",
    (bytes) => {
        const base = '{"padding":"","rows":[{"label":"One","value":1}]}';
        const remaining =
            bytes - new globalThis.TextEncoder().encode(base).byteLength;
        const padding =
            "é".repeat(Math.floor(remaining / 2)) + (remaining % 2 ? "x" : "");
        const raw = base.replace('"padding":""', `"padding":"${padding}"`);
        expect(new globalThis.TextEncoder().encode(raw).byteLength).toBe(bytes);
        expect(raw.length).toBeLessThan(65536);
        render(
            view(
                adaptersFor(() => successful(raw)),
                only("chart"),
            ),
        );
        if (bytes === 65536)
            expect(screen.getByRole("cell", { name: "One" })).toBeTruthy();
        else {
            expect(screen.getByRole("alert").textContent).toBe(
                "The result exceeds the display limit.",
            );
            expect(screen.queryByRole("table")).toBeNull();
        }
    },
);
