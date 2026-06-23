import { useEffect, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from "react-leaflet";

type Event = {
  id?: string;
  event_cause?: string;
  corridor?: string;
  latitude?: number;
  longitude?: number;
  severity_score?: number;
  closure_prob?: number;
  expected_crowd?: number;
  barricades_needed?: number;
  officers_needed?: number;
  diversion_corridor?: string;
  diversion_lat?: number;
  diversion_lon?: number;
  requires_road_closure?: boolean;
};

const KARNATAKA: [number, number] = [15.3173, 75.7139];

async function fetchRoute(token: string | null, a: [number, number], b: [number, number]) {
  const url = `/api/routing/diversion?from_lat=${a[0]}&from_lon=${a[1]}&to_lat=${b[0]}&to_lon=${b[1]}`;
  const r = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!r.ok) return null;
  return r.json();
}

export function MapView({ events, onSelect, themeMode = "dark" }: { events: Event[]; onSelect: (e: Event) => void; themeMode?: "dark" | "light" }) {
  const severe = events.filter((e) => (e.severity_score ?? 0) >= 0.3);
  const topSevere = severe.slice().sort((a, b) => (b.severity_score ?? 0) - (a.severity_score ?? 0)).slice(0, 25);
  const [routes, setRoutes] = useState<Record<string, [number, number][]>>({});

  useEffect(() => {
    const token = localStorage.getItem("token");
    let cancelled = false;
    (async () => {
      const next: Record<string, [number, number][]> = {};
      for (const e of topSevere) {
        if (!(e.latitude && e.longitude && e.diversion_lat && e.diversion_lon)) continue;
        const key = `${e.latitude},${e.longitude}->${e.diversion_lat},${e.diversion_lon}`;
        const r = await fetchRoute(token, [e.latitude, e.longitude], [e.diversion_lat, e.diversion_lon]);
        if (cancelled) return;
        if (r && r.coords) next[key] = r.coords as [number, number][];
      }
      if (!cancelled) setRoutes(next);
    })();
    return () => { cancelled = true; };
  }, [events]);

  return (
    <MapContainer center={KARNATAKA} zoom={7} style={{ height: "100%", width: "100%" }} preferCanvas>
      <TileLayer
        key={themeMode}
        url={themeMode === "light"
          ? "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          : "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"}
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
      />
      {events.map((e, i) => (
        e.latitude && e.longitude ? (
          <CircleMarker
            key={i}
            center={[e.latitude, e.longitude]}
            radius={Math.max(3, 3 + (e.severity_score ?? 0) * 10)}
            color={e.requires_road_closure ? "#cc3333" : "#3366cc"}
            fillOpacity={0.75} weight={1}
            eventHandlers={{ click: () => onSelect(e) }}
          >
            <Popup>
              <b>{e.event_cause ?? "?"}</b><br />
              {e.corridor ?? "—"}
              {e.severity_score != null && <><br />severity: {e.severity_score.toFixed(2)}</>}
            </Popup>
          </CircleMarker>
        ) : null
      ))}
      {topSevere.map((e, i) => {
        if (!(e.latitude && e.longitude && e.diversion_lat && e.diversion_lon)) return null;
        const key = `${e.latitude},${e.longitude}->${e.diversion_lat},${e.diversion_lon}`;
        const coords = routes[key] ?? [[e.latitude, e.longitude], [e.diversion_lat, e.diversion_lon]];
        return (
          <Polyline key={`d-${i}`} positions={coords}
            color="#22c55e" weight={3} opacity={0.6} dashArray={routes[key] ? undefined : "6 8"} />
        );
      })}
    </MapContainer>
  );
}
