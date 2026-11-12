import { describe, expect, it } from "vitest";
import fixture from "../../../../../../docs/contracts/canvas/fixtures/semantic-v2.fixture.json";
import v1 from "../../../../../../docs/contracts/canvas/semantic-v1/canvas-spec-v1.fixture.json";
import { parseCanvasSpec, parseCanvasViewMetadata } from "./mcp-bridge";

const fresh = () => globalThis.structuredClone(fixture);

describe("explicit Canvas semantic v2 foundation", () => {
    it("round trips all four nodes and preserves v1 shape/order", () => {
        expect(parseCanvasSpec(fresh())).toEqual(fixture);
        expect(
            parseCanvasViewMetadata({ preview: true, spec: fresh() }).spec,
        ).toEqual(fixture);
        expect(parseCanvasSpec(v1)).toEqual(v1);
        expect(Object.keys(parseCanvasSpec(v1))).toEqual([
            "schemaVersion",
            "title",
            "visibility",
            "bindingIds",
            "root",
        ]);
    });
    it.each(["actions.canvas-spec/v0", "actions.canvas-spec/v3", null, 1])(
        "refuses unknown version %s",
        (version) => {
            expect(() =>
                parseCanvasSpec({ ...fresh(), schemaVersion: version }),
            ).toThrow();
        },
    );
    it.each([
        "v1",
        "extra",
        "duplicate-id",
        "duplicate-field",
        "unknown-binding",
        "unused-binding",
        "title",
        "empty-fields",
        "fields17",
        "path",
        "surrogate",
        "symbol",
        "getter",
        "inherited",
        "array-hole",
        "array-getter",
    ])("rejects %s", (mutation) => {
        const value = fresh();
        const root = value.root;
        const chart = root.children[0];
        const inspector = root.children[2];
        if (mutation === "v1") value.schemaVersion = "actions.canvas-spec/v1";
        else if (mutation === "extra")
            Object.assign(chart, { url: "https://example.invalid" });
        else if (mutation === "duplicate-id") root.children[1].id = chart.id;
        else if (mutation === "duplicate-field")
            inspector.fields = [...inspector.fields!, ...inspector.fields!];
        else if (mutation === "unknown-binding") chart.bindingId = "missing";
        else if (mutation === "unused-binding") value.bindingIds.push("unused");
        else if (mutation === "title") root.title = "x".repeat(257);
        else if (mutation === "empty-fields") inspector.fields = [];
        else if (mutation === "fields17")
            inspector.fields = Array.from({ length: 17 }, (_, i) => ({
                key: `f${i}`,
                label: "Field",
            }));
        else if (mutation === "path") chart.valueKey = "a.b";
        else if (mutation === "surrogate") root.title = "\ud800";
        else if (mutation === "symbol")
            Object.assign(root, { [Symbol("extra")]: true });
        else if (mutation === "getter")
            Object.defineProperty(root, "title", {
                get: () => {
                    throw new Error("accessor executed");
                },
            });
        else if (mutation === "inherited")
            Object.setPrototypeOf(root, { inherited: true });
        else if (mutation === "array-hole") delete root.children[1];
        else
            Object.defineProperty(root.children, "0", {
                get: () => {
                    throw new Error("accessor executed");
                },
            });
        expect(() => parseCanvasSpec(value)).toThrow();
        try {
            parseCanvasSpec(value);
        } catch (error) {
            expect(String(error)).not.toContain("accessor executed");
        }
    });
    it("enforces exact depth/count/field/text limits through cards", () => {
        const value = fresh();
        value.root.title = "😀".repeat(256);
        value.root.children[2].fields = Array.from({ length: 16 }, (_, i) => ({
            key: `f${i}`,
            label: "x".repeat(256),
        }));
        expect(() => parseCanvasSpec(value)).not.toThrow();
        let root: unknown = { type: "text", id: "leaf", text: "x" };
        for (let i = 0; i < 7; i++)
            root = {
                type: "card",
                id: `c${i}`,
                title: "Card",
                children: [root],
            };
        expect(() =>
            parseCanvasSpec({ ...value, bindingIds: [], root }),
        ).not.toThrow();
        expect(() =>
            parseCanvasSpec({
                ...value,
                bindingIds: [],
                root: { type: "stack", id: "tooDeep", children: [root] },
            }),
        ).toThrow();
        const children = Array.from({ length: 127 }, (_, i) => ({
            type: "text",
            id: `t${i}`,
            text: "x",
        }));
        expect(() =>
            parseCanvasSpec({
                ...value,
                bindingIds: [],
                root: { type: "card", id: "root", title: "Card", children },
            }),
        ).not.toThrow();
        children.push({ type: "text", id: "overflow", text: "x" });
        expect(() =>
            parseCanvasSpec({
                ...value,
                bindingIds: [],
                root: { type: "card", id: "root", title: "Card", children },
            }),
        ).toThrow();
        expect(() =>
            parseCanvasSpec({
                ...value,
                bindingIds: [],
                root: {
                    type: "stack",
                    id: "root",
                    children: Array.from({ length: 9 }, (_, i) => ({
                        type: "text",
                        id: `t${i}`,
                        text: "é".repeat(4096),
                    })),
                },
            }),
        ).toThrow();
    });
});
