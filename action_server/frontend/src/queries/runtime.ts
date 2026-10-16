import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  cancelRuntimeRun,
  getRuntimeConfig,
  getRuntimeRun,
  listRuntimeActions,
  listRuntimeRuns,
  runRuntimeAction,
  type RuntimeActionRunRequest,
} from "@/shared/runtime-api";
import { runtimeQueryKeys } from "@/shared/runtime-query-keys";
import type { WebsocketStatus } from "@/shared/utils/websocketConn";

export const RUNTIME_RUN_PAGE_SIZE = 200;

const initialWebsocketStatus: WebsocketStatus = {
  phase: "connecting",
  attempt: 0,
  maxAttempts: 5,
};

export const useRuntimeActions = () =>
  useQuery({
    queryKey: runtimeQueryKeys.actions(),
    queryFn: ({ signal }) => listRuntimeActions(signal),
  });

export const useRuntimeRuns = (runType = "all") =>
  useQuery({
    queryKey: runtimeQueryKeys.runs(runType),
    queryFn: ({ signal }) => listRuntimeRuns(runType, signal),
  });

export const useRuntimeRunPages = (runType = "all") =>
  useInfiniteQuery({
    queryKey: runtimeQueryKeys.runPages(runType),
    initialPageParam: 0,
    queryFn: ({ pageParam, signal }) =>
      listRuntimeRuns(runType, signal, {
        limit: RUNTIME_RUN_PAGE_SIZE,
        offset: pageParam,
      }),
    getNextPageParam: (lastPage, _allPages, lastPageParam) =>
      lastPage.length === RUNTIME_RUN_PAGE_SIZE
        ? lastPageParam + RUNTIME_RUN_PAGE_SIZE
        : undefined,
  });

export const useRuntimeWebsocketStatus = () =>
  useQuery({
    queryKey: runtimeQueryKeys.websocketStatus(),
    queryFn: async () => initialWebsocketStatus,
    initialData: initialWebsocketStatus,
    staleTime: Infinity,
  });

export const useRuntimeRun = (runId: string) =>
  useQuery({
    queryKey: runtimeQueryKeys.run(runId),
    queryFn: ({ signal }) => getRuntimeRun(runId, signal),
    enabled: Boolean(runId),
  });

export const useRuntimeConfig = () =>
  useQuery({
    queryKey: runtimeQueryKeys.config(),
    queryFn: ({ signal }) => getRuntimeConfig(signal),
  });

export const useRunRuntimeAction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: RuntimeActionRunRequest) => runRuntimeAction(payload),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: runtimeQueryKeys.runs() }),
  });
};

export const useCancelRuntimeRun = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, signal }: { runId: string; signal?: AbortSignal }) =>
      cancelRuntimeRun(runId, signal),
    onSuccess: (_result, { runId }) =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: runtimeQueryKeys.runs() }),
        queryClient.invalidateQueries({
          queryKey: runtimeQueryKeys.run(runId),
        }),
      ]),
  });
};
