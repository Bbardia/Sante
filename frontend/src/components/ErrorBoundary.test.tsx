import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithProviders } from "../test/utils";
import ErrorBoundary from "./ErrorBoundary";

function Boom(): never {
  throw new Error("kaboom");
}

describe("ErrorBoundary", () => {
  // React logs the caught error to console.error; silence it so the test output stays clean.
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders children when nothing throws", () => {
    renderWithProviders(
      <ErrorBoundary>
        <p>all good</p>
      </ErrorBoundary>
    );
    expect(screen.getByText("all good")).toBeInTheDocument();
  });

  it("shows the fallback (with the error message and a Reload button) when a child throws", () => {
    renderWithProviders(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("kaboom")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reload" })).toBeInTheDocument();
  });
});
