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
    if (path.includes("/api/runs/summary")) {
      return new Response(JSON.stringify([]), { status: 200 });
    }
    if (path.startsWith("/api/runs/")) {
      return new Response(
        JSON.stringify({ detail: `Unknown run id: ${path.split("/").at(-1)}` }),
        { status: 404 },
      );
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

  it("closes mobile navigation when the current route is selected", async () => {
    const user = userEvent.setup();
    renderRuntimeAt("/actions");
    await screen.findByText(/No actions available yet/);
    const menuButton = screen.getByRole("button", { name: "Open menu" });
    await user.click(menuButton);
    await user.click(screen.getByRole("link", { name: "Actions" }));
    expect(menuButton).toHaveAttribute("aria-expanded", "false");
    expect(menuButton).toHaveFocus();
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
    ["/logs/run-1", /Unknown run id: run-1/],
    ["/artifacts/run-1", /could not be found/],
  ])("preserves supported deep link %s", async (path, content) => {
    renderRuntimeAt(path);

    await waitFor(() => expect(screen.getByText(content)).toBeInTheDocument());
  });

  it("loads run inputs and results from the detail endpoint", async () => {
    const user = userEvent.setup();
    const detail = {
      id: "run-detail",
      status: 2,
      action_id: "action-1",
      start_time: "2026-10-08T00:00:00Z",
      run_time: 1.5,
      numbered_id: 7,
      run_type: "action",
      inputs: '{"value":"input-detail-secret"}',
      result: '{"value":"result-detail-secret"}',
      error_message: null,
      relative_artifacts_dir: "run-detail",
    };
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = String(input);
      if (path.endsWith("/api/runs/run-detail")) {
        return new Response(JSON.stringify(detail), { status: 200 });
      }
      if (path.includes("/api/runs")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (path.endsWith("/config")) {
        return new Response(JSON.stringify(runtimeConfig), { status: 200 });
      }
      if (path.includes("/api/actionPackages")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response("Not found", { status: 404 });
    });

    renderRuntimeAt("/logs/run-detail");

    await waitFor(() => expect(screen.getByText("Run #7")).toBeInTheDocument());
    await user.click(screen.getByText("Show run inputs and result"));
    expect(screen.getByText(/input-detail-secret/)).toBeInTheDocument();
    expect(screen.getByText(/result-detail-secret/)).toBeInTheDocument();
  });

  it("loads run history from the bounded summary endpoint", async () => {
    const summary = {
      id: "run-summary",
      status: 2,
      action_id: "action-1",
      start_time: "2026-10-08T00:00:00Z",
      run_time: 1.5,
      numbered_id: 5,
      run_type: "action",
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = String(input);
      if (path.includes("/api/runs/summary")) {
        return new Response(JSON.stringify([summary]), { status: 200 });
      }
      if (path.endsWith("/config")) {
        return new Response(JSON.stringify(runtimeConfig), { status: 200 });
      }
      if (path.includes("/api/actionPackages")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response("Not found", { status: 404 });
    });

    renderRuntimeAt("/runs");

    await waitFor(() => expect(screen.getByText("5")).toBeInTheDocument());
    expect(
      fetchMock.mock.calls.some(([input]) =>
        String(input).includes("/api/runs/summary?limit=200"),
      ),
    ).toBe(true);
  });

  it("loads older history pages without replacing the first page cache", async () => {
    const user = userEvent.setup();
    const firstPage = Array.from({ length: 200 }, (_, index) => ({
      id: `run-${index}`,
      status: 2,
      action_id: "action-1",
      start_time: "2026-10-08T00:00:00Z",
      run_time: 1.5,
      numbered_id: 200 - index,
      run_type: "action",
    }));
    const olderRun = {
      id: "older-run-after-first-page",
      status: 2,
      action_id: "action-1",
      start_time: "2026-10-07T00:00:00Z",
      run_time: 1.5,
      numbered_id: 0,
      run_type: "action",
    };
    const requestedPages: Array<{ offset: number; runType: string }> = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = String(input);
      if (path.includes("/api/runs/summary")) {
        const url = new URL(path, "http://runtime.test");
        const offset = Number(url.searchParams.get("offset") || 0);
        const runType = url.searchParams.get("run_type") || "all";
        requestedPages.push({ offset, runType });
        return new Response(
          JSON.stringify(offset === 0 ? firstPage : [olderRun]),
          { status: 200 },
        );
      }
      if (path.endsWith("/config")) {
        return new Response(JSON.stringify(runtimeConfig), { status: 200 });
      }
      if (path.includes("/api/actionPackages")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response("Not found", { status: 404 });
    });

    renderRuntimeAt("/runs");

    await waitFor(() =>
      expect(screen.getByText("run-199")).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: /load older runs/i }));
    await waitFor(() =>
      expect(
        screen.getByText("older-run-after-first-page"),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText("run-199")).toBeInTheDocument();
    expect(requestedPages).toEqual([
      { offset: 0, runType: "all" },
      { offset: 200, runType: "all" },
    ]);
  });

  it("shows a bounded reconnect status when the summary socket is rejected", async () => {
    class RejectedWebSocket {
      onopen: (() => void) | null = null;
      onclose: (() => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: (() => void) | null = null;

      constructor() {
        queueMicrotask(() => {
          this.onerror?.();
          this.onclose?.();
        });
      }

      close() {
        this.onclose?.();
      }

      send() {}
    }
    vi.stubGlobal("WebSocket", RejectedWebSocket);
    const summary = {
      id: "run-with-live-status",
      status: 2,
      action_id: "action-1",
      start_time: "2026-10-08T00:00:00Z",
      run_time: 1,
      numbered_id: 1,
      run_type: "action",
    };
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = String(input);
      if (path.includes("/api/runs/summary")) {
        return new Response(JSON.stringify([summary]), { status: 200 });
      }
      if (path.endsWith("/config")) {
        return new Response(JSON.stringify(runtimeConfig), { status: 200 });
      }
      if (path.includes("/api/actionPackages")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response("Not found", { status: 404 });
    });

    renderRuntimeAt("/runs");

    await waitFor(() =>
      expect(
        screen.getByText(/Live run updates are reconnecting \(attempt 1 of 5\)/),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByText(/undefined/i)).not.toBeInTheDocument();
  });
});
