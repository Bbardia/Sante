export type Role = "admin" | "manager" | "salesman" | "stockman";

export interface NavItem { key: string; label: string; }

// Tab order mirrors the legacy app.
export const NAV_ITEMS: NavItem[] = [
  { key: "dashboard", label: "Dashboard" },
  { key: "inventory", label: "Inventory" },
  { key: "products", label: "Products" },
  { key: "recipes", label: "Recipes" },
  { key: "sales", label: "Sales" },
  { key: "history", label: "Sales History" },
  { key: "debts", label: "Debts" },
  { key: "reports", label: "Reports" },
  { key: "users", label: "Users" },
];

export const ROLE_PERMISSIONS: Record<Role, string[]> = {
  admin:    ["dashboard","inventory","products","recipes","sales","history","debts","reports","users"],
  manager:  ["dashboard","inventory","products","recipes","sales","history","debts","reports","users"],
  salesman: ["dashboard","sales","history","debts","reports"],
  stockman: ["inventory"],
};
