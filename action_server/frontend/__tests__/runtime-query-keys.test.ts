import { describe, expect, it } from "vitest";
import { runtimeQueryKeys } from "../src/shared/runtime-query-keys";

describe("Runtime query keys", () => {
  it("provides stable hierarchical keys for shared Runtime state", () => {
    expect(runtimeQueryKeys.actions()).toEqual(["runtime", "actions"]);
    expect(runtimeQueryKeys.runs()).toEqual(["runtime", "runs"]);
    expect(runtimeQueryKeys.runPages()).toEqual([
      "runtime",
      "runs",
      "all",
      "pages",
    ]);
    expect(runtimeQueryKeys.runs("robot")).toEqual([
      "runtime",
      "runs",
      "robot",
    ]);
    expect(runtimeQueryKeys.run("run-1")).toEqual(["runtime", "run", "run-1"]);
    expect(runtimeQueryKeys.websocketStatus()).toEqual([
      "runtime",
      "websocket-status",
    ]);
    expect(runtimeQueryKeys.config()).toEqual(["runtime", "config"]);
  });
});
