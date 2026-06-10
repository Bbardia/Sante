import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "../test/utils";
import SalesPage from "./SalesPage";

vi.mock("../api/client", () => ({
  ApiError: class ApiError extends Error {
    status: number;
    detail?: unknown;
    constructor(status: number, message: string, detail?: unknown) {
      super(message);
      this.status = status;
      this.detail = detail;
    }
  },
  listProducts: vi.fn(async () => [
    { id: 1, name: "Espresso", price: 2.5 },
    { id: 2, name: "Latte", price: 4 },
    { id: 3, name: "Tea", price: 1.5 },
    { id: 4, name: "Cake", price: 5 },
  ]),
  listCustomers: vi.fn(async () => []),
  createCustomer: vi.fn(),
  checkout: vi.fn(),
}));

describe("SalesPage", () => {
  it("supports cashier-friendly quick add, inline cart quantity editing, and clear cart", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SalesPage />);

    await user.click(await screen.findByRole("button", { name: "Quick add Espresso" }));

    const cartRow = screen.getByRole("row", { name: /Espresso/ });
    expect(within(cartRow).getByText("Espresso")).toBeInTheDocument();
    expect(within(cartRow).getAllByText("2.50")).toHaveLength(2);

    const qtyInput = screen.getByLabelText("Quantity for Espresso");
    await user.clear(qtyInput);
    await user.type(qtyInput, "3");

    expect(screen.getAllByText("7.50").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: "Clear cart" }));
    expect(screen.getByText("Cart is empty.")).toBeInTheDocument();
  });
});
