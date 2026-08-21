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
  detail?: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
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
    let message = res.statusText;
    let rawDetail: unknown;
    try {
      const body = await res.json();
      rawDetail = body.detail;
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg?: string }) => d.msg ?? "").filter(Boolean).join("; ") || message;
      else if (body.detail !== null && typeof body.detail === "object" && typeof (body.detail as { message?: unknown }).message === "string") message = (body.detail as { message: string }).message;
    } catch { /* ignore */ }
    throw new ApiError(res.status, message, rawDetail);
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

export interface RecipeSetItem { ingredient_id: number; qty: number }
export async function setProductRecipe(productId: number, items: RecipeSetItem[]): Promise<Recipe[]> {
  return request<Recipe[]>(`/recipes/product/${productId}`, { method: "PUT", body: JSON.stringify({ items }) });
}

// ─── Customers ────────────────────────────────────────────────────────────────

export interface Customer {
  id: number;
  name: string;
  discount: number;
}

export async function listCustomers(search?: string): Promise<Customer[]> {
  const qs = search ? `?search=${encodeURIComponent(search)}` : "";
  return request<Customer[]>(`/customers${qs}`);
}

export async function createCustomer(data: { name: string; discount: number }): Promise<Customer> {
  return request<Customer>("/customers", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateCustomer(
  id: number,
  data: { name?: string; discount?: number }
): Promise<Customer> {
  return request<Customer>(`/customers/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteCustomer(id: number): Promise<void> {
  return request<void>(`/customers/${id}`, { method: "DELETE" });
}

// ─── Sales History & Debts ────────────────────────────────────────────────────

export interface SaleSummary {
  id: number;
  created_at: string;
  customer_name: string | null;
  total: number;
  payment_status: string;
  item_count: number;
}

export async function listSales(params?: {
  search?: string;
  start?: string;
  end?: string;
}): Promise<SaleSummary[]> {
  const qs = params
    ? (() => {
        const p = new URLSearchParams();
        if (params.search) p.set("search", params.search);
        if (params.start) p.set("start", params.start);
        if (params.end) p.set("end", params.end);
        const s = p.toString();
        return s ? `?${s}` : "";
      })()
    : "";
  return request<SaleSummary[]>(`/sales${qs}`);
}

export async function getReceipt(id: number): Promise<Receipt> {
  return request<Receipt>(`/sales/${id}`);
}

export async function listDebts(): Promise<SaleSummary[]> {
  return request<SaleSummary[]>("/debts");
}

export async function payDebt(saleId: number): Promise<SaleSummary> {
  return request<SaleSummary>(`/debts/${saleId}/pay`, { method: "POST" });
}

// ─── Sales / Checkout ─────────────────────────────────────────────────────────

export interface ReceiptItem {
  product_name: string;
  qty: number;
  unit_price: number;
  line_total: number;
}

export interface Receipt {
  sale_id: number;
  created_at: string;
  customer_name: string | null;
  items: ReceiptItem[];
  subtotal: number;
  discount_pct: number;
  discount_amount: number;
  total: number;
  payment_status: string;
}

export interface CartItem {
  product_id: number;
  qty: number;
}

export async function checkout(req: {
  customer_id?: number | null;
  discount_pct?: number;
  pay_later?: boolean;
  items: CartItem[];
}): Promise<Receipt> {
  return request<Receipt>("/sales", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export interface Dashboard {
  today: { revenue: number; sales_count: number };
  top_products: { product: string; qty: number }[];
  low_stock: { name: string; qty: number; unit: string; reorder_level: number }[];
}

export async function getDashboard(): Promise<Dashboard> {
  return request<Dashboard>("/dashboard");
}

// ─── Backup / Restore ─────────────────────────────────────────────────────────

export async function downloadBackup(): Promise<Blob> {
  const res = await fetch(`${BASE}/backup`, {
    headers: { Authorization: `Bearer ${tokenStore.get()}` },
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch { /* ignore */ }
    throw new ApiError(res.status, message);
  }
  return res.blob();
}

export async function restoreDatabase(
  file: File
): Promise<{ restored: boolean; safety_backup: string | null }> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${BASE}/restore`, {
    method: "POST",
    headers: { Authorization: `Bearer ${tokenStore.get()}` },
    body: formData,
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch { /* ignore */ }
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<{ restored: boolean; safety_backup: string | null }>;
}

// ─── Reports ──────────────────────────────────────────────────────────────────

export interface ReportRange {
  start: string;
  end: string;
  label: string;
}

export interface ReportOverview {
  sales_count: number;
  paid_revenue: number;
  unpaid_debt: number;
  grand_total: number;
}

export interface SaleDetailRow {
  sale_id: number;
  date: string;
  product: string;
  qty: number;
  line_total: number;
  customer: string | null;
  payment_status: string;
}

export interface InventoryConsumptionRow {
  ingredient: string;
  consumed: number;
  remaining: number;
  unit: string;
}

export interface CurrentInventoryRow {
  name: string;
  qty: number;
  unit: string;
}

export interface CustomerSummaryRow {
  customer: string;
  purchases: number;
  paid: number;
  debt: number;
}

export interface UnpaidBillRow {
  sale_id: number;
  date: string;
  customer: string | null;
  total: number;
}

export interface Report {
  range: ReportRange;
  overview: ReportOverview;
  sales_details: SaleDetailRow[];
  inventory_consumption: InventoryConsumptionRow[];
  current_inventory: CurrentInventoryRow[];
  customer_summary: CustomerSummaryRow[];
  unpaid_bills: UnpaidBillRow[];
}

export interface ReportParams {
  type?: string;
  start?: string;
  end?: string;
}

export async function getReport(params: ReportParams): Promise<Report> {
  const p = new URLSearchParams();
  if (params.type) p.set("type", params.type);
  if (params.start) p.set("start", params.start);
  if (params.end) p.set("end", params.end);
  const qs = p.toString() ? `?${p.toString()}` : "";
  return request<Report>(`/reports${qs}`);
}

export async function downloadReportExcel(params: ReportParams): Promise<Blob> {
  const p = new URLSearchParams();
  if (params.type) p.set("type", params.type);
  if (params.start) p.set("start", params.start);
  if (params.end) p.set("end", params.end);
  const qs = p.toString() ? `?${p.toString()}` : "";
  const token = tokenStore.get();
  const res = await fetch(`${BASE}/reports/export.xlsx${qs}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch { /* ignore */ }
    throw new ApiError(res.status, message);
  }
  return res.blob();
}
