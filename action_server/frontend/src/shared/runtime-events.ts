import type { QueryClient } from "@tanstack/react-query";
import { runtimeQueryKeys } from "./runtime-query-keys";
import { WEBSOCKET_BASE_URL } from "./constants";
import { WebsocketConn } from "./utils/websocketConn";
import type { Run } from "./types";

export type RuntimeEvent =
  | { type: "connect" | "mtime_changed" }
  | { type: "runs_collected"; runs: Run[] }
  | { type: "run_added"; run: Run }
  | {
      type: "run_changed";
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
  return async (event: RuntimeEvent) => {
    return applyRuntimeEvent(queryClient, event);
  };
};

export const subscribeRuntimeEvents = (queryClient: QueryClient) => {
  const socket = new WebsocketConn(`${WEBSOCKET_BASE_URL}/api/ws`);
  const adapter = createRuntimeEventAdapter(queryClient);

  socket.on("connect", () => {
    void adapter({ type: "connect" });
    void socket.emit("start_listen_run_events");
  });
  socket.on("runs_collected", (runs: Run[]) =>
    adapter({ type: "runs_collected", runs }),
  );
  socket.on("run_added", ({ run }: { run: Run }) =>
    adapter({ type: "run_added", run }),
  );
  socket.on(
    "run_changed",
    (data: Omit<Extract<RuntimeEvent, { type: "run_changed" }>, "type">) =>
      adapter({ type: "run_changed", ...data }),
  );
  socket.on("mtime_changed", () => adapter({ type: "mtime_changed" }));
  void socket.connect();
  return () => socket.disconnect();
};
