import { describe, it, expect } from "vitest";
import { NAV_ITEMS, ROLE_PERMISSIONS, type Role } from "./roles";

const ALL_KEYS = NAV_ITEMS.map((n) => n.key);

describe("ROLE_PERMISSIONS", () => {
  it("gives admin access to every nav item", () => {
    expect([...ROLE_PERMISSIONS.admin].sort()).toEqual([...ALL_KEYS].sort());
  });

  it("never grants a key that isn't a real nav item", () => {
    for (const [role, keys] of Object.entries(ROLE_PERMISSIONS)) {
      for (const key of keys) {
        expect(ALL_KEYS, `role "${role}" references unknown key "${key}"`).toContain(key);
      }
    }
  });

  // Regression: Users management + Settings (DB backup/restore) are admin-only.
  // Manager used to have these; locking them down must not silently regress.
  it("does NOT let manager reach users or settings", () => {
    expect(ROLE_PERMISSIONS.manager).not.toContain("users");
    expect(ROLE_PERMISSIONS.manager).not.toContain("settings");
  });

  it("only admin can reach users and settings", () => {
    const roles: Role[] = ["admin", "manager", "salesman", "stockman"];
    const canUsers = roles.filter((r) => ROLE_PERMISSIONS[r].includes("users"));
    const canSettings = roles.filter((r) => ROLE_PERMISSIONS[r].includes("settings"));
    expect(canUsers).toEqual(["admin"]);
    expect(canSettings).toEqual(["admin"]);
  });

  it("keeps manager on the operational tabs", () => {
    for (const key of ["dashboard", "inventory", "products", "recipes", "sales", "history", "debts", "reports"]) {
      expect(ROLE_PERMISSIONS.manager).toContain(key);
    }
  });

  it("limits salesman to selling/history/reports and stockman to inventory", () => {
    expect([...ROLE_PERMISSIONS.salesman].sort()).toEqual(
      ["dashboard", "debts", "history", "reports", "sales"].sort()
    );
    expect(ROLE_PERMISSIONS.stockman).toEqual(["inventory"]);
  });
});
