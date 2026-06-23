# Event-Driven Traffic Congestion Forecasting

Predicts event-driven traffic impact for Karnataka (Bengaluru data shipped). Wires together:
- **CatBoost** classifier predicting road-closure probability per event
- **Rule-based planner** for officers / barricades / crowd / diversion target
- **FAISS RAG** over 8k historical events + scraped Reddit/News
- **Real-time feeds** (Open-Meteo, GDELT, Google News RSS, Reddit RSS)
- **Ollama-default LLM** (auto-detect, with OpenAI / Anthropic / OpenRouter fallbacks)
- **MCP server** exposing every tool to AI agents (stdio + HTTP, dual-auth)
- **FastAPI + React + Leaflet** dashboard
- **Full ISO 27001 + GDPR scaffolding**: PII strip, audit log, JWT auth, classification, encryption, right-to-erasure

## Quick start (Docker)

```bash
# 1. Create .env from .env.example, then generate secrets
python -c "import secrets; print('AUTH_SECRET=' + secrets.token_urlsafe(48))" >> .env
python -c "from cryptography.fernet import Fernet; print('CRYPTO_KEY=' + Fernet.generate_key().decode())" >> .env

# 2. (Assumes Ollama running on host with a model pulled)
docker compose up --build
```

Open **http://localhost:5173** → click "Sign in as operator" → run a query.

To bundle Ollama in the container too:
```bash
docker compose --profile bundled up --build
docker exec -it event-traffic-ollama ollama pull qwen3:1.7b
```

## Quick start (local dev)

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

# Stage 1-9 (one-time data prep)
python scripts/stage1_inspect.py        # clean + write events.csv
python scripts/stage4_model.py          # train CatBoost
python scripts/stage4c_plan.py          # score + plan every event
python scripts/stage5_heatmap_v2.py     # heatmap
python scripts/stage6_karnataka_map.py  # Karnataka view + metrics
python scripts/stage9_build_rag.py      # FAISS index

# Run
uvicorn src.api.main:app --reload --port 8000   # backend
cd frontend && npm install && npm run dev       # frontend (port 5173)
```

## Layout

```
src/
  config.py            env + paths
  data/                load, clean, cache, sources/{weather,news,reddit,gdelt,datagov}
  rag/                 embeddings, FAISS vector store, retriever
  models/forecast.py   CatBoost prepare/train/load
  agents/              orchestrator + planner
  llm/                 run_llm() with mode switch (ollama|openai|anthropic|openrouter)
  viz/heatmap.py       Folium maps + metrics overlays
  api/                 FastAPI app + Pydantic schemas
  mcp_server/          MCP server exposing 9 tools (stdio + HTTP transports)
  security/            pii, audit, auth, crypto, classify, retention, erasure

scripts/               numbered stage scripts + admin CLIs
tests/                 pytest suite (42 tests, ~20 s)
frontend/              Vite + React + Leaflet dashboard
data/{raw,processed,rag}/
models/                trained CatBoost artifact
logs/                  audit-YYYY-MM-DD.jsonl
```

## MCP server

```bash
python -m src.mcp_server.server                       # stdio (Claude Desktop)
MCP_TRANSPORT=http python -m src.mcp_server.server    # streamable HTTP on :8765
```

Issue a token for an AI agent:
```bash
python scripts/issue_mcp_token.py my-agent --scopes forecast,plan,rag
```

Drop the `mcpServers` block from `mcp_config.json` into Claude Desktop's config.

## Security

See `SECURITY.md` (controls), `DPIA.md` (data protection impact assessment), `RUNBOOK.md` (operational procedures).

## Testing

```bash
pytest -q                       # 42 tests, ~20 seconds
ruff check src/ tests/          # lint
```

## License

Internal hackathon project.
