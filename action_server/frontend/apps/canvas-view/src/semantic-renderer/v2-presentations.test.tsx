import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { SemanticChart, SemanticLog, SemanticInspector } from "./components";

// These exercise admitted presentation values, not Runtime projection admission.
it.each(["bar", "line"] as const)(
    "renders a %s chart with equivalent accessible values",
    (chartType) => {
        render(
            <SemanticChart
                title="Daily totals"
                chartType={chartType}
                points={[
                    { label: "Monday", value: -12.5 },
                    { label: "Tuesday", value: 0 },
                    { label: "Wednesday", value: 20 },
                ]}
            />,
        );
        expect(screen.getByRole("img", { name: "Daily totals" })).toBeTruthy();
        const table = screen.getByRole("table", { name: "Daily totals data" });
        expect(within(table).getAllByRole("row")).toHaveLength(4);
        for (const value of [
            "Monday",
            "-12.5",
            "Tuesday",
            "0",
            "Wednesday",
            "20",
        ]) {
            expect(
                within(table).getByRole("cell", { name: value }),
            ).toBeTruthy();
        }
        expect(document.querySelector("svg")?.outerHTML).not.toMatch(
            /NaN|Infinity/,
        );
    },
);

it("does not silently truncate an oversized chart", () => {
    render(
        <SemanticChart
            title="Too many points"
            chartType="bar"
            points={Array.from({ length: 201 }, (_, index) => ({
                label: String(index),
                value: index,
            }))}
        />,
    );
    expect(screen.getByRole("alert").textContent).toContain("exceeds");
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.queryByRole("table")).toBeNull();
});

it("renders log snapshots in source order as plain text without a live history", () => {
    render(
        <SemanticLog
            title="Build log"
            messages={["started", "<script>unsafe()</script>", "finished"]}
        />,
    );
    const region = screen.getByRole("region", { name: "Build log entries" });
    expect(region.getAttribute("tabindex")).toBe("0");
    expect(
        within(region)
            .getAllByRole("listitem")
            .map((entry) => entry.textContent),
    ).toEqual(["started", "<script>unsafe()</script>", "finished"]);
    expect(region.getAttribute("aria-live")).toBeNull();
    expect(screen.queryByRole("log")).toBeNull();
    expect(document.querySelector("script")).toBeNull();
});

it("rejects oversized log snapshots instead of showing a partial history", () => {
    render(
        <SemanticLog
            title="Oversized"
            messages={Array.from({ length: 501 }, () => "entry")}
        />,
    );
    expect(screen.getByRole("alert").textContent).toContain("exceeds");
    expect(screen.queryByRole("list")).toBeNull();
});

it("preserves scalar inspector values without interpreting markup", () => {
    render(
        <SemanticInspector
            title="Run details"
            fields={[
                { key: "enabled", label: "Enabled", value: false },
                { key: "count", label: "Count", value: 0 },
                { key: "missing", label: "Missing", value: null },
                { key: "empty", label: "Empty", value: "" },
                {
                    key: "content",
                    label: "Content",
                    value: "<script>unsafe()</script>",
                },
            ]}
        />,
    );
    const region = screen.getByRole("region", { name: "Run details" });
    expect(
        within(region)
            .getAllByRole("definition")
            .map((entry) => entry.textContent),
    ).toEqual(["false", "0", "null", '""', "<script>unsafe()</script>"]);
    expect(document.querySelector("script")).toBeNull();
});

it("refuses oversized inspector projections", () => {
    render(
        <SemanticInspector
            title="Oversized"
            fields={Array.from({ length: 17 }, (_, index) => ({
                key: String(index),
                label: String(index),
                value: index,
            }))}
        />,
    );
    expect(screen.getByRole("alert").textContent).toContain("exceeds");
    expect(screen.queryByRole("definition")).toBeNull();
});
