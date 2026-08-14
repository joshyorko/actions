import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { WebsocketConn } from "../src/shared/utils/websocketConn";

class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((message: MessageEvent) => void) | null = null;
  close = vi.fn(() => this.onclose?.());
  send = vi.fn();

  constructor(public readonly url: string) {
    FakeWebSocket.instances.push(this);
  }
}

beforeEach(() => {
  vi.useFakeTimers();
  FakeWebSocket.instances = [];
  vi.stubGlobal("WebSocket", FakeWebSocket);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("WebsocketConn", () => {
  it("does not reconnect after disconnect cancels a scheduled reconnect", async () => {
    const socket = new WebsocketConn("ws://example.test");
    const connecting = socket.connect();
    FakeWebSocket.instances[0].onopen?.();
    await connecting;
    FakeWebSocket.instances[0].onclose?.();

    socket.disconnect();
    await vi.advanceTimersByTimeAsync(1000);

    expect(FakeWebSocket.instances).toHaveLength(1);
  });

  it("schedules only one reconnect when the same socket closes twice", async () => {
    const socket = new WebsocketConn("ws://example.test");
    const connecting = socket.connect();
    FakeWebSocket.instances[0].onopen?.();
    await connecting;

    FakeWebSocket.instances[0].onclose?.();
    FakeWebSocket.instances[0].onclose?.();

    expect(vi.getTimerCount()).toBe(1);
    await vi.advanceTimersByTimeAsync(1000);

    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it("handles close and error notifications without duplicate reconnects", async () => {
    const socket = new WebsocketConn("ws://example.test");
    const connecting = socket.connect();
    FakeWebSocket.instances[0].onerror?.();
    await expect(connecting).rejects.toBeUndefined();
    FakeWebSocket.instances[0].onclose?.();
    expect(vi.getTimerCount()).toBe(1);
    await vi.advanceTimersByTimeAsync(1000);

    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it("ignores a stale close after a newer socket is active", async () => {
    const socket = new WebsocketConn("ws://example.test");
    const connecting = socket.connect();
    FakeWebSocket.instances[0].onopen?.();
    await connecting;
    const oldSocket = FakeWebSocket.instances[0];
    oldSocket.onclose?.();
    await vi.advanceTimersByTimeAsync(1000);

    const reconnecting = socket.connect();
    FakeWebSocket.instances[1].onopen?.();
    await reconnecting;
    oldSocket.onclose?.();

    expect(vi.getTimerCount()).toBe(0);
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it("does not reconnect after repeated disconnect disposes a scheduled retry", async () => {
    const socket = new WebsocketConn("ws://example.test");
    const connecting = socket.connect();
    FakeWebSocket.instances[0].onopen?.();
    await connecting;
    FakeWebSocket.instances[0].onclose?.();

    socket.disconnect();
    socket.disconnect();
    await vi.advanceTimersByTimeAsync(1000);

    expect(vi.getTimerCount()).toBe(0);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });
});
