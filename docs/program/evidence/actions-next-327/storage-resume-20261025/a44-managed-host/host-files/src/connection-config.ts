/** Trusted configuration only: one literal loopback Runtime, never a URL token. */
export function runtimeEndpoint(value: unknown): URL {
  if (typeof value !== "string") throw new Error("A configured loopback Runtime is required.");
  let url: URL;
  try { url = new URL(value); } catch { throw new Error("A valid loopback Runtime endpoint is required."); }
  if (url.protocol !== "http:" || url.hostname !== "127.0.0.1" ||
      !url.port || url.pathname !== "/mcp" || url.search || url.hash ||
      url.username || url.password || value !== url.href) {
    throw new Error("Runtime must be http://127.0.0.1:PORT/mcp without credentials or query parameters.");
  }
  return url;
}

export function configuredServers(value: unknown): string[] {
  if (!Array.isArray(value) || value.length !== 1) {
    throw new Error("Exactly one trusted Runtime endpoint is required.");
  }
  return [runtimeEndpoint(value[0]).href];
}

export function disposableBearer(value: string): string {
  if (!/^[A-Za-z0-9_-]{16,256}$/.test(value)) {
    throw new Error("Enter the disposable test key supplied by the owner.");
  }
  return value;
}
