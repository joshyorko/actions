import type { QueryClient } from "@tanstack/react-query";
import { runtimeQueryKeys } from "./runtime-query-keys";
import { WEBSOCKET_BASE_URL } from "./constants";
import { WebsocketConn } from "./utils/websocketConn";

export type RuntimeEvent =
  | { type: "connect" | "mtime_changed"; sequence: number }
  | { type: "runs_collected" | "run_added"; sequence: number }
  | {
      type: "run_changed";
      sequence: number;
      run_id: string;
      changes: Record<string, unknown>;
    };

export const applyRuntimeEvent = async (
  queryClient: QueryClient,
  event: RuntimeEvent,
) => {
  if (event.type === "run_changed") {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: runtimeQueryKeys.runs() }),
      queryClient.invalidateQueries({
        queryKey: runtimeQueryKeys.run(event.run_id),
      }),
    ]);
    return;
  }
  await queryClient.invalidateQueries({
    queryKey:
      event.type === "runs_collected" || event.type === "run_added"
        ? runtimeQueryKeys.runs()
        : runtimeQueryKeys.root,
  });
};

export const createRuntimeEventAdapter = (queryClient: QueryClient) => {
  const latestSequence = new Map<string, number>();
  return async (event: RuntimeEvent) => {
    const identity =
      event.type === "run_changed"
        ? `${event.type}:${event.run_id}`
        : event.type;
    if ((latestSequence.get(identity) ?? -1) >= event.sequence) return;
    latestSequence.set(identity, event.sequence);
    return applyRuntimeEvent(queryClient, event);
  };
};

export const subscribeRuntimeEvents = (queryClient: QueryClient) => {
  const socket = new WebsocketConn(`${WEBSOCKET_BASE_URL}/api/ws`);
  const adapter = createRuntimeEventAdapter(queryClient);
  let sequence = 0;
  const event =
    (type: RuntimeEvent["type"]) =>
    (data?: Omit<RuntimeEvent, "type" | "sequence">) =>
      adapter({ type, sequence: ++sequence, ...(data ?? {}) } as RuntimeEvent);

  socket.on("connect", () => {
    void adapter({ type: "connect", sequence: ++sequence });
    void socket.emit("start_listen_run_events");
  });
  socket.on("runs_collected", event("runs_collected"));
  socket.on("run_added", event("run_added"));
  socket.on("run_changed", event("run_changed"));
  socket.on("mtime_changed", event("mtime_changed"));
  void socket.connect();
  return () => socket.disconnect();
};
