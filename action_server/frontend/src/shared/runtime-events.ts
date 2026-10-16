import type { QueryClient } from "@tanstack/react-query";
import { runtimeQueryKeys } from "./runtime-query-keys";
import { WEBSOCKET_BASE_URL } from "./constants";
import { WebsocketConn, type WebsocketStatus } from "./utils/websocketConn";
import type { RunSummary } from "./types";

export type RuntimeEvent =
  | { type: "connect" | "mtime_changed" }
  | { type: "runs_unavailable" }
  | { type: "runs_collected"; runs: RunSummary[] }
  | { type: "run_added"; run: RunSummary }
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
      event.type === "runs_collected" ||
      event.type === "run_added" ||
      event.type === "runs_unavailable"
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
  const socket = new WebsocketConn(`${WEBSOCKET_BASE_URL}/api/ws/summary`);
  const adapter = createRuntimeEventAdapter(queryClient);

  socket.on("status", (status: WebsocketStatus) => {
    queryClient.setQueryData(runtimeQueryKeys.websocketStatus(), status);
  });

  socket.on("connect", () => {
    void adapter({ type: "connect" });
    void socket.emit("start_listen_run_events").catch(() => undefined);
  });
  socket.on("runs_collected", (runs: RunSummary[]) =>
    adapter({ type: "runs_collected", runs }),
  );
  socket.on("run_added", ({ run }: { run: RunSummary }) =>
    adapter({ type: "run_added", run }),
  );
  socket.on(
    "run_changed",
    (data: Omit<Extract<RuntimeEvent, { type: "run_changed" }>, "type">) =>
      adapter({ type: "run_changed", ...data }),
  );
  socket.on("mtime_changed", () => adapter({ type: "mtime_changed" }));
  socket.on("runs_unavailable", () => adapter({ type: "runs_unavailable" }));
  void socket.connect().catch(() => undefined);
  return () => socket.disconnect();
};
