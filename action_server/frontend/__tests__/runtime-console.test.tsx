import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { RuntimeNavigation } from "../src/app/RuntimeNavigation";

describe("Direction A Runtime console navigation", () => {
  it("exposes grouped runtime identity and execution destinations", () => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: { getItem: () => null, setItem: () => undefined },
    });

    render(
      <MemoryRouter initialEntries={["/overview"]}>
        <RuntimeNavigation />
      </MemoryRouter>,
    );

    expect(screen.getByText("Actions Runtime")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Actions" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Runs" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Logs & artifacts" }),
    ).toBeInTheDocument();
  });
});
