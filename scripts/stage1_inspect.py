"""Stage 1 CLI: load Astram, clean, featurize, save processed parquet, print summary."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DATA_PROCESSED
from src.data.loader import load_astram
from src.data.preprocess import clean, featurize


def main() -> None:
    df = load_astram()
    print(f"raw shape: {df.shape}")
    print(f"raw columns: {list(df.columns)}")

    df = featurize(clean(df))
    print(f"\nclean shape: {df.shape}")
    print(f"clean dtypes:\n{df.dtypes}")

    for col in ("event_type", "event_cause"):
        if col in df.columns:
            print(f"\n{col} value counts:\n{df[col].value_counts(dropna=False).head(10)}")

    if "duration_min" in df.columns:
        print(f"\nduration_min summary:\n{df['duration_min'].describe()}")

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    out = DATA_PROCESSED / "events.csv"
    df.to_csv(out, index=False)
    print(f"\nwrote {out} ({out.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
