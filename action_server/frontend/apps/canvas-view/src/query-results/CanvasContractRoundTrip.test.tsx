import { readFileSync, writeFileSync } from "node:fs";
import { env } from "node:process";

import Ajv2020 from "ajv/dist/2020.js";
import { describe, expect, it } from "vitest";

import fixture from "../../../../../../docs/contracts/canvas/fixtures/query-results-v0.1.fixture.json";
import schema from "../../../../../../docs/contracts/canvas/fixtures/query-results-v0.1.schema.json";
import type {
    QueryActionResult,
    QueryInput,
    QueryResultsAdapter,
} from "./QueryResultsView";

interface QueryResultsFixture {
    fixtureVersion: "query-results-fixture/0.1";
    input: QueryInput;
    success: QueryActionResult;
    domainError: QueryActionResult;
    view: unknown;
}

const validateFixture = new Ajv2020({
    allErrors: true,
    strict: true,
}).compile<QueryResultsFixture>(schema);
const roundTripRequired = env.ACTIONS_CANVAS_REQUIRE_ROUNDTRIP === "1";
const roundTripPathsAvailable =
    Boolean(env.ACTIONS_CANVAS_PYTHON_JSON_PATH) &&
    Boolean(env.ACTIONS_CANVAS_TYPESCRIPT_JSON_PATH);

function isQueryResultsFixture(value: unknown): value is QueryResultsFixture {
    return validateFixture(value);
}

function cloneFixture(): typeof fixture {
    return JSON.parse(JSON.stringify(fixture)) as typeof fixture;
}

function assertTypedDispatchBoundary(adapter: QueryResultsAdapter): void {
    adapter.submitQuery({ query: "alpha" });

    adapter.submitQuery({
        query: "alpha",
        // @ts-expect-error Canvas UI data does not select a binding or tool.
        bindingId: "binding.search-records",
    });

    // @ts-expect-error The adapter exposes fixed typed methods, not tool dispatch.
    adapter.callTool("canvas_fixture_search", {});
}

void assertTypedDispatchBoundary;

describe("Canvas query-results JSON Schema interchange", () => {
    it("validates the one shared fixture and rejects dynamic binding changes", () => {
        expect(isQueryResultsFixture(fixture)).toBe(true);

        const changedBinding = cloneFixture();
        changedBinding.view.form.submitBindingId = "binding.user-selected";
        expect(isQueryResultsFixture(changedBinding)).toBe(false);

        const selectedTool = cloneFixture();
        Object.assign(selectedTool.input, { toolName: "user-selected-tool" });
        expect(isQueryResultsFixture(selectedTool)).toBe(false);
    });

    it.skipIf(!roundTripPathsAvailable && !roundTripRequired)(
        "validates Python JSON and writes its typed TypeScript round trip",
        () => {
            const inputPath = env.ACTIONS_CANVAS_PYTHON_JSON_PATH;
            const outputPath = env.ACTIONS_CANVAS_TYPESCRIPT_JSON_PATH;
            if (!inputPath || !outputPath) {
                throw new Error("Python round-trip paths are required.");
            }

            const inputText = readFileSync(inputPath, "utf8");
            const parsed: unknown = JSON.parse(inputText);
            expect(isQueryResultsFixture(parsed)).toBe(true);
            if (!isQueryResultsFixture(parsed)) {
                throw new Error(
                    "Python serialized fixture failed schema validation.",
                );
            }

            const outputText = JSON.stringify(parsed);
            writeFileSync(outputPath, outputText, "utf8");
        },
    );
});
