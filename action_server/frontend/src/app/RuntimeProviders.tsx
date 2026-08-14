import type { ReactNode } from "react";
import { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ActionServerContext } from "@/shared/context/actionServerContext";
import type { ViewSettings } from "@/shared/context/actionServerContext";
import { useLocalStorage } from "@/shared/hooks/useLocalStorage";
import {
  useRuntimeActions,
  useRuntimeConfig,
  useRuntimeRuns,
} from "@/queries/runtime";
import { subscribeRuntimeEvents } from "@/shared/runtime-events";

export const runtimeQueryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, refetchOnWindowFocus: false },
  },
});

const ActionServerProvider = ({ children }: { children: ReactNode }) => {
  const [viewSettings, setViewSettings] = useLocalStorage<ViewSettings>(
    "view-settings",
    { theme: "dark" },
  );
  const actions = useRuntimeActions();
  const runs = useRuntimeRuns();
  const config = useRuntimeConfig();

  useEffect(() => {
    return subscribeRuntimeEvents(runtimeQueryClient);
  }, []);

  return (
    <ActionServerContext.Provider
      value={{
        viewSettings,
        setViewSettings,
        loadedRuns: {
          data: runs.data,
          isPending: runs.isPending,
          errorMessage: runs.error?.message,
        },
        loadedActions: {
          data: actions.data,
          isPending: actions.isPending,
          errorMessage: actions.error?.message,
        },
        loadedServerConfig: {
          data: config.data,
          isPending: config.isPending,
          errorMessage: config.error?.message,
        },
        setLoadedRuns: () => undefined,
        setLoadedActions: () => undefined,
        setLoadedServerConfig: () => undefined,
      }}
    >
      {children}
    </ActionServerContext.Provider>
  );
};

export const RuntimeProviders = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={runtimeQueryClient}>
    <ActionServerProvider>{children}</ActionServerProvider>
  </QueryClientProvider>
);
