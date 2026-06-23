"""Ollama admin CLI: list, search, pull.

Usage:
  python scripts/ollama_admin.py list
  python scripts/ollama_admin.py search llama
  python scripts/ollama_admin.py pull llama3.2:3b
"""
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.llm import ollama


def cmd_list() -> None:
    if not ollama.health():
        print("ollama not running — start it with: ollama serve")
        return
    models = ollama.list_local()
    if not models:
        print("no local models. pull one e.g.:  python scripts/ollama_admin.py pull llama3.2:3b")
        return
    print(f"{'NAME':30}  {'SIZE (GB)':>10}  PARAMS  QUANT")
    for m in models:
        size_gb = m.get("size", 0) / 1024**3
        d = m.get("details", {})
        print(f"{m.get('name',''):30}  {size_gb:>10.2f}  {d.get('parameter_size','-'):>6}  {d.get('quantization_level','-')}")


def cmd_search(query: str) -> None:
    hits = ollama.search_library(query, limit=20)
    if not hits:
        print(f"no models found matching {query!r}")
        return
    print(f"{'NAME':28}  DESCRIPTION")
    for h in hits:
        print(f"  {h['name']:28}  {h['description'][:80]}")


def cmd_pull(name: str) -> None:
    if not ollama.health():
        print("ollama not running. start: ollama serve")
        return
    print(f"pulling {name} ...")
    last_status = None
    for evt in ollama.pull(name):
        status = evt.get("status", "")
        if status != last_status:
            print(f"  {status}")
            last_status = status
        if evt.get("completed") and evt.get("total"):
            pct = 100 * evt["completed"] / evt["total"]
            print(f"    {pct:5.1f}%  ({evt['completed']/1024**2:.1f} / {evt['total']/1024**2:.1f} MB)", end="\r")
    print(f"\ndone. {name} is ready.")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, *args = sys.argv[1:]
    if cmd == "list":
        cmd_list()
    elif cmd == "search":
        cmd_search(args[0] if args else "")
    elif cmd == "pull" and args:
        cmd_pull(args[0])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
