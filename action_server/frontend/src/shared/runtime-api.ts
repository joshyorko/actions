import { API_BASE_URL } from "./constants";
import type { ActionPackage, Run, RunSummary, ServerConfig } from "./types";

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

export type CancelRuntimeRunResponse = "cancelled" | "not-running";

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
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...init.headers,
      },
    });
  } catch (error) {
    if (init.signal?.aborted) throw error;
    throw new RuntimeApiError(
      0,
      "Could not reach the Runtime. Check the connection and try again.",
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detailMessage =
      typeof body.detail === "string"
        ? body.detail
        : body.detail && typeof body.detail.message === "string"
          ? body.detail.message
          : undefined;
    const message =
      detailMessage ||
      (typeof body.message === "string" ? body.message : response.statusText);
    throw new RuntimeApiError(
      response.status,
      message.slice(0, 512),
    );
  }
  try {
    return (await response.json()) as T;
  } catch (error) {
    if (init.signal?.aborted) throw error;
    throw new RuntimeApiError(
      response.status,
      "Runtime returned invalid or incomplete JSON. Refresh and try again.",
    );
  }
};

export const listRuntimeActions = (signal?: AbortSignal) =>
  requestJson<ActionPackage[]>("/api/actionPackages", { signal });

export type RuntimeRunListOptions = {
  limit?: number;
  offset?: number;
};

export const listRuntimeRuns = (
  runType = "all",
  signal?: AbortSignal,
  options: RuntimeRunListOptions = {},
) => {
  const query = new URLSearchParams({
    limit: String(options.limit ?? 200),
  });
  if (options.offset) query.set("offset", String(options.offset));
  if (runType !== "all") query.set("run_type", runType);
  return requestJson<RunSummary[]>(`/api/runs/summary?${query}`, { signal });
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
  requestJson<CancelRuntimeRunResponse>(
    `/api/runs/${encodeURIComponent(runId)}/cancel`,
    {
      method: "POST",
      signal,
    },
  );
