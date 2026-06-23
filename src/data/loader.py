"""Load Astram event dataset."""
from pathlib import Path
import pandas as pd

from src.config import ASTRAM_PATH


def load_astram(path: Path | None = None) -> pd.DataFrame:
    p = Path(path) if path else ASTRAM_PATH
    if not p.exists():
        raise FileNotFoundError(f"Astram dataset not found at {p}")
    return pd.read_excel(p)
