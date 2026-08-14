import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  ActionServerContext,
  defaultActionServerState,
} from "@/shared/context/actionServerContext";
import type { ViewSettings } from "@/shared/context/actionServerContext";
import { useLocalStorage } from "@/shared/hooks/useLocalStorage";
import {
  startTrackActions,
  startTrackRuns,
  startTrackServerConfig,
  stopTrackActions,
  stopTrackRuns,
  stopTrackServerConfig,
} from "@/shared/api-client";
import type {
  LoadedActionsPackages,
  LoadedRuns,
  LoadedServerConfig,
} from "@/shared/types";

const queryClient = new QueryClient();

const ActionServerProvider = ({ children }: { children: ReactNode }) => {
  const [viewSettings, setViewSettings] = useLocalStorage<ViewSettings>(
    "view-settings",
    { theme: "dark" },
  );
  const [loadedRuns, setLoadedRuns] = useState<LoadedRuns>(
    defaultActionServerState.loadedRuns,
  );
  const [loadedActions, setLoadedActions] = useState<LoadedActionsPackages>(
    defaultActionServerState.loadedActions,
  );
  const [loadedServerConfig, setLoadedServerConfig] =
    useState<LoadedServerConfig>(defaultActionServerState.loadedServerConfig);

  useEffect(() => {
    startTrackActions(setLoadedActions);
    startTrackRuns(setLoadedRuns);
    startTrackServerConfig(setLoadedServerConfig);
    return () => {
      stopTrackActions(setLoadedActions);
      stopTrackRuns(setLoadedRuns);
      stopTrackServerConfig(setLoadedServerConfig);
    };
  }, []);

  return (
    <ActionServerContext.Provider
      value={{
        viewSettings,
        setViewSettings,
        loadedRuns,
        setLoadedRuns,
        loadedActions,
        setLoadedActions,
        loadedServerConfig,
        setLoadedServerConfig,
      }}
    >
      {children}
    </ActionServerContext.Provider>
  );
};

export const RuntimeProviders = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    <ActionServerProvider>{children}</ActionServerProvider>
  </QueryClientProvider>
);
