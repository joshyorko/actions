import { afterEach, describe, expect, it, vi } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import {
  applyRuntimeEvent,
  createRuntimeEventAdapter,
  subscribeRuntimeEvents,
} from "../src/shared/runtime-events";
import { runtimeQueryKeys } from "../src/shared/runtime-query-keys";

afterEach(() => vi.useRealTimers());

describe("Runtime event freshness adapter", () => {
  it("keeps run-page caches under the runs invalidation prefix", () => {
    const pageKey = runtimeQueryKeys.runPages("robot");
    expect(pageKey).toEqual(["runtime", "runs", "robot", "pages"]);
    expect(pageKey.slice(0, 2)).toEqual(runtimeQueryKeys.runs().slice(0, 2));
    expect(pageKey).not.toEqual(runtimeQueryKeys.runs("robot"));
  });

  it("invalidates canonical queries without maintaining a second store", async () => {
    const client = new QueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const adapter = createRuntimeEventAdapter(client);
    await adapter({
      type: "run_changed",
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

  it("treats duplicate and out-of-order events as freshness signals only", async () => {
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
      run_id: "run-1",
      changes: { status: "latest" },
    });
    await adapter({
      type: "run_changed",
      run_id: "run-1",
      changes: { status: "stale" },
    });
    await adapter({
      type: "run_changed",
      run_id: "run-1",
      changes: { status: "staler" },
    });
    expect(invalidate).toHaveBeenCalledTimes(6);
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
    await applyRuntimeEvent(client, { type: "connect" });
    await applyRuntimeEvent(client, { type: "mtime_changed" });
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: runtimeQueryKeys.root,
    });
  });

  it("subscribes the Runtime UI to the bounded summary WebSocket route", async () => {
    let connectedUrl = "";
    class FakeWebSocket {
      onopen: (() => void) | null = null;
      onclose: (() => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: (() => void) | null = null;

      constructor(url: string) {
        connectedUrl = url;
        queueMicrotask(() => this.onopen?.());
      }

      send() {}

      close() {}
    }
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const disconnect = subscribeRuntimeEvents(new QueryClient());
    await new Promise<void>((resolve) => queueMicrotask(resolve));

    expect(connectedUrl).toContain("/api/ws/summary");
    disconnect();
    vi.unstubAllGlobals();
  });

  it("handles rejected summary sockets and publishes bounded connection status", async () => {
    vi.useFakeTimers();
    const client = new QueryClient();
    class FakeWebSocket {
      static instances: FakeWebSocket[] = [];
      onopen: (() => void) | null = null;
      onclose: (() => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: (() => void) | null = null;

      constructor(public readonly url: string) {
        FakeWebSocket.instances.push(this);
      }

      send() {}

      close() {
        this.onclose?.();
      }
    }
    FakeWebSocket.instances = [];
    vi.stubGlobal("WebSocket", FakeWebSocket);
    const unhandled = vi.fn();
    window.addEventListener("unhandledrejection", unhandled);
    const disconnect = subscribeRuntimeEvents(client);

    FakeWebSocket.instances[0].onerror?.();
    FakeWebSocket.instances[0].onclose?.();
    expect(client.getQueryData(runtimeQueryKeys.websocketStatus())).toMatchObject({
      phase: "reconnecting",
      attempt: 1,
    });
    let delay = 1000;
    for (let attempt = 1; attempt <= 5; attempt += 1) {
      await vi.advanceTimersByTimeAsync(delay);
      FakeWebSocket.instances[attempt].onerror?.();
      FakeWebSocket.instances[attempt].onclose?.();
      delay = Math.min(delay * 2, 16_000);
    }

    expect(client.getQueryData(runtimeQueryKeys.websocketStatus())).toMatchObject({
      phase: "offline",
      maxAttempts: 5,
    });
    expect(FakeWebSocket.instances).toHaveLength(6);
    expect(unhandled).not.toHaveBeenCalled();

    disconnect();
    window.removeEventListener("unhandledrejection", unhandled);
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });
});
