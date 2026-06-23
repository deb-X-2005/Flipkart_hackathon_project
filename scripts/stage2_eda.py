"""Stage 2 EDA: print key distributions, missingness, time/space coverage."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.config import DATA_PROCESSED


def section(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def main() -> None:
    df = pd.read_csv(DATA_PROCESSED / "events.csv", parse_dates=["start_datetime", "end_datetime"])
    print(f"rows: {len(df):,}  cols: {len(df.columns)}")

    section("time coverage")
    print(f"start min: {df['start_datetime'].min()}")
    print(f"start max: {df['start_datetime'].max()}")
    print(f"span (days): {(df['start_datetime'].max() - df['start_datetime'].min()).days}")

    section("event_type x event_cause")
    print(pd.crosstab(df["event_cause"], df["event_type"]).sort_values("unplanned", ascending=False).head(15))

    section("closure rate by cause")
    closure = df.groupby("event_cause")["requires_road_closure"].agg(["mean", "count"])
    closure = closure.sort_values("count", ascending=False).head(15)
    closure["mean"] = (closure["mean"] * 100).round(1).astype(str) + "%"
    print(closure)

    section("priority levels")
    print(df["priority"].value_counts(dropna=False).head(10))

    section("hour-of-day distribution")
    print(df["hour"].value_counts().sort_index())

    section("day-of-week distribution (0=Mon)")
    print(df["dow"].value_counts().sort_index())

    section("top zones / corridors / junctions")
    for col in ("zone", "corridor", "junction"):
        if col in df.columns:
            print(f"\n--- {col} top 10 ---")
            print(df[col].value_counts(dropna=False).head(10))

    section("missingness (top 15)")
    miss = (df.isna().mean() * 100).round(1).sort_values(ascending=False).head(15)
    print(miss.astype(str) + "%")

    section("geographic spread")
    print(f"lat range: {df['latitude'].min():.4f} -> {df['latitude'].max():.4f}")
    print(f"lon range: {df['longitude'].min():.4f} -> {df['longitude'].max():.4f}")
    print(f"valid coords: {df[['latitude', 'longitude']].dropna().shape[0]:,} / {len(df):,}")

    section("duration sanity")
    d = df["duration_min"].dropna()
    print(f"valid duration rows: {len(d):,}")
    if len(d):
        clipped = d.clip(lower=0, upper=60 * 24 * 7)  # clip negatives + cap at 1 week
        print(f"after clip [0, 1 week]: count={len(clipped)}  median={clipped.median():.1f}  mean={clipped.mean():.1f}")


if __name__ == "__main__":
    main()
