"""Stage 4c: score every event with CatBoost + run planner. Save enriched CSV."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from tqdm import tqdm

from src.config import DATA_PROCESSED, ROOT
from src.models.forecast import prepare, load, CAT_COLS
from src.agents.planner_agent import plan, corridor_centroids, nearest_diversion


def main() -> None:
    df = pd.read_csv(DATA_PROCESSED / "events.csv")
    df = df.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)

    model = load(ROOT / "models" / "closure_clf.cbm")
    X, _ = prepare(df.assign(requires_road_closure=df.get("requires_road_closure", False).fillna(False)))
    probs = model.predict_proba(X)[:, 1]

    centroids = corridor_centroids(df)
    plans, divs = [], []
    for i, p in enumerate(tqdm(probs, desc="planning")):
        ev = df.iloc[i].to_dict()
        plans.append(plan(ev, p))
        divs.append(nearest_diversion(ev, centroids))

    enriched = pd.concat(
        [df.reset_index(drop=True), pd.DataFrame(plans), pd.DataFrame(divs)], axis=1
    )
    out = DATA_PROCESSED / "events_with_plan.csv"
    enriched.to_csv(out, index=False)
    print(f"\nwrote {out}  ({out.stat().st_size / 1024:.0f} KB)")

    print("\nseverity_score summary:")
    print(enriched["severity_score"].describe().round(3))
    print("\ntop 5 most severe events:")
    cols = ["event_cause", "corridor", "closure_prob", "expected_crowd",
            "barricades_needed", "officers_needed", "severity_score", "diversion_corridor"]
    print(enriched.nlargest(5, "severity_score")[cols].to_string(index=False))


if __name__ == "__main__":
    main()
