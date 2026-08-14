export const runtimeQueryKeys = {
  root: ["runtime"] as const,
  actions: () => ["runtime", "actions"] as const,
  runs: (runType = "all") => ["runtime", "runs", runType] as const,
  run: (runId: string) => ["runtime", "run", runId] as const,
  config: () => ["runtime", "config"] as const,
};
