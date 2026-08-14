import { API_BASE_URL } from "./constants";
import type { ActionPackage, Run, ServerConfig } from "./types";

export type RuntimeActionRunRequest = {
  actionPackageName: string;
  actionName: string;
  args: Record<string, unknown>;
  apiKey?: string;
  workItemQueue?: string;
};

export type RuntimeActionRunResponse = {
  run_id?: string;
  request_id?: string;
  [key: string]: unknown;
};

export class RuntimeApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "RuntimeApiError";
  }
}

const toKebabCase = (value: string) =>
  value.replace(/[\s_]+/g, "-").toLowerCase();

const requestJson = async <T>(
  path: string,
  init: RequestInit = {},
): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...init.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new RuntimeApiError(
      response.status,
      body.detail || body.message || response.statusText,
    );
  }
  return response.json() as Promise<T>;
};

export const listRuntimeActions = (signal?: AbortSignal) =>
  requestJson<ActionPackage[]>("/api/actionPackages", { signal });

export const listRuntimeRuns = (runType = "all", signal?: AbortSignal) => {
  const query =
    runType === "all" ? "" : `?run_type=${encodeURIComponent(runType)}`;
  return requestJson<Run[]>(`/api/runs${query}`, { signal });
};

export const getRuntimeRun = (runId: string, signal?: AbortSignal) =>
  requestJson<Run>(`/api/runs/${encodeURIComponent(runId)}`, { signal });

export const getRuntimeConfig = (signal?: AbortSignal) =>
  requestJson<ServerConfig>("/config", { signal });

export const runRuntimeAction = (
  payload: RuntimeActionRunRequest,
  signal?: AbortSignal,
) =>
  requestJson<RuntimeActionRunResponse>(
    `/api/actions/${toKebabCase(payload.actionPackageName)}/${toKebabCase(payload.actionName)}/run`,
    { method: "POST", body: JSON.stringify(payload.args), signal },
  );

export const cancelRuntimeRun = (runId: string, signal?: AbortSignal) =>
  requestJson<Record<string, unknown>>(
    `/api/runs/${encodeURIComponent(runId)}/cancel`,
    {
      method: "POST",
      signal,
    },
  );
