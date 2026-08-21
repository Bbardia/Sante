const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8756";

export interface Health {
  status: string;
}

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(`health request failed: ${res.status}`);
  return res.json();
}
