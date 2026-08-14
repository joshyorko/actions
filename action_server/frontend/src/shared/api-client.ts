/* eslint-disable @typescript-eslint/no-explicit-any */

import { Dispatch, SetStateAction } from "react";
import { API_BASE_URL } from "./constants";
import { ArtifactInfo, AsyncLoaded, Run } from "./types";

export const baseUrl = API_BASE_URL;

interface Opts {
  body?: string;
  params?: Record<string, string | readonly string[]>;
}

const serializeParams = (
  params: Record<string, string | readonly string[]>,
) => {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (typeof value === "string") {
      searchParams.append(key, value);
    } else {
      value.forEach((item) => searchParams.append(key, item));
    }
  });
  return searchParams;
};

type CachedModel<T> = AsyncLoaded<T>;

const loadAsync = async <T>(
  url: string,
  method: "POST" | "GET",
  opts?: Opts,
  headers?: HeadersInit,
): Promise<CachedModel<T>> => {
  try {
    let requestURL = url;
    if (opts?.params) requestURL += `?${serializeParams(opts.params)}`;
    const response = await fetch(requestURL, {
      method,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...headers,
      },
      body: opts?.body,
    });
    if (!response.ok)
      return {
        isPending: false,
        errorMessage: `${response.status} (${response.statusText})`,
      };
    return { isPending: false, data: await response.json() };
  } catch (error) {
    return {
      isPending: false,
      errorMessage:
        error instanceof Error ? error.message : JSON.stringify(error),
    };
  }
};

export const collectRunArtifacts = async (
  runId: string,
  setLoaded: Dispatch<SetStateAction<AsyncLoaded<any>>>,
  params: Record<string, string | readonly string[]>,
) => {
  setLoaded({ isPending: true, data: undefined });
  setLoaded(
    await loadAsync(
      `${baseUrl}/api/runs/${runId}/artifacts/text-content`,
      "GET",
      { params },
    ),
  );
};

export const fetchRunArtifactsList = async (
  runId: string,
  setLoaded: Dispatch<SetStateAction<AsyncLoaded<ArtifactInfo[]>>>,
) => {
  setLoaded({ isPending: true, data: undefined });
  setLoaded(
    await loadAsync<ArtifactInfo[]>(
      `${baseUrl}/api/runs/${runId}/artifacts`,
      "GET",
    ),
  );
};

export const collectOAuth2Status = async (
  setLoaded: Dispatch<SetStateAction<AsyncLoaded<any>>>,
  params: Record<string, string | readonly string[]>,
) => {
  setLoaded({ isPending: true, data: undefined });
  setLoaded(await loadAsync(`${baseUrl}/oauth2/status`, "GET", { params }));
};

export const cancelRun = async (runId?: string, requestId?: string) => {
  if (!runId && !requestId)
    throw new Error("Either runId or requestId must be provided.");
  let resolvedRunId = runId;
  if (!resolvedRunId) {
    const result = await loadAsync<{ run_id?: string }>(
      `${baseUrl}/api/runs/run-id-from-request-id/${requestId}`,
      "GET",
    );
    resolvedRunId = result.data?.run_id;
    if (!resolvedRunId)
      throw new Error(
        `Error getting run id from request id: ${result.errorMessage}`,
      );
  }
  return loadAsync(`${baseUrl}/api/runs/${resolvedRunId}/cancel`, "POST");
};

export const fetchRuns = async (runType?: string): Promise<Run[]> => {
  const query =
    runType && runType !== "all"
      ? `?run_type=${encodeURIComponent(runType)}`
      : "";
  const result = await loadAsync<Run[]>(`${baseUrl}/api/runs${query}`, "GET");
  return result.data || [];
};
