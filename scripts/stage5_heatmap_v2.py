"""Stage 5: render enhanced heatmap with planner overlays + diversion lines."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.config import DATA_PROCESSED, ROOT
from src.viz.heatmap import render


def main() -> None:
    df = pd.read_csv(DATA_PROCESSED / "events_with_plan.csv")
    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    out = render(df, out_dir / "heatmap_v2.html", severity_threshold=0.3)
    print(f"wrote {out}  ({out.stat().st_size / 1024:.0f} KB)")
    print(f"open: file:///{out.as_posix()}")

    severe = df[df["severity_score"] >= 0.3]
    print(f"\nsevere events on map: {len(severe)}  (threshold=0.3)")
    print(f"top causes among severe:\n{severe['event_cause'].value_counts().head(8)}")
    print(f"\ntop corridors among severe:\n{severe['corridor'].value_counts().head(8)}")


if __name__ == "__main__":
    main()
