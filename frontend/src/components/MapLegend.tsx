/** Legend overlay on the map. Explains symbols, colors, sizes. */
export function MapLegend() {
  return (
    <div className="map-legend">
      <div className="legend-title">Legend</div>

      <div className="legend-row">
        <span className="dot dot-red" />
        <span className="legend-text">Event required road closure</span>
      </div>
      <div className="legend-row">
        <span className="dot dot-blue" />
        <span className="legend-text">Event did not close road</span>
      </div>

      <div className="legend-divider" />

      <div className="legend-row">
        <span className="dot dot-severity-low" />
        <span className="dot dot-severity-mid" />
        <span className="dot dot-severity-high" />
        <span className="legend-text">Size = predicted severity (low → high)</span>
      </div>

      <div className="legend-divider" />

      <div className="legend-row">
        <span className="line line-route" />
        <span className="legend-text">Diversion route (OSRM)</span>
      </div>
      <div className="legend-row">
        <span className="line line-fallback" />
        <span className="legend-text">Diversion (straight-line fallback)</span>
      </div>
    </div>
  );
}
