// @vitest-environment jsdom
import type { ReactNode } from "react";
import { afterEach, expect, test, vi } from "vitest";
import { cleanup, renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useActionRunMutation } from "../src/queries/actions";

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

test("browser action execution uses the session without an undefined bearer", async () => {
    const fetch = vi.fn(
        async () =>
            new Response("{}", {
                headers: { "content-type": "application/json" },
            }),
    );
    vi.stubGlobal("fetch", fetch);
    const queryClient = new QueryClient();
    const { result } = renderHook(() => useActionRunMutation(), {
        wrapper: ({ children }: { children: ReactNode }) => (
            <QueryClientProvider client={queryClient}>
                {children}
            </QueryClientProvider>
        ),
    });
    await act(async () => {
        await result.current.mutateAsync({
            actionPackageName: "example",
            actionName: "action",
            args: {},
        });
    });
    const options = (
        fetch.mock.calls as unknown as [string, RequestInit][]
    )[0][1];
    expect(new Headers(options.headers).has("Authorization")).toBe(false);
    queryClient.clear();
});
