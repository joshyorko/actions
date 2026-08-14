import { describe, expect, it, vi } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import {
  applyRuntimeEvent,
  createRuntimeEventAdapter,
} from "../src/shared/runtime-events";
import { runtimeQueryKeys } from "../src/shared/runtime-query-keys";

describe("Runtime event freshness adapter", () => {
  it("invalidates canonical queries without maintaining a second store", async () => {
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const adapter = createRuntimeEventAdapter(client);
    await adapter({
      type: "run_changed",
      sequence: 2,
      run_id: "run-1",
      changes: {},
    });
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: runtimeQueryKeys.runs(),
    });
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: runtimeQueryKeys.run("run-1"),
    });
  });

  it("ignores duplicate and older events so stale events cannot regress cache data", async () => {
    const client = new QueryClient();
    client.setQueryData(runtimeQueryKeys.run("run-1"), {
      id: "run-1",
      status: "new",
    });
    const adapter = createRuntimeEventAdapter(client);
    const invalidate = vi
      .spyOn(client, "invalidateQueries")
      .mockResolvedValue();
    await adapter({
      type: "run_changed",
      sequence: 3,
      run_id: "run-1",
      changes: { status: "latest" },
    });
    await adapter({
      type: "run_changed",
      sequence: 3,
      run_id: "run-1",
      changes: { status: "stale" },
    });
    await adapter({
      type: "run_changed",
      sequence: 2,
      run_id: "run-1",
      changes: { status: "staler" },
    });
    expect(invalidate).toHaveBeenCalledTimes(2);
    expect(client.getQueryData(runtimeQueryKeys.run("run-1"))).toEqual({
      id: "run-1",
      status: "new",
    });
  });

  it("refreshes all Runtime keys after reconnect and accepts direct events", async () => {
    const client = new QueryClient();
    const invalidate = vi
      .spyOn(client, "invalidateQueries")
      .mockResolvedValue();
    await applyRuntimeEvent(client, { type: "connect", sequence: 1 });
    await applyRuntimeEvent(client, { type: "mtime_changed", sequence: 2 });
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: runtimeQueryKeys.root,
    });
  });
});
