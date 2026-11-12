import { describe, expect, it, vi } from "vitest";
import { createGeneratedProjectionController } from "./generated-projection";

const execution = { runId: "run-1", attemptId: "attempt-1" };
const wire = (
    canonicalJson = '{"a":3}',
    data: unknown = JSON.parse(canonicalJson),
) => ({ bindingId: "result", ...execution, canonicalJson, data });
const deferred = () => {
    let resolve!: (value: unknown) => void;
    const promise = new Promise<unknown>((done) => {
        resolve = done;
    });
    return { promise, resolve };
};

// Exact canonical bytes cross-checked against Python canonicalize_json.
const vectors = [
    ['{"é":"é"}', '{"é":"é"}'],
    ['{"":1,"😀":2}', '{"😀":2,"":1}'],
    [
        "[-0,1e-7,0.000001,1.25,9007199254740991]",
        "[0,1e-7,0.000001,1.25,9007199254740991]",
    ],
    ['{"2":2,"10":10}', '{"10":10,"2":2}'],
];

describe("authorized generated projection state", () => {
    it("is inert until explicit load; freezes derived data and clears on begin", async () => {
        const changed = vi.fn();
        const controller = createGeneratedProjectionController(changed);
        expect(controller.getProjection("result").state).toBe("not-run");
        expect(changed).not.toHaveBeenCalled();
        const id = controller.begin("result");
        await controller.load("result", id, execution, async () => wire());
        const state = controller.getProjection("result");
        expect(state.state).toBe("ready");
        if (state.state === "ready") {
            expect(state.data).toEqual({ a: 3 });
            expect(Object.isFrozen(state.data)).toBe(true);
            expect(Object.isFrozen(state.execution)).toBe(true);
        }
        controller.begin("result");
        expect(controller.getProjection("result")).not.toHaveProperty("data");
    });
    it.each(vectors)(
        "accepts Python canonical bytes for %s",
        async (_raw, canonical) => {
            const c = createGeneratedProjectionController(() => {});
            await c.load("result", c.begin("result"), execution, async () =>
                wire(canonical),
            );
            expect(c.getProjection("result").state).toBe("ready");
        },
    );
    it.each(["null", "[]"])("distinguishes empty %s", async (text) => {
        const c = createGeneratedProjectionController(() => {});
        await c.load("result", c.begin("result"), execution, async () =>
            wire(text),
        );
        expect(c.getProjection("result").state).toBe("empty");
    });
    it.each([
        '{"a":1,"a":1}',
        '{"a": 1}',
        "-0",
        "1e-999",
        "9007199254740992",
        '"é"',
        '"\\ud800"',
        "NaN",
        '{"2":2,"10":10}',
        JSON.stringify("x".repeat(65535)),
    ])("rejects noncanonical/nonportable bytes case %#", async (text) => {
        const c = createGeneratedProjectionController(() => {});
        await c.load("result", c.begin("result"), execution, async () =>
            wire(text, null),
        );
        expect(c.getProjection("result").state).toBe("error");
        expect(c.getProjection("result")).not.toHaveProperty("data");
    });
    it.each(["bindingId", "runId", "attemptId", "data"])(
        "rejects mismatched %s",
        async (key) => {
            const c = createGeneratedProjectionController(() => {});
            await c.load("result", c.begin("result"), execution, async () => ({
                ...wire(),
                [key]: "wrong",
            }));
            expect(c.getProjection("result").state).toBe("error");
        },
    );
    it("ignores stale completion and stale denial after a newer request", async () => {
        const c = createGeneratedProjectionController(() => {});
        const first = c.begin("result");
        const pending = deferred();
        const loading = c.load(
            "result",
            first,
            execution,
            () => pending.promise,
        );
        const next = c.begin("result");
        await c.load("result", next, execution, async () => wire('{"a":4}'));
        pending.resolve(wire());
        await loading;
        c.fail("result", first);
        expect(c.getProjection("result")).toMatchObject({
            state: "ready",
            data: { a: 4 },
        });
    });
    it("denial clears data and invalidates an in-flight read", async () => {
        const c = createGeneratedProjectionController(() => {});
        const id = c.begin("result");
        const pending = deferred();
        const loading = c.load("result", id, execution, () => pending.promise);
        c.fail("result", id);
        pending.resolve(wire());
        await loading;
        expect(c.getProjection("result").state).toBe("error");
        expect(c.getProjection("result")).not.toHaveProperty("data");
    });
    it("does not read on stale, duplicate or failed generations", async () => {
        const c = createGeneratedProjectionController(() => {});
        const id = c.begin("result");
        c.fail("result", id);
        const read = vi.fn(async () => wire());
        await c.load("result", id, execution, read);
        await c.load("result", "stale", execution, read);
        expect(read).not.toHaveBeenCalled();
    });
    it("rejects errors without leaking their message or prior data", async () => {
        const c = createGeneratedProjectionController(() => {});
        const id = c.begin("result");
        await c.load("result", id, execution, async () => {
            throw new Error("private response");
        });
        expect(c.getProjection("result")).toEqual({
            state: "error",
            bindingId: "result",
            requestId: id,
            message: "Generated result unavailable.",
        });
    });
});
