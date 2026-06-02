// API base comes from VITE_API_BASE (.env.development); the literal fallback
// keeps local dev working if no env file is present.
const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8756";

import type { Role } from "../lib/roles";

// ─── Token store ────────────────────────────────────────────────────────────

const TOKEN_KEY = "sante_token";
export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

// ─── Error type ─────────────────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// ─── Shared request helper ──────────────────────────────────────────────────

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = tokenStore.get();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: { msg?: string }) => d.msg ?? "").filter(Boolean).join("; ") || detail;
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

// ─── Types ───────────────────────────────────────────────────────────────────

export interface Health {
  status: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: Role;
  username: string;
}

export interface User {
  id: number;
  username: string;
  role: Role;
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<Health> {
  return request<Health>("/health");
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function getMe(): Promise<User> {
  return request<User>("/auth/me");
}

// ─── Users ───────────────────────────────────────────────────────────────────

export async function listUsers(search?: string): Promise<User[]> {
  const qs = search ? `?search=${encodeURIComponent(search)}` : "";
  return request<User[]>(`/users${qs}`);
}

export async function createUser(data: { username: string; password: string; role: Role }): Promise<User> {
  return request<User>("/users", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateUser(id: number, data: Partial<{ username: string; password: string; role: Role }>): Promise<User> {
  return request<User>(`/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteUser(id: number): Promise<void> {
  return request<void>(`/users/${id}`, { method: "DELETE" });
}

// ─── Inventory ────────────────────────────────────────────────────────────────

export interface Inventory {
  id: number;
  name: string;
  qty: number;
  unit: string;
  total_value: number;
  avg_price: number;
  reorder_level: number;
}

export async function listInventory(search?: string): Promise<Inventory[]> {
  const qs = search ? `?search=${encodeURIComponent(search)}` : "";
  return request<Inventory[]>(`/inventory${qs}`);
}

export async function addStock(data: {
  name: string;
  qty: number;
  unit: string;
  price: number;
  reorder_level?: number;
}): Promise<Inventory> {
  return request<Inventory>("/inventory", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateInventory(
  id: number,
  data: { name?: string; unit?: string; reorder_level?: number }
): Promise<Inventory> {
  return request<Inventory>(`/inventory/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteInventory(id: number): Promise<void> {
  return request<void>(`/inventory/${id}`, { method: "DELETE" });
}

export async function resetInventory(): Promise<{ reset: number }> {
  return request<{ reset: number }>("/inventory/reset", { method: "POST" });
}

// ─── Products ─────────────────────────────────────────────────────────────────

export interface Product {
  id: number;
  name: string;
  price: number;
}

export async function listProducts(search?: string): Promise<Product[]> {
  const qs = search ? `?search=${encodeURIComponent(search)}` : "";
  return request<Product[]>(`/products${qs}`);
}

export async function createProduct(data: { name: string; price: number }): Promise<Product> {
  return request<Product>("/products", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateProduct(
  id: number,
  data: { name?: string; price?: number }
): Promise<Product> {
  return request<Product>(`/products/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteProduct(id: number): Promise<void> {
  return request<void>(`/products/${id}`, { method: "DELETE" });
}

// ─── Recipes ──────────────────────────────────────────────────────────────────

export interface Recipe {
  id: number;
  product_id: number;
  product_name: string;
  ingredient_id: number;
  ingredient_name: string;
  qty: number;
}

export async function listRecipes(productId?: number): Promise<Recipe[]> {
  const qs = productId != null ? `?product_id=${productId}` : "";
  return request<Recipe[]>(`/recipes${qs}`);
}

export async function createRecipe(data: {
  product_id: number;
  ingredient_id: number;
  qty: number;
}): Promise<Recipe> {
  return request<Recipe>("/recipes", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateRecipe(id: number, data: { qty: number }): Promise<Recipe> {
  return request<Recipe>(`/recipes/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteRecipe(id: number): Promise<void> {
  return request<void>(`/recipes/${id}`, { method: "DELETE" });
}
