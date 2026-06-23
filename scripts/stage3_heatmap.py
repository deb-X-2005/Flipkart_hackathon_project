"""Stage 3: render heatmap of all events to reports/heatmap.html."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from src.config import DATA_PROCESSED, ROOT
from src.viz.heatmap import render


def main() -> None:
    df = pd.read_csv(DATA_PROCESSED / "events.csv")
    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    out = render(df, out_dir / "heatmap.html")
    print(f"wrote {out}  ({out.stat().st_size / 1024:.0f} KB)")
    print(f"open: file:///{out.as_posix()}")


if __name__ == "__main__":
    main()
