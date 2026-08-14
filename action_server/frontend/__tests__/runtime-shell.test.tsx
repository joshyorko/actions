import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { RuntimeLayout } from "../src/app/RuntimeLayout";
import { RuntimeRoutes } from "../src/app/RuntimeRoutes";
import { RuntimeProviders } from "../src/app/RuntimeProviders";
import { render } from "./utils/test-utils";

const runtimeConfig = {
  expose_url: "http://localhost:8080",
  auth_enabled: false,
  version: "1.0.0",
  mtime_uuid: "runtime-1",
  capabilities: {
    actions: true,
    runs: true,
    schedules: false,
    robots: false,
    work_items: true,
    analytics: false,
  },
};

beforeEach(() => {
  vi.restoreAllMocks();
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

describe("Actions Runtime shell", () => {
  it("identifies the product and lands on a useful overview", async () => {
    renderRuntime();

    expect(screen.getAllByText("Actions Runtime").length).toBeGreaterThan(0);
    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Overview" }),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText("No runs yet")).toBeInTheDocument();
    expect(screen.getByText("No actions available")).toBeInTheDocument();
  });

  it("shows only capabilities advertised by the Runtime config", async () => {
    renderRuntime();

    await waitFor(() =>
      expect(
        screen.getByRole("link", { name: "Work Items" }),
      ).toBeInTheDocument(),
    );
    expect(
      screen.queryByRole("link", { name: "Schedules" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Robots" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Analytics" }),
    ).not.toBeInTheDocument();
  });

  it("renders a degraded overview when config and data endpoints are unavailable", async () => {
    vi.mocked(globalThis.fetch).mockRejectedValue(new Error("offline"));
    renderRuntime();

    await waitFor(() =>
      expect(
        screen.getByRole("heading", { name: "Runtime unavailable" }),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText(/could not be loaded/i)).toBeInTheDocument();
    expect(screen.getByText("Actions Runtime")).toBeInTheDocument();
  });
});
