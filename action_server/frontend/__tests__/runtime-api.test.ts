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
    expect(fetchMock.mock.calls[1][1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({ value: 1 }),
    });
  });

  it("preserves typed input values in the action execution request", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ run_id: "run-2" }), { status: 200 }),
      );

    await runRuntimeAction({
      actionPackageName: "My Package",
      actionName: "Do Work",
      args: { count: 2, enabled: true, nested: { name: "Ada" } },
    });

    expect(String(fetchMock.mock.calls[0][0])).toBe(
      "/api/actions/my-package/do-work/run",
    );
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({ count: 2, enabled: true, nested: { name: "Ada" } }),
    });
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
});
