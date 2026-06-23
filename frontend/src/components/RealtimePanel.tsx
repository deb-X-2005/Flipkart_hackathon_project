import { useEffect, useState } from "react";
import * as api from "../api";

type News = { title: string; source: string; link: string };
type Reddit = { title: string; subreddit: string; link: string };

export function RealtimePanel({ query }: { query: string }) {
  const [news, setNews] = useState<News[]>([]);
  const [reddit, setReddit] = useState<Reddit[]>([]);
  const [temp, setTemp] = useState<[number, number] | null>(null);
  const [rain, setRain] = useState<number | null>(null);
  const [updated, setUpdated] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setError(null);
    const q = query.trim();
    if (!q) {
      setNews([]); setReddit([]); setTemp(null); setRain(null); setUpdated("");
      return;
    }
    try {
      const [n, r, w] = await Promise.all([
        api.getRealtimeNews(q, 4),
        api.getRealtimeReddit(q, 4),
        api.getRealtimeWeather(),
      ]);
      setNews(n.items?.slice(0, 4) ?? []);
      setReddit((r.items ?? []).slice(0, 4));
      const temps: number[] = w?.hourly?.temperature_2m ?? [];
      const rains: number[] = w?.hourly?.precipitation ?? [];
      if (temps.length) setTemp([Math.min(...temps), Math.max(...temps)]);
      if (rains.length) setRain(rains.reduce((a, b) => a + b, 0));
      setUpdated(new Date().toLocaleTimeString());
    } catch (e: any) { setError(e.message); }
  }

  useEffect(() => {
    const q = query.trim();
    if (!q) return;
    refresh();
    const t = setInterval(refresh, 60000);
    return () => clearInterval(t);
  }, [query]);

  const hasQuery = !!query.trim();

  return (
    <div className="section">
      <h3>Live signals <span className="muted" style={{ marginLeft: 6, fontWeight: 400 }}>{updated && `· ${updated}`}</span></h3>
      {error && <div className="err">{error}</div>}
      {!hasQuery ? (
        <div className="muted" style={{ fontStyle: "italic" }}>
          Type a query above to pull matching news, Reddit posts, and weather.
        </div>
      ) : (
        <>
          <div className="weather-strip">
            {temp ? <div className="chip">{temp[0].toFixed(0)}–{temp[1].toFixed(0)}°C</div> : <div className="chip">temp —</div>}
            {rain != null ? <div className="chip">{rain.toFixed(1)} mm rain (6h)</div> : <div className="chip">rain —</div>}
          </div>
          <div className="rt-block">
            <div className="rt-title">News</div>
            {news.length === 0 ? <div className="muted">No matches.</div> :
              news.map((n, i) => (
                <a className="rt-item" key={i} href={n.link} target="_blank" rel="noreferrer">
                  <span className="rt-src">{n.source || "news"}</span>
                  <span className="rt-headline">{n.title.slice(0, 80)}</span>
                </a>
              ))}
          </div>
          <div className="rt-block">
            <div className="rt-title">Reddit</div>
            {reddit.length === 0 ? <div className="muted">No matches.</div> :
              reddit.map((p, i) => (
                <a className="rt-item" key={i} href={p.link} target="_blank" rel="noreferrer">
                  <span className="rt-src">r/{p.subreddit}</span>
                  <span className="rt-headline">{p.title.slice(0, 80)}</span>
                </a>
              ))}
          </div>
        </>
      )}
    </div>
  );
}
