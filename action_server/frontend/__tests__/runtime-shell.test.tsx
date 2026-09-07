import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";
import { render as rtlRender } from "@testing-library/react";
import { RuntimeLayout } from "../src/app/RuntimeLayout";
import { RuntimeRoutes } from "../src/app/RuntimeRoutes";
import { RuntimeProviders } from "../src/app/RuntimeProviders";
import { render } from "./utils/test-utils";

const runtimeConfig = {
  expose_url: "http://localhost:8080",
  auth_enabled: false,
  version: "1.0.0",
  mtime_uuid: "runtime-1",
};

beforeEach(() => {
  vi.restoreAllMocks();
  vi.stubGlobal(
    "WebSocket",
    class {
      onopen: (() => void) | null = null;
      onclose: (() => void) | null = null;
      onerror: (() => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;

      constructor() {
        queueMicrotask(() => this.onopen?.());
      }

      close() {
        this.onclose?.();
      }

      send() {}
    },
  );
  const storage = new Map<string, string>();
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => storage.set(key, value),
      removeItem: (key: string) => storage.delete(key),
      clear: () => storage.clear(),
    },
  });
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = String(input);
    if (path.endsWith("/config")) {
      return new Response(JSON.stringify(runtimeConfig), { status: 200 });
    }
    if (path.includes("/api/actionPackages")) {
      return new Response(JSON.stringify([]), { status: 200 });
    }
    if (path.includes("/api/runs")) {
      return new Response(JSON.stringify([]), { status: 200 });
    }
    if (path.includes("/api/schedules")) {
      return new Response(JSON.stringify({ schedules: [] }), { status: 200 });
    }
    if (path.includes("/api/robots/catalog")) {
      return new Response(JSON.stringify({ robots: [] }), { status: 200 });
    }
    if (path.includes("/api/work-items")) {
      return new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 });
    }
    if (path.includes("/api/analytics/summary")) {
      return new Response(
        JSON.stringify({
          total_runs: 0,
          success_rate: 0,
          avg_duration_ms: 0,
          runs_today: 0,
        }),
        { status: 200 },
      );
    }
    if (path.includes("/api/analytics/")) {
      return new Response(JSON.stringify([]), { status: 200 });
    }
    return new Response("Not found", { status: 404 });
  });
});

const renderRuntime = () =>
  render(
    <RuntimeProviders>
      <RuntimeLayout>
        <RuntimeRoutes />
      </RuntimeLayout>
    </RuntimeProviders>,
  );

const renderRuntimeAt = (path: string) =>
  rtlRender(
    <MemoryRouter initialEntries={[path]}>
      <RuntimeProviders>
        <RuntimeLayout>
          <RuntimeRoutes />
        </RuntimeLayout>
      </RuntimeProviders>
    </MemoryRouter>,
  );

describe("Actions Runtime shell", () => {
  it("closes mobile navigation with Escape and returns focus to the menu button", async () => {
    const user = userEvent.setup();
    renderRuntime();

    const menuButton = screen.getByRole("button", { name: "Open menu" });
    await user.click(menuButton);
    expect(menuButton).toHaveAttribute("aria-expanded", "true");

    await user.keyboard("{Escape}");

    expect(menuButton).toHaveAttribute("aria-expanded", "false");
    expect(menuButton).toHaveFocus();
  });

  it("closes mobile navigation when a route is selected", async () => {
    const user = userEvent.setup();
    renderRuntime();

    const menuButton = screen.getByRole("button", { name: "Open menu" });
    await user.click(menuButton);
    await user.click(screen.getByRole("link", { name: "Actions" }));

    expect(menuButton).toHaveAttribute("aria-expanded", "false");
  });

  it("identifies the product and lands on a useful overview", async () => {
    renderRuntime();

    expect(screen.getAllByText("Actions Runtime").length).toBeGreaterThan(0);
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Overview" }),
      ).toBeInTheDocument(),
    );
    await waitFor(() => {
      expect(screen.getByText("No runs yet")).toBeInTheDocument();
      expect(screen.getByText("No actions available")).toBeInTheDocument();
    });
  });

  it("keeps existing navigation available when the real config has no capabilities", async () => {
    renderRuntime();

    await waitFor(() =>
      expect(screen.getByRole("link", { name: "Actions" })).toBeInTheDocument(),
    );
    expect(screen.getByRole("link", { name: "Runs" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Work Items" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Schedules" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Robots" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Analytics" })).toBeInTheDocument();
  });

  it("renders a degraded overview when config and data endpoints are unavailable", async () => {
    vi.mocked(globalThis.fetch).mockImplementation(
      async () =>
        new Response(JSON.stringify({ detail: "offline" }), { status: 503 }),
    );
    renderRuntime();

    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Runtime unavailable" }),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText(/could not be loaded/i)).toBeInTheDocument();
    expect(screen.getAllByText("Actions Runtime").length).toBeGreaterThan(0);
  });

  it.each([
    ["/schedules", "No schedules yet"],
    ["/robots", "No robots found"],
    ["/work-items", "No work items yet"],
    ["/analytics", "No analytics data yet"],
  ])("preserves existing direct link %s", async (path, content) => {
      renderRuntimeAt(path);

      await waitFor(() => expect(screen.getByText(content)).toBeInTheDocument());
    });

  it.each([
    ["/actions", /No actions available yet/],
    ["/runs", /No runs recorded yet/],
    ["/logs/run-1", /was not found in the local cache/],
    ["/artifacts/run-1", /could not be found/],
  ])("preserves supported deep link %s", async (path, content) => {
    renderRuntimeAt(path);

    await waitFor(() => expect(screen.getByText(content)).toBeInTheDocument());
  });
});
