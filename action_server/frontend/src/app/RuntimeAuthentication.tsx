import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { observeBrowserAuthFailures } from "@/shared/browser-auth";

type SessionStatus = {
    required: boolean;
    authenticated: boolean;
    transport_allowed: boolean;
    expires_in: number | null;
};

/** Providers mount only after the server confirms the browser's authority. */
export const RuntimeAuthentication = ({
    children,
}: {
    children: ReactNode;
}) => {
    const [status, setStatus] = useState<SessionStatus | null>(null);
    const [error, setError] = useState("");
    const [key, setKey] = useState("");
    const [busy, setBusy] = useState(false);
    const requestGeneration = useRef(0);
    const mounted = useRef(true);
    const refresh = useCallback(async () => {
        const generation = ++requestGeneration.current;
        try {
            const response = await window.fetch("/browser-session", {
                cache: "no-store",
                credentials: "same-origin",
            });
            if (!response.ok) throw new Error("Session status unavailable");
            const next: SessionStatus = await response.json();
            if (
                typeof next.required !== "boolean" ||
                typeof next.authenticated !== "boolean" ||
                typeof next.transport_allowed !== "boolean"
            )
                throw new Error("Invalid session status");
            if (mounted.current && generation === requestGeneration.current) {
                setStatus(next);
                setError("");
            }
        } catch {
            if (mounted.current && generation === requestGeneration.current) {
                setStatus(null);
                setError(
                    "Could not check your Runtime session. Check the connection and try again.",
                );
            }
        }
    }, []);

    useEffect(() => {
        mounted.current = true;
        // Remove credentials persisted by earlier versions of the action form.
        try {
            window.localStorage.removeItem("action-server-api-key");
        } catch {
            /* Storage may be disabled. */
        }
        void refresh();
        const restore = observeBrowserAuthFailures(() => {
            void refresh();
        });
        const onFocus = () => {
            void refresh();
        };
        window.addEventListener("focus", onFocus);
        const timer = window.setInterval(onFocus, 15_000);
        return () => {
            mounted.current = false;
            restore();
            window.removeEventListener("focus", onFocus);
            window.clearInterval(timer);
        };
    }, [refresh]);

    useEffect(() => {
        if (
            !status?.required ||
            !status.authenticated ||
            status.expires_in === null
        )
            return;
        const timer = window.setTimeout(
            () => {
                void refresh();
            },
            Math.max(0, status.expires_in * 1000),
        );
        return () => window.clearTimeout(timer);
    }, [status, refresh]);

    const signIn = async (event: FormEvent) => {
        event.preventDefault();
        if (busy) return;
        setBusy(true);
        setError("");
        const submittedKey = key;
        setKey("");
        ++requestGeneration.current;
        try {
            const response = await window.fetch("/browser-session", {
                method: "POST",
                credentials: "same-origin",
                cache: "no-store",
                headers: { Authorization: `Bearer ${submittedKey}` },
            });
            if (!response.ok) throw new Error("Sign-in failed");
            await refresh();
        } catch {
            setError(
                "Could not sign in. Check the API key and use the Runtime's HTTPS or loopback address.",
            );
        } finally {
            setBusy(false);
        }
    };

    const signOut = async () => {
        setBusy(true);
        ++requestGeneration.current;
        try {
            const response = await window.fetch("/browser-session", {
                method: "DELETE",
                credentials: "same-origin",
                cache: "no-store",
            });
            if (!response.ok) throw new Error("Sign-out failed");
            setStatus(null);
            await refresh();
        } catch {
            setError("Could not sign out. Check the connection and try again.");
        } finally {
            setBusy(false);
        }
    };

    if (status && (!status.required || status.authenticated)) {
        return (
            <>
                {status.required && (
                    <div className="flex items-center justify-end gap-3 border-b border-border bg-background px-4 py-2 text-foreground">
                        {error && <span role="alert">{error}</span>}
                        <button
                            type="button"
                            onClick={() => {
                                void signOut();
                            }}
                            disabled={busy}
                            className="rounded border border-border px-3 py-1 focus-visible:outline focus-visible:outline-2"
                        >
                            Sign out
                        </button>
                    </div>
                )}
                {children}
            </>
        );
    }
    return (
        <main className="flex min-h-screen items-center justify-center bg-background p-6 text-foreground">
            <section
                aria-label="Runtime sign in"
                className="w-full max-w-md space-y-4 rounded-lg border border-border p-6"
            >
                <h1 className="text-xl font-semibold">Actions Runtime</h1>
                {error && <p role="alert">{error}</p>}
                {!status ? (
                    <>
                        {!error && <p role="status">Checking your session…</p>}
                        {error && (
                            <button
                                type="button"
                                onClick={() => {
                                    void refresh();
                                }}
                            >
                                Try again
                            </button>
                        )}
                    </>
                ) : !status.transport_allowed ? (
                    <p>
                        Open the Runtime using HTTPS or its loopback address to
                        sign in.
                    </p>
                ) : (
                    <form
                        onSubmit={(event) => {
                            void signIn(event);
                        }}
                        className="space-y-4"
                    >
                        <p>Enter the API key configured for this Runtime.</p>
                        <label htmlFor="runtime-session-key" className="block">
                            API key
                        </label>
                        <input
                            id="runtime-session-key"
                            type="password"
                            autoComplete="off"
                            value={key}
                            onChange={(event) => setKey(event.target.value)}
                            required
                            disabled={busy}
                            className="w-full rounded border border-border bg-background p-2"
                        />
                        <button
                            type="submit"
                            disabled={busy || !key}
                            className="rounded bg-primary px-4 py-2 text-primary-foreground"
                        >
                            {busy ? "Signing in…" : "Sign in"}
                        </button>
                    </form>
                )}
            </section>
        </main>
    );
};
