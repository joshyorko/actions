import { afterEach, describe, expect, it, vi } from "vitest";
import { collectRunArtifacts } from "../src/shared/api-client";

afterEach(() => vi.restoreAllMocks());

describe("legacy artifact API client", () => {
  it("serializes readonly array query values as repeated parameters", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
    const setLoaded = vi.fn();

    await collectRunArtifacts("run-1", setLoaded, {
      artifact_names: ["output.robolog", "console.robolog"],
      format: "text",
    });

    const requestUrl = new URL(
      String(fetchMock.mock.calls[0][0]),
      "http://localhost",
    );
    expect(requestUrl.searchParams.getAll("artifact_names")).toEqual([
      "output.robolog",
      "console.robolog",
    ]);
    expect(requestUrl.searchParams.get("format")).toBe("text");
  });
});
