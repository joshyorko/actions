import React from "react";
import { render } from "../../utils/test-utils";
import { describe, it, expect } from "vitest";

import { Badge } from "@/core/components/ui/Badge";

describe("Badge", () => {
  it("renders the default (neutral) variant when no variant is provided", () => {
    const { getByText } = render(<Badge>Neutral</Badge>);
    expect(getByText("Neutral")).toBeTruthy();
  });

  it('applies success variant styling when variant="success"', () => {
    const { container } = render(<Badge variant="success">OK</Badge>);
    const el = container.firstChild as HTMLElement | null;
    expect(el).toBeTruthy();
    // Variant classes use semantic color tokens
    expect(el?.className).toContain("bg-success/10");
    expect(el?.className).toContain("text-success");
  });

  it("renders a named status icon and accessible status text", () => {
    const { getByRole, getByText } = render(
      <Badge status="running">Running</Badge>,
    );
    expect(getByRole("img", { name: "Running" })).toBeTruthy();
    expect(getByText("Running")).toBeTruthy();
  });
});
