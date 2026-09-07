import type { ReactNode } from "react";
import { useEffect, useState } from "react";
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

const ActionServerProvider = ({
    children,
    queryClient,
}: {
    children: ReactNode;
    queryClient: QueryClient;
}) => {
    const [viewSettings, setViewSettings] = useLocalStorage<ViewSettings>(
        "view-settings",
        { theme: "dark" },
    );
    const actions = useRuntimeActions();
    const runs = useRuntimeRuns();
    const config = useRuntimeConfig();

    useEffect(() => {
        return subscribeRuntimeEvents(queryClient);
    }, [queryClient]);

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

export const RuntimeProviders = ({ children }: { children: ReactNode }) => {
    const [queryClient] = useState(
        () =>
            new QueryClient({
                defaultOptions: {
                    queries: {
                        staleTime: 30_000,
                        refetchOnWindowFocus: false,
                        retry: false,
                    },
                },
            }),
    );

    useEffect(() => () => queryClient.clear(), [queryClient]);

    return (
        <QueryClientProvider client={queryClient}>
            <ActionServerProvider queryClient={queryClient}>
                {children}
            </ActionServerProvider>
        </QueryClientProvider>
    );
};
