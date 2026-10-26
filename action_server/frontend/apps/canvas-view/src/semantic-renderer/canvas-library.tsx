import {
    parseCanvasSpec,
    parseCanvasViewMetadata,
    type CanvasViewMetadata,
} from "./mcp-bridge";

interface LibraryApplication {
    applicationId: string;
    title: string;
    activeRevisionId: string | null;
    summary: string | null;
}

export interface CanvasLibraryMetadata {
    applications: LibraryApplication[];
    currentApplicationId: string | null;
    emptyMessage: string | null;
}

export type CanvasContentMetadata =
    | { kind: "library"; library: CanvasLibraryMetadata }
    | { kind: "app"; canvas: CanvasViewMetadata };

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iu;
const digest = /^sha256:[0-9a-f]{64}$/u;

function record(value: unknown): value is Record<string, unknown> {
    return (
        typeof value === "object" &&
        value !== null &&
        !Array.isArray(value) &&
        (Object.getPrototypeOf(value) === Object.prototype ||
            Object.getPrototypeOf(value) === null)
    );
}

function keys(value: Record<string, unknown>, expected: string[]): boolean {
    return (
        Object.keys(value).length === expected.length &&
        expected.every((key) => Object.hasOwn(value, key))
    );
}

function text(value: unknown, max: number): value is string {
    return (
        typeof value === "string" &&
        value.length > 0 &&
        Array.from(value).length <= max
    );
}

function unique(applications: LibraryApplication[]): void {
    if (
        new Set(applications.map((app) => app.applicationId)).size !==
        applications.length
    )
        throw new Error("Duplicate Canvas library application.");
}

function authoringLibrary(
    value: Record<string, unknown>,
): CanvasLibraryMetadata {
    if (
        !keys(value, ["applications"]) ||
        !Array.isArray(value.applications) ||
        value.applications.length > 200
    )
        throw new Error("Invalid Canvas application library.");
    const applications = value.applications.map((item): LibraryApplication => {
        if (
            !record(item) ||
            !keys(item, ["applicationId", "title", "activeRevisionId"]) ||
            !text(item.applicationId, 128) ||
            !uuid.test(item.applicationId) ||
            !text(item.title, 128) ||
            !(
                item.activeRevisionId === null ||
                (typeof item.activeRevisionId === "string" &&
                    digest.test(item.activeRevisionId))
            )
        )
            throw new Error("Invalid Canvas library application.");
        return {
            applicationId: item.applicationId,
            title: item.title,
            activeRevisionId: item.activeRevisionId,
            summary: null,
        };
    });
    unique(applications);
    return {
        applications,
        currentApplicationId: null,
        emptyMessage:
            applications.length === 0
                ? "No apps are available to you yet. Ask your assistant to create one."
                : null,
    };
}

function projectedApplication(item: unknown) {
    if (
        !record(item) ||
        !keys(item, ["appId", "title", "revisionId", "summary", "spec"]) ||
        !text(item.appId, 128) ||
        !text(item.title, 128) ||
        !text(item.revisionId, 128) ||
        !text(item.summary, 1024)
    )
        throw new Error("Invalid Canvas library projection.");
    const spec = parseCanvasSpec(item.spec);
    if (spec.title !== item.title)
        throw new Error("Canvas library title differs from its spec.");
    return {
        application: {
            applicationId: item.appId,
            title: item.title,
            activeRevisionId: item.revisionId,
            summary: item.summary,
        },
        spec,
    };
}

function projectedLibrary(
    value: Record<string, unknown>,
): CanvasLibraryMetadata {
    if (
        !keys(value, ["apps", "currentApp", "empty", "emptyMessage"]) ||
        !Array.isArray(value.apps) ||
        value.apps.length > 200 ||
        value.empty !== (value.apps.length === 0) ||
        (value.empty
            ? !text(value.emptyMessage, 1024)
            : value.emptyMessage !== null)
    )
        throw new Error("Invalid Canvas library state.");
    const entries = value.apps.map(projectedApplication);
    const applications = entries.map((item) => item.application);
    unique(applications);
    let currentApplicationId: string | null = null;
    if (value.currentApp !== null) {
        const current = projectedApplication(value.currentApp);
        if (
            !entries.some(
                (entry) => JSON.stringify(entry) === JSON.stringify(current),
            )
        )
            throw new Error(
                "Current Canvas application is outside the library.",
            );
        currentApplicationId = current.application.applicationId;
    }
    return {
        applications,
        currentApplicationId,
        emptyMessage:
            typeof value.emptyMessage === "string" ? value.emptyMessage : null,
    };
}

/** Parse disjoint library and app wire shapes without granting execution. */
export function parseCanvasContentMetadata(
    value: unknown,
): CanvasContentMetadata {
    if (!record(value)) throw new Error("Canvas content must be an object.");
    if (Object.hasOwn(value, "applications") || Object.hasOwn(value, "apps")) {
        if (
            new globalThis.TextEncoder().encode(JSON.stringify(value))
                .byteLength >
            1024 * 1024
        )
            throw new Error("Canvas library exceeds its size limit.");
        return {
            kind: "library",
            library: Object.hasOwn(value, "applications")
                ? authoringLibrary(value)
                : projectedLibrary(value),
        };
    }
    return { kind: "app", canvas: parseCanvasViewMetadata(value) };
}

export function CanvasLibraryView({
    library,
}: {
    library: CanvasLibraryMetadata;
}) {
    return (
        <main aria-labelledby="canvas-library-title">
            <h1 id="canvas-library-title">Action Canvas library</h1>
            {library.emptyMessage ? (
                <p role="status">{library.emptyMessage}</p>
            ) : null}
            {library.applications.length > 0 ? (
                <ul aria-label="Canvas applications">
                    {library.applications.map((app) => (
                        <li key={app.applicationId}>
                            <strong>{app.title}</strong>
                            {app.applicationId ===
                            library.currentApplicationId ? (
                                <span>Current</span>
                            ) : null}
                            {app.summary ? <p>{app.summary}</p> : null}
                        </li>
                    ))}
                </ul>
            ) : null}
        </main>
    );
}
