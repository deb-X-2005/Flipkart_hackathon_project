"""Folium heatmap + plan overlays."""
from pathlib import Path
import folium
from folium.plugins import HeatMap, MarkerCluster

BANGALORE = (12.9716, 77.5946)
KARNATAKA = (15.3173, 75.7139)


def _metrics_panel_html(metrics: dict, subtitle: str = "") -> str:
    rows = "\n".join(
        f'<div class="row"><span class="k">{k}</span><span class="v">{v}</span></div>'
        for k, v in metrics.items()
    )
    sub = f'<div class="sub">{subtitle}</div>' if subtitle else ""
    return f"""
    <style>
      #metrics-panel {{
        position: fixed; top: 12px; left: 60px; z-index: 9999;
        background: rgba(255,255,255,0.94); border: 1px solid #d0d0d0;
        border-radius: 8px; padding: 12px 16px; min-width: 260px;
        font-family: -apple-system, system-ui, "Segoe UI", sans-serif; font-size: 13px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.12); color:#222;
      }}
      #metrics-panel .title {{ font-weight:600; font-size:14px; margin-bottom:4px; }}
      #metrics-panel .sub   {{ font-size:11px; color:#666; margin-bottom:8px; }}
      #metrics-panel .row   {{ display:flex; justify-content:space-between; padding:3px 0; }}
      #metrics-panel .k     {{ color:#555; }}
      #metrics-panel .v     {{ font-weight:600; color:#111; }}
    </style>
    <div id="metrics-panel">
      <div class="title">Karnataka — Event Metrics</div>
      {sub}
      {rows}
    </div>
    """


def _popup(r) -> str:
    bits = [
        f"<b>{r.get('event_cause', '?')}</b>",
        f"type: {r.get('event_type', '?')}",
        f"corridor: {r.get('corridor', '?')}",
        f"start: {r.get('start_datetime', '')}",
    ]
    if "closure_prob" in r:
        bits += [
            f"<hr style='margin:4px 0'>",
            f"<b>Predicted plan</b>",
            f"closure prob: {r['closure_prob']:.2f}",
            f"expected crowd: {int(r.get('expected_crowd', 0))}",
            f"barricades: {int(r.get('barricades_needed', 0))}",
            f"officers: {int(r.get('officers_needed', 0))}",
            f"severity: {r.get('severity_score', 0):.2f}",
            f"divert to: <b>{r.get('diversion_corridor', '-')}</b>",
        ]
    return "<br>".join(bits)


def render(
    df,
    out_path: Path | str,
    severity_threshold: float = 0.3,
    center: tuple[float, float] = BANGALORE,
    zoom: int = 11,
    metrics: dict | None = None,
    metrics_subtitle: str = "",
) -> Path:
    out = Path(out_path)
    pts = df.dropna(subset=["latitude", "longitude"]).copy()
    has_plan = "severity_score" in pts.columns

    m = folium.Map(location=center, zoom_start=zoom, tiles="cartodbpositron")

    weights = pts.get("severity_score", 1.0) if has_plan else [1.0] * len(pts)
    heat_data = [[r.latitude, r.longitude, float(w)] for r, w in zip(pts.itertuples(), weights)]
    HeatMap(heat_data, name="Heat (severity-weighted)" if has_plan else "Heat",
            radius=14, blur=20, min_opacity=0.25).add_to(m)

    cluster = MarkerCluster(name="All events").add_to(m)
    for r in pts.head(2000).itertuples():
        color = "#cc3333" if getattr(r, "requires_road_closure", False) else "#3366cc"
        folium.CircleMarker((r.latitude, r.longitude), radius=3, color=color,
                            fill=True, popup=_popup(r._asdict())).add_to(cluster)

    if has_plan:
        severe = pts[pts["severity_score"] >= severity_threshold]
        severe_layer = folium.FeatureGroup(name=f"Severe (>= {severity_threshold})")
        divert_layer = folium.FeatureGroup(name="Diversion routes")
        for r in severe.itertuples():
            radius = 6 + min(int(getattr(r, "expected_crowd", 0)) / 200, 14)
            folium.CircleMarker(
                (r.latitude, r.longitude),
                radius=radius,
                color="#b30000",
                fill=True, fill_opacity=0.75,
                weight=1,
                popup=_popup(r._asdict()),
            ).add_to(severe_layer)
            dlat, dlon = getattr(r, "diversion_lat", None), getattr(r, "diversion_lon", None)
            if dlat and dlon:
                folium.PolyLine(
                    [(r.latitude, r.longitude), (dlat, dlon)],
                    color="#006400", weight=2, opacity=0.6, dash_array="6,8",
                    popup=f"divert {r.corridor} -> {r.diversion_corridor}",
                ).add_to(divert_layer)
        severe_layer.add_to(m)
        divert_layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    if metrics:
        m.get_root().html.add_child(folium.Element(_metrics_panel_html(metrics, metrics_subtitle)))
    m.save(str(out))
    return out
