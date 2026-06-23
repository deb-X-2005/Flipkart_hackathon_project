import { useCallback, useEffect, useMemo, useState } from "react";
import { MapView } from "./components/MapView";
import { MapLegend } from "./components/MapLegend";
import { Filters, EMPTY_FILTERS, FilterState } from "./components/Filters";
import { RealtimePanel } from "./components/RealtimePanel";
import { Emblem } from "./components/Emblem";
import { LLMSettings } from "./components/LLMSettings";
import * as api from "./api";
import { getTheme, setTheme as setThemePref, Theme } from "./theme";

type Metrics = {
  total_events: number; severe_events: number; severe_pct: number;
  expected_crowd_sum: number; barricades_needed_sum: number; officers_needed_sum: number;
  top_cause: string | null; top_corridor: string | null; time_range: [string, string];
};

type LLMInfo = {
  mode: string | null;
  default_model?: string;
  installed_models?: string[];
  ollama_running?: boolean;
  error?: string;
};

export default function App() {
  const [token, setToken] = useState<string | null>(api.getToken());
  const [role, setRole] = useState<string | null>(api.parseTokenRole());
  const [theme, setThemeState] = useState<Theme>(getTheme());
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [llm, setLlm] = useState<LLMInfo | null>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [selected, setSelected] = useState<any | null>(null);
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [briefing, setBriefing] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");
  const [loginUser, setLoginUser] = useState("");
  const [loginPass, setLoginPass] = useState("");
  const [signupRole, setSignupRole] = useState<"viewer" | "operator" | "admin">("operator");
  const [demoUsers, setDemoUsers] = useState<{ username: string; password: string; role: string }[]>([]);
  const [llmOpen, setLlmOpen] = useState(false);

  useEffect(() => {
    if (!token) api.getDemoUsers().then((r) => setDemoUsers(r.users ?? [])).catch(() => {});
  }, [token]);

  function toggleTheme() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setThemeState(next); setThemePref(next);
  }

  async function doAuth() {
    setError(null);
    try {
      const r = authMode === "login"
        ? await api.login(loginUser, loginPass)
        : await api.signup(loginUser, loginPass, signupRole);
      api.setToken(r.token);
      setToken(r.token);
      setRole(api.parseTokenRole());
      setLoginPass("");
    } catch (e: any) { setError(e.message); }
  }

  function autofill(u: { username: string; password: string }) {
    setAuthMode("login");
    setLoginUser(u.username);
    setLoginPass(u.password);
  }

  function doLogout() {
    api.setToken(null);
    setToken(null); setRole(null); setEvents([]); setMetrics(null); setBriefing(null);
  }

  const reloadEvents = useCallback(async () => {
    try {
      const e = await api.getEvents({ limit: 1500, ...filters });
      setEvents(e.items);
    } catch (e: any) { setError(e.message); }
  }, [filters]);

  async function loadStatic() {
    try {
      const [m, l] = await Promise.all([api.getMetrics(), api.getLLMInfo().catch(() => null)]);
      setMetrics(m); setLlm(l);
    } catch (e: any) { setError(e.message); }
  }

  async function runQuery() {
    setLoading(true); setError(null); setBriefing(null);
    try {
      const r = await api.chat(query);
      setBriefing(r);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }

  async function eraseSelected() {
    if (!selected?.id) return;
    if (!confirm(`Erase event ${selected.id}? This is permanent (GDPR Art 17).`)) return;
    try {
      await api.eraseEvent(selected.id);
      setSelected(null);
      reloadEvents();
    } catch (e: any) { setError(e.message); }
  }

  useEffect(() => { if (token) { loadStatic(); reloadEvents(); } }, [token, reloadEvents]);

  const llmBadge = useMemo(() => {
    if (!llm || !llm.mode) return "no llm";
    return llm.default_model ? `${llm.mode} · ${llm.default_model}` : llm.mode;
  }, [llm]);

  if (!token) {
    return (
      <div className="app">
        <header className="header">
          <h1>Karnataka Event Traffic<span className="sub">· Bengaluru Traffic Police</span></h1>
          <button className="ghost small" style={{ marginLeft: "auto" }} onClick={toggleTheme}>
            {theme === "dark" ? "☀ light" : "☾ dark"}
          </button>
        </header>
        <div className="login-shell">
          <div className="login-emblem"><Emblem size={420} opacity={0.12} /></div>
          <div className="login-card">
            <div className="login-tricolour" />
            <div className="crest">
              <Emblem size={56} opacity={0.95} />
              <div className="crest-text">
                <div className="top">Government of Karnataka</div>
                <div className="name">Bengaluru Traffic Police</div>
              </div>
            </div>
            <div className="auth-tabs">
              <button className={`tab ${authMode === "login" ? "active" : ""}`}
                      onClick={() => setAuthMode("login")}>Login</button>
              <button className={`tab ${authMode === "signup" ? "active" : ""}`}
                      onClick={() => setAuthMode("signup")}>Sign up</button>
            </div>

            <p className="hint">
              {authMode === "login"
                ? "Enter your credentials or click a demo account below."
                : "Pick a role and create an account. Password ≥ 8 characters."}
            </p>

            <label className="lbl">Username</label>
            <input value={loginUser} onChange={(e) => setLoginUser(e.target.value)}
                   placeholder={authMode === "login" ? "e.g. operator" : "choose a username"} autoComplete="username" />

            <label className="lbl">Password</label>
            <input type="password" value={loginPass} onChange={(e) => setLoginPass(e.target.value)}
                   placeholder={authMode === "login" ? "e.g. operator123" : "min 8 characters"}
                   onKeyDown={(e) => e.key === "Enter" && doAuth()} autoComplete={authMode === "login" ? "current-password" : "new-password"} />

            {authMode === "signup" && (
              <>
                <label className="lbl">Role</label>
                <select value={signupRole} onChange={(e) => setSignupRole(e.target.value as any)}>
                  <option value="operator">Operator — run forecasts (default)</option>
                  <option value="viewer">Viewer — read-only</option>
                  <option value="admin">Admin — full access + erasure + LLM settings</option>
                </select>
              </>
            )}

            <button onClick={doAuth}
                    disabled={!loginUser || !loginPass || (authMode === "signup" && loginPass.length < 8)}>
              {authMode === "login" ? "Login" : "Create account & sign in"}
            </button>
            {error && <div className="err">{error}</div>}

            {authMode === "login" && demoUsers.length > 0 && (
              <>
                <div className="modal-divider" style={{ marginTop: 18 }} />
                <div className="muted" style={{ marginBottom: 6 }}>Demo accounts — click to autofill:</div>
                <div className="demo-users">
                  {demoUsers.map((u) => (
                    <button key={u.username} className="ghost small demo-user-btn" onClick={() => autofill(u)}>
                      <b>{u.username}</b> <span className="muted">/ {u.password} · {u.role}</span>
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Karnataka Event Traffic<span className="sub">· BTP</span></h1>
        <span className={`badge ${role === "admin" ? "admin" : "active"}`}>role: {role}</span>
        <span className="badge llm" onClick={() => setLlmOpen(true)} style={{ cursor: "pointer" }} title="LLM settings">{llmBadge}</span>
        <span className="badge">{events.length} events</span>
        <span style={{ marginLeft: "auto" }} className="muted">
          {metrics ? `${metrics.time_range[0]} → ${metrics.time_range[1]}` : ""}
        </span>
        <button className="ghost small" onClick={toggleTheme}>
          {theme === "dark" ? "☀ light" : "☾ dark"}
        </button>
        <button className="ghost small" onClick={doLogout}>logout</button>
      </header>

      <div className="body">
        <aside className="sidebar">
          <div className="section">
            <h3>Natural-language query</h3>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Tree fell on Bellary Road this morning blocking one lane"
            />
            <button onClick={runQuery} disabled={loading || !query.trim() || role === "viewer"}>
              {loading ? "Thinking… (10-30 s on first call)" : "Forecast & brief"}
            </button>
            {role === "viewer" && <div className="muted" style={{ marginTop: 4 }}>Sign in as operator to run forecasts.</div>}
            {error && <div className="err">{error}</div>}
          </div>

          <Filters value={filters} onChange={setFilters} />

          {metrics && (
            <div className="section">
              <h3>State metrics</h3>
              <div className="metric-strip" style={{ gridTemplateColumns: "1fr 1fr" }}>
                <div className="metric"><div className="label">Events</div><div className="value">{metrics.total_events.toLocaleString()}</div></div>
                <div className="metric"><div className="label">Severe</div><div className="value">{metrics.severe_events} <span className="muted">({metrics.severe_pct}%)</span></div></div>
                <div className="metric"><div className="label">Crowd</div><div className="value">{metrics.expected_crowd_sum.toLocaleString()}</div></div>
                <div className="metric"><div className="label">Officers</div><div className="value">{metrics.officers_needed_sum.toLocaleString()}</div></div>
              </div>
              <div className="kv"><span className="k">Top cause</span><span className="v">{metrics.top_cause}</span></div>
              <div className="kv"><span className="k">Top corridor</span><span className="v">{metrics.top_corridor}</span></div>
            </div>
          )}
        </aside>

        <main className="map-wrap">
          <MapView events={events} onSelect={setSelected} themeMode={theme} />
          <MapLegend />
        </main>

        <aside className="plan-panel">
          <RealtimePanel query={query} />

          {briefing ? (
            <>
              <div className="section">
                <h3>Extracted attributes</h3>
                {Object.entries(briefing.extracted).map(([k, v]) => (
                  <div key={k} className="kv"><span className="k">{k}</span><span className="v">{String(v)}</span></div>
                ))}
              </div>
              <div className="section">
                <h3>Forecast & plan</h3>
                <div className="kv"><span className="k">Closure prob</span><span className="v">{(briefing.forecast.closure_prob * 100).toFixed(0)}%</span></div>
                <div className="kv"><span className="k">Severity</span><span className="v">{briefing.plan.severity_score}</span></div>
                <div className="kv"><span className="k">Crowd</span><span className="v">{briefing.plan.expected_crowd.toLocaleString()}</span></div>
                <div className="kv"><span className="k">Officers</span><span className="v">{briefing.plan.officers_needed}</span></div>
                <div className="kv"><span className="k">Barricades</span><span className="v">{briefing.plan.barricades_needed}</span></div>
                <div className="kv"><span className="k">Divert to</span><span className="v">{briefing.plan.diversion_corridor ?? "—"}</span></div>
              </div>
              <div className="section">
                <h3>Officer briefing</h3>
                <div className="briefing">{briefing.briefing}</div>
              </div>
            </>
          ) : selected ? (
            <>
              <div className="section">
                <h3>Selected event</h3>
                {Object.entries(selected).slice(0, 12).map(([k, v]) => v != null && (
                  <div key={k} className="kv"><span className="k">{k}</span><span className="v">{String(v).slice(0, 40)}</span></div>
                ))}
                {role === "admin" && selected.id && (
                  <button className="danger" onClick={eraseSelected} style={{ marginTop: 10 }}>
                    Erase event (GDPR Art 17)
                  </button>
                )}
              </div>
            </>
          ) : null}
        </aside>
      </div>

      <LLMSettings
        open={llmOpen}
        onClose={() => setLlmOpen(false)}
        isAdmin={role === "admin"}
        onUpdated={loadStatic}
      />
    </div>
  );
}
