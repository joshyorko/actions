import { afterEach, describe, expect, it, vi } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

vi.mock("../src/shared/runtime-events", () => ({
  subscribeRuntimeEvents: vi.fn(() => vi.fn()),
}));
vi.mock("../src/shared/hooks/useLocalStorage", () => ({
  useLocalStorage: () => [{ theme: "dark" }, vi.fn()],
}));

import { RuntimeProviders } from "../src/app/RuntimeProviders";

afterEach(() => cleanup());

describe("RuntimeProviders", () => {
  it("owns an isolated QueryClient per mounted provider and clears it on teardown", () => {
    const clients: ReturnType<typeof useQueryClient>[] = [];
    const Probe = () => {
      const client = useQueryClient();
      useEffect(() => {
        clients.push(client);
        client.setQueryData(["probe"], "owned");
      }, [client]);
      return null;
    };

    const first = render(
      <RuntimeProviders>
        <Probe />
      </RuntimeProviders>,
    );
    const second = render(
      <RuntimeProviders>
        <Probe />
      </RuntimeProviders>,
    );

    expect(clients[0]).not.toBe(clients[1]);
    expect(clients[0].getQueryData(["probe"])).toBe("owned");
    expect(clients[1].getQueryData(["probe"])).toBe("owned");

    const firstClient = clients[0];
    first.unmount();
    expect(firstClient.getQueryCache().getAll()).toHaveLength(0);
    expect(clients[1].getQueryData(["probe"])).toBe("owned");
    expect(clients[1].getQueryCache().getAll().length).toBeGreaterThan(0);
    second.unmount();
  });
});
