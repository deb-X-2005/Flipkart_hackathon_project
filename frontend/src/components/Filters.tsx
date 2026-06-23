import { useEffect, useState } from "react";
import * as api from "../api";

export type FilterState = {
  cause: string;
  corridor: string;
  min_severity: number;
  from_date: string;
  to_date: string;
};

export const EMPTY_FILTERS: FilterState = {
  cause: "", corridor: "", min_severity: 0.1, from_date: "", to_date: "",
};

export function Filters({ value, onChange }: { value: FilterState; onChange: (f: FilterState) => void }) {
  const [facets, setFacets] = useState<{ causes: string[]; corridors: string[]; date_range: [string, string] } | null>(null);

  useEffect(() => { api.getFacets().then(setFacets).catch(() => {}); }, []);

  const set = (k: keyof FilterState, v: any) => onChange({ ...value, [k]: v });

  return (
    <div className="section">
      <h3>Filters</h3>
      <label className="lbl">Cause</label>
      <select value={value.cause} onChange={(e) => set("cause", e.target.value)}>
        <option value="">All causes</option>
        {facets?.causes.map((c) => <option key={c} value={c}>{c}</option>)}
      </select>
      <label className="lbl">Corridor</label>
      <select value={value.corridor} onChange={(e) => set("corridor", e.target.value)}>
        <option value="">All corridors</option>
        {facets?.corridors.map((c) => <option key={c} value={c}>{c}</option>)}
      </select>
      <label className="lbl">Min severity: {value.min_severity.toFixed(2)}</label>
      <input type="range" min={0} max={1} step={0.05}
             value={value.min_severity}
             onChange={(e) => set("min_severity", parseFloat(e.target.value))} />
      <div className="row2">
        <div>
          <label className="lbl">From</label>
          <input type="date" value={value.from_date}
                 min={facets?.date_range[0]} max={facets?.date_range[1]}
                 onChange={(e) => set("from_date", e.target.value)} />
        </div>
        <div>
          <label className="lbl">To</label>
          <input type="date" value={value.to_date}
                 min={facets?.date_range[0]} max={facets?.date_range[1]}
                 onChange={(e) => set("to_date", e.target.value)} />
        </div>
      </div>
      <button className="ghost" onClick={() => onChange(EMPTY_FILTERS)}>Reset</button>
    </div>
  );
}
