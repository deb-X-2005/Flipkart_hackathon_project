import { useEffect, useState } from "react";
import * as api from "../api";

type Props = { open: boolean; onClose: () => void; isAdmin: boolean; onUpdated: () => void };

const CLOUD_MODELS: Record<string, string[]> = {
  openai: ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "o4-mini"],
  anthropic: ["claude-haiku-4-5", "claude-sonnet-4-6", "claude-opus-4-7"],
  openrouter: [
    "anthropic/claude-sonnet-4.5",
    "openai/gpt-4o",
    "meta-llama/llama-3.3-70b-instruct",
    "qwen/qwen-2.5-72b-instruct",
    "mistralai/mixtral-8x22b-instruct",
  ],
};

export function LLMSettings({ open, onClose, isAdmin, onUpdated }: Props) {
  const [mode, setMode] = useState<string>("ollama");
  const [model, setModel] = useState<string>("");
  const [apiKey, setApiKey] = useState<string>("");
  const [installedOllama, setInstalledOllama] = useState<string[]>([]);
  const [searchQ, setSearchQ] = useState<string>("");
  const [searchHits, setSearchHits] = useState<{ name: string; description: string }[]>([]);
  const [pulling, setPulling] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [probe, setProbe] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    if (!open) return;
    api.getLLMInfo().then((i) => {
      setMode(i.mode ?? "ollama");
      setModel(i.default_model ?? "");
      if (i.installed_models) setInstalledOllama(i.installed_models);
    }).catch(() => {});
  }, [open]);

  async function doSave() {
    setBusy(true); setError(null); setMsg(null); setProbe(null);
    try {
      await api.setLLMSettings({ mode, model: model || undefined, api_key: apiKey || undefined });
      setMsg("Saved. Future queries use this backend.");
      setApiKey("");
      onUpdated();
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function doProbe() {
    setBusy(true); setError(null); setMsg(null); setProbe(null);
    try {
      const r = await api.probeLLMSettings({ mode, model: model || undefined, api_key: apiKey || undefined });
      if (r.ok) {
        setProbe({ ok: true, text: `OK · sample reply: ${(r.sample_response || "").slice(0, 100)}` });
      } else {
        setProbe({ ok: false, text: `${r.error_type}: ${r.error}` });
      }
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function doSearch() {
    setBusy(true); setError(null);
    try {
      const r = await api.searchOllamaLibrary(searchQ);
      setSearchHits(r.items ?? []);
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function doPull(name: string) {
    setPulling(name); setError(null); setMsg(null);
    try {
      await api.pullOllamaModel(name);
      setMsg(`pulled ${name}`);
      const info = await api.getLLMInfo();
      if (info.installed_models) setInstalledOllama(info.installed_models);
    } catch (e: any) { setError(e.message); }
    finally { setPulling(null); }
  }

  if (!open) return null;

  const cloud = mode !== "ollama";
  const modelOpts = mode === "ollama" ? installedOllama : (CLOUD_MODELS[mode] ?? []);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>LLM Settings</h3>
          <button className="ghost small" onClick={onClose}>close</button>
        </div>
        {!isAdmin && <div className="muted">Read-only — sign in as admin to change.</div>}

        <label className="lbl">Backend</label>
        <select value={mode} onChange={(e) => { setMode(e.target.value); setModel(""); }}
                disabled={!isAdmin}>
          <option value="ollama">Ollama (local, free)</option>
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic Claude</option>
          <option value="openrouter">OpenRouter</option>
        </select>

        <label className="lbl">Model</label>
        {modelOpts.length > 0 ? (
          <select value={model} onChange={(e) => setModel(e.target.value)} disabled={!isAdmin}>
            <option value="">(default)</option>
            {modelOpts.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        ) : (
          <input value={model} onChange={(e) => setModel(e.target.value)}
                 placeholder={mode === "ollama" ? "llama3.2:3b" : "model name"}
                 disabled={!isAdmin} />
        )}

        {cloud && (
          <>
            <label className="lbl">API Key (not stored on disk, only in process memory)</label>
            <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                   placeholder="sk-..." disabled={!isAdmin} />
          </>
        )}

        <div className="row2" style={{ gridTemplateColumns: "1fr 1fr", marginTop: 8, gap: 8 }}>
          <button className="ghost" onClick={doProbe} disabled={busy || !isAdmin} style={{ marginTop: 0 }}>
            Test key
          </button>
          <button onClick={doSave} disabled={busy || !isAdmin} style={{ marginTop: 0 }}>
            Save settings
          </button>
        </div>
        {probe && (
          <div className={probe.ok ? "muted" : "err"} style={{ marginTop: 8, wordBreak: "break-word" }}>
            {probe.ok ? "✅ " : "❌ "}{probe.text}
          </div>
        )}

        {mode === "ollama" && (
          <>
            <div className="modal-divider" />
            <label className="lbl">Search Ollama library (then click pull)</label>
            <div className="row2" style={{ gridTemplateColumns: "1fr auto" }}>
              <input value={searchQ} onChange={(e) => setSearchQ(e.target.value)} placeholder="llama" />
              <button onClick={doSearch} disabled={busy} style={{ width: "auto", padding: "8px 14px" }}>Search</button>
            </div>
            <div className="search-list">
              {searchHits.map((h) => {
                const installed = installedOllama.some((m) => m.startsWith(h.name.split(":")[0]));
                return (
                  <div key={h.name} className="search-row">
                    <div>
                      <div className="search-name">{h.name} {installed && <span className="muted">· installed</span>}</div>
                      <div className="muted" style={{ fontSize: 11 }}>{h.description.slice(0, 80)}</div>
                    </div>
                    <button className="ghost small"
                            onClick={() => doPull(h.name)}
                            disabled={!isAdmin || pulling === h.name}
                            style={{ width: "auto", marginTop: 0 }}>
                      {pulling === h.name ? "pulling…" : "pull"}
                    </button>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {msg && <div className="muted" style={{ marginTop: 8 }}>{msg}</div>}
        {error && <div className="err">{error}</div>}
      </div>
    </div>
  );
}
