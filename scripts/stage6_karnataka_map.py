"""Stage 6: Karnataka-wide map + KPI metrics panel."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.config import DATA_PROCESSED, ROOT
from src.viz.heatmap import render, KARNATAKA


def _fmt(n: float) -> str:
    return f"{int(n):,}"


def main() -> None:
    df = pd.read_csv(DATA_PROCESSED / "events_with_plan.csv")
    severe = df[df["severity_score"] >= 0.3]

    metrics = {
        "Total events": _fmt(len(df)),
        "Severe (predicted)": f"{_fmt(len(severe))} ({len(severe)/len(df)*100:.1f}%)",
        "Expected crowd (sum)": _fmt(severe["expected_crowd"].sum()),
        "Barricades needed": _fmt(severe["barricades_needed"].sum()),
        "Officers needed": _fmt(severe["officers_needed"].sum()),
        "Top cause": severe["event_cause"].mode().iloc[0],
        "Top corridor": severe["corridor"].mode().iloc[0],
        "Time range": f"{df['start_datetime'].min()[:10]} - {df['start_datetime'].max()[:10]}",
    }
    subtitle = "Source: Astram dataset (Bengaluru Metropolitan Area). State-wide feeds added in Stage 7."

    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    out = render(
        df,
        out_dir / "heatmap_karnataka.html",
        center=KARNATAKA,
        zoom=7,
        severity_threshold=0.3,
        metrics=metrics,
        metrics_subtitle=subtitle,
    )
    print(f"wrote {out}  ({out.stat().st_size / 1024:.0f} KB)")
    print(f"open: file:///{out.as_posix()}")
    print("\nmetrics:")
    for k, v in metrics.items():
        print(f"  {k:24} {v}")


if __name__ == "__main__":
    main()
