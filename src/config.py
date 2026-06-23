"""Central config: env vars + paths."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"

ASTRAM_PATH = Path(os.getenv("ASTRAM_DATA_PATH", DATA_RAW / "astram.xlsx"))
LLM_MODE = os.getenv("LLM_MODE", "openai")
