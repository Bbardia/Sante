// API base comes from VITE_API_BASE (.env.development); the literal fallback
// keeps local dev working if no env file is present.
const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8756";

export interface Health {
  status: string;
}

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(`health request failed: ${res.status}`);
  // Note: response shape is asserted, not validated. Add schema validation
  // (e.g. zod) before this client grows many endpoints.
  return res.json() as Promise<Health>;
}
