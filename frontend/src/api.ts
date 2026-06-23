// Dev (vite dev server): proxy /api -> http://localhost:8000  -> BASE="/api"
// Prod (built bundle, same-origin):                            -> BASE=""
// Separate deploy: set VITE_API_URL=https://backend.example.com
const _env = (import.meta as any).env;
const BASE =
  _env?.VITE_API_URL !== undefined ? _env.VITE_API_URL
  : _env?.PROD ? ""
  : "/api";

let _token: string | null = localStorage.getItem("token");

export function getToken(): string | null {
  return _token;
}

export function setToken(t: string | null) {
  _token = t;
  if (t) localStorage.setItem("token", t);
  else localStorage.removeItem("token");
}

async function req(path: string, init?: RequestInit) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (_token) headers.Authorization = `Bearer ${_token}`;
  const r = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export function login(username: string, password: string) {
  return req("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
}
export function signup(username: string, password: string, role = "operator") {
  return req("/auth/signup", { method: "POST", body: JSON.stringify({ username, password, role }) });
}
export function getDemoUsers() {
  return fetch(`${BASE}/auth/demo-users`).then((r) => r.json());
}
export function getMetrics() { return req("/metrics"); }
export function getEvents(params: Record<string, any> = {}) {
  const cleaned = Object.fromEntries(
    Object.entries(params).filter(([_, v]) => v !== "" && v != null)
  );
  const q = new URLSearchParams(cleaned as any).toString();
  return req(`/events?${q}`);
}
export function getFacets() { return req("/events/facets"); }
export function getLLMInfo() { return req("/llm/info"); }
export function chat(query: string) {
  return req("/chat", { method: "POST", body: JSON.stringify({ query }) });
}
export function ragRetrieve(query: string, k = 5) {
  return req("/rag/retrieve", { method: "POST", body: JSON.stringify({ query, k }) });
}
export function getRealtimeNews(q: string, limit = 8) {
  return req(`/realtime/news?q=${encodeURIComponent(q)}&limit=${limit}`);
}
export function getRealtimeReddit(q: string, limit = 8) {
  return req(`/realtime/reddit?q=${encodeURIComponent(q)}&limit_each=${limit}`);
}
export function getRealtimeWeather(lat = 12.97, lon = 77.59, hours = 6) {
  return req(`/realtime/weather?lat=${lat}&lon=${lon}&hours=${hours}`);
}
export function eraseEvent(id: string) {
  return req(`/events/${encodeURIComponent(id)}`, { method: "DELETE" });
}
export function setLLMSettings(body: { mode: string; model?: string; api_key?: string }) {
  return req("/llm/settings", { method: "POST", body: JSON.stringify(body) });
}
export function probeLLMSettings(body: { mode: string; model?: string; api_key?: string }) {
  return req("/llm/probe", { method: "POST", body: JSON.stringify(body) });
}
export function searchOllamaLibrary(q: string) {
  return req(`/llm/search?q=${encodeURIComponent(q)}`);
}
export function pullOllamaModel(model: string) {
  return req("/llm/pull", { method: "POST", body: JSON.stringify({ model }) });
}
export function parseTokenRole(): string | null {
  if (!_token) return null;
  try {
    const payload = JSON.parse(atob(_token.split(".")[1]));
    return payload.role ?? null;
  } catch { return null; }
}
