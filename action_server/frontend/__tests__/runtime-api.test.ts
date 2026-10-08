import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cancelRuntimeRun,
  getRuntimeRun,
  listRuntimeActions,
  listRuntimeRuns,
  runRuntimeAction,
  RuntimeApiError,
} from "../src/shared/runtime-api";

afterEach(() => vi.restoreAllMocks());

describe("Runtime API", () => {
  it("uses typed list and detail calls with the expected endpoints", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: "run-1" }), { status: 200 }),
      );
    await listRuntimeActions();
    await getRuntimeRun("run-1");
    expect(fetchMock.mock.calls.map(([input]) => String(input))).toEqual([
      "/api/actionPackages",
      "/api/runs/run-1",
    ]);
  });

  it("supports typed list and mutation payloads", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ run_id: "run-1" }), { status: 200 }),
      );
    await listRuntimeRuns("robot");
    await runRuntimeAction({
      actionPackageName: "pkg",
      actionName: "task",
      args: { value: 1 },
    });
    expect(String(fetchMock.mock.calls[0][0])).toContain("run_type=robot");
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: "POST" });
  });

  it("requests bounded run-list pages with metadata summaries", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }));

    await listRuntimeRuns("robot", undefined, { limit: 5, offset: 10 });

    expect(String(fetchMock.mock.calls[0][0])).toBe(
      "/api/runs/summary?limit=5&offset=10&run_type=robot",
    );
  });

  it("turns HTTP errors into typed errors and forwards cancellation", async () => {
    const controller = new AbortController();
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "nope" }), { status: 409 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify("cancelled"), { status: 200 }),
      );
    await expect(listRuntimeActions()).rejects.toBeInstanceOf(RuntimeApiError);
    await expect(cancelRuntimeRun("run-1", controller.signal)).resolves.toBe(
      "cancelled",
    );
    expect(fetchMock.mock.calls[1][1]).toMatchObject({
      method: "POST",
      signal: controller.signal,
    });
  });

  it("maps truncated successful JSON to a bounded actionable Runtime error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response('{"runs":[', {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const request = listRuntimeRuns();
    await expect(request).rejects.toMatchObject({
      name: "RuntimeApiError",
      status: 200,
      message: expect.stringMatching(/invalid or incomplete JSON.*refresh/i),
    });
    await expect(request).rejects.not.toMatchObject({
      message: expect.stringMatching(/Unexpected end of JSON input/i),
    });
  });

  it("maps transport rejection to a bounded connection message", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(
      new TypeError("raw transport implementation detail"),
    );

    await expect(listRuntimeRuns()).rejects.toMatchObject({
      name: "RuntimeApiError",
      status: 0,
      message: "Could not reach the Runtime. Check the connection and try again.",
    });
  });
});
