export const runtimeQueryKeys = {
  root: ["runtime"] as const,
  actions: () => ["runtime", "actions"] as const,
  runs: (runType?: string) =>
    runType ? (["runtime", "runs", runType] as const) : (["runtime", "runs"] as const),
  runPages: (runType = "all") =>
    ["runtime", "runs", runType, "pages"] as const,
  run: (runId: string) => ["runtime", "run", runId] as const,
  websocketStatus: () => ["runtime", "websocket-status"] as const,
  config: () => ["runtime", "config"] as const,
};
