// @vitest-environment jsdom
import { afterEach, expect, test, vi } from "vitest";
import {
    cleanup,
    fireEvent,
    render,
    screen,
    waitFor,
} from "@testing-library/react";
import { RuntimeAuthentication } from "../src/app/RuntimeAuthentication";

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});
const status = (authenticated = false, required = true) =>
    new Response(
        JSON.stringify({
            required,
            authenticated,
            transport_allowed: true,
            expires_in: 3600,
        }),
    );

test("gates protected content and clears the sign-in key; logout unmounts it", async () => {
    let authenticated = false;
    const fetch = vi.fn(
        async (_input: RequestInfo | URL, init?: RequestInit) => {
            if (init?.method === "POST") {
                authenticated = true;
                return new Response("{}");
            }
            if (init?.method === "DELETE") {
                authenticated = false;
                return new Response(null, { status: 204 });
            }
            return status(authenticated);
        },
    );
    vi.stubGlobal("fetch", fetch);
    render(
        <RuntimeAuthentication>
            <div>Protected content</div>
        </RuntimeAuthentication>,
    );
    expect(screen.queryByText("Protected content")).toBeNull();
    fireEvent.change(await screen.findByLabelText("API key"), {
        target: { value: "synthetic-key" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await screen.findByText("Protected content");
    expect(
        fetch.mock.calls.find(([, init]) => init?.method === "POST")?.[1]
            ?.headers,
    ).toEqual({ Authorization: "Bearer synthetic-key" });
    expect(localStorage.getItem("action-server-api-key")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    await screen.findByLabelText("API key");
    expect(screen.queryByText("Protected content")).toBeNull();
    expect((screen.getByLabelText("API key") as HTMLInputElement).value).toBe(
        "",
    );
});

test("status failure stays gated with retry and local no-key mode mounts", async () => {
    const fetch = vi
        .fn()
        .mockRejectedValueOnce(new Error("network"))
        .mockResolvedValue(status(true, false));
    vi.stubGlobal("fetch", fetch);
    render(
        <RuntimeAuthentication>
            <div>Local content</div>
        </RuntimeAuthentication>,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Try again" }));
    await screen.findByText("Local content");
    expect(screen.queryByRole("button", { name: "Sign out" })).toBeNull();
});

test("403 recovery rechecks session and clears protected content", async () => {
    let authenticated = true;
    vi.stubGlobal(
        "fetch",
        vi.fn(async (input: RequestInfo | URL) =>
            String(input).includes("browser-session")
                ? status(authenticated)
                : new Response("denied", { status: 403 }),
        ),
    );
    render(
        <RuntimeAuthentication>
            <div>Private data</div>
        </RuntimeAuthentication>,
    );
    await screen.findByText("Private data");
    authenticated = false;
    await window.fetch("/api/runs");
    await screen.findByLabelText("API key");
    await waitFor(() => expect(screen.queryByText("Private data")).toBeNull());
});

test("invalid key is cleared and receives an accessible error", async () => {
    vi.stubGlobal(
        "fetch",
        vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) =>
            init?.method === "POST"
                ? new Response("denied", { status: 403 })
                : status(),
        ),
    );
    render(
        <RuntimeAuthentication>
            <div>Private data</div>
        </RuntimeAuthentication>,
    );
    fireEvent.change(await screen.findByLabelText("API key"), {
        target: { value: "wrong" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await screen.findByRole("alert");
    expect((screen.getByLabelText("API key") as HTMLInputElement).value).toBe(
        "",
    );
    expect(screen.queryByText("Private data")).toBeNull();
});
